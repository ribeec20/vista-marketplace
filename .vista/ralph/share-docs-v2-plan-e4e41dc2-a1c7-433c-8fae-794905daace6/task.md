Plan improvements and V2 enhancements to the Share Docs (Documentation Export) feature.

## Context
The share-docs feature was implemented in commit 10cb21e. It allows users to export Vista feature documentation (Mermaid architecture diagrams + domain requirements) as a self-contained HTML file from the Vista dashboard.

## Current Implementation
1. ExportService (vista/server/services/export_service.py) - Scans .vista/features/ for exportable features, generates self-contained HTML
2. Export Routes (vista/server/routes/export.py) - GET /api/projects/{id}/export/features, POST /api/projects/{id}/export
3. Export Template (vista/server/views/export.html) - Standalone HTML with CDN Tailwind, Mermaid @11, Marked @15
4. Project Page Modal (vista/server/views/project.html) - Export Docs button + tree checklist modal
5. ProgressService.read_domain_requirements() - Reads domain-requirements.md for features
6. 16 tests (vista/tests/test_export_service.py)

## What to Plan
Analyze the current share-docs implementation and create an implementation plan for V2 improvements:
1. Specs and Implementation Plans - Also export spec files and implementation plans from .vista/ralph/ jobs
2. Offline-First - Inline CDN dependencies (Tailwind/Mermaid/Marked) for true offline support
3. Export History - Track previous exports with metadata
4. Template Customization - Light/dark theme toggle, table of contents
5. Progress File Export - Include progress.txt and agents.md from feature planning

## Codebase References
- ExportService: vista/server/services/export_service.py
- Export routes: vista/server/routes/export.py
- Export template: vista/server/views/export.html
- Project page modal: vista/server/views/project.html
- ProgressService: vista/server/services/progress_service.py
- Tests: vista/tests/test_export_service.py
- Domain requirements: .vista/features/share-docs/domain-requirements.md
- Previous plan: .vista/ralph/share-docs-plan/IMPLEMENTATION_PLAN.md
- Previous build: .vista/ralph/share-docs-build/IMPLEMENTATION_PLAN.md

## Deliverable
Create an IMPLEMENTATION_PLAN.md with prioritized phases, each with file changes, new tests, and acceptance criteria.