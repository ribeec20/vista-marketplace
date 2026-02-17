# Spec: MCP Tool Definitions

## Problem Statement

Vista needs a `providers` tool group (following the `tool_groups/` pattern established by teams and ralph) that registers two tools: one for provider/model discovery and one for one-shot CLI invocation.

## Proposed Solution

Create `vista/tool_groups/providers_tools.py` with `register(mcp, settings)` function that registers 2 tools.

### Tool Group Registration

In `tool_groups/__init__.py`, add to `_TOOL_GROUPS`:
```python
_TOOL_GROUPS = {
    "teams": "tool_groups.teams_tools",
    "ralph": "tool_groups.ralph_tools",
    "providers": "tool_groups.providers_tools",  # NEW
}
```

In `server/config.py`, add to `_TOOLS_DEFAULTS`:
```python
_TOOLS_DEFAULTS = {
    ...
    "providers": {
        "enabled": True,  # On by default — core functionality
        "default_timeout": 120,
    },
}
```

### Tool 1: `list_providers`

```python
@mcp.tool()
async def list_providers() -> str:
    """Discover available CLI agent providers and their models.

    Returns a JSON object with:
    - providers: list of enabled providers, each with name, display_name,
      and available models (discovered live from CLIs)
    - models include optional cost_tier, best_for_tags, best_for_notes
      metadata from settings to help choose the right model

    Use this before invoke_provider to see what's available.
    """
```

- **Parameters**: None
- **Returns**: JSON string
- **Side effects**: May invoke CLI commands for model discovery (e.g. `opencode models`)
- **Timeout**: Should complete within 15s worst case

**Return format**:
```json
{
  "providers": [
    {
      "name": "claude",
      "display_name": "Claude Code",
      "models": [
        {
          "id": "sonnet",
          "cost_tier": "moderate",
          "best_for_tags": ["code generation", "planning"],
          "best_for_notes": "Good all-rounder"
        }
      ]
    },
    {
      "name": "opencode",
      "display_name": "OpenCode",
      "models": [
        { "id": "gemini-2.5-pro", "cost_tier": null, "best_for_tags": [], "best_for_notes": "" }
      ]
    }
  ]
}
```

**Implementation**: Reuses existing `get_ralph_providers()` from `provider_service.py` — this function already does live discovery, settings filtering, and metadata enrichment. The ralph-specific parts (defaults, summarizer) are simply not included in the response.

**Difference from `ralph_providers`**: `ralph_providers` returns `{providers, defaults, summarizer}` for ralph loop context. `list_providers` returns only `{providers}` — general-purpose discovery without ralph-specific baggage.

### Tool 2: `invoke_provider`

```python
@mcp.tool()
async def invoke_provider(
    provider: str,
    model: str,
    prompt: str,
    timeout: int = 120,
) -> str:
    """Send a prompt to a CLI agent and get the complete response.

    Spawns a one-shot CLI process, pipes the prompt via stdin, and
    returns the response text. The process runs to completion or
    until the timeout is reached.

    Use list_providers first to see available providers and models.

    :param provider: Provider name (e.g. "claude", "opencode")
    :param model: Model name (e.g. "sonnet", "gemini-2.5-pro")
    :param prompt: The prompt to send
    :param timeout: Max seconds to wait (default 120)
    """
```

- **Parameters**: provider (required), model (required), prompt (required), timeout (optional)
- **Returns**: The CLI's response text as a string
- **Side effects**: Spawns subprocess, blocks until completion
- **Timeout**: Configurable per-call, default from settings

**Implementation flow**:
1. Look up provider in `_PROVIDER_REGISTRY` via `get_provider_by_name()`
2. Validate provider is enabled (via `get_enabled_providers()`)
3. Validate model is available (via `provider.get_models()`)
4. Get CLI command via `provider.get_chat_cmd(model)`
5. If `get_chat_cmd()` returns None: CLI binary not found, return error
6. Spawn subprocess with existing `_run_cli_with_timeout()` infrastructure:
   - `stdin=PIPE`, write prompt, close stdin (signals EOF → response)
   - `stdout=PIPE`, `stderr=PIPE`
   - `CREATE_NO_WINDOW` on Windows
   - `.cmd`/`.bat` wrapper handling
7. On success: return stdout text
8. On timeout: kill process tree, return error
9. On non-zero exit: return error with stderr

**Error responses** (returned as JSON with `error` key, matching teams/ralph pattern):
- `{"error": "Provider 'foo' not found. Available: claude, opencode"}`
- `{"error": "Provider 'opencode' is not enabled"}`
- `{"error": "'opencode' binary not found on PATH"}`
- `{"error": "Model 'gpt-4' not available for opencode. Available: gemini-2.5-pro, ..."}`
- `{"error": "Provider timed out after 120s"}`
- `{"error": "Provider exited with code 1: <stderr snippet>"}`

## Data Requirements

- Both tools return strings (JSON for list_providers, plain text for invoke_provider success, JSON for errors)
- No persistent state needed — stateless tool group
- Settings read fresh on each call

## Edge Cases

- **Both stdout and stderr have content**: Return stdout as response. Include stderr only in error messages.
- **Empty response**: Return empty string (not an error — the CLI may legitimately produce no output)
- **Very large response**: No truncation. MCP handles large strings.
- **Concurrent invocations**: Each spawns its own subprocess, no shared state. Safe.
- **CLI binary is a `.cmd` wrapper (Windows)**: Existing `_run_cli_with_timeout()` already handles this with `cmd.exe /c` prefix.

## Dependencies

- `vista/server/services/provider_service.py` — Provider registry, `get_chat_cmd()`, `get_ralph_providers()`, `get_provider_by_name()`
- `vista/server/config.py` — Settings loading
- `vista/tool_groups/__init__.py` — Tool group registration
- Spec: [provider-registry](provider-registry.md) — Provider base class requirements

## Testing Strategy

- Unit test: `list_providers` returns correct JSON structure with mocked providers
- Unit test: `invoke_provider` with mocked subprocess (success, timeout, error exit)
- Unit test: Error cases (unknown provider, disabled provider, missing binary, unavailable model)
- Unit test: Error JSON format matches teams/ralph pattern
- Integration test: `list_providers` with real Claude provider
- Integration test: `invoke_provider("claude", "haiku", "Say hello in one word")` returns non-empty
