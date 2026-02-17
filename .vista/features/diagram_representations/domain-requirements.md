# Domain Requirements: Diagram Representations

## Problem Statement

Vista currently stores all architecture diagrams (UI flows, data models, sequence diagrams, services, implementation phases) as structured JSON inside a monolithic `_plan.json` file, then renders them as custom SVG via vanilla JavaScript. This approach has three problems:

1. **No native editing** - Diagrams can't be opened in standard tools (Mermaid live editor, Draw.io). Editing requires modifying JSON and re-rendering.
2. **Rendering complexity** - 1,500+ lines of custom SVG layout code in template.html that must be maintained for every diagram type.
3. **Review friction** - The current approve/reject-per-item flow is passive. Users need an interactive way to review diagrams with AI assistance.

## Users & Personas

- **Developer (primary)** - Uses Vista to plan features. Wants to see architecture diagrams, edit them in native tools, and discuss them with AI before approving.
- **Plugin author** - Creates Vista planning workflows. Needs a simple file-based format that agents can generate (Mermaid syntax is LLM-friendly).

## Business Objectives

1. Replace the monolithic plan JSON diagram sections with native file formats (.mmd, .drawio)
2. Simplify the rendering pipeline by using established libraries (mermaid.js, drawio viewer)
3. Replace the passive review flow with an interactive AI chat interface
4. Keep the plan lightweight - `_plan.json` references the arch/ directory rather than embedding diagram data

## Success Metrics

- All 5 current diagram types representable via .mmd or .drawio files
- Web app renders diagrams from native files with zero custom SVG code
- AI chat interface connects to user's CLI providers (Claude, OpenCode) for review
- Agents can generate .mmd files directly (no intermediate JSON translation)

## Functional Requirements

### Core Functionality

1. **Architecture directory** - Each feature gets an `arch/` subdirectory containing native diagram files and a `_arch.json` manifest
2. **Manifest file** - `_arch.json` registers each diagram with name, file reference, type (mermaid/drawio), diagram subtype, and description
3. **Mermaid rendering** - Web app renders .mmd files client-side via mermaid.js
4. **Draw.io rendering** - Web app renders .drawio files via embedded viewer/iframe
5. **Plan reference** - `_plan.json` includes an `architecture.ref` field pointing to `./arch/_arch.json`
6. **AI chat panel** - Side-by-side chat interface that slides out from a button (Notion-style popup)
7. **Provider/model selection** - Chat dropdown selects from user's enabled CLI providers and their models
8. **Diagram context injection** - User clicks a diagram to add its content to the AI chat context

### User Workflows

1. **Plan generation** - Agent generates .mmd files in arch/ and writes _arch.json manifest
2. **Diagram viewing** - User opens web app, sees rendered diagrams organized by manifest
3. **AI review** - User clicks chat button, selects provider/model, clicks diagram to add context, discusses changes
4. **Diagram editing** - User edits .mmd files directly in text editor or via AI suggestions

### Business Rules

- _arch.json is the single source of truth for which diagrams exist
- Diagram files are stored in their native format - no format translation
- The web app reads the manifest first, then loads each file by type
- Chat messages are sent to the selected CLI provider's API

## Non-Functional Requirements

- **Performance:** Mermaid diagrams render client-side in < 1s. Draw.io viewer loads via iframe.
- **Platform:** Web only (Vista server dashboard)
- **Offline:** Not required - server must be running
- **Security:** CLI invocations run server-side with user's existing permissions
- **Accessibility:** Diagrams should have alt text from manifest descriptions

## Constraints & Dependencies

- **Technical:** mermaid.js loaded from CDN or bundled. Draw.io viewer requires iframe embedding.
- **Dependencies:** Existing provider system (ClaudeProvider, OpenCodeProvider) for chat. Existing FastAPI server for routes.
- **Breaking change:** Replaces the current plan JSON sections (uiFlows, dataModels, dataFlow, services) and removes the approve/reject review system entirely.

## User Experience Requirements

- **Discovery:** Diagrams tab/section on the feature page in the web dashboard
- **Journey:** Open feature -> see rendered diagrams -> click chat button -> select provider -> click diagram for context -> discuss with AI
- **Feedback:** Loading spinners while diagrams render. Chat shows streaming responses.
- **Error handling:** Missing .mmd file shows placeholder. Provider connection errors shown in chat.

---

## Expansion: Multi-Format Diagram Support

### Problem Statement (Addendum)

The initial design supports only Mermaid (.mmd) and Draw.io (.drawio) diagrams. While Mermaid is excellent for standard software diagrams (flowcharts, sequences, ER), it has significant representational limitations:

1. **Limited arrow vocabulary** — Mermaid supports only a handful of arrow styles. It cannot express multiple simultaneous connections between the same nodes, bidirectional data flows with different labels per direction, or protocol-specific link types.
2. **No hardware/physical diagrams** — There is no Mermaid syntax for network topology, rack/cabinet layouts, physical wiring, bus architectures, or pin-level connections. This is a major blindspot for projects involving embedded systems, IoT, infrastructure, or any hardware component.
3. **Rigid layout control** — Mermaid's auto-layout makes it hard to express spatial relationships that matter in hardware (e.g., "this board sits in slot 3 of this chassis").

