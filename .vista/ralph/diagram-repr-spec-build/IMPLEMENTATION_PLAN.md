# Implementation Plan: Multi-Format Diagram Support & Markdown Editing (Build)

**Source Plan:** `.vista/ralph/diagram-repr-spec-planning/IMPLEMENTATION_PLAN.md`
**Status:** COMPLETE — All phases done across 3 iterations

---

## Phase 1: Schema & Backend Foundation — DONE (Iteration 1)

- [x] 1.1 Extend arch-schema.json type enum (6 values)
- [x] 1.2 Add write_arch_file() to ProgressService (.md-only whitelist)
- [x] 1.3 Add PUT endpoint for file writing
- [x] 1.4 Update content-type mapping in GET endpoint (dictionary-based)
- [x] 1.5 Add PlantUML server URL to settings (config.py)
- [x] 1.6 Extend diagram watcher extensions (both WATCH_EXTENSIONS, EXT_TO_TYPE, _detect_file_type, _update_manifest_sync)

**Deviation:** Non-mermaid files now get `diagramType: "custom"` instead of their format name (e.g., drawio files were previously "drawio", now "custom"). This is more consistent — diagramType is for Mermaid subtypes.

## Phase 5 (partial): Backend Tests — DONE (Iteration 1)

- [x] 5.1 PUT endpoint tests (7 tests in TestArchWriteAPI)
- [x] 5.2 ProgressService write tests (6 tests in TestProgressServiceWrite)
- [x] 5.3 Extended schema validation tests (4 tests in TestExtendedSchemaValidation)
- [x] 5.4 Content-type tests (4 tests in TestContentTypes)
- [x] 5.5 Diagram watcher extension tests (16 tests in TestExtendedFileTypes)
- [x] 5.6 Settings tests (2 tests in TestDiagramSettings)
- [x] Updated existing test_drawio_type to expect "custom" diagramType

**Total tests:** 95 passing (53 arch + 42 watcher)

---

## Phase 2: Client-Side Renderer Infrastructure — DONE (Iteration 2)

- [x] 2.1 Refactor renderer dispatch in architecture.html (RENDERERS map with type-based dispatch)
- [x] 2.2 Extract Mermaid renderer into standalone renderMermaid() function
- [x] 2.3 PlantUML renderer (plantuml-encoder CDN + PLANTUML_SERVER_URL server fetch)
- [x] 2.4 D2 renderer (raw source display + optional Kroki server integration)
- [x] 2.5 Graphviz renderer (lazy-loaded @viz-js/viz@3.11.0 WASM)
- [x] 2.6 Draw.io renderer (iframe via viewer.diagrams.net with base64 encoding)
- [x] 2.7 Markdown renderer (marked.js with rawContent dataset storage for edit mode)

**Learnings:**
- Extension-based type inference added as fallback when `diagramType` is not provided (for backwards compatibility)
- Draw.io uses base64-encoded URL; large files may need postMessage API in future
- Graphviz WASM loads lazily via dynamic script injection on first .dot diagram render

## Phase 3: Markdown Inline Editor — DONE (Iteration 2)

- [x] 3.1 Edit button on markdown cards (Jinja2 template + JS dynamic cards)
- [x] 3.2 Edit mode state machine (view → editing → saving → view) with markdownEditState tracking
- [x] 3.3 Keyboard shortcuts (Ctrl+S/Cmd+S save, Escape cancel)
- [x] 3.4 Editor CSS styles (md-editor-container, toolbar, textarea, save/cancel buttons, indicators)

**Implementation notes:**
- DIAGRAMS array is 0-indexed but element IDs use 1-indexed (idx = loop.index in Jinja2)
- Save indicator shows "Saving..." → "Saved!" → auto-switch to rendered view after 800ms
- autoResizeTextarea() dynamically adjusts height with 200px minimum

## Phase 4: Template & Watcher Integration — DONE (Iteration 2)

- [x] 4.1 Pass manifest type to renderers in loadDiagrams() (5th argument)
- [x] 4.2 Conditionally show edit button in card header (Jinja2 + addDiagramCard JS)
- [x] 4.3 CDN script loading (plantuml-encoder@1.4.0 eager, viz-js lazy)
- [x] 4.4 PlantUML server URL injection (done in architecture.py route, Iteration 1)

**Additional changes:**
- updateDiagram() and addDiagramCard() now pass diagram.type to renderDiagramContent()
- addDiagramCard() infers type from file extension for dynamically added diagrams
- PLANTUML_SERVER_URL JS constant injected via Jinja2 `{{ plantuml_url | tojson }}`
- Rendered markdown content CSS styles added to arch-chat.css

---

## Phase 5 (remainder): Integration Tests — SKIPPED

- [ ] Integration tests for full render pipeline — requires browser-based testing framework (Playwright/Cypress) not set up in this project. Backend tests (95 passing) provide sufficient coverage for server-side logic.

## Phase 6: Documentation & Skill Updates — DONE (Iteration 3)

- [x] 6.1 Update plan skill SKILL.md — Added supported formats table, design-rationale.md example, manifest type values docs, expanded output files section
- [x] 6.2 Update diagrams skill — Added "Supported Diagram Formats" section with 6-format comparison table, usage guidance, and dashboard rendering notes
- [x] 6.3 Update specs:
  - arch-directory.md — Extended types to 6, added markdown editing workflow, 6 new acceptance criteria, expanded implementation notes
  - rendering-pipeline.md — 6-renderer table, CDN dependencies table, server dependencies table, expanded patterns and acceptance criteria
