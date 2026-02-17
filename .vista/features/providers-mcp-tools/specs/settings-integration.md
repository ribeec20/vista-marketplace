# Spec: Settings Integration

## Problem Statement

The providers tool group needs settings for:
1. Enabling/disabling the tool group itself (`tools.providers.enabled`)
2. Default timeout for `invoke_provider`
3. Model metadata (cost tier, best-for) is already stored under `ralph.providers` — should `list_providers` use the same metadata or have its own?

## Proposed Solution

### Tool Group Settings

Add to `_TOOLS_DEFAULTS` in `config.py`:

```python
_TOOLS_DEFAULTS = {
    "teams": { "enabled": False, "claude_binary": None, "opencode_url": None },
    "ralph": { "enabled": True },
    "providers": {
        "enabled": True,
        "default_timeout": 120,
    },
}
```

In `settings.json`:
```json
{
  "tools": {
    "providers": {
      "enabled": true,
      "default_timeout": 120
    }
  }
}
```

### Model Metadata Reuse

`list_providers` reuses the metadata already defined in `ralph.providers` settings. The `get_ralph_providers()` function already does:
1. Live discovery via `provider.get_models()`
2. Filtering via `models_allowed` / `models_blocked`
3. Metadata enrichment via `model_metadata`

`list_providers` calls the same function and strips the ralph-specific outer structure (no `defaults`, no `summarizer`). This avoids duplicating metadata configuration.

**Rationale**: Having two places to configure model metadata (one for ralph, one for general providers) would be confusing. One source of truth under `ralph.providers` is sufficient. If this naming becomes awkward in the future, the settings key can be renamed.

### Timeout Configuration

The `invoke_provider` tool accepts a per-call `timeout` parameter but falls back to `settings.tools.providers.default_timeout` (default 120s). The `register()` function passes the settings to the tool via closure.

## Data Requirements

- Settings read fresh on each tool call (via `config.get_tools_settings()`)
- No caching needed
- No write-back from tools (read-only)

## Edge Cases

- **Missing `tools.providers` section**: Falls back to `_TOOLS_DEFAULTS` (enabled=True, timeout=120)
- **Timeout of 0**: Treated as "no timeout" (subprocess runs indefinitely). Not recommended but allowed.
- **Negative timeout**: Clamped to 0.

## Dependencies

- `vista/server/config.py` — `_TOOLS_DEFAULTS`, `get_tools_settings()`
- `vista/settings.json` — User-facing config
- Spec: [mcp-tools](mcp-tools.md) — Consumer of settings

## Testing Strategy

- Unit test: Default settings applied when section missing
- Unit test: Custom timeout passed through to `invoke_provider`
- Unit test: Settings merge preserves existing sections
