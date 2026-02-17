Implement the share_docs feature for the Vista dashboard based on the implementation plan at .vista/ralph/share-docs-plan/IMPLEMENTATION_PLAN.md

Follow the plan's 6 steps in order:

1. Add `read_domain_requirements()` to `vista/server/services/progress_service.py`
2. Create `vista/server/services/export_service.py` with `ExportService` class
3. Create `vista/server/routes/export.py` with GET/POST endpoints + register router in `vista/server/app.py`
4. Create `vista/server/views/export.html` — self-contained HTML export template (standalone, NOT extending _base.html). Must include full JS for Mermaid rendering, pan/zoom, modal expand, and marked.js requirements rendering. Copy CSS/JS patterns from `vista/server/views/architecture.html`.
5. Add Export modal + button to `vista/server/views/project.html` — tree-style checklist with per-diagram selection
6. Create `vista/tests/test_export_service.py` with unit tests

Key requirements:
- Exported HTML must work without any server — all content embedded, libraries via CDN
- Embed diagram/requirements data as JSON via |tojson filter, render client-side
- Match Vista dark theme from architecture.html
- Card gallery with modal overlay for expanded diagrams
- Tree checklist in export modal: features as parents, diagrams as children, indeterminate state support

Reference the implementation plan for exact code, file locations, and codebase references.