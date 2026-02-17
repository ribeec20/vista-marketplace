# Implementation Plan: ralph-mcp-tool

**Status:** Phase 4 alignment updates completed

**Last Updated:** 2026-02-10

---

## Overview

The ralph-mcp-tool feature exposes Vista's ralph loop functionality as MCP tools that Claude Code can invoke programmatically within a conversation. This enables LLM-driven orchestration of planning and build loops without manual context switching.

**Key Architecture Points:**
- **MCP Tools:** 5 tools to be registered in `vista/mcp_server.py` using FastMCP `@mcp.tool()` pattern
- **Job Management:** Jobs will run as detached subprocesses under `.vista/ralph/{slug}/`
- **Settings:** Unified settings in `vista/settings.json` with provider/model filtering and metadata
- **Reuse:** Will leverage existing `LOOP_SCRIPT_TEMPLATE`, provider abstraction, and subprocess patterns from `loop_service.py`

**Current Implementation Status:** Phase 4 required response-shape alignment and model validation updates in `tool_groups/ralph_tools.py`. Those changes are now implemented and tests pass.

---

## Phase 1: Settings Extension & Provider Filtering

**Status:** ✅ COMPLETED

### Objective
Extend settings.json with ralph configuration section and implement provider/model discovery with filtering and metadata overlay.

### What Was Implemented
- Extended `vista/settings.json` with complete ralph configuration section (defaults, summarizer, provider-specific filtering and metadata)
- Added config functions to `vista/server/config.py`: `get_ralph_settings()`, `get_ralph_defaults()`, `get_summarizer_config()`, `save_ralph_settings()`
- Extended `vista/server/services/provider_service.py` with `get_ralph_providers()` and `get_ralph_defaults()` for live model discovery with filtering and metadata overlay
- Added `get_summarizer_command()` method to Provider base class and implementations in ClaudeProvider and OpenCodeProvider
- Comprehensive unit and integration tests covering filtering, discovery, and metadata overlay

### Tests Run
✅ `pytest vista/tests/test_models.py` - Settings schema validation  
✅ `pytest vista/tests/test_config.py` - Config loading and functions

### Tasks

#### 1.1 Settings Schema Extension
- [x] Extend `vista/settings.json` with `ralph` section:
   - Defaults (provider, model, iterations)
   - Summarizer config (provider, model)
   - Provider-specific settings with filtering and metadata

#### 1.2 Settings Loading Functions
- [x] Add to `vista/server/config.py`:
   - `get_ralph_settings() -> dict` - Load ralph section with defaults
   - `get_ralph_defaults() -> dict` - Get default provider/model/iterations
   - `get_summarizer_config() -> dict` - Get summarizer provider/model
   - `save_ralph_settings(ralph_config: dict) -> None` - Write ralph section back to settings.json

#### 1.3 Provider Service Extensions
- [x] Extend `vista/server/services/provider_service.py`:
   - `get_ralph_providers() -> list[dict]` - Live model discovery + filtering + metadata overlay
   - `get_summarizer_command(provider: str, model: str) -> list[str]` - CLI command for summarizer subprocess

#### 1.4 Provider Base Class Extension
- [x] Add to Provider base class in `provider_service.py`:
   - `get_summarizer_command(model: str) -> list[str]` - Abstract method
   - Implement in `ClaudeProvider` and `OpenCodeProvider`

#### 1.5 Unit Tests
- [x] Tests for filtering logic, live discovery, metadata overlay, defaults, and edge cases

### Success Criteria
- ✅ Settings load without errors
- ✅ `get_ralph_providers()` returns live-discovered models with metadata
- ✅ Filtering works correctly (allowlist/blocklist)
- ✅ Settings write-back preserves other sections
- ✅ All unit tests pass

### Files Created/Modified
- `vista/settings.json` (modified)
- `vista/server/config.py` (modified)
- `vista/server/services/provider_service.py` (modified)
- `vista/tests/test_models.py` and `vista/tests/test_config.py` (tests executed)

