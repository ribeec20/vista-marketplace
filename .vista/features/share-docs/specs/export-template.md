# Spec: Export Template (Self-Contained HTML)

## Overview

A Jinja2 template (`export.html`) that renders a self-contained, dark-themed HTML document with Mermaid diagram rendering, markdown requirements prose, pan/zoom controls, modal expand, and feature navigation. The exported file works in any modern browser with no server required.

## Parent JTBD

As a documentation recipient, I want to open an exported HTML file in my browser and see fully rendered architecture diagrams and formatted requirements without needing Vista or any development tools.

## Scope

**In Scope:**
- Self-contained HTML document with CDN-loaded dependencies
- Client-side Mermaid diagram rendering from embedded JSON data
- Client-side Marked.js markdown rendering for domain requirements
- Pan/zoom controls per diagram (mouse drag + scroll wheel + buttons)
- Modal expand for full-screen diagram viewing
- Feature navigation bar for multi-feature exports
- Dark theme consistent with Vista dashboard styling

**Out of Scope:**
- Server-side rendering of diagrams
- Export file generation logic (see export-service spec)
- Export selection UI (see export-ui spec)
- Diagram editing or AI chat features

## Requirements

### Functional

1. **CDN dependencies** - The template loads three CDN scripts in the `<head>`:
   - Tailwind CSS via `cdn.tailwindcss.com`
   - Mermaid @11 via `cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js`
   - Marked @15 via `cdn.jsdelivr.net/npm/marked@15/marked.min.js`
2. **Data embedding** - Diagram sources and requirements markdown are embedded as a JSON object inside `<script id="export-data" type="application/json">{{ export_data | tojson }}</script>`, parsed on load via `JSON.parse()`
3. **Mermaid initialization** - Mermaid configured with `startOnLoad: false`, dark theme, custom theme variables matching the Vista dark palette (`background: #0f172a`, `primaryColor: #1e3a5f`, `lineColor: #94a3b8`, etc.)
4. **Diagram rendering** - `renderAllDiagrams()` iterates `EXPORT_DATA.diagrams`, calls `mermaid.render()` for each, injects SVG into placeholder elements. On parse error, shows a yellow pre-formatted error message with the raw Mermaid source.
5. **Requirements rendering** - `renderAllRequirements()` iterates `EXPORT_DATA.requirements`, calls `marked.parse()` for each markdown string, injects into corresponding `requirements-content` div. Marked configured with `breaks: true, gfm: true`.
6. **Diagram cards** - Each diagram is wrapped in a `.diagram-card` with a header (name, category badge, description) and a body containing the viewport and zoom controls
7. **Category badges** - Diagrams display a category badge: blue "architecture" (`badge-arch`) or amber "tdd" (`badge-tdd`)
8. **Pan/zoom per diagram** - Each diagram viewport supports:
   - Mouse wheel zoom (0.3x to 3.0x range, 0.1 step)
   - Click-and-drag panning
   - Button controls: zoom out (-), reset (1:1), zoom in (+)
   - CSS `transform-origin: 0 0` with `translate()` and `scale()` transforms
9. **Modal expand** - Each diagram card has an expand button (Unicode `&#x26F6;`) that opens a full-screen modal (`95vw x 90vh`) showing the diagram's SVG content with a title bar and close button
10. **Modal dismiss** - Modal closes on: clicking the X button, clicking the backdrop overlay, or pressing Escape
11. **Feature navigation** - When multiple features are exported, a sticky nav bar renders anchor links for each feature section; clicks trigger smooth scrolling
12. **Feature sections** - Each feature renders as a `<section>` with an `id` anchor, containing its diagrams followed by a requirements panel (if present)
13. **Requirements styling** - The `.requirements-content` class applies prose styling: sized headings, colored text, styled lists, code highlighting, table borders, blockquote left-border, and link coloring
14. **SVG enhancements** - Mermaid SVG edges get thicker strokes (`2.5px`), node/edge labels get `14px`/`12px` font sizes, and marker paths get `1.5px` strokes for readability

### Non-Functional

- **Performance:** Mermaid renders client-side asynchronously; each diagram rendered sequentially via `async/await`
- **Compatibility:** Works in modern browsers (Chrome, Firefox, Safari, Edge) that support ES2017+ and CSS custom properties
- **Accessibility:** Diagram descriptions shown in card headers; feature names used as section headings
- **File size:** Minimal - only metadata and Mermaid source text embedded; rendering libraries loaded from CDN

