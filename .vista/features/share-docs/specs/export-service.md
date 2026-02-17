# Spec: Export Service

## Overview

Python service that scans Vista feature directories for exportable content (diagrams and domain requirements) and generates self-contained HTML documentation files.

## Parent JTBD

As a developer, I want to export selected feature documentation as a portable HTML file so I can share architecture diagrams and requirements with teammates who don't have Vista running.

## Scope

**In Scope:**
- `ExportService` class with `get_exportable_features()` and `generate_export_html()` static methods
- REST API routes: GET `/api/projects/{id}/export/features` and POST `/api/projects/{id}/export`
- Pydantic request models for export selection
- Integration with `ProgressService` for reading manifests, diagram files, and requirements

**Out of Scope:**
- The HTML export template itself (see export-template spec)
- The project page export modal UI (see export-ui spec)
- Diagram rendering logic (handled client-side in the template)

## Requirements

### Functional

1. `get_exportable_features(project_path)` scans `.vista/features/` and returns a list of features that have at least one diagram in `_arch.json` OR a non-empty `domain-requirements.md`
2. Features whose directory name starts with `_` are excluded
3. Each returned feature includes: `name` (string), `has_requirements` (bool), `diagrams` (list of objects with `name`, `file`, `type`, `description`, `category`)
4. `generate_export_html(project_name, project_path, selected_features)` accepts a list of `{name, diagrams: [filenames]}` selections
5. For each selected feature, the service reads the `_arch.json` manifest, filters to only selected diagram files, reads `.mmd` content via `ProgressService.read_arch_file()`, and reads `domain-requirements.md` via `ProgressService.read_domain_requirements()`
6. Missing diagram files are skipped with a warning log (no error raised)
7. Features with no remaining diagrams and no requirements after filtering are excluded from output
8. The service builds an `export_data` JSON structure with `diagrams` (array of `{id, content, name}`) and `requirements` (object mapping feature name to markdown string)
9. Diagram IDs follow the pattern `"{feature_index}-{diagram_index}"` matching the template's rendering expectations
10. The service renders the `export.html` Jinja2 template with `project_name`, `export_date` (YYYY-MM-DD), `features` (full feature data), and `export_data` (JSON blob)
11. GET `/api/projects/{id}/export/features` returns the feature tree as JSON (200) or 404 if project not found
12. POST `/api/projects/{id}/export` accepts `{features: [{name, diagrams: [filenames]}]}`, returns HTML with `Content-Disposition: attachment` header, filename `{project_name}-docs-{YYYY-MM-DD}.html`

### Non-Functional

- **Performance:** Synchronous file I/O; acceptable for typical project sizes
- **Security:** Jinja2 autoescape enabled; path traversal prevention delegated to `ProgressService.read_arch_file()`
- **Testability:** Service methods are static and stateless, easily testable with `tmp_path` fixtures

## User Workflows

### Workflow 1: Fetching Export Feature Tree

**Actor:** Project page JavaScript (via export modal)
**Trigger:** User clicks "Export Docs" button

**Steps:**
1. Frontend sends GET `/api/projects/{id}/export/features`
2. Route handler looks up project via `ProjectService.get_by_id()`
3. Calls `ExportService.get_exportable_features(project.path)`
4. Returns JSON array of features with their diagrams and requirements availability

**Error Cases:**
- Project not found: 404 response
- No `.vista/features/` directory: empty array returned

### Workflow 2: Generating Export HTML

**Actor:** Project page JavaScript (via export modal download button)
**Trigger:** User clicks "Download" after selecting features

**Steps:**
1. Frontend sends POST `/api/projects/{id}/export` with `{features: [...]}`
2. Route handler validates request body via `ExportRequest` Pydantic model
3. Calls `ExportService.generate_export_html()` with project details and selections
4. Service reads manifests, filters diagrams, reads content, renders template
5. Returns HTML response with `Content-Disposition: attachment` header

**Error Cases:**
- Project not found: 404 response
- Missing diagram file on disk: skipped with warning log, remaining diagrams still exported
- Feature with no exportable content after filtering: silently excluded

## Data Model

**Entities:**
- `ExportFeatureSelection` (Pydantic): `{ name: str, diagrams: list[str] }` - user's selection of a feature and which diagram files to include
- `ExportRequest` (Pydantic): `{ features: list[ExportFeatureSelection] }` - the full export request body
- Export feature tree item (dict): `{ name: str, has_requirements: bool, diagrams: list[{name, file, type, description, category}] }`
- Export data blob (dict): `{ diagrams: list[{id, content, name}], requirements: dict[str, str] }`

**Relationships:**
- ExportRequest 1:N ExportFeatureSelection
- ExportFeatureSelection references a Vista feature by name
- Each diagram file reference is validated against `_arch.json` manifest

## Integration Points

**Dependencies:**
- `ProgressService.read_arch_manifest()` - reads `_arch.json` for a feature
- `ProgressService.read_domain_requirements()` - reads `domain-requirements.md` for a feature
- `ProgressService.read_arch_file()` - reads individual `.mmd` file content with path traversal protection
- `ProjectService.get_by_id()` - looks up project by ID (used in route handlers)
- `config.VIEWS_DIR` - directory containing Jinja2 templates
- `jinja2` - template rendering engine

**Provides to:**
- Export modal UI (project.html) - feature tree data via GET endpoint
- Export template (export.html) - rendered HTML via POST endpoint

## Technical Considerations

### Architecture
- Stateless static methods on `ExportService` class
- Route handlers in `server/routes/export.py`, registered in `app.py` via `app.include_router(export.router)`
- No database; all data read from file system

### Patterns
- Service/route separation: business logic in `ExportService`, HTTP concerns in route handlers
- Pydantic models for request validation (`ExportRequest`, `ExportFeatureSelection`)
- `Content-Disposition: attachment` for triggering browser download

### Libraries/APIs
- `jinja2` for template rendering (with `FileSystemLoader` and `autoescape=True`)
- `pathlib` for file system operations
- `datetime` for export date formatting
- `fastapi` for API routes and response handling
- `pydantic` for request body validation

## Acceptance Criteria

- [x] `ExportService.get_exportable_features()` returns features with diagrams and/or requirements
- [x] Features with `_` prefix are excluded from scanning
- [x] Empty features (no diagrams, no requirements) are excluded
- [x] Features with only requirements (no diagrams) are included with `has_requirements: True`
- [x] `ExportService.generate_export_html()` produces valid self-contained HTML
- [x] Multiple features generate navigation links in the output
- [x] Missing diagram files are skipped gracefully (no crash)
- [x] Features with only requirements and no manifest produce valid output
- [x] Empty selection produces minimal valid HTML
- [x] GET `/api/projects/{id}/export/features` returns 200 with feature tree JSON
- [x] POST `/api/projects/{id}/export` returns 200 with HTML attachment
- [x] POST to non-existent project returns 404
- [x] Export filename includes project name and date
- [x] Router registered in `app.py`
- [x] 16 tests pass covering service methods, routes, and edge cases
