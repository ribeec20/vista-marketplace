# Spec: Export UI (Project Page Modal)

## Overview

A modal dialog on the Vista project page that provides a tree-based checklist for selecting features and diagrams to export, with Select All / Deselect All controls and a download button that triggers HTML generation.

## Parent JTBD

As a developer, I want to select exactly which features and diagrams to include in my documentation export so I can share only the relevant parts of my project's architecture.

## Scope

**In Scope:**
- "Export Docs" button in the project page header
- Modal overlay with feature/diagram tree checklist
- Feature-level and diagram-level checkbox selection
- Select All / Deselect All controls
- Download button that triggers export and browser download
- Indeterminate checkbox state for partially selected features
- Loading and error states

**Out of Scope:**
- Export HTML generation logic (see export-service spec)
- Export HTML template content (see export-template spec)
- Any modification to the export API endpoints

## Requirements

### Functional

1. **Export button** - An "Export Docs" button appears in the project page header (`project.html`), styled as a bordered blue button (`border-blue-600 text-blue-300`), positioned to the left of the "Remove Project" button
2. **Modal structure** - Clicking the button opens a centered modal overlay (`fixed inset-0 bg-black/60 z-50`) containing a `max-w-lg max-h-[80vh]` card with header, scrollable body, and footer
3. **Feature loading** - On modal open, fetches `GET /api/projects/{PROJECT_ID}/export/features` and populates the tree. Shows "Loading features..." placeholder during fetch.
4. **Empty state** - If no exportable features exist, shows "No exportable features found" message
5. **Error state** - If the fetch fails, shows the error message in red text
6. **Tree structure** - Each feature renders as a collapsible parent row with:
   - Expand/collapse toggle button (triangle `\u25B6` / `\u25BC`)
   - Feature-level checkbox (checked by default)
   - Feature name
   - Diagram count badge (e.g., "3 diagrams")
   - "+ requirements" indicator (green text) if `has_requirements` is true
7. **Diagram children** - Expanding a feature reveals its child diagram checkboxes, each showing diagram name and description. All checked by default. Indented with `ml-7`.
8. **Feature toggle cascades** - Checking/unchecking a feature checkbox sets all its child diagram checkboxes to the same state
9. **Indeterminate state** - When some (but not all) child diagrams are checked, the parent feature checkbox shows the indeterminate state (`featureCb.indeterminate = true`)
10. **Select All / Deselect All** - Footer buttons toggle all feature and diagram checkboxes, clearing any indeterminate states
11. **Download button state** - The "Download" button (`bg-blue-600`) is disabled (`disabled:opacity-40 disabled:cursor-not-allowed`) when no features are selected; enabled when at least one feature checkbox is checked
12. **Selection collection** - `collectSelectedFeatures()` builds the payload: for each checked or indeterminate feature, collects the filenames of checked child diagrams into `{name, diagrams: [filenames]}`
13. **Export trigger** - Clicking "Download" disables the button, shows "Generating..." text, POSTs to `/api/projects/{PROJECT_ID}/export` with the selected features JSON
14. **File download** - On success, creates a blob URL from the response, programmatically clicks a temporary `<a>` element to trigger the browser download, extracts filename from `Content-Disposition` header (fallback: `export.html`)
15. **Post-download** - Revokes the blob URL, closes the modal
16. **Export failure** - Shows `alert()` with the error message, re-enables the download button

### Non-Functional

- **Performance:** Feature tree fetched on each modal open (not cached) to reflect latest state
- **Accessibility:** Checkboxes use native `<input type="checkbox">` with `<label>` wrappers for click targets
- **Responsiveness:** Modal constrained to `max-w-lg max-h-[80vh]` with scrollable content area

## User Workflows

### Workflow 1: Full Export

**Actor:** Developer
**Trigger:** User wants to export all documentation

**Steps:**
1. User clicks "Export Docs" button on project page
2. Modal opens, features load (all checked by default)
3. User clicks "Download"
4. Browser downloads the HTML file
5. Modal closes automatically

### Workflow 2: Selective Export

**Actor:** Developer
**Trigger:** User wants to export specific features/diagrams

**Steps:**
1. User clicks "Export Docs" button
2. Modal opens with all features checked
3. User clicks "Deselect All"
4. User checks specific features
5. User expands a feature to deselect individual diagrams
6. Feature checkbox shows indeterminate state
7. User clicks "Download"
8. Browser downloads HTML with only selected content

**Error Cases:**
- Network failure on feature fetch: red error message in modal
- Export generation failure: alert dialog with error message

## Data Model

**Client-side State:**
- `exportFeatures` (array) - cached feature tree from the API, each item: `{ name, has_requirements, diagrams: [{name, file, type, description, category}] }`
- Checkbox state tracked via DOM: `.feature-cb[data-fi]` for features, `.diagram-cb[data-fi][data-di]` for diagrams

**API Request (POST /export):**
- `{ features: [{ name: string, diagrams: string[] }] }` - feature names with selected diagram filenames

## Integration Points

**Dependencies:**
- GET `/api/projects/{id}/export/features` - provides the feature tree data
- POST `/api/projects/{id}/export` - generates the HTML export
- `PROJECT_ID` JavaScript constant (injected via Jinja2 template variable)

**Provides to:**
- User interaction layer for the export feature; no other components depend on this UI

## Technical Considerations

### Architecture
- All export UI logic is inline JavaScript in `project.html` within the `{% block scripts %}` section
- No separate JavaScript module or build step required
- HTML structure defined in `{% block content %}` with the `#export-modal` div

### Patterns
- Modal show/hide via CSS class toggle (`hidden` class on the modal container)
- Tree rendering via template literal string concatenation in `renderExportTree()`
- Checkbox state synchronization: parent -> children cascade, children -> parent indeterminate calculation
- Blob download pattern: `fetch() -> resp.blob() -> URL.createObjectURL() -> <a>.click() -> URL.revokeObjectURL()`
- HTML escaping via `escapeHtmlExport()` for user-generated content (feature names, diagram names, descriptions)

### Libraries/APIs
- Native `fetch()` API for HTTP requests
- Native `Blob` and `URL.createObjectURL()` for file download
- DOM manipulation for checkbox state management
- No external UI framework (vanilla JavaScript)

## Acceptance Criteria

- [x] "Export Docs" button visible in project page header
- [x] Clicking button opens modal overlay with loading state
- [x] Feature tree renders with expand/collapse toggles
- [x] All features and diagrams checked by default
- [x] Feature checkbox toggles all child diagram checkboxes
- [x] Partial child selection shows indeterminate parent checkbox
- [x] "Select All" checks all features and diagrams
- [x] "Deselect All" unchecks all features and diagrams, clears indeterminate
- [x] Download button disabled when no features selected
- [x] Download button enabled when at least one feature selected
- [x] Download button shows "Generating..." during export
- [x] Successful export triggers browser file download
- [x] Filename extracted from Content-Disposition header
- [x] Modal closes after successful download
- [x] Export failure shows alert with error message
- [x] Empty features state shows appropriate message
- [x] Feature names and diagram descriptions are HTML-escaped
- [x] Requirements indicator shown for features with domain-requirements.md
