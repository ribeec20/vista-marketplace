# Implementation Plan: Activity Log Parsing Improvements

## Overview

This plan analyzes the vista plugin's ralph loop activity log parsing feature and proposes 3 targeted improvements focusing on edge cases in tool name display, handling of multi-tool assistant messages, and performance optimizations for large output.log files.

## Current Architecture Analysis

### Key Components

1. **`vista/server/services/output_parser.py`**
   - `OutputParser` class: Stateful parser for multi-line RALPH_CONTROL blocks
   - `parse_stream_json_activity()`: Main function that converts stream-json to human-readable activity
   - `_tool_summary()`: Generates brief descriptions for tool calls

2. **Usage Locations**
   - `vista/server/routes/ralph.py:85`: GET `/api/ralph/jobs/{job_id}/progress` endpoint
   - `vista/server/services/ralph_service.py:254`: `_read_activity()` method for fallback activity parsing

3. **Current Behavior**
   - Parses last 500 lines for efficiency (ralph.py:85, ralph_service.py:264)
   - Extracts tool calls from `"type":"assistant"` messages with `content` array
   - Displays tool names with parameter summaries via `_tool_summary()`
   - Truncates long text blocks to 200 characters

### Identified Issues

#### Issue 1: Edge Cases in Tool Name Display

**Current Problem**:
- MCP tool names like `mcp__plugin_playwright_playwright__browser_snapshot` are displayed verbatim (line 167)
- Long tool names can dominate the activity log readability
- No special handling for namespaced tools (mcp__, serena__)

**Evidence**:
```python
# output_parser.py:170
activity.append(f"> Tool: {name}{detail}")
```

Stream-json assistant messages show MCP tools with full prefixes:
```json
{"type":"tool_use","id":"...","name":"mcp__serena__find_file","input":{...}}
```

#### Issue 2: Multi-Tool Assistant Messages

**Current Problem**:
- Assistant messages with multiple tool calls in a single content block are processed sequentially
- No indication that tools are part of the same logical action
- Mixed text + tool_use blocks don't show clear association

**Evidence**:
```python
# output_parser.py:155-170
if msg_type == "assistant":
    content_blocks = obj.get("message", {}).get("content", [])
    for block in content_blocks:
        btype = block.get("type")
        if btype == "text":
            # ... handle text
        elif btype == "tool_use":
            # ... handle tool
```

When Claude makes 3 parallel tool calls, the activity log shows:
```
> Tool: mcp__serena__find_file  *ralph*
> Tool: mcp__serena__search_for_pattern  "activity.*log"
> Tool: Grep  "output\.log"
```
No visual grouping or indication these are parallel.

#### Issue 3: Performance for Large Output.log Files

**Current Problem**:
- `parse_stream_json_activity()` receives pre-sliced lines (last 500)
- But it still iterates through all 500 lines doing JSON parsing
- No early exit if the last N activity entries are found
- Large iteration loops can produce 10k+ line output.log files

**Evidence**:
```python
# ralph_service.py:263-265
lines = text.splitlines()
# Only parse last 500 lines for efficiency
activity, iteration = parse_stream_json_activity(lines[-500:])
```

The function processes all 500 lines even if caller only needs last 50 (ralph.py:85).

## Proposed Improvements

### Improvement 1: Smart Tool Name Formatting

**Goal**: Make tool names more readable while preserving essential information

**Changes**:
1. Add `_format_tool_name()` helper function to clean up tool names
2. Strip common prefixes (`mcp__plugin_*`, `mcp__serena__`)
3. Apply formatting before display in line 170

**Implementation**:

```python
def _format_tool_name(name: str) -> str:
    """Format tool names for readability in activity logs.

    Examples:
    - mcp__plugin_playwright_playwright__browser_snapshot -> browser_snapshot
    - mcp__serena__find_file -> serena:find_file
    - Read -> Read (unchanged)
    """
    # Strip MCP plugin prefix pattern
    if name.startswith("mcp__plugin_"):
        # mcp__plugin_playwright_playwright__browser_snapshot
        # -> browser_snapshot
        parts = name.split("__")
        if len(parts) >= 3:
            # Last part after double underscore
            return parts[-1]

    # Strip serena prefix but keep namespace
    if name.startswith("mcp__serena__"):
        return "serena:" + name[len("mcp__serena__"):]

    # Other MCP tools - strip mcp__ prefix
    if name.startswith("mcp__"):
        return name[5:]

    # Built-in tools unchanged
    return name
```

