# Domain Requirements: Share Docs (Documentation Export)

## Problem Statement

Vista stores architecture diagrams (.mmd files) and domain requirements (domain-requirements.md) across per-feature `.vista/features/` directories, viewable only through the running Vista dashboard. This creates three problems:

1. **No offline sharing** - Diagrams and requirements can only be viewed while the Vista server is running. They cannot be shared with stakeholders who lack access to the development environment.
2. **No portable documentation** - There is no way to produce a single shareable artifact containing selected feature documentation, diagrams, and requirements for code reviews, architecture discussions, or handoffs.
3. **Selective export missing** - Users need to choose exactly which features and which diagrams to include, rather than exporting everything or nothing.

## Users & Personas

- **Developer (primary)** - Uses Vista to plan features. Wants to export selected diagrams and requirements as a self-contained file to share with teammates or attach to pull requests.
- **Tech Lead / Reviewer** - Receives exported documentation. Needs to view Mermaid diagrams and domain requirements in a browser without installing Vista or running any server.

## Business Objectives

1. Allow users to export selected feature documentation (diagrams + requirements) as a single self-contained HTML file
2. Exported file must render correctly when opened directly in any modern browser (no server needed)
3. Provide a tree-based selection UI so users can pick individual features and diagrams to include

## Success Metrics

- User can export documentation via the project page "Export Docs" button
- Exported HTML renders Mermaid diagrams client-side without any server
- Exported HTML renders domain requirements from markdown to formatted prose
- Feature/diagram selection tree allows granular control over export contents
- 16 tests pass covering export service, routes, and edge cases

## Functional Requirements

### Core Functionality

1. **Feature scanning** - `ExportService.get_exportable_features()` scans `.vista/features/` to find features with at least one diagram in `_arch.json` or a non-empty `domain-requirements.md`
2. **Selective export** - `ExportService.generate_export_html()` accepts a list of feature selections (feature name + selected diagram filenames), reads diagram content and requirements, and renders a self-contained HTML template
3. **REST API** - GET `/api/projects/{id}/export/features` returns the feature tree; POST `/api/projects/{id}/export` generates and returns the HTML file as a download
4. **Self-contained HTML** - The export template (`export.html`) uses CDN-loaded Tailwind CSS, Mermaid @11, and Marked @15 to render everything client-side with zero server dependencies
5. **Data embedding** - Diagram sources and requirements markdown are embedded as a JSON blob via Jinja2's `|tojson` filter inside a `<script type="application/json">` tag

### User Workflows

1. **Export workflow** - User clicks "Export Docs" on project page -> modal opens -> features load as a tree checklist -> user selects/deselects features and diagrams -> clicks "Download" -> POST request generates HTML -> browser downloads the file
2. **Viewing exported docs** - Recipient opens the `.html` file in any browser -> Mermaid diagrams render client-side -> requirements render as formatted prose -> feature navigation links allow jumping between sections

### Business Rules

- Features prefixed with `_` are excluded from export scanning
- Features must have at least one diagram or non-empty requirements to appear in the export tree
- Missing diagram files referenced in `_arch.json` are silently skipped with a warning log
- The export filename follows the pattern `{project_name}-docs-{YYYY-MM-DD}.html`
- Path traversal is prevented when reading diagram files (delegated to `ProgressService.read_arch_file()`)

## Non-Functional Requirements

- **Performance:** Feature scanning and HTML generation are synchronous; acceptable for typical project sizes (< 50 features)
- **Platform:** Web only (Vista server dashboard for the export UI; exported file works in any modern browser)
- **Offline:** The exported HTML file requires internet access only for CDN resources (Tailwind, Mermaid, Marked). Once cached, it works offline.
- **Security:** Path traversal prevention in `read_arch_file()`. Jinja2 autoescape enabled for template rendering.
- **Testability:** 16 tests covering service methods, route handlers, and edge cases (empty features, missing files, multiple features)

## Constraints & Dependencies

- **Technical:** CDN dependencies (Tailwind CSS, Mermaid @11, Marked @15) require internet on first load of exported file
- **Dependencies:** `ProgressService` for `read_arch_manifest()`, `read_domain_requirements()`, and `read_arch_file()` methods. `ProjectService` for project lookup by ID. Jinja2 for template rendering.
- **Non-breaking:** This feature is purely additive - it adds new routes, a new service, a new template, and a UI button without modifying any existing functionality

## User Experience Requirements

- **Discovery:** "Export Docs" button in the project page header, styled as a bordered blue button
- **Journey:** Click button -> modal with tree checklist -> select features/diagrams -> download
- **Feedback:** Loading state while features are fetched; "Generating..." state on download button during export; error messages in the modal on failure
- **Selection controls:** Select All / Deselect All buttons in modal footer; parent checkbox toggles all child diagram checkboxes; indeterminate state when some (but not all) child diagrams are selected
- **Exported document:** Dark theme matching Vista dashboard; feature navigation bar for multi-feature exports; pan/zoom controls on each diagram; expand-to-modal button for full-screen diagram viewing
