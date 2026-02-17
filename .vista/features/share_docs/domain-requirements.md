# Domain Requirements: share_docs

## Problem Statement
Vista's documentation (architecture diagrams, domain requirements) is only accessible through the localhost dashboard. There is no way to share polished, self-contained documentation with external stakeholders, clients, or for archival purposes. Users need a portable export that works on any device without requiring the Vista server.

## Users & Personas
- **Developer/Architect**: Exports documentation to share with team leads, clients, or for project handoffs
- **External Stakeholder/Client**: Receives and views the exported HTML file on their own device — no Vista installation needed
- **Future Self**: Archives documentation snapshots for later reference or version history

## Business Objectives
- Enable documentation sharing beyond the local development machine
- Produce professional, branded exports that represent project architecture clearly
- Preserve the look and feel of the Vista dashboard in a portable format

## Success Metrics
- Exported HTML file opens correctly on any modern browser without a server
- All Mermaid diagrams render correctly in the exported file
- Navigation (card gallery + modal expansion) works identically to the dashboard
- Export completes in under 5 seconds for a typical project

## Functional Requirements

### Core Functionality
- Export documentation as a **single self-contained HTML file** downloadable from the browser
- Content includes: **architecture diagrams** (Mermaid) + **domain requirements** (rendered markdown)
- **Configurable scope**: user selects which features to include via a checklist before export
- Features without diagrams or domain requirements can be excluded via selection
- Mermaid diagrams render **client-side** using bundled Mermaid.js (via CDN)
- Domain requirements markdown rendered via Marked.js (via CDN)

### User Workflows

#### 1. Export from Project Page
1. User navigates to project detail page (`/project/{id}`)
2. User clicks "Export Documentation" button
3. Modal dialog opens showing:
   - **Tree-style checklist**: Features as parent items, individual diagrams as child items
   - Each feature is expandable to show its diagrams with checkboxes
   - Feature-level checkbox toggles all diagrams within that feature
   - Domain requirements included automatically when a feature is selected (no separate toggle needed)
   - "Select All" / "Deselect All" controls at the top
   - "Download" button at the bottom
4. User expands features to select specific diagrams (or checks the feature to include all)
5. User clicks "Download"
6. Browser downloads the generated HTML file
7. User opens the file on any device — diagrams render, navigation works

### Business Rules
- Only features with at least one diagram OR non-empty domain requirements should appear in the checklist
- Individual diagrams within a feature are selectable — user can include only specific diagrams
- If all diagrams in a feature are unchecked but the feature is still selected, only domain requirements are included
- The exported file must work without any server — all content embedded, libraries via public CDN
- Export file naming convention: `{project-name}-docs-{YYYY-MM-DD}.html`

## Non-Functional Requirements
- **Performance**: Export generation should complete in < 5 seconds for projects with up to 20 features
- **Platform**: Exported HTML must work in Chrome, Firefox, Safari, Edge (modern versions)
- **Offline**: Diagrams will NOT render offline (CDN dependency for Mermaid.js) — this is an accepted trade-off for smaller file size
- **Security**: No sensitive data should be included. Export contains only diagram source and requirements text
- **File Size**: Target < 500KB for a typical project with 5-10 diagrams

## Constraints & Dependencies
- **Technical**: Mermaid.js, Tailwind CSS, and Marked.js loaded from public CDNs (cdn.jsdelivr.net)
- **Dependencies**: Reuses existing Jinja2 templates and Tailwind dark theme from the Vista dashboard
- **Server-side**: New FastAPI endpoint to generate the HTML file and serve it as a download

## User Experience Requirements

### Exported HTML Layout
- **Vista-branded header**: Vista logo/name, project name, export date
- **Feature sections**: Each selected feature gets a section with:
  - Feature name as heading
  - **Diagram card gallery**: Cards showing each diagram with name, description, and rendered preview
  - **Modal overlay**: Click a diagram card to expand it to full-screen view with zoom/pan
  - **Domain requirements**: Rendered markdown below diagrams
- **Navigation**: If multiple features are exported, a top-level nav or anchor links to jump between features

### Discovery
- "Export Documentation" button on the project detail page (`/project/{id}`)
- Button visible alongside existing feature management controls

### Feedback
- Loading spinner while HTML is being generated
- Success: browser download starts automatically
- Error: toast notification with error message

### Error Handling
- Feature with missing/corrupt `_arch.json`: skip diagrams, include requirements only
- Feature with empty `domain-requirements.md`: skip requirements, include diagrams only
- No features selected: disable download button with tooltip "Select at least one feature"

## TDD Candidates

- **HTML Generator Service**: Complex template assembly with variable content (0-N features, each with 0-N diagrams + optional requirements). Multiple edge cases: empty features, corrupt manifests, missing files.
- **Export Modal Component**: UI state management with feature selection, select-all logic, validation (at least one feature selected), and download triggering.