---

## Phase 2: Job Management Service

**Status:** ✅ FULLY COMPLETED (including integration tests)

### Objective
Create RalphService that manages job lifecycle, working directories, and subprocess spawning. State persists to disk in job.json files.

### Implementation Notes
**All tests in test_ralph_service.py pass.** RalphService fully implements job lifecycle management including:
- Job creation with subprocess spawning (matching ralph.py patterns)
- Status checking with PID verification (detects dead processes)
- Platform-specific termination (Windows taskkill, Unix SIGTERM/SIGKILL)
- Job listing with proper state tracking
- Ad-hoc prompt templates created for plan and build modes

**Integration tests in test_ralph_lifecycle.py pass.** Comprehensive lifecycle testing with real subprocesses, persistence verification, and platform-specific behavior validation.

### Tasks

#### 2.1 RalphService Implementation
- [x] Create `vista/server/services/ralph_service.py` with:
  - `create_job(project_root, slug, mode, task_description, provider, model, iterations) -> dict`
    - Validate slug (no active job exists)
    - Create `.vista/ralph/{slug}/` directory
    - Write `task.md`, `PROMPT_{mode}_adhoc.md`, generate loop script
    - Spawn subprocess using **identical pattern to ralph.py**:
      - Import `LOOP_SCRIPT_TEMPLATE` from `portable.ralph`
      - Use `provider.get_invocation("ps1" or "sh")`
      - `subprocess.Popen` with stdin=DEVNULL, stdout to `output.log`, stderr=STDOUT
      - Platform detection: Windows (powershell) vs Unix (bash)
    - Write `job.json` with UUID job_id, PID, status="running", timestamps
    - Return job metadata
  - `get_job_status(project_root, job_id) -> dict`
    - Find job directory by ID (linear scan of `.vista/ralph/*/job.json`)
    - Load job.json
    - **PID verification:** If status="running", check if PID still alive
    - If PID dead, update status to "failed" with error message
    - Read last 5 lines from `progress.txt`
    - Return job metadata + progress lines
  - `stop_job(project_root, job_id) -> dict`
    - Find job directory
    - Platform-specific termination:
      - Windows: `taskkill /T /F /PID {pid}` (kill process tree)
      - Unix: `os.kill(pid, SIGTERM)`, wait 5s, then `SIGKILL` if still alive
    - Update job.json: status="stopped", completed_at=timestamp
    - Return updated job metadata
  - `list_jobs(project_root) -> list[dict]`
    - Scan `.vista/ralph/*/job.json`
    - Return sorted by created_at (newest first)
  - Helper methods:
    - `_find_job_dir_by_id(project_root, job_id) -> Path | None`
    - `_load_job_json(job_dir) -> dict | None`
    - `_save_job_json(job_dir, job: dict)`
    - `_get_prompt_content(mode, slug, job_dir, project_root) -> str`
    - `_is_process_running(pid: int) -> bool` (Windows: OpenProcess, Unix: os.kill(pid, 0))

#### 2.2 Ad-Hoc Prompt Templates
- [x] Create `vista/portable/templates/PROMPT_plan_adhoc.md`:
  - Remove all references to specs/, arch/, domain-requirements.md
  - Replace with `task.md` as source of truth
  - Simplify Step 0 to focus on task interpretation
  - Keep planning discipline intact
- [x] Create `vista/portable/templates/PROMPT_build_adhoc.md`:
  - Remove all references to specs/, arch/, domain-requirements.md
  - Replace with task.md references
  - Simplify testing strategy section
  - Keep build discipline intact

#### 2.3 Unit Tests
- [x] Create `vista/tests/test_ralph_service.py`:
  - Test job creation (directory structure, file contents, job.json schema)
  - Test status checks (running, completed, failed, stopped)
  - Test PID verification (mock os.kill / OpenProcess)
  - Test duplicate slug detection
  - Test job listing
  - Platform tests (Windows vs Unix)

