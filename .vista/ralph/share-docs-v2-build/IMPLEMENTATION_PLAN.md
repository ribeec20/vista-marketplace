# Implementation Plan: Share Docs V2 Build

Based on the plan from `.vista/ralph/share-docs-v2-plan-6556ab4b-1235-428b-b9d2-da3c725732ac/IMPLEMENTATION_PLAN.md`.

## DONE: Phase 1 — Progress File & Planning Artifacts Export

All sub-tasks completed in iteration 1:

- **1a.** Extended `get_exportable_features()` with `has_progress`, `has_agents_md`, `has_implementation_plan` flags
- **1b.** Extended `generate_export_html()` to collect and pass new content types (progress, agents, implementation_plan) with toggle support
- **1c.** Updated `ExportFeatureSelection` model with `include_requirements`, `include_progress`, `include_agents`, `include_implementation_plan` optional boolean fields (backward compatible, all default `True`)
- **1d.** Extended `export.html` template with Implementation Plan, Progress Log, and Agents sections. Renamed `renderAllRequirements()` to `renderAllMarkdown()`.
- **1e.** Updated export modal tree in `project.html` with indicator badges and per-content-type checkboxes
- **1f.** Added 7 new tests (23 total, all passing)

## DONE: Phase 2 — Specs and Implementation Plans from Ralph Jobs

All sub-tasks completed in iteration 2:

- **2a.** Added `get_exportable_ralph_jobs()` — scans `.vista/ralph/` for jobs with task.md, IMPLEMENTATION_PLAN.md, or progress.txt. Reads job.json for metadata (mode, status).
- **2b.** Added `read_ralph_artifact()` with whitelist (RALPH_EXPORTABLE_FILES) and path traversal prevention on job_slug.
- **2c.** Added `ExportRalphJobSelection` model with slug, include_task, include_plan, include_progress toggles. Added `ralph_jobs` field to `ExportRequest`.
- **2d.** Added `GET /api/projects/{id}/export/ralph-jobs` endpoint.
- **2e.** Extended `generate_export_html()` with `selected_ralph_jobs` parameter. Populates ralph_tasks, ralph_plans, ralph_progress in export_data.
- **2f.** Added Ralph Jobs section to `export.html` with Task, Implementation Plan, and Progress Log subsections. Updated nav and renderAllMarkdown().
- **2g.** Updated export modal in `project.html` — parallel fetch of features + ralph-jobs, Ralph Jobs tree section with per-artifact checkboxes, collectSelectedRalphJobs(), updated selectAll/download logic.
- **2h.** Added 12 new tests (35 total, all passing) in TestExportableRalphJobs and TestExportRalphRoutes.

## DONE: Phase 3 — Offline-First (Inline CDN Dependencies)

All sub-tasks completed in iteration 3:

- **3a.** Created `vista/server/views/static/vendor/` with pre-downloaded minified dependencies: `tailwind-export.css` (pre-built utility classes), `mermaid.min.js` (~2.7MB), `marked.min.js` (~40KB)
- **3b.** Added `read_vendor_file()` static method to ExportService with `VENDOR_DIR` / `VENDOR_FILES` constants (simpler than a separate service — all vendor logic lives in ExportService)
- **3c.** Added `offline: bool = False` to `ExportRequest` model
- **3d.** Modified `export.html` template with `{% if offline %}` Jinja2 conditionals — inlines vendor deps as `<style>` and `<script>` tags when offline, falls back to CDN otherwise
- **3e.** Updated `generate_export_html()` with `offline` parameter — reads vendor files and passes them as `vendor_deps` dict to template
- **3f.** Added offline checkbox to export modal footer in `project.html`
- **3g.** Used a pre-built CSS approach instead of a build script — extracted exact Tailwind classes from template into `tailwind-export.css`
- **3h.** Added 5 tests for offline mode (vendor file reading, CDN vs inline, route integration)

## DONE: Phase 4 — Template Customization (Theme Toggle + Table of Contents)

All sub-tasks completed in iteration 3:

- **4a.** Added CSS custom properties for theming — `[data-theme="dark"]` and `[data-theme="light"]` rule sets with 20+ variables (bg, text, border, accent, code, etc.)
- **4b.** Added theme toggle button (sun/moon icon) with `toggleTheme()` that switches `data-theme` attribute and calls `reRenderMermaid()` to re-render diagrams with appropriate theme config
- **4c.** Added collapsible TOC sidebar with overlay — slides in from left, lists all features and ralph jobs as clickable links with smooth scroll
- **4d.** Added `default_theme: str = "dark"` to `ExportRequest` model, passed through to template `<html data-theme="...">`
- **4e.** Added 8 tests for theme and TOC (default theme, light theme, toggle button, TOC sidebar, feature/ralph links, route integration, CSS custom properties)

## Phase 5: Export History

**Priority: LOW** — Track previous exports with metadata.

### Steps:
- 5a. Create `ExportHistoryEntry` dataclass in `vista/server/models/export_history.py`
- 5b. Create `ExportHistoryService` with JSON file storage at `~/.vista/data/export-history/`
- 5c. Record exports in the export route handler
- 5d. Add `GET /api/projects/{id}/export/history` endpoint
- 5e. Show recent exports in export modal or project overview
- 5f. Add 5 tests for export history
