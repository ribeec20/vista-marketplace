# Spec: Provider Registry Extensibility

## Problem Statement

The existing `Provider` base class and `_PROVIDER_REGISTRY` work but have two gaps:

1. **Undocumented contract**: Which methods are required vs optional is implicit. A developer adding a new backend has to read all existing implementations to figure out the minimum.

2. **Teams spawner divergence**: The teams tool group (`teams_tools.py`) uses `discover_harness_binary()` from claude-teams for backend discovery instead of Vista's `Provider` registry. The Provider base class lacks the metadata the teams spawner needs (binary name, spawn style).

## Proposed Solution

### 1. Document the Provider contract

Add clear docstrings to the `Provider` base class categorizing methods:

**Required** (must override — raise `NotImplementedError` by default):
- `get_models() -> list[str]` — Live model discovery
- `get_chat_cmd(model, *, streaming, permissions) -> list[str] | None` — One-shot invocation command
- `get_invocation(shell) -> str` — Shell snippet for ralph scripts

**Optional** (have working defaults):
- `get_summarizer_command(model) -> list[str]` — Falls back to `get_chat_cmd()` if not overridden
- `get_persistent_cmd(model, *, permissions) -> list[str] | None` — Returns `None` (not supported)
- `parse_stream_event(line) -> dict | None` — Returns `None` (no streaming)
- `supports_streaming -> bool` — Returns `False`
- `stdin_pipe -> bool` — Returns `True`
- `to_dict() / to_summary_dict()` — Serialization (working defaults exist)

### 2. Add `get_spawn_info()` for teams integration (future)

```python
def get_spawn_info(self) -> dict:
    """Return metadata for the teams spawner to know how to launch
    this provider as a teammate.

    Override this in subclasses that have specific spawn requirements.
    """
    return {
        "binary": self.name,
        "spawn_style": "generic-cli",
        "supports_interactive": False,
    }
```

This is a forward-looking addition. The current teams spawner won't use it yet, but it signals the architectural direction: Provider registry becomes the single source of truth for all provider capabilities.

### 3. Ensure `get_summarizer_command()` has a fallback

Currently `get_summarizer_command()` raises `NotImplementedError` in the base class, but it's not truly required — a sensible default is to use `get_chat_cmd()`:

```python
def get_summarizer_command(self, model: str) -> list[str]:
    """Return CLI command for summarizer invocation.

    Default: falls back to get_chat_cmd() if not overridden.
    """
    cmd = self.get_chat_cmd(model)
    return cmd if cmd else []
```

### 4. Adding a new provider (documented pattern)

Example for a hypothetical GeminiProvider:

```python
class GeminiProvider(Provider):
    name = "gemini"
    display_name = "Gemini CLI"

    def get_models(self) -> list[str]:
        cmd = _find_command("gemini")
        if cmd is None:
            return []
        output = _run_cli_with_timeout([cmd, "models"], timeout=10)
        if output is None:
            return []
        return [line.strip() for line in output.splitlines() if line.strip()]

    def get_invocation(self, shell: str = "ps1") -> str:
        if shell == "sh":
            return 'gemini run --model "$MODEL" "$(cat "$PROMPT_FILE")"'
        return "gemini run --model $Model $PromptContent"

    def get_chat_cmd(self, model: str, *, streaming=False, permissions=False):
        cmd_path = _find_command("gemini")
        if cmd_path is None:
            return None
        return [cmd_path, "run", "--model", model]

# Register:
_PROVIDER_REGISTRY["gemini"] = GeminiProvider

# Settings entry in settings.json:
# "providers": { "gemini": { "enabled": true, "display_name": "Gemini CLI" } }
```

## Data Requirements

- `_PROVIDER_REGISTRY` is module-level, populated at import time
- Provider instances created fresh per `get_enabled_providers()` call
- No thread safety issues (registry is read-only after module load)

## Edge Cases

- **Provider in registry, CLI not installed**: `get_models()` returns `[]`, `get_chat_cmd()` returns `None`. Provider listed but with zero models.
- **Provider in settings, not in registry**: Silently skipped by `get_enabled_providers()`
- **Provider in registry, not in settings**: Not returned by `get_enabled_providers()` (settings gate)

## Dependencies

- `vista/server/services/provider_service.py` — All changes here
- `vista/tool_groups/teams_tools.py` — Future consumer of `get_spawn_info()`
- Spec: [mcp-tools](mcp-tools.md) — Consumer of provider registry

## Testing Strategy

- Unit test: Subclass with only required methods works correctly
- Unit test: `get_summarizer_command()` fallback to `get_chat_cmd()`
- Unit test: `get_spawn_info()` default and override
- Unit test: `get_enabled_providers()` respects settings enabled/disabled