## User Workflows

### Workflow 1: Viewing Exported Documentation

**Actor:** Documentation recipient
**Trigger:** Opening the exported `.html` file in a browser

**Steps:**
1. Browser loads the HTML file and fetches CDN dependencies
2. JavaScript parses the embedded `export-data` JSON
3. Mermaid initializes with dark theme configuration
4. `renderAllDiagrams()` renders each diagram into its placeholder
5. `renderAllRequirements()` converts markdown to HTML for each requirements section
6. User sees fully rendered diagrams with zoom controls and formatted requirements

**Error Cases:**
- CDN unavailable: Diagrams and requirements won't render (plain JSON visible in source)
- Invalid Mermaid syntax: Error message shown inline with raw source code

### Workflow 2: Interacting with Diagrams

**Actor:** Documentation recipient
**Trigger:** Diagram is too large or too small to read

**Steps:**
1. User scrolls mouse wheel over diagram to zoom in/out
2. User clicks and drags to pan the diagram
3. User clicks zoom buttons (+, -, 1:1) for precise control
4. User clicks expand button to view diagram in full-screen modal
5. User presses Escape or clicks backdrop to close modal

## Data Model

**Template Context Variables (from Jinja2):**
- `project_name` (string) - displayed in header
- `export_date` (string, YYYY-MM-DD) - displayed in header
- `features` (list of objects) - each with `name`, `diagrams` (list with `name`, `category`, `description`, `content`), `requirements_md` (string or None)
- `export_data` (dict) - JSON blob with `diagrams` (array of `{id, content, name}`) and `requirements` (dict of feature name to markdown)

**Client-side State:**
- `EXPORT_DATA` - parsed JSON from embedded script tag
- `viewportState[idx]` - per-diagram object: `{ scale, panX, panY, dragging, startX, startY }`
- `mermaidCounter` - incrementing counter for unique Mermaid render IDs

## Integration Points

**Dependencies:**
- Jinja2 template engine (server-side rendering of template variables)
- Tailwind CSS CDN (styling)
- Mermaid @11 CDN (diagram rendering)
- Marked @15 CDN (markdown rendering)

**Provides to:**
- `ExportService.generate_export_html()` - the template is loaded and rendered by the service

## Technical Considerations

### Architecture
- Single-file self-contained HTML with embedded CSS and JavaScript
- No external assets beyond CDN scripts
- All diagram and requirements data embedded as JSON to avoid any server round-trips

### Patterns
- Data embedding via `<script type="application/json">` + `|tojson` Jinja2 filter
- Async sequential rendering of Mermaid diagrams to avoid race conditions
- Per-viewport state management via `viewportState` object keyed by diagram index
- CSS transform-based pan/zoom (no external pan/zoom library)

### Libraries/APIs
- `mermaid.render(id, source)` - async Mermaid rendering API
- `marked.parse(markdown)` - synchronous Marked rendering API
- DOM event listeners for mouse interactions (wheel, mousedown, mousemove, mouseup, mouseleave)
- `element.scrollIntoView({ behavior: 'smooth' })` for navigation

## Acceptance Criteria

- [x] Template loads Tailwind CSS, Mermaid @11, and Marked @15 from CDN
- [x] Diagram data embedded as JSON via `|tojson` in a `<script type="application/json">` tag
- [x] Mermaid initialized with dark theme and custom color variables
- [x] All diagrams render client-side via `mermaid.render()`
- [x] Parse errors display inline with raw source and yellow error text
- [x] Requirements render via `marked.parse()` with GFM and breaks enabled
- [x] Each diagram has pan (drag), zoom (wheel + buttons), and reset (1:1) controls
- [x] Zoom range clamped between 0.3x and 3.0x
- [x] Expand button opens full-screen modal (95vw x 90vh) with diagram content
- [x] Modal closes on Escape key, backdrop click, or X button
- [x] Feature navigation bar appears when multiple features are exported
- [x] Navigation links trigger smooth scroll to feature sections
- [x] Category badges display correctly (blue for architecture, amber for TDD)
- [x] Dark theme applied consistently (#0f172a background, #1e293b cards, slate text colors)
- [x] Mermaid SVG edges rendered with enhanced stroke widths for readability
- [x] Requirements prose styled with proper headings, lists, code blocks, tables, and blockquotes
