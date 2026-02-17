"""Parse ralph loop script stdout for structured data.

Matches output from:
- portable/ralph-loop.ps1 (iteration markers, timestamps, completion)
- PROMPT_build.md RALPH_CONTROL block (status, files_changed)
- PROMPT_plan.md progress updates
"""
import json
import re
from dataclasses import dataclass
from typing import Optional


# Regex patterns matching actual script output
ITERATION_PATTERN = re.compile(r"=+ ITERATION (\d+) =+")
TIMESTAMP_PATTERN = re.compile(r"Started: (\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
ITERATION_COMPLETE = re.compile(r"\[.*?\] ITERATION (\d+) complete")
LOOP_FINISHED = re.compile(r"Loop finished after (\d+) iteration\(s\)")
MAX_REACHED = re.compile(r"Reached max iterations: (\d+)")
ALL_PHASES = re.compile(r"All phases complete")
RALPH_CONTROL_HEADER = re.compile(r"#\s*RALPH_CONTROL")
KV_LINE = re.compile(r"^(\w[\w_]*):\s*(.+)$")


@dataclass
class ParsedEvent:
    """A structured event parsed from script output."""
    event_type: str    # "iteration_start", "iteration_complete", "ralph_control",
                       # "loop_finished", "all_phases_complete", "raw"
    data: dict


class OutputParser:
    """Stateful parser that tracks multi-line RALPH_CONTROL blocks."""

    def __init__(self):
        self._in_ralph_control = False
        self._ralph_buffer: dict = {}

    def parse_line(self, line: str) -> list[ParsedEvent]:
        """Parse a single output line. May return 0 or more events."""
        events = []
        stripped = line.strip()

        # Check for RALPH_CONTROL block start
        if RALPH_CONTROL_HEADER.match(stripped):
            self._in_ralph_control = True
            self._ralph_buffer = {}
            return events

        # Inside RALPH_CONTROL block - collect key: value pairs
        if self._in_ralph_control:
            kv = KV_LINE.match(stripped)
            if kv:
                self._ralph_buffer[kv.group(1).lower()] = kv.group(2).strip()
                return events
            elif stripped == "" or stripped.startswith("```"):
                # End of block
                if self._ralph_buffer:
                    events.append(ParsedEvent("ralph_control", dict(self._ralph_buffer)))
                self._in_ralph_control = False
                self._ralph_buffer = {}
                return events

        # Iteration start
        m = ITERATION_PATTERN.search(line)
        if m:
            events.append(ParsedEvent("iteration_start", {"iteration": int(m.group(1))}))
            return events

        # Timestamp
        m = TIMESTAMP_PATTERN.search(line)
        if m:
            events.append(ParsedEvent("timestamp", {"time": m.group(1)}))
            return events

        # Iteration complete
        m = ITERATION_COMPLETE.search(line)
        if m:
            events.append(ParsedEvent("iteration_complete", {"iteration": int(m.group(1))}))
            return events

        # Loop finished
        m = LOOP_FINISHED.search(line)
        if m:
            events.append(ParsedEvent("loop_finished", {"total_iterations": int(m.group(1))}))
            return events

        # Max iterations reached
        m = MAX_REACHED.search(line)
        if m:
            events.append(ParsedEvent("max_reached", {"max": int(m.group(1))}))
            return events

        # All phases complete
        if ALL_PHASES.search(line):
            events.append(ParsedEvent("all_phases_complete", {}))
            return events

        return events


def parse_stream_json_activity(
    lines: list[str],
) -> tuple[list[str], Optional[int]]:
    """Parse stream-json output lines into human-readable activity entries.

    Extracts assistant text, tool calls, and iteration markers from
    Claude's ``--output-format=stream-json`` output.

    Returns ``(activity_lines, current_iteration)``.
    """
    activity: list[str] = []
    current_iteration: Optional[int] = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # Non-JSON iteration markers from the loop script
        m = ITERATION_PATTERN.search(line)
        if m:
            current_iteration = int(m.group(1))
            activity.append(line)
            continue
        m = ITERATION_COMPLETE.search(line)
        if m:
            current_iteration = int(m.group(1))
            activity.append(line)
            continue
        m = LOOP_FINISHED.search(line)
        if m:
            activity.append(line)
            continue
        m = MAX_REACHED.search(line)
        if m:
            activity.append(line)
            continue
        m = TIMESTAMP_PATTERN.search(line)
        if m:
            activity.append(line)
            continue

        # Try parsing as JSON (stream-json output)
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        msg_type = obj.get("type")

        if msg_type == "assistant":
            content_blocks = obj.get("message", {}).get("content", [])
            for block in content_blocks:
                btype = block.get("type")
                if btype == "text":
                    text = block.get("text", "").strip()
                    if text:
                        # Truncate long text to keep the log readable
                        if len(text) > 200:
                            text = text[:200] + "..."
                        activity.append(text)
                elif btype == "tool_use":
                    name = block.get("name", "unknown")
                    inp = block.get("input", {})
                    detail = _tool_summary(name, inp)
                    activity.append(f"> Tool: {name}{detail}")

        elif msg_type == "result":
            subtype = obj.get("subtype", "")
            turns = obj.get("num_turns", "?")
            cost = obj.get("total_cost_usd")
            cost_str = f", cost=${cost:.2f}" if isinstance(cost, (int, float)) else ""
            activity.append(f"Finished ({subtype}, {turns} turns{cost_str})")

    return activity, current_iteration


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


# Patterns for OpenCode plaintext output
_TOOL_READ = re.compile(r'^→\s*Read\s+(.+)')
_TOOL_WRITE = re.compile(r'^←\s*Write\s+(.+)')
_TOOL_EDIT = re.compile(r'^←\s*Edit\s+(.+)')
_TOOL_COMMAND = re.compile(r'^\$\s+(.+)')

# Lines to skip in plaintext output (boilerplate / PowerShell noise)
_PLAINTEXT_SKIP = re.compile(
    r'^(Write-Host|if\s*\(|else\s*\{|\}|param\s*\(|\[string\]|'
    r'Set-|Get-|\$\w+\s*=|\s*\[0m\s*$)',
    re.IGNORECASE,
)


def parse_plaintext_activity(
    lines: list[str],
) -> tuple[list[str], Optional[int]]:
    """Parse plaintext output (e.g. OpenCode) into human-readable activity entries.

    Handles ANSI-coded output with arrow-prefixed tool calls and plain
    assistant text.  Returns ``(activity_lines, current_iteration)``.
    """
    activity: list[str] = []
    current_iteration: Optional[int] = None

    for raw in lines:
        line = strip_ansi(raw).strip()
        if not line:
            continue

        # Iteration markers (shared with stream-json parser)
        m = ITERATION_PATTERN.search(line)
        if m:
            current_iteration = int(m.group(1))
            activity.append(line)
            continue
        m = ITERATION_COMPLETE.search(line)
        if m:
            current_iteration = int(m.group(1))
            activity.append(line)
            continue
        m = LOOP_FINISHED.search(line)
        if m:
            activity.append(line)
            continue
        m = MAX_REACHED.search(line)
        if m:
            activity.append(line)
            continue
        m = TIMESTAMP_PATTERN.search(line)
        if m:
            activity.append(line)
            continue

        # Tool reads: → Read path
        m = _TOOL_READ.match(line)
        if m:
            activity.append(f"> Read {m.group(1).strip()}")
            continue

        # Tool writes: ← Write path
        m = _TOOL_WRITE.match(line)
        if m:
            activity.append(f"> Wrote {m.group(1).strip()}")
            continue

        # Tool edits: ← Edit path
        m = _TOOL_EDIT.match(line)
        if m:
            activity.append(f"> Edit {m.group(1).strip()}")
            continue

        # Shell commands: $ ls -la
        m = _TOOL_COMMAND.match(line)
        if m:
            cmd = m.group(1).strip()
            if len(cmd) > 200:
                cmd = cmd[:200] + "..."
            activity.append(f"> $ {cmd}")
            continue

        # Skip boilerplate / PowerShell noise
        if _PLAINTEXT_SKIP.match(line):
            continue

        # Preserve assistant text (truncate long lines)
        if len(line) > 200:
            line = line[:200] + "..."
        activity.append(line)

    return activity, current_iteration


def _tool_summary(name: str, inp: dict) -> str:
    """Return a brief description suffix for a tool call."""
    if not inp:
        return ""
    # Common tool patterns
    if name in ("Read", "Write", "Edit"):
        path = inp.get("file_path", "")
        if path:
            # Show just the filename
            parts = path.replace("\\", "/").rsplit("/", 1)
            return f"  {parts[-1]}"
    if name == "Bash":
        cmd = inp.get("command", "")
        if cmd:
            return f"  {cmd[:80]}"
    if name == "Grep":
        pattern = inp.get("pattern", "")
        return f'  "{pattern[:60]}"' if pattern else ""
    if name == "Glob":
        pattern = inp.get("pattern", "")
        return f"  {pattern[:60]}" if pattern else ""
    if name == "Task":
        desc = inp.get("description", "")
        return f"  {desc[:60]}" if desc else ""
    # Serena tools
    if "find_symbol" in name:
        return f"  {inp.get('name_path_pattern', '')[:60]}"
    if "list_dir" in name:
        return f"  {inp.get('relative_path', '')[:60]}"
    if "search_for_pattern" in name:
        return f'  "{inp.get("substring_pattern", "")[:60]}"'
    if "get_symbols_overview" in name:
        return f"  {inp.get('relative_path', '')[:60]}"
    return ""