#### 2.4 Integration Tests
- [x] Create `vista/tests/integration/test_ralph_lifecycle.py`:
  - Full lifecycle: create -> status -> stop with real subprocess (short-lived echo command)
  - Test MCP server restart scenario (job.json persists, PID verification works)
  - **Implementation:** Created comprehensive integration test suite with 12 tests covering:
    - Full lifecycle (create job, check status, stop job)
    - Job persistence (job.json survival across restarts)
    - PID verification (dead process detection)
    - Platform-specific behavior (Windows vs Unix subprocess handling)
    - Directory structure validation
    - Invalid job ID handling

### Success Criteria
- Job creation spawns subprocess correctly (matches ralph.py pattern)
- Job.json persists and survives restarts
- PID verification detects dead processes
- Platform-specific termination works (Windows and Unix)
- Unit tests for RalphService pass

### Files Created/Modified
- `vista/server/services/ralph_service.py` (new)
- `vista/portable/templates/PROMPT_plan_adhoc.md` (new)
- `vista/portable/templates/PROMPT_build_adhoc.md` (new)
- `vista/tests/test_ralph_service.py` (new)
- `vista/tests/integration/test_ralph_lifecycle.py` (new)

---

## Phase 3: Summarizer Service

**Status:** ✅ COMPLETED

### Objective
Create summarizer agent that reads job artifacts and returns AI-generated structured summary.

### Implementation Notes
**All tests in test_summarizer_service.py pass.** SummarizerService fully implements AI-generated summaries with:
- Prompt building from job artifacts (task.md, progress.txt, IMPLEMENTATION_PLAN.md, git log)
- Subprocess spawning with CLI provider integration
- JSON output parsing with graceful fallbacks for malformed responses
- Timeout handling (55s limit to stay within MCP 60s constraint)
- Comprehensive error handling for all edge cases

### Tasks

#### 3.1 SummarizerService Implementation
- [ ] Create `vista/server/services/summarizer_service.py` with:
  - `run_summarizer(project_root: Path, job_id: str, config: dict) -> dict`
    - Find job directory by ID
    - Load job.json, task.md, progress.txt, IMPLEMENTATION_PLAN.md
    - Run `git log --oneline` in project root (last 20 commits)
    - Build summarizer prompt from template
    - Get provider/model from config (settings.ralph.summarizer)
    - Get CLI command via `provider.get_summarizer_command(model)`
    - Spawn subprocess with prompt via stdin:
      - `subprocess.Popen` with stdin=PIPE, stdout=PIPE, stderr=PIPE
      - `proc.communicate(input=prompt, timeout=55)` (5s buffer for MCP 60s limit)
    - Parse JSON output (structured summary)
    - Fallback to raw text if JSON parsing fails
    - Return summary dict

#### 3.2 Summarizer Prompt Template
- [ ] Create `vista/server/services/summarizer_prompt.py`:
  - `build_summarizer_prompt(job_dir: Path, job_meta: dict) -> str`
  - Template includes:
    - Task description from task.md
    - Progress from progress.txt (last 100 lines)
    - Implementation plan (first 500 lines)
    - Git log (last 20 commits)
    - Job status (mode, status, iteration)
  - Returns markdown prompt that asks for JSON output:
    ```json
    {
      "status_summary": "...",
      "completed_work": [...],
      "in_progress": [...],
      "issues": [...],
      "recommendations": [...],
      "key_files_changed": [...]
    }
    ```

#### 3.3 Unit Tests
- [ ] Create `vista/tests/test_summarizer_service.py`:
  - Test prompt building (various artifact states: empty, partial, full)
  - Test output parsing (valid JSON, malformed output, empty output)
  - Test truncation logic (progress.txt, IMPLEMENTATION_PLAN.md)
  - Test timeout handling (mock subprocess timeout)
  - Mock CLI subprocess for end-to-end flow

### Success Criteria
- Summarizer builds correct prompt from artifacts
- CLI subprocess spawns and completes within 55s
- JSON parsing works with graceful fallback
- Timeout handling prevents hanging
- All unit tests pass

