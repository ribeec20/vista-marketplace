# Spec: Job Management

## Problem Statement

Ralph MCP tools need to create, track, and manage background loop jobs. Each job has a lifecycle (queued -> running -> completed/failed/stopped), a working directory with artifacts, and a subprocess that must be monitored. Job state must survive MCP server restarts since the subprocess is detached.

## Proposed Solution

Create a `RalphService` that manages job lifecycle, working directories, and subprocess spawning. State is persisted to disk in `job.json` files. Process state is verified by PID checks on each status query.

### Job Directory Structure

```
.vista/ralph/{slug}/
├── job.json              # Job metadata (ID, status, provider, model, timestamps)
├── task.md               # User's intent (written by Claude before ralph_start)
├── PROMPT_plan.md        # Generated from template (for plan mode)
├── PROMPT_build.md       # Generated from template (for build mode)
├── progress.txt          # Updated by worker each iteration
├── IMPLEMENTATION_PLAN.md # Output of planning loop
├── AGENTS.md             # Operational docs (created by worker)
└── output.log            # Captured stdout/stderr from subprocess
```

### job.json Schema

```json
{
  "job_id": "uuid-v4",
  "slug": "refactor-api-handlers",
  "mode": "plan",
  "status": "running",
  "provider": "claude",
  "model": "opus",
  "iterations": 3,
  "current_iteration": 1,
  "pid": 12345,
  "created_at": "2026-02-10T12:00:00Z",
  "started_at": "2026-02-10T12:00:01Z",
  "completed_at": null,
  "error": null
}
```

### Job Lifecycle

```
     ralph_start()
         │
         ▼
     ┌────────┐
     │ queued  │  (directory created, files written, subprocess not yet spawned)
     └───┬────┘
         │  subprocess.Popen()
         ▼
     ┌─────────┐
     │ running │  (subprocess active, progress.txt updating)
     └───┬─────┘
         │
    ┌────┴────────┬──────────────┐
    ▼             ▼              ▼
┌───────────┐ ┌────────┐  ┌─────────┐
│ completed │ │ failed │  │ stopped │
└───────────┘ └────────┘  └─────────┘
  (exit 0)    (exit != 0    (ralph_stop
               or crash)     called)
```

### RalphService API

```python
class RalphService:
    def __init__(self, project_root: Path):
        self.ralph_dir = project_root / ".vista" / "ralph"

    def create_job(self, slug: str, mode: str, task_description: str,
                   provider: Provider, model: str, iterations: int) -> dict:
        """Create job directory, write files, spawn subprocess. Returns job metadata."""

    def get_job(self, job_id: str) -> dict | None:
        """Load job.json by ID. Returns None if not found."""

    def get_job_status(self, job_id: str) -> dict:
        """Get job status with live process check and progress tail."""

    def stop_job(self, job_id: str) -> dict:
        """Send termination signal to job subprocess."""

    def list_jobs(self) -> list[dict]:
        """List all jobs (for dashboard)."""

    def find_job_by_slug(self, slug: str) -> dict | None:
        """Find job by slug (for duplicate detection)."""
```

### Subprocess Spawning — Must Match ralph.py Exactly

**Critical**: The MCP tool must generate and run loop scripts using the exact same code path as `ralph.py`. This is not a reimplementation — it reuses the same template and provider methods.

The existing `ralph.py` does this (lines 208-233):

1. **Generate loop script** via `LOOP_SCRIPT_TEMPLATE.format(...)` with `provider.get_invocation("ps1")` injected
2. **Write** the script to disk as `loop.ps1`
3. **Run** via `subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(loop_script)], cwd=str(PROJECT_ROOT.resolve()))`

The MCP tool does the same, but uses `subprocess.Popen` instead of `subprocess.run` for non-blocking execution:

```python
# Step 1: Import and use the SAME template and provider methods as ralph.py
from portable.ralph import LOOP_SCRIPT_TEMPLATE, get_prompt_content

# Step 2: Generate loop script identically to ralph.py lines 208-218
script_content = LOOP_SCRIPT_TEMPLATE.format(
    mode=mode,
    max_iterations=iterations,
    model=model,
    feature_name=slug,
    feature_dir_abs=str(job_dir.resolve()),
    project_root_abs=str(project_root.resolve()),
    provider_name=provider.display_name,
    invocation_block=provider.get_invocation("ps1"),  # Same method ralph.py uses
)
loop_script.write_text(script_content, encoding='utf-8')

# Step 3: Run non-blocking (ralph.py uses subprocess.run which blocks)
proc = subprocess.Popen(
    ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(loop_script)],
    stdin=subprocess.DEVNULL,      # Never read from MCP stdin
    stdout=open(output_log, 'w'),  # Capture to file (ralph.py inherits terminal)
    stderr=subprocess.STDOUT,      # Merge stderr into stdout
    cwd=str(project_root.resolve()),  # Same cwd as ralph.py line 233
    text=True,
    encoding="utf-8",
    errors="replace",
)
```

**Key differences from ralph.py (intentional):**
- `subprocess.Popen` instead of `subprocess.run` (non-blocking for MCP)
- stdout redirected to `output.log` instead of inherited terminal
- stdin is `DEVNULL` instead of inherited (MCP server owns stdin)

**Everything else is identical:**
- Same `LOOP_SCRIPT_TEMPLATE` string
- Same `provider.get_invocation("ps1")` call
- Same `cwd=str(PROJECT_ROOT.resolve())`
- Same PowerShell execution flags

If `ralph.py` changes how loops are invoked, those changes automatically flow to the MCP tool because they share the same template and provider methods.

### Process State Verification

On each `ralph_status` call:
1. Read `job.json` from disk
2. If status is "running", check if PID is still alive
3. If PID is dead and status is "running", update to "failed" (or "completed" if exit code was 0)
4. Read last N lines of `progress.txt` for progress info
5. Parse current iteration from progress.txt content

### Job ID Lookup

Jobs are stored by slug directory but identified by UUID job_id:
- Maintain an in-memory index (rebuilt on startup by scanning `.vista/ralph/*/job.json`)
- Or: linear scan of slug directories (acceptable for small numbers of jobs)
- Prefer linear scan for v1 simplicity (no state to get stale)

## Data Requirements

- `job.json` is the authoritative state file
- `progress.txt` is updated by the worker subprocess (not by RalphService)
- `output.log` captures raw subprocess output for debugging
- All paths are relative to project root

## Edge Cases

- **Slug already has active job**: Return error with existing job_id and status
- **Slug has completed job**: Allow re-use. New job gets a new job_id. Previous job.json is renamed to `job.{old-id}.json`.
- **MCP server restarts**: Jobs continue running (subprocess is detached). On next status check, PID is verified against OS.
- **Orphaned process**: If job.json says "running" but PID doesn't exist, mark as "failed" with appropriate error message.
- **Concurrent status checks**: Read-only, no race conditions.
- **Platform differences**: Use `os.kill(pid, 0)` for PID check on Unix, `ctypes.windll.kernel32.OpenProcess` or `psutil` on Windows.

## Dependencies

- `vista/server/services/provider_service.py` (existing) - Provider invocation blocks
- `vista/portable/templates/` (existing) - Prompt templates
- `vista/server/services/loop_service.py` (existing) - Subprocess patterns to reuse
- Spec: [settings](settings.md) - Default values
- Spec: [mcp-tools](mcp-tools.md) - Calls RalphService methods

## Testing Strategy

- Unit tests for job creation (directory structure, file contents)
- Unit tests for status checks (running, completed, failed, stopped)
- Unit tests for PID verification (mock os.kill / psutil)
- Unit tests for duplicate slug detection
- Integration test: create -> status -> stop lifecycle with real subprocess
- Platform tests: Windows PID checking vs Unix
