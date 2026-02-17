# Domain Requirements: providers-mcp-tools

## Problem Statement

Vista now has a tool group registry (`tool_groups/`) with teams (13 tools) and ralph (5 tools) registered. However:

1. **No general-purpose provider discovery tool.** `ralph_providers` exists but is scoped to ralph loops (includes ralph-specific defaults, summarizer config, and model metadata filtered through ralph settings). There's no tool for an MCP client to simply ask "what CLI agents and models are available?"

2. **No way to invoke another CLI agent.** The teams spawner can spawn long-lived tmux-based agents, but there's no simple "send a prompt to OpenCode's gemini-2.5-pro and get the answer back" tool. This is the one-shot request/response pattern — the simplest and most common use case.

3. **The teams tool group does its own backend discovery** (`discover_harness_binary`) independently of Vista's `Provider` registry. The Provider registry should be the single source of truth for "what CLIs exist and what models they offer."

## Users & Personas

- **Claude Code user (primary)**: Wants to leverage other CLI agents during a conversation. "Let me ask Gemini to review this code" or "Use a cheaper model for this simple summarization."
- **Teams lead agent**: Needs to know which backends are available before spawning teammates. Currently hardcoded to claude/opencode.
- **Plugin developer**: Wants to add a new CLI backend (Gemini, Codex, Aider) by subclassing `Provider` and registering it.

## Business Objectives

- Make Vista a multi-CLI bridge — any MCP client can discover and invoke any installed CLI agent
- Provide the foundation that teams spawner should eventually use for backend discovery
- Keep the Provider interface simple: adding a new backend is ~50 lines of code
- Follow the established tool group pattern (`tool_groups/providers_tools.py`)

## Success Metrics

- `list_providers` returns accurate provider/model data within 15 seconds
- `invoke_provider` successfully pipes a prompt and returns a response for both Claude and OpenCode
- New tool group follows the same `register(mcp, settings)` pattern as teams/ralph
- Both tools discoverable and callable from Claude Code via MCP

## Functional Requirements

### Core Functionality

1. **`list_providers` MCP tool**: Returns all enabled providers with their models and optional metadata (cost tier, best-for tags). Uses live model discovery (`provider.get_models()`). General-purpose — not scoped to ralph settings.

2. **`invoke_provider` MCP tool**: Accepts provider name, model, prompt, and optional timeout. Spawns a one-shot CLI process via `get_chat_cmd()`, pipes prompt via stdin, returns the complete response. Simple request/response pattern.

3. **`providers` tool group**: New module `tool_groups/providers_tools.py` with `register(mcp, settings)`. Registered in `_TOOL_GROUPS` dict. Gated by `tools.providers.enabled` in settings.

4. **Provider registry extensibility**: Document which Provider methods are required vs optional. Make it clear how to add a new backend (subclass + register + settings entry).

### User Workflows

1. **Discovery**: Claude calls `list_providers` → sees claude (opus/sonnet/haiku) and opencode (gemini-2.5-pro/...) → picks the right model
2. **Invoke**: Claude calls `invoke_provider("opencode", "gemini-2.5-pro", "Review this code: ...")` → gets response text
3. **With teams**: Lead agent calls `list_providers` to see what's available, then `teams_spawn_teammate` with the right `backend_type` and `model`

### Business Rules

- Provider must be enabled in `settings.json` providers section to appear
- Model lists always from `provider.get_models()`, never hardcoded
- `invoke_provider` respects configurable timeout (default 120s)
- Prompts sent via stdin pipe, not CLI arguments (security)
- If CLI binary not found, provider appears with zero models (not an error)

## Non-Functional Requirements

- **Performance**: `list_providers` within 15s. `invoke_provider` within configured timeout.
- **Platform**: Windows (primary) + Linux/macOS
- **Security**: stdin piping, process-tree cleanup, `CREATE_NO_WINDOW` on Windows
- **Pattern compliance**: Follows tool group registry pattern exactly

## Constraints & Dependencies

- **Existing**: `provider_service.py` (Provider classes, registry), `config.py` (settings), `tool_groups/__init__.py` (registration)
- **In progress**: Teams tool group already ported — uses its own backend discovery. Future work to unify with Provider registry.
- **Infra**: `_find_command()`, `_run_cli_with_timeout()`, `get_chat_cmd()` all exist and should be reused