**Modified call site** (line 170):
```python
display_name = _format_tool_name(name)
activity.append(f"> Tool: {display_name}{detail}")
```

**Impact**: Cleaner activity logs, especially for MCP-heavy workflows

### Improvement 2: Multi-Tool Message Grouping

**Goal**: Visually indicate when multiple tools are called together

**Changes**:
1. Track when processing assistant messages with multiple tool_use blocks
2. Add visual grouping indicator for parallel tool calls
3. Prefix with "⎿" (box drawing) for grouped tools

**Implementation**:

```python
if msg_type == "assistant":
    content_blocks = obj.get("message", {}).get("content", [])

    # Count tool uses in this message
    tool_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
    is_multi_tool = len(tool_blocks) > 1

    for i, block in enumerate(content_blocks):
        btype = block.get("type")
        if btype == "text":
            text = block.get("text", "").strip()
            if text:
                if len(text) > 200:
                    text = text[:200] + "..."
                activity.append(text)
        elif btype == "tool_use":
            name = block.get("name", "unknown")
            inp = block.get("input", {})
            detail = _tool_summary(name, inp)
            display_name = _format_tool_name(name)

            # Add grouping prefix for parallel tools
            if is_multi_tool:
                # Find tool index in tool_blocks
                tool_idx = sum(1 for b in content_blocks[:content_blocks.index(block)]
                              if b.get("type") == "tool_use")
                is_last = (tool_idx == len(tool_blocks) - 1)
                prefix = "  └─" if is_last else "  ├─"
                activity.append(f"{prefix} {display_name}{detail}")
            else:
                activity.append(f"> Tool: {display_name}{detail}")
```

**Example Output**:
```
  ├─ serena:find_file  *ralph*
  ├─ serena:search_for_pattern  "activity.*log"
  └─ Grep  "output\.log"
```

**Impact**: Better visualization of Claude's parallel tool execution strategy

### Improvement 3: Configurable Activity Limit with Early Exit

**Goal**: Improve performance by only parsing what's needed

**Changes**:
1. Add optional `max_activity_entries` parameter to `parse_stream_json_activity()`
2. Track activity count and exit early when limit reached
3. Process lines in reverse to get most recent entries first

**Implementation**:

```python
def parse_stream_json_activity(
    lines: list[str],
    max_activity_entries: Optional[int] = None,
) -> tuple[list[str], Optional[int]]:
    """Parse stream-json output lines into human-readable activity entries.

    Extracts assistant text, tool calls, and iteration markers from
    Claude's ``--output-format=stream-json`` output.

    Args:
        lines: Raw output lines from output.log
        max_activity_entries: If set, stop parsing after collecting this many
                             activity entries (more efficient for large logs)

    Returns ``(activity_lines, current_iteration)``.
    """
    activity: list[str] = []
    current_iteration: Optional[int] = None

    # Process in reverse to get most recent entries first
    for raw in reversed(lines):
        # Early exit if we have enough entries
        if max_activity_entries and len(activity) >= max_activity_entries:
            break

        line = raw.strip()
        if not line:
            continue

        # ... existing parsing logic ...

    # Reverse activity to chronological order
    return list(reversed(activity)), current_iteration
```

**Call site updates**:

```python
# ralph.py:85 - only need last N entries
activity, _iteration = parse_stream_json_activity(
    raw[-500:],
    max_activity_entries=last
)
return {"lines": activity}  # Already limited, no need for [-last:]

# ralph_service.py:265 - limit to 5 for progress tail
activity, iteration = parse_stream_json_activity(
    lines[-500:],
    max_activity_entries=5
)
```

