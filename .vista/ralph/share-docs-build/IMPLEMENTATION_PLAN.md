# Implementation Plan: share_docs (Documentation Export)

## Status: ALL PHASES COMPLETE

All 6 steps implemented in iteration 1.

---

## DONE: Step 1: Add `read_domain_requirements()` to ProgressService
- Added static method to `vista/server/services/progress_service.py`
- Returns Optional[str], handles missing/empty/error cases

## DONE: Step 2: Create ExportService
- Created `vista/server/services/export_service.py`
- `get_exportable_features()` scans .vista/features/, returns features with diagrams/requirements
- `generate_export_html()` collects diagram content + requirements, builds JSON data blob, renders Jinja2 template

## DONE: Step 3: Create Export Routes
- Created `vista/server/routes/export.py` with GET and POST endpoints
- Registered router in `vista/server/app.py`
- GET returns feature tree JSON for modal checklist
- POST generates and returns HTML file with Content-Disposition attachment header

## DONE: Step 4: Create Export HTML Template
- Created `vista/server/views/export.html` (standalone, NOT extending _base.html)
- Dark theme CSS extracted from architecture.html
- CDN dependencies: Tailwind, Mermaid @11, Marked @15
- Data embedded as JSON via `|tojson` filter for safe escaping
- Client-side rendering of Mermaid diagrams and markdown requirements
- Pan/zoom controls copied from architecture.html
- Modal overlay for expanded diagram view
- Feature navigation for multi-feature exports
- Fixed Jinja2 nested loop indexing using `{% set fi = loop.index0 %}` + `{% set did = fi ~ '-' ~ loop.index0 %}`

## DONE: Step 5: Add Export Modal to Project Page
- Added "Export Docs" button next to "Remove Project" in project header
- Added export modal with tree-style checklist UI
- Feature checkboxes toggle all child diagrams
- Individual diagram toggles update parent (checked/indeterminate/unchecked)
- Select All / Deselect All buttons
- Download button disabled when nothing selected
- Export JS uses `escapeHtmlExport()` (renamed to avoid collision with potential existing `escapeHtml`)
- Uses existing `PROJECT_ID` variable already defined in project.html

## DONE: Step 6: Tests
- Created `vista/tests/test_export_service.py` with 16 tests
- 3 tests for ProgressService.read_domain_requirements
- 5 tests for ExportService.get_exportable_features
- 5 tests for ExportService.generate_export_html
- 3 tests for export routes (GET features, POST export, POST 404)
- All 16 tests passing