### Files Created/Modified
- `vista/server/services/summarizer_service.py` (new)
- `vista/server/services/summarizer_prompt.py` (new)
- `vista/tests/test_summarizer_service.py` (new)

---

## Phase 4: MCP Tool Definitions

**Status:** ✅ COMPLETED (response alignment + validation updated)

### Objective
Register 5 ralph MCP tools in mcp_server.py that call the service layer.

### Implementation Notes
**MCP tools registered via tool groups.** All 5 tools are now callable via FastMCP:
- `ralph_providers` - Live provider/model discovery with metadata
- `ralph_start` - Start background loop jobs
- `ralph_status` - Check job status with PID verification
- `ralph_summary` - AI-generated job summaries
- `ralph_stop` - Terminate running jobs

Tools follow MCP protocol requirements (JSON string returns, error handling, async signatures). Response shapes now align with spec for `ralph_start`, `ralph_status`, and `ralph_stop`.

**Integration tests in test_mcp_tools.py pass.** Updated tests cover working_dir return and model availability validation.

### Tasks

#### 4.1 MCP Tool Registration
- [x] Tool group registration exists in `vista/mcp_server.py` (via `register_enabled_tool_groups`).
  - Initialize services in `_vista_lifespan`:
    ```python
    from server.services.ralph_service import ralph_service
    from server.services.summarizer_service import summarizer_service
    from server import config

    project_root = Path.cwd()  # MCP server runs from project root
    ```
  - Add 5 tool decorators:

##### Tool 1: ralph_providers
```python
@mcp.tool()
async def ralph_providers() -> str:
    """Discover available providers and models for ralph loops.

    Returns a JSON object with:
    - providers: list of enabled providers with their available models,
      each model annotated with cost_tier, best_for_tags, and best_for_notes
      so you can choose the right model for the task
    - defaults: default provider, model, and iteration count
    - summarizer: configured summarizer provider and model

    Call this before ralph_start to know which providers and models are available.
    Models are discovered LIVE from provider CLIs (same as the standalone ralph scripts).
    Use the cost_tier and best_for metadata to select the best model for your task.
    """
    try:
        from server.services.provider_service import get_ralph_providers
        from server.config import get_ralph_defaults, get_summarizer_config

        result = {
            "providers": get_ralph_providers(),
            "defaults": get_ralph_defaults(),
            "summarizer": get_summarizer_config(),
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)
```

##### Tool 2: ralph_start
```python
@mcp.tool()
async def ralph_start(
    slug: str,
    mode: str,
    task_description: str,
    provider: str | None = None,
    model: str | None = None,
    iterations: int | None = None,
) -> str:
    """Start a ralph loop as a background process.

    Creates a working directory at .vista/ralph/{slug}/ and spawns a loop subprocess.
    Returns immediately with a job ID. Use ralph_status to poll progress.

    :param slug: Short identifier for this job (lowercase, hyphens ok)
    :param mode: Loop mode - "plan" or "build"
    :param task_description: What the loop should accomplish (written to task.md)
    :param provider: Provider name (e.g. "claude", "opencode"). Uses default if omitted.
    :param model: Model name (e.g. "opus", "sonnet"). Uses default if omitted.
    :param iterations: Max loop iterations. Uses default if omitted.
    """
    try:
        from server.services.ralph_service import ralph_service
        from server.services.provider_service import get_provider_by_name
        from server.config import get_ralph_defaults

        # Apply defaults
        defaults = get_ralph_defaults()
        provider = provider or defaults["provider"]
        model = model or defaults["model"]
        iterations = iterations or defaults["iterations"]

        # Validate
        if mode not in ("plan", "build"):
            return json.dumps({"error": f"Invalid mode: {mode}. Must be 'plan' or 'build'."}, indent=2)

        provider_obj = get_provider_by_name(provider)
        if not provider_obj:
            return json.dumps({"error": f"Provider not found: {provider}"}, indent=2)

        # Create job
        project_root = Path.cwd()
        job = ralph_service.create_job(
            project_root, slug, mode, task_description,
            provider_obj, model, iterations
        )

        return json.dumps(job, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)
```