**Impact**:
- Faster parsing for large logs (can exit after ~50 lines instead of 500)
- Memory efficient (don't build large activity arrays just to slice them)
- Especially beneficial for jobs with many iterations

## Implementation Steps

### Phase 1: Tool Name Formatting (Low Risk)
1. Add `_format_tool_name()` function to `output_parser.py`
2. Add unit tests in `test_output_parser.py`:
   - Test MCP plugin prefix stripping
   - Test serena namespace preservation
   - Test built-in tool passthrough
3. Update line 170 to use formatted names
4. Run existing tests to ensure no regressions

**Files Modified**:
- `vista/server/services/output_parser.py` (+20 lines)
- `vista/tests/test_output_parser.py` (+40 lines)

**Testing**: Unit tests + manual verification with existing ralph jobs

### Phase 2: Multi-Tool Grouping (Medium Risk)
1. Modify assistant message parsing to detect multi-tool blocks
2. Add tree-style prefixes for grouped tools
3. Add unit tests:
   - Single tool message (existing behavior)
   - Multi-tool message (grouped display)
   - Mixed text + tools (proper ordering)
4. Integration test with mock stream-json output

**Files Modified**:
- `vista/server/services/output_parser.py` (+25 lines)
- `vista/tests/test_output_parser.py` (+60 lines)

**Testing**: Unit tests + create test job with parallel tools

### Phase 3: Performance Optimization (Medium Risk)
1. Add `max_activity_entries` parameter to `parse_stream_json_activity()`
2. Implement reverse parsing with early exit
3. Update call sites in ralph.py and ralph_service.py
4. Add performance tests:
   - Large log file (1000+ lines)
   - Verify early exit behavior
   - Benchmark parsing time improvement
5. Ensure activity order is preserved (reverse twice)

**Files Modified**:
- `vista/server/services/output_parser.py` (+15 lines)
- `vista/server/routes/ralph.py` (3 lines changed)
- `vista/server/services/ralph_service.py` (2 lines changed)
- `vista/tests/test_output_parser.py` (+45 lines)

**Testing**: Unit tests + performance benchmark + existing integration tests

## Test Plan

### Unit Tests
- `test_format_tool_name_mcp_plugin`: Verify playwright/vista tools formatted correctly
- `test_format_tool_name_serena`: Verify serena namespace preserved
- `test_format_tool_name_builtin`: Verify Read/Write/Edit unchanged
- `test_multi_tool_grouping`: Verify tree-style output for parallel calls
- `test_single_tool_no_grouping`: Verify existing format for single tools
- `test_max_activity_entries_limit`: Verify early exit behavior
- `test_max_activity_entries_reverse`: Verify chronological order maintained
- `test_performance_large_log`: Benchmark improvement with 1000+ lines

### Integration Tests
- Create test ralph job that uses MCP tools
- Verify activity log shows formatted tool names
- Verify multi-tool messages display grouping
- Verify performance with large output.log (10k+ lines)

### Manual Testing
- Run existing ralph jobs and review activity logs
- Check dashboard `/jobs/{id}/progress` endpoint
- Verify backward compatibility with old output.log files

## Risk Assessment

### Low Risk
- Tool name formatting (pure display change, no data loss)
- Fully testable with unit tests
- Backward compatible (old logs still parse correctly)

### Medium Risk
- Multi-tool grouping (changes output format slightly)
- Early exit optimization (must verify no data loss)
- Both require integration testing

### Mitigation
- All changes are in display/formatting layer, not data collection
- Existing tests ensure no regressions in core parsing
- Feature flags could be added if rollback needed

## Success Criteria

1. **Tool names** are more readable (no long mcp__ prefixes)
2. **Multi-tool messages** show visual grouping in activity logs
3. **Performance** improvement measurable (>50% faster for large logs)
4. **All existing tests** pass without modification
5. **New tests** provide >90% coverage of new code
6. **No breaking changes** to API contracts or file formats

## Future Enhancements (Out of Scope)

- Color-coding for different tool types in UI
- Collapsible tool groups in dashboard
- Activity log search/filtering
- Export activity log to JSON/CSV
- Real-time streaming updates (WebSocket)
