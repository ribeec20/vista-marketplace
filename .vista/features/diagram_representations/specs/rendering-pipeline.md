# Spec: Diagram Rendering Pipeline

> Updated: 2026-02-15 — Multi-format support: 6 renderers, CDN dependencies, markdown inline editing

## Overview

Client-side rendering of native diagram files using type-specific libraries in the web dashboard. Supports 6 diagram formats with a dispatcher-based architecture.

## Parent JTBD

As a developer, I want to see my architecture diagrams rendered visually in the web dashboard without custom SVG code.

## Scope

**In Scope:**
- Mermaid.js client-side rendering for .mmd files
- PlantUML server-side rendering for .puml files (via configurable PlantUML server)
- D2 raw source display for .d2 files (with optional Kroki server rendering)
- Graphviz client-side WASM rendering for .dot files (via @viz-js/viz)
- Draw.io embedded viewer for .drawio files (via viewer.diagrams.net iframe)
- Markdown rendering and inline editing for .md files (via marked.js)
- Type-to-renderer dispatch based on _arch.json manifest `type` field
- Diagram page/view in the web dashboard
- Loading states and error handling per diagram

**Out of Scope:**
- AI chat panel (see chat-review spec)
- Standalone HTML preview generation (being removed)
- Template.html custom SVG rendering (being removed)

## Requirements

### Functional

1. Web app reads _arch.json manifest via API, then fetches each diagram file by type
2. Mermaid diagrams (.mmd): Render client-side via mermaid.js `mermaid.render()` with node click handlers
3. PlantUML diagrams (.puml): Encode via plantuml-encoder, fetch SVG from configurable PlantUML server
4. D2 diagrams (.d2): Display raw source with info message; optionally render via Kroki server if configured
5. Graphviz diagrams (.dot): Render client-side via @viz-js/viz WASM (lazy-loaded on first use)
6. Draw.io diagrams (.drawio): Embed via viewer.diagrams.net iframe with base64-encoded content
7. Markdown files (.md): Render as formatted HTML via marked.js; support inline editing (view/edit toggle)
8. Each diagram rendered in its own card with title and description from manifest
9. Diagrams laid out vertically, one per card, full-width
10. All renderers show error message + raw source as fallback on failure
11. Clickable diagrams (for chat context injection - handled by chat-review spec)

### Non-Functional

- **Performance:** Mermaid renders < 1s per diagram. Draw.io iframe loads within 3s. Graphviz WASM initial load ~2.5MB (subsequent renders instant).
- **Platform:** Modern browsers (Chrome, Firefox, Edge, Safari)
- **CDN dependencies:** PlantUML encoder loaded eagerly (~10KB). Graphviz WASM loaded lazily on first .dot render (~2.5MB).

## User Workflows

### Workflow 1: View Feature Diagrams

**Actor:** Developer
**Trigger:** Navigate to feature architecture page

**Steps:**
1. User opens `/project/{id}/arch/{feature_name}` in browser
2. Server returns page with manifest data and PlantUML server URL
3. Client JavaScript reads manifest, fetches each diagram file via API
4. `renderDiagramContent()` dispatches to the correct renderer via `RENDERERS` map keyed by `diagram.type`
5. Each type-specific renderer handles its own rendering:
   - Mermaid: `mermaid.render()` → SVG with clickable nodes
   - PlantUML: plantuml-encoder → fetch SVG from PlantUML server
   - D2: raw source display (or Kroki SVG if server configured)
   - Graphviz: lazy-load @viz-js/viz WASM → `renderSVGElement()`
   - Draw.io: iframe with base64-encoded content via viewer.diagrams.net
   - Markdown: `marked.parse()` → formatted HTML with edit button
6. All diagrams visible with titles and descriptions

**Error Cases:**
- Mermaid parse error: Show error message + raw source in card
- PlantUML server unreachable: Show error + raw source as fallback
- Graphviz WASM load failure: Show error + raw source
- Draw.io file missing: Show "File not found" placeholder in card
- Network error fetching diagram: Show retry button

## Data Model

**Entities:**
- DiagramCard: `{ name, description, type, diagramType, content (fetched), renderState (loading|rendered|error) }`

**Relationships:**
- DiagramCard maps 1:1 to DiagramEntry in manifest

## Integration Points

**Dependencies:**
- Arch directory spec: Provides _arch.json manifest and file structure
- Server API: New endpoints to serve manifest and diagram file contents

**Provides to:**
- Chat review spec: Rendered diagrams are clickable to inject into chat context

## Technical Considerations

### Architecture

Server-side:
- `GET /api/projects/{id}/features/{name}/arch` — Returns _arch.json manifest
- `GET /api/projects/{id}/features/{name}/arch/{filename}` — Returns raw file content with correct Content-Type:
  | Extension | Content-Type |
  |-----------|-------------|
  | `.mmd` | `text/plain` |
  | `.drawio` | `application/xml` |
  | `.puml` | `text/plain` |
  | `.d2` | `text/plain` |
  | `.dot` | `text/plain` |
  | `.md` | `text/markdown` |
- `PUT /api/projects/{id}/features/{name}/arch/{filename}` — Write content to `.md` files only (with path traversal protection)

Client-side:
- Renderer dispatch map: `RENDERERS = { mermaid, plantuml, d2, graphviz, drawio, markdown }`
- Each renderer takes `(el, content, idx, filename)` and produces the visual
- Manifest `type` field is passed as 5th argument to `renderDiagramContent()` for dispatch

### Renderer Map

