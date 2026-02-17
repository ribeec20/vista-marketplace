# Spec: Summarizer Agent

## Problem Statement

When a ralph loop finishes (or while it's running), the orchestrator LLM needs a concise, actionable summary of what the loop accomplished. Raw artifacts (progress.txt, IMPLEMENTATION_PLAN.md, git log) are too verbose and unstructured for the orchestrator to parse efficiently. A summarizer agent reads these artifacts and produces a structured summary.

## Proposed Solution

The summarizer is a CLI subprocess that reads job artifacts from disk and returns a structured summary. It uses a configurable provider/model from settings (typically a fast, cheap model like Haiku). The summarizer is invoked on-demand via the `ralph_summary` MCP tool, never automatically.

### Summarizer Flow

```
ralph_summary(job_id)
        │
        ▼
  Load job.json
  Load summarizer config from settings
        │
        ▼
  Build summarizer prompt:
    - Read progress.txt
    - Read IMPLEMENTATION_PLAN.md (if exists)
    - Read task.md
    - Run git log --oneline in job dir
        │
        ▼
  Spawn CLI subprocess:
    echo "{prompt}" | claude -p --model haiku
    (or equivalent for configured provider)
        │
        ▼
  Parse output, return structured JSON
```

### Summarizer Prompt Template

```markdown
You are a summarizer. Read the following artifacts from a ralph loop job and produce a structured JSON summary.

## Task
{contents of task.md}

## Progress
{contents of progress.txt}

## Implementation Plan
{contents of IMPLEMENTATION_PLAN.md or "Not yet created"}

## Git Activity
{git log --oneline output or "No commits yet"}

## Job Status
Mode: {plan|build}
Status: {running|completed|failed|stopped}
Iteration: {current}/{total}

---

Respond with ONLY a JSON object (no markdown fences):
{
  "status_summary": "One sentence describing the current state",
  "completed_work": ["List of things accomplished"],
  "in_progress": ["List of things currently being worked on"],
  "issues": ["List of problems or blockers encountered"],
  "recommendations": ["List of suggested next steps"],
  "key_files_changed": ["List of significant file paths modified"]
}
```

### Subprocess Invocation

```python
def run_summarizer(job_dir: Path, job_meta: dict, config: dict) -> dict:
    """Spawn summarizer CLI and parse output."""

    # Build prompt from artifacts
    prompt = build_summarizer_prompt(job_dir, job_meta)

    # Get invocation from provider
    provider = get_provider(config["provider"])
    model = config["model"]

    # Spawn subprocess
    proc = subprocess.Popen(
        provider.get_summarizer_command(model),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        cwd=str(job_dir),
        timeout=55,  # Leave 5s buffer for MCP timeout
    )

    stdout, stderr = proc.communicate(input=prompt, timeout=55)

    # Parse JSON from output
    return parse_summary_json(stdout)
```

### Provider-Specific Summarizer Commands

Each provider needs a method to return the CLI command for summarizer invocation:

```python
class ClaudeProvider(Provider):
    def get_summarizer_command(self, model: str) -> list[str]:
        return ["claude", "-p", "--model", model, "--output-format", "text"]

class OpenCodeProvider(Provider):
    def get_summarizer_command(self, model: str) -> list[str]:
        return ["opencode", "run", "--model", model]
```

The summarizer always pipes prompt via stdin and reads response from stdout.

### Configuration

From `vista/settings.json`:

```json
{
  "ralph": {
    "summarizer": {
      "provider": "claude",
      "model": "haiku"
    }
  }
}
```

- Provider and model are fixed in settings (not chosen per-call by the LLM)
- The summarizer config is independent of the loop provider filtering
- If summarizer config is missing, default to `claude` / `haiku`

## Data Requirements

- **Input**: job.json, task.md, progress.txt, IMPLEMENTATION_PLAN.md, git log
- **Output**: Structured JSON summary
- All inputs are read-only (summarizer does not modify job artifacts)
- Git log is run in the project root directory, not the job directory

## UI/UX Considerations

- The LLM receives a clean JSON summary it can present to the user naturally
- Summarizer output is designed for LLM consumption, not direct human display
- Dashboard may also call the summarizer for richer job detail views (future)

## Edge Cases

- **Summarizer CLI not available**: Return error indicating the configured provider CLI is not installed
- **Summarizer timeout**: If subprocess takes > 55 seconds, kill it and return a timeout error
- **Empty artifacts**: progress.txt or IMPLEMENTATION_PLAN.md may not exist yet (job just started). Summarizer handles gracefully.
- **Malformed output**: If the CLI returns non-JSON output, extract what we can or return a raw text fallback
- **Running job**: Summarizer works on current state of artifacts (may be mid-write). This is acceptable - the summary is a snapshot.
- **Large artifacts**: Truncate progress.txt to last 100 lines and IMPLEMENTATION_PLAN.md to first 500 lines to stay within model context

## Dependencies

- `vista/server/services/provider_service.py` (existing) - Provider CLI commands
- `vista/server/config.py` (existing) - Settings loading
- Spec: [settings](settings.md) - Summarizer config schema
- Spec: [job-management](job-management.md) - Job directory structure and job.json

## Testing Strategy

- Unit tests for prompt building (various artifact states: empty, partial, full)
- Unit tests for output parsing (valid JSON, malformed output, empty output)
- Unit tests for truncation logic
- Integration test: mock CLI subprocess, verify end-to-end flow
- Timeout test: verify cleanup on subprocess timeout
