# Spec: MCP Tool Definitions

## Problem Statement

Vista's MCP server (`vista/mcp_server.py`) currently registers zero tools. We need to register 5 ralph-related MCP tools using the FastMCP pattern so that Claude Code can discover and call them during a conversation.

## Proposed Solution

Register 5 tools directly on the `FastMCP` instance in `vista/mcp_server.py` using the `@mcp.tool()` decorator pattern. Each tool is a simple async function with typed parameters and a docstring (which becomes the tool description for the LLM).

### Tool 1: `ralph_providers`

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
```

- **Parameters**: None
- **Returns**: JSON string with providers (including per-model cost_tier, best_for_tags, best_for_notes), defaults, summarizer config
- **Side effects**: None (read-only)
- **Timeout concern**: Calls `provider.get_models()` which may invoke CLI commands (e.g., `opencode models` with 10s timeout). Should complete within 15 seconds worst case.

**Critical implementation detail**: This tool calls the exact same `provider.get_models()` that `ralph.py` line 295 uses. Models are discovered live from the provider CLIs, then filtered by settings (allowlist/blocklist), then enriched with metadata (cost_tier, best_for_tags, best_for_notes) from settings. The LLM uses this metadata to autonomously pick the best model for the task — no hardcoded model names anywhere.

**Return format**:
```json
{
  "providers": [
    {
      "name": "claude",
      "display_name": "Claude Code",
      "models": [
        {
          "id": "opus",
          "cost_tier": "expensive",
          "best_for_tags": ["complex reasoning", "architecture", "debugging"],
          "best_for_notes": "Best for tasks requiring deep analysis"
        },
        {
          "id": "sonnet",
          "cost_tier": "moderate",
          "best_for_tags": ["code generation", "planning", "general"],
          "best_for_notes": "Good all-rounder, fast enough for iteration loops"
        }
      ]
    }
  ],
  "defaults": { "provider": "claude", "model": "sonnet", "iterations": 3 },
  "summarizer": { "provider": "claude", "model": "haiku" }
}
```

### Tool 2: `ralph_start`

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
```

- **Parameters**: slug (required), mode (required), task_description (required), provider/model/iterations (optional, fall back to settings defaults)
- **Returns**: JSON string with `{job_id, slug, status, working_dir}`
- **Side effects**: Creates directory, writes files, spawns subprocess
- **Timeout concern**: Must return within 5 seconds. Subprocess is fire-and-forget.

### Tool 3: `ralph_status`

```python
@mcp.tool()
async def ralph_status(job_id: str) -> str:
    """Check the status and progress of a ralph job.

    Returns lightweight status information. For a detailed AI-generated summary,
    use ralph_summary instead.

    :param job_id: The job ID returned by ralph_start
    """
```

- **Parameters**: job_id (required)
- **Returns**: JSON string with `{job_id, status, current_iteration, total_iterations, last_progress_lines, elapsed_time}`
- **Side effects**: None (reads process state + progress.txt)
- **Timeout concern**: Must return within 1 second.

### Tool 4: `ralph_summary`

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
```

- **Parameters**: job_id (required)
- **Returns**: JSON string with structured summary (phases, findings, recommendations)
- **Side effects**: Spawns summarizer subprocess
- **Timeout concern**: May take 10-30 seconds. Must complete within 60 seconds (MCP limit).

### Tool 5: `ralph_stop`

```python
@mcp.tool()
async def ralph_stop(job_id: str) -> str:
    """Stop a running ralph loop.

    Sends a termination signal to the loop subprocess and updates the job status.

    :param job_id: The job ID returned by ralph_start
    """
```

- **Parameters**: job_id (required)
- **Returns**: JSON string with `{job_id, status: "stopped", message}`
- **Side effects**: Terminates subprocess, updates job state
- **Timeout concern**: Should complete within 5 seconds.

## Data Requirements

- All tools return JSON strings (MCP protocol requirement)
- Job IDs are generated UUIDs stored in a `job.json` file in the job directory
- Job state is persisted to disk (survives MCP server restarts)

## Edge Cases

- **Duplicate slug**: If `.vista/ralph/{slug}/` exists with an active job, `ralph_start` returns an error
- **Invalid job_id**: All tools return a clear error message
- **Process crash**: `ralph_status` detects dead process (PID check) and updates status to "failed"
- **Provider not found**: `ralph_start` returns error if specified provider isn't enabled
- **Model not available**: `ralph_start` returns error if specified model isn't in the filtered list

## Dependencies

- `vista/server/services/ralph_service.py` (new) - Business logic for job management
- `vista/server/services/provider_service.py` (existing) - Provider/model discovery
- `vista/server/config.py` (existing) - Settings loading
- Spec: [settings](settings.md) - Settings schema
- Spec: [job-management](job-management.md) - Job lifecycle
- Spec: [summarizer](summarizer.md) - Summarizer agent

## Testing Strategy

- Unit tests for each tool function with mocked services
- Integration test: start -> status -> stop lifecycle
- Integration test: start -> status (wait for completion) -> summary
- Edge case tests: duplicate slug, invalid job_id, missing provider
- Timeout tests: verify tools return within their time budgets
