# Spec: Migration and Cleanup

> Updated: 2026-02-15 — All acceptance criteria verified as complete

## Overview

Remove legacy diagram rendering, review system, and template generation code, updating the plan schema for the new arch-based approach.

## Parent JTBD

As a plugin maintainer, I want to remove the old monolithic diagram system so the codebase stays clean and the new file-based approach is the only path.

## Scope

**In Scope:**
- Remove plan JSON diagram sections (uiFlows, dataModels, dataFlow, services) from schema
- Remove custom SVG rendering code (template.html JavaScript)
- Remove standalone preview.py template generation
- Remove approve/reject review system (review schema, review routes, review UI, collect-review.py)
- Update plan schema to include `architecture.ref`
- Update setup-feature.py to scaffold arch/ directory
- Update plan skill workflow to generate arch/ files instead of plan JSON sections

**Out of Scope:**
- New rendering pipeline (see rendering-pipeline spec)
- New chat review (see chat-review spec)
- Backward compatibility with old plan format (clean break)

## Requirements

### Functional

1. `plan-schema.json` updated: remove required sections `uiFlows`, `dataModels`, `dataFlow`, `services`. Add optional `architecture` object with `ref` field. Keep `implementationPhases`.
2. Remove `vista/scripts/visualizer/template.html` (1,500+ lines of custom SVG)
3. Remove template generation logic from `vista/scripts/preview.py` (or repurpose to open web app URL)
4. Remove `vista/templates/review-schema.json`
5. Remove `POST /api/.../review` route and `ProgressService.read_review_json()` / `write_review_json()`
6. Remove `vista/scripts/collect-review.py`
7. Remove review UI code from `vista_preview.html` (approve/reject buttons, copy-to-clipboard)
8. Update `setup-feature.py` to create `arch/` directory and empty `_arch.json` alongside existing scaffolding
9. Update plan skill (`vista/skills/plan/SKILL.md`) workflow Steps 5-7 to generate .mmd files + _arch.json instead of plan JSON sections

### Non-Functional

- **Breaking:** This is a clean break. Existing _plan.json files with diagram sections will not render in the new system.

## User Workflows

### Workflow 1: Clean Break Migration

**Actor:** Plugin maintainer
**Trigger:** Feature implementation

**Steps:**
1. Update plan-schema.json
2. Remove legacy files (template.html, review-schema.json, collect-review.py)
3. Update server routes (remove review POST, update vista preview route)
4. Update progress_service.py (remove review methods, add arch methods)
5. Update setup-feature.py (scaffold arch/)
6. Update plan skill documentation
7. Test that new workflow generates arch/ files correctly

**Error Cases:**
- Existing features with old plan JSON: They won't have an arch/ directory. The new view shows "No architecture diagrams found" with instructions.

## Data Model

**Removed Entities:**
- ReviewJSON (meta, sections with approve/reject/notes)
- Plan JSON sections: uiFlows, dataModels, dataFlow, services (as embedded diagram data)

**Updated Entities:**
- PlanJSON: Now includes `architecture: { ref: string }` and only requires `meta`, `implementationPhases`

## Integration Points

**Dependencies:**
- None (this is cleanup)

**Provides to:**
- Arch directory spec: Clean schema for new approach
- Rendering pipeline: Removed legacy rendering makes way for new pipeline

## Technical Considerations

### Files to Remove

```
vista/scripts/visualizer/template.html     # Custom SVG rendering (1,500+ lines)
vista/scripts/collect-review.py            # Review clipboard collection
vista/templates/review-schema.json         # Review JSON schema
```

### Files to Modify

```
vista/templates/plan-schema.json           # Remove diagram sections, add architecture.ref
vista/scripts/preview.py                   # Repurpose or remove
vista/scripts/setup-feature.py             # Add arch/ scaffolding
vista/server/routes/plans.py               # Remove review route, update vista route
vista/server/services/progress_service.py  # Remove review methods, add arch methods
vista/server/views/vista_preview.html      # Complete rewrite for new rendering
vista/skills/plan/SKILL.md                 # Update Steps 5-7 for arch/ generation
```

### Files to Keep As-Is

```
vista/server/routes/projects.py            # Unchanged
vista/server/routes/providers.py           # Unchanged (reused by chat)
vista/server/routes/loops.py               # Unchanged
vista/server/routes/stream.py              # Unchanged
vista/server/views/_base.html              # Unchanged (base template)
vista/server/views/dashboard.html          # Unchanged
vista/server/views/project.html            # Unchanged
```

## Acceptance Criteria

- [x] plan-schema.json no longer requires uiFlows, dataModels, dataFlow, services
- [x] plan-schema.json includes architecture.ref field
- [x] template.html removed
- [x] collect-review.py removed
- [x] review-schema.json removed
- [x] Review POST route removed from plans.py
- [x] Review methods removed from progress_service.py
- [x] setup-feature.py creates arch/ directory and _arch.json
- [x] Plan skill documentation updated for arch/ generation workflow

## Resolved Questions

- preview.py has been fully removed (not repurposed). All 5 legacy files (template.html, collect-review.py, review-schema.json, preview.py, vista_preview.html) are deleted.
