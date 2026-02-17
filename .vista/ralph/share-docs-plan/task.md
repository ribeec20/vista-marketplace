Create an implementation plan for the "share_docs" feature — a documentation export system for the Vista dashboard.

## What to build

A single self-contained HTML file export that lets users download a portable version of their project's architecture diagrams and domain requirements. The exported HTML replicates the Vista dashboard look and feel, works on any device with internet (CDN dependencies for Mermaid.js, Tailwind, Marked.js), and requires no server.

## Key components to plan

1. **Export API endpoint** (`POST /api/projects/{id}/export`) — FastAPI route that accepts a JSON payload specifying which features and diagrams to include, reads the .mmd files and domain-requirements.md from `.vista/features/`, renders a Jinja2 export template, and returns the HTML as a downloadable file response.

2. **HTML Generator Service** (`server/services/export_service.py`) — Assembles the export HTML by reading arch manifests, diagram source files, and requirements markdown for each selected feature. Handles edge cases: missing manifests, empty requirements, corrupt files.

3. **Export Jinja2 template** (`server/views/export.html`) — Self-contained HTML template matching the Vista dark theme. Includes: Vista-branded header with project name and export date, feature sections with diagram card galleries, modal overlay for expanded diagram view, and rendered markdown requirements sections. Uses CDN links for Tailwind CSS v4, Mermaid.js v11, and Marked.js v15.

4. **Export Modal on Project Page** — JavaScript modal on `project.html` triggered by an "Export Documentation" button. Displays a tree-style checklist where features are parent nodes and individual diagrams are child nodes. Features can be expanded to select specific diagrams. Includes select-all/deselect-all, a download button (disabled when nothing selected), and loading/error states.

5. **Feature content API** (`GET /api/projects/{id}/export/features`) — Returns the list of features with their diagrams and requirements availability, used to populate the export modal's tree checklist.

## Reference files

- Domain requirements: `.vista/features/share_docs/domain-requirements.md`
- Architecture diagrams: `.vista/features/share_docs/arch/` (5 diagrams: system-architecture, user-flow, sequence-export, data-model, state-export-modal)
- Existing patterns to follow: `server/routes/architecture.py`, `server/services/progress_service.py`, `server/views/architecture.html`
- Arch manifest schema: `vista/templates/arch-schema.json`

## Constraints

- Reuse existing Jinja2 + Tailwind patterns from the dashboard
- CDN links for external libraries (not inlined) — accepted trade-off for file size
- Export must work without any server running
- Target < 500KB output for typical projects