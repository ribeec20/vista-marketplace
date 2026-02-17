# Domain Requirements: Ralph MCP Tool

## Problem Statement

Vista's ralph loop runner currently operates as a standalone CLI tool (PowerShell/Bash/Python scripts) that users invoke manually outside of their AI coding session. There is no way for an LLM inside a Claude Code session to programmatically kick off, monitor, or retrieve results from ralph loops. Users must context-switch between their conversation and terminal to run planning/build loops, losing conversational context and requiring manual coordination.

The ralph MCP tool bridges this gap by exposing ralph loop operations as MCP tools that Claude Code (or any MCP-compatible client) can call directly within a conversation.

## Users & Personas

### Primary: AI Coding Assistant (Claude Code)
- The LLM orchestrator that calls MCP tools on behalf of the user
- Needs to discover available providers/models, start loops, poll status, get summaries, and stop loops
- Must work within the 60-second MCP tool timeout constraint

### Secondary: Developer (Human User)
- Directs Claude to run ralph loops via natural language (e.g., "Refactor the API handlers. Use ralph.")
- May specify a preferred model or CLI provider in their prompt
- Reviews plans and build artifacts via the Vista dashboard or conversation
- Configures available providers, models, and summarizer settings

## Business Objectives

1. Enable LLM-driven orchestration of ralph loops without leaving the conversation
2. Provide a unified settings system for provider/model discovery and filtering
3. Maintain full visibility into loop progress via dashboard integration
4. Keep the existing standalone CLI scripts working unchanged (MCP tools are a thin orchestration layer)

## Success Metrics

- LLM can complete a full plan+build cycle entirely through MCP tool calls
- Provider/model discovery returns accurate, settings-filtered results
- Job status is always queryable and reflects real subprocess state
- Summarizer produces actionable summaries from loop artifacts
- Dashboard shows ralph jobs with real-time status and output
- No regression in standalone CLI ralph scripts

## Functional Requirements

### Core Functionality

#### MCP Tools (5 tools)

1. **ralph_providers** - Discover available providers and models
   - Returns all enabled providers with their available models
   - Respects settings-based filtering (provider enable/disable + per-model allowlist/blocklist)
   - Includes summarizer configuration (predefined provider/model)
   - Read-only, instant response

2. **ralph_start** - Start a loop as a background subprocess
   - Accepts: slug, mode ("plan"|"build"), provider, model, iterations
   - Creates `.vista/ralph/{slug}/` working directory
   - Writes prompt files using existing portable templates
   - Spawns loop subprocess (detached from MCP process)
   - Returns immediately with a job ID
   - Must not block beyond a few seconds

3. **ralph_status** - Check job progress
   - Accepts: job_id
   - Returns: status (queued|running|completed|failed|stopped), current iteration, total iterations, last progress line
   - Lightweight - reads process state and tail of progress.txt
   - Instant response, no subprocess spawning

4. **ralph_summary** - Get AI-generated summary of job artifacts
   - Accepts: job_id
   - Runs summarizer agent (configurable provider/model from settings)
   - Reads progress.txt, IMPLEMENTATION_PLAN.md, git log from job directory
   - Returns structured summary for the orchestrator LLM
   - Works for both running and completed jobs
   - Spawns a subprocess; may take 10-30 seconds

5. **ralph_stop** - Terminate a running loop
   - Accepts: job_id
   - Sends termination signal to the loop subprocess
   - Updates job status to "stopped"
   - Returns confirmation

#### Unified Settings System

Extend `vista/settings.json` with a `ralph` section:

```json
{
  "ralph": {
    "defaults": {
      "provider": "claude",
      "model": "sonnet",
      "iterations": 3
    },
    "summarizer": {
      "provider": "claude",
      "model": "haiku",
      "cli": "claude"
    },
    "providers": {
      "claude": {
        "enabled": true,
        "models": ["opus", "sonnet", "haiku"]
      },
      "opencode": {
        "enabled": true,
        "models_blocked": []
      }
    }
  }
}
```

- **Provider-level filtering**: enable/disable entire providers
- **Per-model filtering**: optional `models` allowlist or `models_blocked` blocklist within enabled providers
- **Defaults**: fallback provider/model/iterations when not specified by the user
- **Summarizer config**: predefined provider, model, and CLI for the summarizer agent

