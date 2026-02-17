# Spec: Unified Settings System

## Problem Statement

The existing `vista/settings.json` has a top-level `providers` section for enabling/disabling CLI providers, but lacks:
- Per-model filtering (allowlist/blocklist within a provider)
- Model metadata (cost tier, best-for tags) so the LLM can choose intelligently
- Default provider/model/iteration configuration for ralph loops
- Summarizer agent configuration (which provider/model to use)
- Ralph-specific settings

Users need to control which models are available for MCP tool calling, annotate models with cost and capability metadata, and pre-configure the summarizer agent — all without modifying code.

## Critical Design Principle: Live Model Discovery

**Model lists are NEVER hardcoded in settings.** The canonical source of available models is always `provider.get_models()` — the same method used by `ralph.py` (line 295) and the existing loop scripts.

- `ClaudeProvider.get_models()` returns `["opus", "sonnet", "haiku"]`
- `OpenCodeProvider.get_models()` calls `opencode models` CLI and parses output live

The settings file only stores **overlays** on top of live-discovered models:
- Which models are allowed/blocked (filtering)
- Metadata per model (cost tier, best-for tags/notes)

If a model appears in settings but not in `provider.get_models()`, it is ignored. If a model appears in `provider.get_models()` but not in settings, it is available with default metadata (no cost tier, no best-for).

## Proposed Solution

Extend `vista/settings.json` with a `ralph` section. The existing top-level `providers` section continues to work for the standalone CLI scripts. The new `ralph.providers` section adds MCP-specific filtering and model metadata on top.

### Settings Schema

```json
{
  "server": {
    "auto_start": true,
    "auto_open_browser": true,
    "host": "127.0.0.1",
    "port": 3456
  },
  "providers": {
    "claude": {
      "enabled": true,
      "display_name": "Claude Code"
    },
    "opencode": {
      "enabled": true,
      "display_name": "OpenCode"
    }
  },
  "ralph": {
    "defaults": {
      "provider": "claude",
      "model": "sonnet",
      "iterations": 3
    },
    "summarizer": {
      "provider": "claude",
      "model": "haiku"
    },
    "providers": {
      "claude": {
        "enabled": true,
        "models_allowed": ["opus", "sonnet", "haiku"],
        "models_blocked": [],
        "model_metadata": {
          "opus": {
            "cost_tier": "expensive",
            "best_for_tags": ["complex reasoning", "architecture", "debugging"],
            "best_for_notes": "Best for tasks requiring deep analysis"
          },
          "sonnet": {
            "cost_tier": "moderate",
            "best_for_tags": ["code generation", "planning", "general"],
            "best_for_notes": "Good all-rounder, fast enough for iteration loops"
          },
          "haiku": {
            "cost_tier": "cheap",
            "best_for_tags": ["fast iteration", "simple tasks", "summarization"],
            "best_for_notes": ""
          }
        }
      },
      "opencode": {
        "enabled": true,
        "models_allowed": [],
        "models_blocked": [],
        "model_metadata": {}
      }
    }
  }
}
```

### Model Metadata Fields

Each model can have these optional metadata fields stored in `model_metadata`:

| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| `cost_tier` | string | `"free"`, `"cheap"`, `"moderate"`, `"expensive"` | Informational — LLM uses this to make cost-aware choices |
| `best_for_tags` | string[] | Predefined tags from curated list | Quick categorization for LLM model selection |
| `best_for_notes` | string | Freeform text | Additional context the user wants the LLM to consider |

**Predefined best_for_tags** (curated list, UI shows these as multi-select):
- `"complex reasoning"`, `"architecture"`, `"debugging"`, `"code generation"`,
  `"planning"`, `"code review"`, `"fast iteration"`, `"simple tasks"`,
  `"summarization"`, `"refactoring"`, `"testing"`, `"general"`

The cost tier and best-for metadata are **purely informational**. The LLM reads them from `ralph_providers` and uses its judgment to pick the best model for the task. No hard rules are enforced.

### Filtering Logic

1. **Provider-level**: A provider must be enabled in BOTH `providers` (top-level) AND `ralph.providers` to be available for ralph MCP tools. If `ralph.providers` is omitted, all top-level enabled providers are available.

2. **Model-level** (within an enabled provider):
   - **Live discovery first**: Call `provider.get_models()` to get the canonical model list
   - If `models_allowed` is non-empty: intersect with live models (only allowed models that actually exist)
   - If `models_blocked` is non-empty: subtract from live models (exclude blocked models)
   - If both are empty: all live-discovered models are available
   - `models_allowed` takes precedence if both are non-empty
   - Models in settings but NOT in `provider.get_models()` are silently ignored

