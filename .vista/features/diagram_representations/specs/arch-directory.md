# Spec: Architecture Directory Structure

> Updated: 2026-02-15 — Multi-format support: 6 diagram types, markdown editing, extended watcher

## Overview

File-based architecture directory with manifest for storing native diagram files per feature.

## Parent JTBD

As a developer, I want diagrams stored as native files so I can edit them with standard tools and agents can generate them directly.

## Scope

**In Scope:**
- `arch/` subdirectory creation within `.vista/features/<name>/`
- `_arch.json` manifest schema and validation
- `_plan.json` reference to arch directory via `architecture.ref`
- Setup script updates to scaffold arch/ directory

**Out of Scope:**
- Diagram content rendering (see rendering-pipeline spec)
- AI chat review (see chat-review spec)
- Migration of existing plans (see migration spec)

## Requirements

### Functional

1. Each feature directory gets an `arch/` subdirectory when scaffolded
2. `_arch.json` manifest contains an array of diagram entries with: `name`, `file`, `type`, `diagramType`, `description`, and optional `category`
3. Supported types: `"mermaid"`, `"drawio"`, `"plantuml"`, `"d2"`, `"graphviz"`, `"markdown"`
4. Supported diagramTypes: `"flowchart"`, `"sequence"`, `"state"`, `"er"`, `"gantt"`, `"architecture"`, `"wireframe"`, `"custom"`, `"logic-flow"`, `"decision-tree"`, `"test-contract"` — non-mermaid types use `"custom"`
5. Supported categories: `"architecture"` (default), `"tdd"` — used for grouping and filtering diagram entries
6. `_plan.json` includes `"architecture": { "ref": "./arch/_arch.json" }` at the top level
7. Plan JSON no longer requires `uiFlows`, `dataModels`, `dataFlow`, `services` sections - these are replaced by arch/ files

### Non-Functional

- **Performance:** Manifest file < 10KB (metadata only, no content)
- **Platform:** File system (cross-platform paths)

## User Workflows

### Workflow 1: Agent Generates Architecture

**Actor:** AI agent (via /vista:plan)
**Trigger:** Step 5 of plan workflow

**Steps:**
1. Agent creates `arch/` directory
2. Agent writes .mmd files for each diagram (system-arch, user-flow, sequence, state-model, data-model)
3. Agent writes `_arch.json` manifest referencing each file
4. Agent writes `_plan.json` with `architecture.ref` pointing to manifest
5. Feature directory is complete

**Error Cases:**
- Invalid Mermaid syntax in .mmd file: Web renderer shows parse error inline
- Missing file referenced in manifest: Web app shows "File not found" placeholder

### Workflow 2: User Adds Diagram Manually

**Actor:** Developer
**Trigger:** User wants to add a diagram outside the plan workflow

**Steps:**
1. User creates a diagram file in arch/ (supported: `.mmd`, `.drawio`, `.puml`, `.d2`, `.dot`, `.md`)
2. DiagramWatcher auto-detects the new file and updates `_arch.json` manifest with correct `type` and `diagramType`
3. Web app picks up the new diagram on next page load (or live via watcher if page is open)

**Error Cases:**
- Malformed _arch.json: Server returns 400 with validation error
- Unsupported file extension: Watcher ignores the file

### Workflow 3: User Edits Markdown Inline

**Actor:** Developer
**Trigger:** User clicks edit button on a markdown diagram card in the web dashboard

**Steps:**
1. User clicks the edit (pencil) button on a markdown card
2. Card switches from rendered view to textarea with raw markdown content
3. User edits the markdown content
4. User saves (Ctrl+S or Save button) — content is written via `PUT /api/.../arch/{filename}`
5. Card returns to rendered view showing updated content
6. User can also cancel (Escape or Cancel button) to discard changes

**Error Cases:**
- Save fails (network error): Error message shown, edits preserved in textarea
- Non-markdown file: Edit button not displayed (only `.md` files are editable inline)

## Data Model

**Entities:**
- ArchManifest: `{ feature: string, diagrams: DiagramEntry[] }`
- DiagramEntry: `{ name: string, file: string, type: "mermaid"|"drawio"|"plantuml"|"d2"|"graphviz"|"markdown", diagramType: string, category?: "architecture"|"tdd", description: string }`

**Relationships:**
- ArchManifest 1:N DiagramEntry
- Feature 1:1 ArchManifest (via _plan.json reference)

## Integration Points

**Dependencies:**
- setup-feature.py: Must scaffold arch/ directory and empty _arch.json
- DiagramWatcher: Auto-detects new/changed files in arch/ and updates _arch.json manifest

**Provides to:**
- Rendering pipeline: Manifest tells the web app what to render and how (type field dispatches to correct renderer)
- Chat review: Manifest provides diagram list for context injection
- Markdown editor: Manifest type=markdown triggers edit button in dashboard

## Technical Considerations

### Architecture
- File system layer only - no database
- JSON schema validation for _arch.json

### Patterns
- Manifest pattern (registry of files, not container of content)
- Reference pattern (_plan.json -> _arch.json)

### Libraries/APIs
- Python `json` for manifest read/write
- `pathlib` for cross-platform path handling

## Acceptance Criteria

- [x] `setup-feature.py --name X` creates `arch/` directory and empty `_arch.json`
- [x] `_arch.json` validates against defined schema
- [x] `_plan.json` includes `architecture.ref` field
- [x] Plan JSON schema no longer requires uiFlows, dataModels, dataFlow, services sections
- [x] Server API can read _arch.json and return manifest data
- [x] Server API can read individual diagram file contents by manifest entry
- [x] Schema `type` enum supports all 6 values: mermaid, drawio, plantuml, d2, graphviz, markdown
- [x] DiagramWatcher detects changes in all 6 file types (.mmd, .drawio, .puml, .d2, .dot, .md)
- [x] `PUT /api/.../arch/{filename}` writes .md files with path traversal protection
- [x] `PUT /api/.../arch/{filename}` rejects non-.md files (400)
- [x] `GET /api/.../arch/{filename}` returns correct Content-Type for all 6 extensions
- [x] Manifest auto-update correctly identifies file types by extension

## Implementation Notes

- `arch-schema.json` has been extended beyond this spec's original definition. The `diagramType` enum now includes TDD-related types (`logic-flow`, `decision-tree`, `test-contract`) and a `category` field (`architecture` | `tdd`) for grouping.
- Path traversal protection is implemented in both `ProgressService.read_arch_file()` and `write_arch_file()` using filename sanitization and resolved path validation.
- Non-mermaid files use `diagramType: "custom"` in the manifest. The `diagramType` field is specifically for Mermaid subtypes (flowchart, sequence, etc.).
- Write endpoint is restricted to `.md` files only — diagram source files (.mmd, .puml, .d2, .dot, .drawio) are not writable through the API.
- DiagramWatcher watches both WATCH_EXTENSIONS locations (module-level and class-level) for `.mmd`, `.drawio`, `.puml`, `.d2`, `.dot`, `.md`.
- PlantUML server URL is configurable via `~/.vista/settings.json` under `diagrams.plantuml_server_url` (default: `https://www.plantuml.com/plantuml`).

## Resolved Questions

- _arch.json supports grouping via a `category` field on each diagram entry (values: `architecture`, `tdd`).
- Non-mermaid file types use `diagramType: "custom"` rather than their format name — diagramType is reserved for Mermaid subtypes.
- Only `.md` files are editable inline through the dashboard. Other formats require external tools.
