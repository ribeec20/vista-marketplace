# Spec: Settings UI (Dashboard Page)

## Problem Statement

The ralph settings in `settings.json` control provider filtering, model metadata, defaults, and summarizer config. Currently these must be edited as raw JSON — error-prone and unfriendly. Users need a visual settings page in the Vista dashboard to manage these settings through dropdowns, toggles, and forms.

## Critical Design Principle: Live Model Discovery

**The settings UI must populate model lists by calling `provider.get_models()` live** — the exact same method used by `ralph.py` (line 295) and the `ralph_providers` MCP tool. Model names are NEVER hardcoded in the UI. The page loads available models from the API, then overlays the saved settings (enabled/blocked, cost tier, best-for) on top.

If a provider's CLI is not installed or returns no models, the UI shows that provider with an empty model list and a warning.

## Proposed Solution

A new dashboard page at `/settings/ralph` with sections for providers, models, defaults, and summarizer configuration. All changes save back to `vista/settings.json` via a PUT API endpoint.

### Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Ralph Settings                                        [Save]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─── Defaults ──────────────────────────────────────────────┐ │
│  │ Default Provider:  [claude        ▼]                       │ │
│  │ Default Model:     [sonnet        ▼]  (filtered by provider│ │
│  │ Default Iterations: [3            ]                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─── Summarizer ────────────────────────────────────────────┐ │
│  │ Provider:  [claude ▼]                                      │ │
│  │ Model:     [haiku  ▼]                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─── Providers & Models ────────────────────────────────────┐ │
│  │                                                            │ │
│  │  Claude Code                                    [Enabled ✓]│ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ Model    │ Allowed │ Cost Tier    │ Best For         │ │ │
│  │  ├──────────┼─────────┼─────────────┼──────────────────┤ │ │
│  │  │ opus     │  [✓]    │ [expensive▼] │ [complex rea..▼] │ │ │
│  │  │          │         │              │ Notes: [______]  │ │ │
│  │  ├──────────┼─────────┼─────────────┼──────────────────┤ │ │
│  │  │ sonnet   │  [✓]    │ [moderate▼]  │ [code gen, ..▼]  │ │ │
│  │  │          │         │              │ Notes: [______]  │ │ │
│  │  ├──────────┼─────────┼─────────────┼──────────────────┤ │ │
│  │  │ haiku    │  [✓]    │ [cheap   ▼]  │ [fast iter..▼]   │ │ │
│  │  │          │         │              │ Notes: [______]  │ │ │
│  │  └──────────┴─────────┴─────────────┴──────────────────┘ │ │
│  │                                                            │ │
│  │  OpenCode                                       [Enabled ✓]│ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ Model                    │ Allowed │ Cost │ Best For │ │ │
│  │  ├──────────────────────────┼─────────┼──────┼─────────┤ │ │
│  │  │ anthropic/claude-sonnet-4│  [✓]    │ [ ▼] │ [    ▼] │ │ │
│  │  │ openai/gpt-4             │  [✓]    │ [ ▼] │ [    ▼] │ │ │
│  │  │ google/gemini-pro        │  [ ]    │ [ ▼] │ [    ▼] │ │ │
│  │  └──────────────────────────┴─────────┴──────┴─────────┘ │ │
│  │  ⚠ Models loaded live from `opencode models` CLI          │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│                                                        [Save]   │
└─────────────────────────────────────────────────────────────────┘
```

### UI Components

#### Defaults Section
- **Default Provider**: Dropdown populated from enabled providers
- **Default Model**: Dropdown populated from allowed models of the selected provider (cascading — changes when provider changes)
- **Default Iterations**: Number input (min 1, max 100)

#### Summarizer Section
- **Provider**: Dropdown from all enabled providers (not subject to ralph model filtering)
- **Model**: Dropdown from all models of selected provider (not filtered)

#### Providers & Models Section
For each provider from `_PROVIDER_REGISTRY`:

- **Provider toggle**: Checkbox to enable/disable for ralph MCP tools
- **Model table**: One row per model from `provider.get_models()` (live discovery), with columns:
  - **Model name**: Read-only text (from live discovery)
  - **Allowed**: Checkbox (checked = in allowlist, unchecked = blocked)
  - **Cost Tier**: Dropdown with options: `(none)`, `free`, `cheap`, `moderate`, `expensive`
  - **Best For Tags**: Multi-select dropdown with predefined tags:
    - `complex reasoning`, `architecture`, `debugging`, `code generation`,
      `planning`, `code review`, `fast iteration`, `simple tasks`,
      `summarization`, `refactoring`, `testing`, `general`
  - **Best For Notes**: Freeform text input for additional context

#### Save Behavior
- **Save button** sends the entire ralph config to `PUT /api/settings/ralph`
- API endpoint reads current `settings.json`, updates only the `ralph` key, writes back
- Success: green toast notification "Settings saved"
- Failure: red toast notification with error message
- No auto-save — explicit save button to prevent accidental writes

### API Endpoints

```
GET  /api/settings/ralph           # Current ralph settings + live model lists
PUT  /api/settings/ralph           # Save ralph settings back to settings.json
GET  /api/settings/ralph/models    # Live model discovery for all providers (for UI refresh)
```

#### GET /api/settings/ralph

Returns the current settings merged with live model discovery:

```json
{
  "defaults": { "provider": "claude", "model": "sonnet", "iterations": 3 },
  "summarizer": { "provider": "claude", "model": "haiku" },
  "providers": {
    "claude": {
      "enabled": true,
      "display_name": "Claude Code",
      "live_models": ["opus", "sonnet", "haiku"],
      "models_allowed": ["opus", "sonnet", "haiku"],
      "models_blocked": [],
      "model_metadata": {
        "opus": {
          "cost_tier": "expensive",
          "best_for_tags": ["complex reasoning", "architecture"],
          "best_for_notes": "Best for deep analysis"
        }
      }
    },
    "opencode": {
      "enabled": true,
      "display_name": "OpenCode",
      "live_models": ["anthropic/claude-sonnet-4", "openai/gpt-4"],
      "models_allowed": [],
      "models_blocked": [],
      "model_metadata": {}
    }
  },
  "available_tags": [
    "complex reasoning", "architecture", "debugging", "code generation",
    "planning", "code review", "fast iteration", "simple tasks",
    "summarization", "refactoring", "testing", "general"
  ]
}
```

The `live_models` field comes from calling `provider.get_models()` at request time. The UI uses this to populate the model table rows. The `models_allowed`, `models_blocked`, and `model_metadata` fields come from the saved settings and are overlaid in the UI.

#### PUT /api/settings/ralph

Accepts the updated ralph config and writes to `settings.json`:

```json
{
  "defaults": { "provider": "claude", "model": "sonnet", "iterations": 3 },
  "summarizer": { "provider": "claude", "model": "haiku" },
  "providers": {
    "claude": {
      "enabled": true,
      "models_allowed": ["opus", "sonnet", "haiku"],
      "models_blocked": [],
      "model_metadata": { ... }
    }
  }
}
```

#### GET /api/settings/ralph/models

Refresh-only endpoint that calls `provider.get_models()` for all registered providers and returns live model lists. Used by the UI for a "Refresh Models" button without reloading the full page.

### Frontend Implementation

- Built with the same HTML template system (`_base.html`) and CSS/JS as existing dashboard pages
- Multi-select dropdowns for best_for_tags (can use a lightweight JS library or custom implementation)
- Cascading dropdowns: changing default provider updates default model dropdown
- Model table rows are dynamically generated from the API response
- "Refresh Models" button calls `/api/settings/ralph/models` to re-discover without page reload

## Data Requirements

- **Read**: `settings.json` for saved config, `provider.get_models()` for live models
- **Write**: `settings.json` (only the `ralph` key, preserving all other keys)
- **Predefined tags**: Stored as a constant in the backend, returned by the API
- No additional database or state files

## UI/UX Considerations

- Page is accessible from dashboard sidebar/navigation
- All dropdowns show "loading..." state while fetching live models
- Warning banner if a provider's CLI is not found: "OpenCode CLI not found — install it to see available models"
- Warning if a model in saved settings no longer appears in live discovery: "⚠ Model 'xyz' is configured but not available from provider"
- Unsaved changes indicator (e.g., Save button highlights when form is dirty)
- Responsive layout for various screen widths

## Edge Cases

- **Provider CLI not installed**: Show provider with empty model table and warning
- **Provider CLI times out**: Show provider with empty model table and timeout warning
- **Stale model_metadata**: Model exists in metadata but not in live_models — show as grayed-out row with "Not available" badge
- **No ralph section in settings.json**: Show all defaults, save creates the section
- **Concurrent edits**: Last writer wins (acceptable for single-user localhost dashboard)
- **Very long model list**: OpenCode may return many models — table scrolls vertically within provider section
- **Invalid cost_tier value**: Dropdown constrains to valid values; backend validates on save

## Dependencies

- `vista/server/app.py` (existing) - FastAPI app for route registration
- `vista/server/config.py` (existing) - Settings loading and saving
- `vista/server/services/provider_service.py` (existing) - `get_models()`, `_PROVIDER_REGISTRY`
- `vista/server/views/` (existing) - Template system
- Spec: [settings](settings.md) - Settings schema and filtering logic
- Spec: [dashboard](dashboard.md) - Navigation and styling patterns

## Testing Strategy

- API tests: GET returns correct merged data (live models + saved settings)
- API tests: PUT saves correctly and preserves other settings sections
- API tests: GET /models returns live discovery results
- Validation tests: PUT rejects invalid cost_tier, invalid provider references
- Edge case tests: missing CLI, stale metadata, empty settings
- Frontend: manual browser testing (verify dropdowns, save, cascading behavior)