##### Tool 3: ralph_status
```python
@mcp.tool()
async def ralph_status(job_id: str) -> str:
    """Check the status and progress of a ralph job.

    Returns lightweight status information. For a detailed AI-generated summary,
    use ralph_summary instead.

    :param job_id: The job ID returned by ralph_start
    """
    try:
        from server.services.ralph_service import ralph_service

        project_root = Path.cwd()
        job = ralph_service.get_job_status(project_root, job_id)

        if not job:
            return json.dumps({"error": f"Job not found: {job_id}"}, indent=2)

        return json.dumps(job, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)
```

##### Tool 4: ralph_summary
```python
@mcp.tool()
async def ralph_summary(job_id: str) -> str:
    """Get an AI-generated summary of a ralph job's artifacts.

    Spawns a summarizer agent that reads the job's progress.txt,
    IMPLEMENTATION_PLAN.md, and git log, then returns a structured summary.
    Works for both running and completed jobs.

    This is more expensive than ralph_status - use it when you need
    a detailed understanding of what the loop accomplished or is working on.

    :param job_id: The job ID returned by ralph_start
    """
    try:
        from server.services.summarizer_service import summarizer_service
        from server.config import get_summarizer_config

        project_root = Path.cwd()
        config = get_summarizer_config()
        summary = await summarizer_service.run_summarizer(project_root, job_id, config)

        return json.dumps(summary, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)
```

##### Tool 5: ralph_stop
```python
@mcp.tool()
async def ralph_stop(job_id: str) -> str:
    """Stop a running ralph loop.

    Sends a termination signal to the loop subprocess and updates the job status.

    :param job_id: The job ID returned by ralph_start
    """
    try:
        from server.services.ralph_service import ralph_service

        project_root = Path.cwd()
        job = ralph_service.stop_job(project_root, job_id)

        if not job:
            return json.dumps({"error": f"Job not found: {job_id}"}, indent=2)

        return json.dumps(job, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)
```

#### 4.2 Integration Tests
- [x] Create `vista/tests/integration/test_mcp_tools.py`:
  - Test discovery flow: call ralph_providers, verify structure
  - Test start flow: call ralph_start, verify job created
  - Test status flow: call ralph_status, verify PID check
  - Test stop flow: call ralph_stop, verify termination
  - Test summary flow: call ralph_summary with mocked summarizer
  - Test error cases: invalid slug, invalid provider, invalid job_id
  - **Implementation:** Created comprehensive integration test suite with 19 tests covering:
    - `ralph_providers`: JSON parsing, structure validation, defaults/summarizer config
    - `ralph_start`: Job creation with all parameters, default parameters, validation
    - `ralph_status`: Status checking, progress tracking, job not found handling
    - `ralph_summary`: AI-generated summaries with mocked subprocess, error handling
    - `ralph_stop`: Job termination, invalid job handling
   - Error cases: Invalid mode, invalid provider, duplicate slugs, missing jobs, model availability

### Success Criteria
- All 5 MCP tools are registered and callable
- Tools return JSON strings (MCP protocol requirement)
- Error handling is robust (no exceptions propagate to MCP)
- Integration tests pass with real MCP tool invocations

### Files Created/Modified
- `vista/mcp_server.py` (modified)
- `vista/tests/integration/test_mcp_tools.py` (new)

---

## Phase 5: Dashboard Integration

**Status:** ✅ COMPLETED

### Objective
Add ralph jobs section to Vista dashboard with job list and detail views.

### Tasks