3. **Metadata overlay**: After filtering, attach `model_metadata` entries to each surviving model. Models without metadata entries get default values (`cost_tier: null`, `best_for_tags: []`, `best_for_notes: ""`).

4. **Defaults**: Used when `ralph_start` is called without explicit provider/model/iterations
   - `defaults.provider` must reference an enabled provider
   - `defaults.model` must be an available model for the default provider
   - `defaults.iterations` must be a positive integer

5. **Summarizer**: Pre-configured provider/model for the summarizer agent
   - Used by `ralph_summary` tool
   - Not subject to the same filtering as loop providers (summarizer might use a cheap model not in the loop allowlist)

### API Surface

Extend `vista/server/services/provider_service.py`:

```python
def get_ralph_providers() -> list[dict]:
    """Return enabled providers with filtered model lists and metadata for ralph MCP tools.

    For each provider:
    1. Call provider.get_models() for live discovery (same as ralph.py line 295)
    2. Apply models_allowed / models_blocked filtering from ralph settings
    3. Attach model_metadata (cost_tier, best_for_tags, best_for_notes) to each model
    4. Return structured dict with provider info + enriched model list
    """

def get_ralph_defaults() -> dict:
    """Return default provider/model/iterations for ralph_start."""

def get_summarizer_config() -> dict:
    """Return summarizer provider/model configuration."""
```

Return format from `get_ralph_providers()`:

```json
[
  {
    "name": "claude",
    "display_name": "Claude Code",
    "models": [
      {
        "id": "opus",
        "cost_tier": "expensive",
        "best_for_tags": ["complex reasoning", "architecture"],
        "best_for_notes": "Best for tasks requiring deep analysis"
      },
      {
        "id": "sonnet",
        "cost_tier": "moderate",
        "best_for_tags": ["code generation", "planning"],
        "best_for_notes": "Good all-rounder"
      }
    ]
  }
]
```

### Settings Write-Back

The dashboard settings UI (see spec: [settings-ui](settings-ui.md)) needs to write changes back to `settings.json`:

```python
def save_ralph_settings(ralph_config: dict) -> None:
    """Write the ralph section back to settings.json, preserving other sections."""
```

This reads the full file, updates only the `ralph` key, and writes back. Preserves comments and formatting where possible (use `json.dumps` with indent=2).

## Data Requirements

- Settings file: `vista/settings.json` (existing, extended)
- Schema validation on load (fail gracefully with warnings for invalid config)
- Settings read on each tool call (no caching needed for v1)
- Write-back from dashboard UI must be atomic (no partial writes)

## Edge Cases

- **No ralph section**: Fall back to top-level providers with all live-discovered models, no metadata, default iterations=3
- **ralph.providers references a disabled top-level provider**: Provider is not available (both levels must be enabled)
- **Default model not in allowlist**: Warning on load, but don't crash. `ralph_start` will fail at call time with a clear error
- **Empty models_allowed array**: All live-discovered models are available (empty = no filter, not "block all")
- **Provider CLI not installed**: `get_models()` returns empty list, provider appears with zero models
- **Model in metadata but not in get_models()**: Metadata entry is silently ignored (stale config)
- **Model in get_models() but not in metadata**: Model is available with default metadata (null cost_tier, empty tags)
- **Concurrent settings UI save + MCP tool call**: Acceptable race — next tool call reads latest file

## Dependencies

- `vista/server/config.py` (existing) - Settings loading
- `vista/server/services/provider_service.py` (existing) - Provider abstraction with `get_models()` and `get_invocation()`
- Spec: [mcp-tools](mcp-tools.md) - Consumes settings via `ralph_providers` and `ralph_start`
- Spec: [settings-ui](settings-ui.md) - Dashboard page that writes settings back

## Testing Strategy

- Unit tests for filtering logic (allowlist, blocklist, both-levels, both-present)
- Unit tests for live model discovery + filter intersection (mock `provider.get_models()`)
- Unit tests for metadata overlay (present, missing, stale entries)
- Unit tests for defaults resolution
- Unit tests for edge cases (missing section, empty arrays, invalid config, stale metadata)
- Unit tests for settings write-back (preserves other sections, atomic write)
- Integration test: settings -> `ralph_providers` returns correctly filtered and enriched list