Adding PlantUML (with `nwdiag` for network diagrams), D2 (with flexible layout and custom icons), Excalidraw (freeform spatial diagrams), and ASCII art (quick hardware sketches) closes these gaps and lets agents pick the right tool for each diagram.

### New Functional Requirements

#### Additional Diagram Formats

1. **PlantUML rendering (.puml)** — Server-side rendering via PlantUML server (local JAR or public API at `plantuml.com/plantuml`). Server converts `.puml` to SVG and returns it to the client. Fallback: if no PlantUML server is configured, show raw source with a "PlantUML server not configured" message.
2. **D2 rendering (.d2)** — Server-side rendering via the `d2` CLI tool. Server invokes `d2 <input>.d2 -` to produce SVG on stdout. Fallback: if `d2` CLI is not installed, show raw source with an install hint.
3. **Excalidraw rendering (.excalidraw)** — Client-side rendering via the `@excalidraw/excalidraw` React component loaded as a standalone bundle or via CDN. The `.excalidraw` JSON file is fetched and passed to the component as read-only.
4. **ASCII art rendering (.txt)** — Client-side rendering in a `<pre>` block with monospace font. No external library required. Supports syntax highlighting for box-drawing characters if feasible.

#### Manifest Extension

5. **Extended type enum** — `_arch.json` diagram entry `type` field now accepts: `mermaid`, `drawio`, `plantuml`, `d2`, `excalidraw`, `ascii`.
6. **Rendering hints** — Optional `renderConfig` object on diagram entries for format-specific settings (e.g., PlantUML theme, D2 layout engine, Excalidraw view options).

#### Hardware & Physical Diagram Support

5b. **PlantUML nwdiag** — Agents can use PlantUML's `nwdiag` syntax to generate network topology diagrams showing routers, switches, servers, VLANs, and IP addressing.
5c. **D2 hardware layouts** — D2's grid and spatial layout features support rack diagrams, board-level block diagrams, and bus architectures with custom icons/shapes.
5d. **Excalidraw freeform hardware** — For non-standard physical layouts (custom PCB outlines, sensor placements, wiring harnesses), Excalidraw's freeform canvas lets users sketch spatial relationships that structured formats can't express.
5e. **ASCII wiring diagrams** — Quick text-based pin diagrams, connector pinouts, and bus timing diagrams that work in any terminal or code review tool.

#### Chat Integration for New Formats

7. **Universal context injection** — All new formats support click-to-attach in the AI chat panel. The raw text content of `.puml`, `.d2`, and `.txt` files is injected directly. For `.excalidraw` (JSON), the element descriptions and text labels are extracted as a readable summary for chat context.
8. **Format-aware system prompt** — When a diagram is attached to chat, the system prompt includes the format name so the AI knows how to interpret and suggest edits in the correct syntax.

#### Server-Side Rendering Service

9. **Render endpoint** — New `GET /api/projects/{id}/features/{name}/arch/{filename}/render` endpoint that returns rendered SVG for server-rendered formats (PlantUML, D2). Client-rendered formats (Mermaid, Excalidraw, ASCII, Draw.io) continue to render on the client.
10. **Render caching** — Server caches rendered SVG output keyed by file content hash. Cache is invalidated when the source file changes.
11. **Render error handling** — If server-side rendering fails (bad syntax, missing tool), the endpoint returns the error message and raw source so the client can display both.

### Updated User Workflows

5. **Multi-format plan generation** — Agents choose the best diagram format per diagram type (e.g., PlantUML for complex class diagrams, D2 for infrastructure layouts, Mermaid for sequences, Excalidraw for freeform sketches).
6. **Server-rendered diagram viewing** — For PlantUML/D2, client requests pre-rendered SVG from the server render endpoint and displays it inline.
7. **Format badge** — Each diagram card shows a small format badge (MMD, PUML, D2, EXCAL, TXT) so users know the source format.

### Updated Business Rules

- The rendering pipeline dispatches by `type` field: client-rendered (mermaid, excalidraw, ascii, drawio) vs. server-rendered (plantuml, d2)
- Server-side renderers are optional dependencies — the system degrades gracefully with raw-source fallback
- Agents should prefer Mermaid for LLM-friendly generation but may use other formats when they better fit the diagram content

### Updated Non-Functional Requirements

- **Performance:** Server-rendered diagrams (PlantUML, D2) should return SVG in < 3s. Cached re-renders should be < 100ms.
- **Dependencies:** PlantUML requires Java + plantuml.jar or network access to public server. D2 requires the `d2` binary on PATH. Excalidraw requires loading ~500KB client bundle.
- **Graceful degradation:** All formats fall back to raw source display if their renderer is unavailable.

### TDD Candidates

- **Render dispatch logic** — The component that routes diagram entries to the correct renderer (client vs. server, by type). High branching, good TDD target.
- **Server render endpoint** — PlantUML/D2 subprocess invocation, caching, error handling. Side-effect-heavy, benefits from mocked tests.
- **Excalidraw context extraction** — Extracting readable text from `.excalidraw` JSON for chat injection. Pure function, ideal for TDD.
- **Manifest validation** — Validating the extended type enum and optional renderConfig field against a schema.
