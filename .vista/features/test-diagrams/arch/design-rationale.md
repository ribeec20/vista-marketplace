# Architecture Decision Record: Multi-Format Diagram Support

## Status
**Accepted** | 2026-02-15

## Context

Vista's architecture viewer originally supported only Mermaid diagrams (`.mmd` files). As the project grew, users needed to express different types of diagrams that Mermaid handles poorly:

- **PlantUML** — superior sequence diagrams with better auto-layout
- **D2** — declarative diagrams with a cleaner syntax for infrastructure
- **Graphviz** — the standard for dependency and network graphs
- **Draw.io** — complex hand-crafted diagrams with a GUI editor
- **Markdown** — inline documentation alongside diagrams (ADRs, design docs)

## Decision

We will support **6 diagram formats** with a unified manifest (`_arch.json`) and type-based renderer dispatch:

| Format | Extension | Renderer | Loading |
|--------|-----------|----------|---------|
| Mermaid | `.mmd` | mermaid.js | Bundled (eager) |
| PlantUML | `.puml` | plantuml-encoder + server | Bundled + HTTP |
| D2 | `.d2` | d2-wasm | Lazy WASM load |
| Graphviz | `.dot` | @viz-js/viz | Lazy WASM load |
| Draw.io | `.drawio` | iframe embed | Lazy iframe |
| Markdown | `.md` | marked.js | Bundled (eager) |

## Consequences

### Positive
- Users can pick the **best tool** for each diagram type
- Markdown docs live alongside diagrams — no context switching
- PlantUML's server-side rendering means zero client overhead for complex diagrams

### Negative
- WASM loaders (D2, Graphviz) add ~2MB lazy-loaded payload
- PlantUML requires network access to a PlantUML server
- Draw.io diagrams are opaque XML — no diffing in git

### Risks
- PlantUML server availability (mitigated by configurable URL + raw fallback)
- WASM load times on slow connections (mitigated by lazy loading + skeleton UI)

## Code References

```
vista/server/routes/architecture.py     # API + page routes
vista/server/views/architecture.html    # Renderer dispatch JS
vista/server/views/static/arch-chat.css # Markdown content styles
```