#### Prompt Synthesis

- Claude synthesizes the user's conversational direction into prompt files
- Uses existing portable templates (`vista/portable/templates/PROMPT_plan.md`, `PROMPT_build.md`)
- Templates adapted for ad-hoc context: instead of looking for specs in `.vista/features/`, the agent looks for the task/domain requirements prompt in `.vista/ralph/{slug}/`
- Claude writes a `task.md` file in the slug directory capturing the user's intent

#### Ad-Hoc Working Directory

- Ralph MCP jobs live under `.vista/ralph/{slug}/`, NOT `.vista/features/`
- No pre-existing specs required - the user's conversation is the spec
- Each job directory contains:
  - `task.md` - User's intent synthesized by Claude
  - `PROMPT_plan.md` / `PROMPT_build.md` - Generated from templates
  - `progress.txt` - Updated by the loop worker each iteration
  - `IMPLEMENTATION_PLAN.md` - Output of planning loop
  - `AGENTS.md` - Operational docs (created by worker)

#### Dashboard Integration

- Ralph jobs appear in the Vista web dashboard
- Job list with status, provider, model, timestamps
- Real-time progress viewing (stream progress.txt)
- Output log viewing
- Link to job artifacts on disk

### User Workflows

1. **Discovery Flow**: User asks Claude to use ralph -> Claude calls `ralph_providers` to discover available options -> Claude selects or asks user about provider/model
2. **Plan Flow**: Claude calls `ralph_start(slug, "plan", ...)` -> polls `ralph_status` -> calls `ralph_summary` when done -> presents plan to user
3. **Build Flow**: User approves plan -> Claude calls `ralph_start(slug, "build", ...)` -> same poll+summarize pattern -> reports what was built
4. **Monitoring Flow**: User asks "how's ralph doing?" -> Claude calls `ralph_status` for lightweight check, or `ralph_summary` for detailed AI summary
5. **Cancel Flow**: User says "stop ralph" -> Claude calls `ralph_stop`
6. **Dashboard Flow**: User opens Vista dashboard -> sees ralph jobs with status, progress, artifacts

### Business Rules

- A slug can only have one active job at a time (running or queued)
- Completed/failed/stopped jobs remain on disk indefinitely
- The summarizer agent is only spawned explicitly via `ralph_summary`, never automatically on status polls
- Settings filtering is applied at discovery time (`ralph_providers`), not at start time - the LLM is trusted to pass valid provider/model from the discovery results
- If no provider/model specified in `ralph_start`, use defaults from settings

## Non-Functional Requirements

- **Performance**: `ralph_start` must return within 5 seconds. `ralph_status` must return within 1 second. `ralph_summary` may take up to 60 seconds (within MCP timeout).
- **Platform**: Windows (primary), Linux/macOS (portable scripts already cross-platform)
- **Reliability**: Job state must survive MCP server restarts (state is on disk, not in-memory only)
- **Security**: No API keys stored in settings or job directories. Provider CLIs handle their own authentication.
- **Concurrency**: Multiple ralph jobs can run simultaneously (different slugs)

## Constraints & Dependencies

- **Technical**: MCP tool calls have a hard 60-second timeout. Long-running loops MUST use async start + poll pattern.
- **Dependencies**: Existing `vista/server/services/provider_service.py` for provider abstraction. Existing `vista/portable/templates/` for prompt templates. Existing `vista/server/services/loop_service.py` for subprocess management patterns.
- **Compatibility**: Must not break existing standalone ralph CLI scripts. MCP tools are a new orchestration layer on top of existing infrastructure.
- **MCP Protocol**: Tools must return strings. Tool descriptions come from docstrings. Parameter schemas from type hints.

## User Experience Requirements

- **Discovery**: LLM calls `ralph_providers` as the entry point; user sees available options in conversation
- **Journey**: Natural language -> tool discovery -> start -> poll -> summarize -> present -> iterate
- **Feedback**: Status tool provides lightweight progress. Summary tool provides rich AI-generated report. Dashboard provides visual monitoring.
- **Error handling**: Clear error messages for: invalid slug, no available providers, subprocess crash, provider CLI not found, model not available