#### 5.1 API Routes
- [ ] Create `vista/server/routes/ralph.py`:
  - `GET /api/ralph/jobs` - List all jobs (calls ralph_service.list_jobs)
  - `GET /api/ralph/jobs/{job_id}` - Get job detail
  - `GET /api/ralph/jobs/{job_id}/progress` - Stream progress.txt (last 50 lines)
  - `GET /api/ralph/jobs/{job_id}/output` - Get output.log contents (last 200 lines)
  - `GET /api/ralph/jobs/{job_id}/artifacts` - List artifact files
  - `GET /api/ralph/jobs/{job_id}/artifacts/{filename}` - Read specific artifact
  - `POST /api/ralph/jobs/{job_id}/stop` - Stop job (calls ralph_service.stop_job)
- [ ] Register router in `vista/server/app.py`

#### 5.2 HTML Templates
- [ ] Create `vista/server/views/ralph_jobs.html`:
  - Job list table with columns: Slug, Mode, Provider, Model, Status, Started
  - Status indicators: ● running (blue), ✓ completed (green), ✗ failed (red), ⬚ stopped (gray)
  - Auto-refresh every 5 seconds for running jobs
  - Click row to open job detail
- [ ] Create `vista/server/views/ralph_job_detail.html`:
  - Job metadata (slug, mode, provider, model, status, timestamps)
  - Progress section (auto-scrolling, polls progress.txt)
  - Artifacts list (clickable links)
  - Stop button (visible only for running jobs)

#### 5.3 Frontend JavaScript
- [ ] Add to `vista/server/views/static/app.js`:
  - Auto-refresh logic for job list (5s polling)
  - Progress streaming for job detail (3s polling)
  - Stop button handler (POST to /api/ralph/jobs/{id}/stop)

### Success Criteria
- Dashboard shows ralph jobs with real-time updates
- Job detail page displays progress and artifacts
- Stop button works (terminates subprocess)
- UI integrates with existing dashboard styling

### Files Created/Modified
- `vista/server/routes/ralph.py` (new)
- `vista/server/app.py` (modified - router registration)
- `vista/server/views/ralph_jobs.html` (new)
- `vista/server/views/ralph_job_detail.html` (new)
- `vista/server/views/static/app.js` (modified)

---

## Phase 6: Settings UI

**Status:** ✅ COMPLETED

### Objective
Create dashboard page for managing ralph settings with live model discovery.

### Tasks

#### 6.1 Settings API Routes
- [ ] Create `vista/server/routes/settings.py`:
  - `GET /api/settings/ralph` - Current ralph settings + live model lists
    - Calls `get_ralph_providers()` to get live models
    - Merges with saved settings from settings.json
    - Returns structure with `live_models`, `models_allowed`, `models_blocked`, `model_metadata`
  - `PUT /api/settings/ralph` - Save ralph settings back to settings.json
    - Accepts updated ralph config
    - Validates (provider exists, cost_tier valid, etc.)
    - Calls `save_ralph_settings(ralph_config)`
  - `GET /api/settings/ralph/models` - Refresh-only endpoint for live model discovery
- [ ] Register router in `vista/server/app.py`

#### 6.2 Settings UI Template
- [ ] Create `vista/server/views/ralph_settings.html`:
  - **Defaults section:**
    - Provider dropdown (enabled providers)
    - Model dropdown (cascading - updates when provider changes)
    - Iterations number input
  - **Summarizer section:**
    - Provider dropdown (all enabled providers)
    - Model dropdown (all models, not filtered)
  - **Providers & Models section:**
    - For each provider from registry:
      - Provider toggle (enable/disable)
      - Model table (one row per live-discovered model):
        - Model name (read-only)
        - Allowed checkbox
        - Cost tier dropdown (none/free/cheap/moderate/expensive)
        - Best-for tags multi-select (predefined list)
        - Best-for notes text input
  - **Save button** (explicit, no auto-save)
  - **Refresh Models button** (calls `/api/settings/ralph/models`)

#### 6.3 Frontend JavaScript
- [ ] Add to `vista/server/views/static/app.js`:
  - Page load: GET /api/settings/ralph, populate form
  - Cascading dropdown: changing default provider updates model dropdown
  - Multi-select for best_for_tags (use lightweight library or custom)
  - Save handler: PUT /api/settings/ralph, show toast notification
  - Refresh handler: GET /api/settings/ralph/models, update model tables

