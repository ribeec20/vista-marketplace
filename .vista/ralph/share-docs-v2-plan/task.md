Plan improvements and V2 enhancements to the Share Docs (Documentation Export) feature.

## Context

The share-docs feature was implemented in commit 10cb21e. It allows users to export Vista feature documentation (Mermaid architecture diagrams + domain requirements) as a self-contained HTML file from the Vista dashboard.

## Current Implementation

### What exists:
1. **ExportService** (vista/server/services/export_service.py) - Scans .vista/features/ for exportable features, generates self-contained HTML
2. **Export Routes** (vista/server/routes/export.py) - GET /api/projects/{id}/export/features (tree data), POST /api/projects/{id}/export (generate HTML)
3. **Export Template** (vista/server/views/export.html) - Standalone HTML with CDN Tailwind, Mermaid @11, Marked @15
4. **Project Page Modal** (vista/server/views/project.html) - Export Docs button + tree checklist modal for feature/diagram selection
5. **ProgressService.read_domain_requirements()** - Reads domain-requirements.md for features
6. **16 tests** (vista/tests/test_export_service.py) - Covering service, routes, and edge cases

### Domain Requirements (from .vista/features/share-docs/domain-requirements.md):
- Users export selected feature documentation as a single self-contained HTML file
- Exported file renders Mermaid diagrams client-side without any server
- Tree-based selection UI for picking features and diagrams
- Dark theme matching Vista dashboard
- Feature navigation bar, pan/zoom controls, expand-to-modal for diagrams

## What to Plan

Analyze the current share-docs implementation and create an implementation plan for V2 improvements. Focus on:

1. **Export Format Options** - Consider adding PDF export alongside HTML, or a markdown-based export
2. **Specs and Implementation Plans** - The export currently only includes diagrams and domain requirements. Consider also exporting spec files (.vista/features/{name}/specs/*.md) and implementation plans (IMPLEMENTATION_PLAN.md from .vista/ralph/ jobs)
3. **Offline-First** - The current export requires CDN internet for Tailwind/Mermaid/Marked on first load. Consider inlining these dependencies for true offline support
4. **Export History** - Track previous exports with metadata (date, features included, file size)
5. **Share Link** - Consider a lightweight share mechanism (e.g., upload to a temporary hosting service or generate a shareable URL)
6. **Template Customization** - Allow users to choose light/dark theme, add custom branding/logo, or include a table of contents
7. **Progress File Export** - Include progress.txt and agents.md content from feature planning sessions

## Codebase References

- ExportService: vista/server/services/export_service.py
- Export routes: vista/server/routes/export.py
- Export template: vista/server/views/export.html
- Project page modal: vista/server/views/project.html
- ProgressService: vista/server/services/progress_service.py
- Tests: vista/tests/test_export_service.py
- Domain requirements: .vista/features/share-docs/domain-requirements.md
- Architecture diagrams: .vista/features/share-docs/arch/
- Existing specs: .vista/features/share-docs/specs/
- Previous plan: .vista/ralph/share-docs-plan/IMPLEMENTATION_PLAN.md
- Previous build: .vista/ralph/share-docs-build/IMPLEMENTATION_PLAN.md

## Deliverable

Create an IMPLEMENTATION_PLAN.md with prioritized phases, focusing on the highest-impact improvements first. Each phase should include file changes, new tests, and acceptance criteria.