| type     | Renderer            | Library                                         | Loading   |
|----------|---------------------|--------------------------------------------------|-----------|
| mermaid  | `renderMermaid()`   | mermaid.js v11 (CDN)                             | Eager     |
| plantuml | `renderPlantUML()`  | plantuml-encoder v1.4.0 (CDN) + PlantUML server  | Eager     |
| d2       | `renderD2()`        | Raw source display / optional Kroki server        | N/A       |
| graphviz | `renderGraphviz()`  | @viz-js/viz v3.11.0 WASM (CDN)                   | Lazy      |
| drawio   | `renderDrawio()`    | viewer.diagrams.net iframe                        | On-demand |
| markdown | `renderMarkdown()`  | marked.js (already loaded)                        | Eager     |

### CDN Dependencies

| Library | CDN URL | Size | Loading Strategy |
|---------|---------|------|-----------------|
| mermaid.js v11 | `cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js` | ~1MB | Eager (script tag) |
| marked.js | `cdn.jsdelivr.net/npm/marked/marked.min.js` | ~40KB | Eager (script tag) |
| plantuml-encoder v1.4.0 | `cdn.jsdelivr.net/npm/plantuml-encoder@1.4.0/dist/plantuml-encoder.min.js` | ~10KB | Eager (script tag) |
| @viz-js/viz v3.11.0 | `cdn.jsdelivr.net/npm/@viz-js/viz@3.11.0/lib/viz-standalone.js` | ~2.5MB | Lazy (dynamic script injection on first .dot render) |

### Server Dependencies

| Service | URL | Configurable | Purpose |
|---------|-----|-------------|---------|
| PlantUML server | `https://www.plantuml.com/plantuml` (default) | Yes — `diagrams.plantuml_server_url` in settings | SVG rendering for .puml files |
| Kroki server | Not configured by default | Future — `window.KROKI_SERVER_URL` | Optional D2 rendering |
| Draw.io viewer | `https://viewer.diagrams.net` | No | Iframe-based .drawio rendering |

### Libraries/APIs

- **mermaid.js** — CDN: `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js` — Client-side Mermaid rendering
- **marked.js** — CDN: already loaded — Markdown to HTML conversion
- **plantuml-encoder** — CDN: `https://cdn.jsdelivr.net/npm/plantuml-encoder@1.4.0/dist/plantuml-encoder.min.js` — PlantUML source encoding
- **@viz-js/viz** — CDN: `https://cdn.jsdelivr.net/npm/@viz-js/viz@3.11.0/lib/viz-standalone.js` — Graphviz DOT to SVG (WASM)
- **Draw.io viewer** — Embedded via iframe with `https://viewer.diagrams.net/?...` — base64-encoded content URL

### Patterns

- Progressive rendering: Show loading skeleton per card, replace with rendered diagram as each completes
- Error boundary per card: One diagram failing doesn't block others
- Lazy vs eager loading: Small libraries (plantuml-encoder ~10KB) loaded eagerly; large WASM (viz.js ~2.5MB) loaded on first use
- Graceful degradation: D2 shows raw source when no Kroki server available; all renderers fall back to raw source on error

## Acceptance Criteria

- [x] Mermaid .mmd files render as interactive SVG in browser
- [x] PlantUML .puml files render as SVG via PlantUML server
- [x] D2 .d2 files display raw source with info message (Kroki rendering optional)
- [x] Graphviz .dot files render as SVG via @viz-js/viz WASM
- [x] Draw.io .drawio files render in embedded iframe viewer via viewer.diagrams.net
- [x] Markdown .md files render as formatted HTML via marked.js
- [x] Markdown files support inline editing (edit/save/cancel with keyboard shortcuts)
- [x] Each diagram shows title and description from manifest
- [x] All renderers show error message + raw source on failure
- [x] Missing files show clear placeholder
- [x] No custom SVG layout code — all rendering delegated to libraries
- [x] RENDERERS dispatch map routes by manifest `type` field
- [x] Graphviz WASM loads lazily (only on first .dot render)
- [x] PlantUML encoder loads eagerly (~10KB)
- [ ] Page loads and renders 5 diagrams in < 3s total — not verified (performance requirement)

## Implementation Notes

- Mermaid.js is loaded from CDN (`https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js`).
- Diagram cards support pan/zoom interaction via viewport transforms.
- Diagrams can be expanded to a full-page view at `/project/{id}/arch/{feature_name}/diagram/{filename}`.
- Live diagram updates are supported via the `DiagramWatcher` service using the `watchdog` library for filesystem events with 100ms debounce.
- `renderDiagramContent()` uses a RENDERERS dispatch map keyed by type (mermaid, plantuml, d2, graphviz, drawio, markdown) — falls back to escaped `<pre>` for unknown types.
- Draw.io viewer uses base64-encoded content in the iframe URL. Very large `.drawio` files may exceed URL limits; postMessage API can be added as future enhancement.
- Graphviz uses `Viz.instance()` from lazy-loaded `@viz-js/viz@3.11.0/lib/viz-standalone.js`. The instance is cached after first load.
- PlantUML server URL is injected from backend via `{{ plantuml_url | tojson }}` Jinja2 expression into `PLANTUML_SERVER_URL` JS constant.
- Markdown inline editor uses a state machine (view → editing → saving → view) with `markdownEditState` tracking per diagram index. Ctrl+S saves, Escape cancels.
- CSS styles for markdown editor and rendered content are in `arch-chat.css`.

## Resolved Questions

- Mermaid.js is loaded from CDN (not bundled).
- Draw.io rendering uses viewer.diagrams.net iframe with base64-encoded content URL.
- D2 has no browser-compatible WASM build. Ships as raw source with optional Kroki server integration.
- Only markdown files are editable inline — other diagram types require external editing tools.