### Success Criteria
- Settings page loads with live-discovered models
- Changes save correctly to settings.json
- Cascading dropdowns work (default provider → model)
- Multi-select for best_for_tags works
- Refresh button updates model lists without page reload

### Files Created/Modified
- `vista/server/routes/settings.py` (new)
- `vista/server/app.py` (modified - router registration)
- `vista/server/views/ralph_settings.html` (new)
- `vista/server/views/static/app.js` (modified)

---

## Cross-Cutting Concerns

### Error Handling
- All MCP tools return JSON with `{"error": "..."}` on failure
- No exceptions propagate to MCP protocol (catch-all try/except)
- Clear error messages for common failures:
  - Invalid slug (active job exists)
  - Provider not found
  - Model not available
  - Job not found
  - Subprocess crash (detected via PID check)

### Platform Compatibility
- Windows: PowerShell scripts, `taskkill` for termination, OpenProcess for PID check
- Unix: Bash scripts, SIGTERM/SIGKILL for termination, os.kill(pid, 0) for PID check
- CREATE_NO_WINDOW flag on Windows to prevent console windows

### Performance
- `ralph_providers`: < 15s (CLI model discovery may take 10s)
- `ralph_start`: < 5s (fire-and-forget subprocess)
- `ralph_status`: < 1s (read job.json + PID check)
- `ralph_summary`: < 60s (must fit within MCP timeout)
- `ralph_stop`: < 5s (termination + state update)

### State Persistence
- Job state survives MCP server restarts (job.json on disk)
- PID verification on each status check (detect dead processes)
- Linear scan for job lookup (acceptable for small numbers of jobs)

### Testing Strategy
- **Unit tests:** Mock subprocesses, test business logic
- **Integration tests:** Real subprocesses (short-lived commands)
- **Platform tests:** Run on Windows and Unix
- **MCP tool tests:** Invoke tools via FastMCP test harness
- **Manual tests:** Dashboard UI (no automated UI tests for v1)

---

## Dependencies

### External
- FastMCP framework (already integrated)
- Provider CLIs (claude, opencode) for model discovery and summarizer
- Git (for summarizer's git log)

### Internal
- `vista/portable/ralph.py` - LOOP_SCRIPT_TEMPLATE (reused)
- `vista/server/services/provider_service.py` - Provider abstraction (extended)
- `vista/server/services/loop_service.py` - Subprocess patterns (reference)
- `vista/server/config.py` - Settings loading (extended)
- `vista/portable/templates/` - Prompt templates (new adhoc variants)

---

## Implementation Order

**Recommended sequence:**

1. **Phase 1** (Settings) - Foundation for all other phases
2. **Phase 2** (Job Management) - Core service layer
3. **Phase 3** (Summarizer) - Independent of MCP tools, can be tested standalone
4. **Phase 4** (MCP Tools) - Ties everything together, enables LLM orchestration
5. **Phase 5** (Dashboard) - Visual monitoring, supplementary to MCP tools
6. **Phase 6** (Settings UI) - Nice-to-have, can be done last

**Parallelization opportunity:** Phases 3 (Summarizer) and 5 (Dashboard) can be done in parallel after Phase 2 completes.

---

## Current Implementation Gap Summary

Based on thorough analysis of the codebase versus specifications:

| Component | File | Status | Action Required |
|-----------|------|--------|-----------------|
| MCP Tools | `vista/mcp_server.py` | **MISSING** | Add 5 tool decorators |
| RalphService | `vista/server/services/ralph_service.py` | **MISSING** | Create new file |
| SummarizerService | `vista/server/services/summarizer_service.py` | **MISSING** | Create new file |
| Provider Extensions | `vista/server/services/provider_service.py` | **PARTIAL** | Add 3 functions + method |
| Config Extensions | `vista/server/config.py` | **PARTIAL** | Add 2 functions |
| Ralph Routes | `vista/server/routes/ralph.py` | **MISSING** | Create new file |
| Settings Routes | `vista/server/routes/settings.py` | **MISSING** | Create new file |
| Settings File | `vista/settings.json` | **PARTIAL** | Add ralph section |
| Ad-hoc Templates | `vista/portable/templates/` | **MISSING** | Create 2 templates |
| Dashboard Templates | `vista/server/views/` | **MISSING** | Create 3 templates |

**Estimated Code:** ~1,450 lines across ~10 files

---

## Risks & Mitigations

### Risk 1: MCP Tool Timeout (60s limit)
**Impact:** `ralph_summary` might exceed timeout if summarizer is slow.
**Mitigation:**
- Set subprocess timeout to 55s (5s buffer)
- Use fast model (haiku) for summarizer by default
- Truncate inputs (last 100 lines of progress.txt)

### Risk 2: Process Orphaning
**Impact:** If MCP server crashes, ralph jobs keep running but lose tracking.
**Mitigation:**
- Job state persists to disk (job.json survives crashes)
- PID verification on status checks (detect orphans)
- Dashboard shows all jobs, even orphaned ones

### Risk 3: Platform Differences
**Impact:** Subprocess management differs on Windows vs Unix.
**Mitigation:**
- Follow loop_service.py patterns (proven cross-platform)
- Comprehensive platform tests
- Use platform.system() checks consistently

### Risk 4: Stale Settings
**Impact:** Settings reference models that are no longer available from provider.
**Mitigation:**
- Live model discovery always authoritative (call `provider.get_models()`)
- Settings are overlays, not source of truth
- Stale metadata entries silently ignored

---

## Success Metrics

1. **LLM can complete a full plan+build cycle entirely through MCP tool calls** (end-to-end workflow)
2. **Provider/model discovery returns accurate, settings-filtered results** (live discovery works)
3. **Job status is always queryable and reflects real subprocess state** (PID verification works)
4. **Summarizer produces actionable summaries from loop artifacts** (AI summary is useful)
5. **Dashboard shows ralph jobs with real-time status and output** (visual monitoring works)
6. **No regression in standalone CLI ralph scripts** (backward compatibility maintained)

---

## Notes

### Critical Implementation Details

1. **Subprocess Spawning Must Match ralph.py:**
   - Import `LOOP_SCRIPT_TEMPLATE` from `portable.ralph`
   - Use `provider.get_invocation("ps1" or "sh")`
   - Same cwd, same command structure
   - Only difference: `subprocess.Popen` instead of `subprocess.run`

2. **Live Model Discovery (Never Hardcode):**
   - Always call `provider.get_models()` first
   - Settings only store filters and metadata overlays
   - Models not in `get_models()` output are ignored

3. **Both-Level Provider Enabling:**
   - Provider must be enabled in top-level `providers` section
   - AND in `ralph.providers` section
   - Both checks required

4. **PID Verification Pattern:**
   - Windows: `OpenProcess` with PROCESS_QUERY_INFORMATION
   - Unix: `os.kill(pid, 0)`
   - Check on every status query

5. **Ad-Hoc Template Adaptation:**
   - New templates: `PROMPT_plan_adhoc.md`, `PROMPT_build_adhoc.md`
   - Remove specs/, arch/ references
   - task.md is the source of truth

### Testing Priorities

1. **Critical Path:** Phases 1-4 (Settings → Job Management → Summarizer → MCP Tools)
2. **Integration:** Full lifecycle with real subprocess
3. **Platform:** Windows and Unix subprocess handling
4. **Edge Cases:** Dead PIDs, stale settings, invalid inputs

### Future Enhancements (Out of Scope for v1)

- SSE streaming for real-time progress (use polling for v1)
- Job history/archiving (keep all jobs indefinitely for v1)
- Multi-project support (single project for v1)
- Advanced filtering (regex on slug, date range)
- Job cancellation during "queued" state
- Retry failed jobs
- Job templates (pre-defined task descriptions)

---

**End of Implementation Plan**
