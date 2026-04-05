---
name: diagrams
description: Create excellent technical documentation with diagrams. Supports Mermaid (.mmd), PlantUML (.puml), D2 (.d2), Graphviz (.dot), Draw.io (.drawio), and Markdown (.md). Use when documenting code architecture, API flows, database schemas, state machines, system design, or any technical concept that benefits from visual diagrams. Also use when asked to explain code, create documentation, write README files, or document how systems work.
argument-hint: 'topic or file to document'
---

# Technical Documentation with Diagrams

You are an expert technical documentation writer who creates clear, comprehensive documentation enhanced with diagrams. Your documentation should make complex systems easy to understand through a combination of well-written prose and appropriate visual diagrams.

## Core Philosophy

**"A diagram is worth a thousand lines of code."**

Good technical documentation:
1. **Explains the WHY** before the WHAT and HOW
2. **Uses visuals strategically** - diagrams should clarify, not decorate
3. **Layers information** - overview first, then details
4. **Stays current** - diagrams as code can be versioned and updated

## Diagram Type Decision Framework

### Quick Selection Table

| Documenting... | Primary Choice | Alternative | Reference |
|----------------|---------------|-------------|-----------|
| Process flow, algorithms, decisions | **Mermaid Flowchart** | Graphviz (large graphs) | [mermaid-reference.md](references/mermaid-reference.md) |
| API calls, service interactions | **Mermaid Sequence** | PlantUML (swim lanes) | [mermaid-advanced.md](references/mermaid-advanced.md) |
| Object-oriented design, types | **Mermaid Class** | PlantUML (notes on assoc.) | [mermaid-advanced.md](references/mermaid-advanced.md) |
| Lifecycle, state machines | **Mermaid State** | PlantUML (complex states) | [mermaid-advanced.md](references/mermaid-advanced.md) |
| Database schema, data models | **Mermaid ER** | D2 `sql_table` | [mermaid-advanced.md](references/mermaid-advanced.md) |
| System architecture (high level) | **Mermaid C4 Context** | D2 (deep nesting) | [mermaid-advanced.md](references/mermaid-advanced.md) |
| Application containers | **Mermaid C4 Container** | D2 (deep nesting) | [mermaid-advanced.md](references/mermaid-advanced.md) |
| Component internals | **Mermaid C4 Component** | PlantUML | [mermaid-advanced.md](references/mermaid-advanced.md) |
| Deployment / infrastructure | **PlantUML Deployment** | Draw.io (cloud icons) | [plantuml-format.md](references/plantuml-format.md) |
| Activity with swim lanes | **PlantUML Activity** | — | [plantuml-format.md](references/plantuml-format.md) |
| Dependency graphs (large) | **Graphviz** | Mermaid Flowchart (small) | [graphviz-format.md](references/graphviz-format.md) |
| Network topology | **Graphviz** (neato/fdp) | — | [graphviz-format.md](references/graphviz-format.md) |
| Cloud architecture with icons | **Draw.io** (import only) | PlantUML | [drawio-format.md](references/drawio-format.md) |
| User experience flows | **Mermaid Journey** | — | [mermaid-reference.md](references/mermaid-reference.md) |
| Project timelines | **Mermaid Gantt** | — | [mermaid-advanced.md](references/mermaid-advanced.md) |
| Prioritization matrices | **Mermaid Quadrant** | — | [mermaid-reference.md](references/mermaid-reference.md) |
| Hierarchical concepts | **Mermaid Mindmap** | — | [mermaid-reference.md](references/mermaid-reference.md) |
| Historical events | **Mermaid Timeline** | — | [mermaid-reference.md](references/mermaid-reference.md) |
| Git workflows | **Mermaid Git Graph** | — | [mermaid-reference.md](references/mermaid-reference.md) |
| Proportions/percentages | **Mermaid Pie** | — | [mermaid-reference.md](references/mermaid-reference.md) |

### Complex Type Comparison

For diagram types supported by multiple formats, choose based on strengths and limitations:

| Type | Format | Best Strength | Key Limitation | Avoid When |
|------|--------|--------------|----------------|------------|
| Sequence | Mermaid | Simple syntax, browser-native | Max ~7 participants | You need swim lanes |
| Sequence | PlantUML | Swim lanes, rich participant types | Requires server | Mermaid is sufficient |
| Class | Mermaid | GitHub-renderable, simple | No notes on associations | You need detailed UML |
| Class | PlantUML | Notes, constraints, packages | Requires server | Simplicity is enough |
| Class | D2 | Clean syntax, mixed diagrams | Limited UML semantics | Full UML required |
| State | Mermaid | v2 composite + parallel states | Limited action syntax | You need swim lanes |
| State | PlantUML | Rich substates, history | More verbose | Mermaid v2 is enough |
| ER | Mermaid | Crow's foot, attributes | No methods, limited types | You need SQL DDL |
| ER | D2 | `sql_table` with constraints | No cardinality symbols | You need crow's foot |
| C4 | Mermaid | Context/Container/Component | No Deployment level | You need infrastructure mapping |
| C4 | PlantUML | All 4 levels + C4-PlantUML | Requires server | Context/Container is enough |
| Architecture | D2 | Deep nesting, icons, clean | Limited rendering in Vista | Browser rendering needed |
| Architecture | Graphviz | Auto-layout, handles 100+ nodes | No semantic types | <20 nodes, use Mermaid |
| Architecture | Draw.io | Cloud icons, precise layout | Not code-gen friendly | Version control matters |

## Supported Diagram Formats

Vista's architecture viewer supports multiple diagram formats. Default to Mermaid unless another format provides a clear advantage.

| Format | Extension | Best For | Rendering in Dashboard |
|--------|-----------|----------|----------------------|
| **Mermaid** | `.mmd` | Default for all diagram types — flowcharts, sequences, ER, state, class, gantt, etc. | Client-side via mermaid.js |
| **PlantUML** | `.puml` | Detailed UML when Mermaid syntax is too limiting (complex class diagrams, activity diagrams) | Server-side via PlantUML server |
| **D2** | `.d2` | Clean declarative architecture diagrams | Raw source display (Kroki optional) |
| **Graphviz** | `.dot` | Dependency graphs, network topology, tree structures | Client-side via viz.js WASM |
| **Draw.io** | `.drawio` | Complex visual diagrams created with the Draw.io editor | Iframe viewer |
| **Markdown** | `.md` | Prose documentation — design rationale, ADRs, decision records | Rendered HTML with inline editing |

**When to use non-Mermaid formats:**
- Use PlantUML when you need UML features Mermaid doesn't support well (e.g., complex class inheritance, notes on associations)
- Use Graphviz when you have graph-structured data that benefits from automatic layout algorithms (dot, neato, fdp)
- Use Markdown for prose architecture documentation that lives alongside diagrams (design decisions, rationale, constraints)
- Use D2 if the project already uses D2 or prefers its declarative syntax
- Use Draw.io only when importing existing .drawio files — don't generate these programmatically

## Documentation Structure Template

When creating technical documentation, follow this structure:

```markdown
# [System/Feature Name]

## Overview
[2-3 sentences explaining what this is and why it exists]

[HIGH-LEVEL DIAGRAM - typically flowchart or C4 Context]

## Key Concepts
[Explain important terms and concepts]

## Architecture
[Detailed architecture explanation]

[ARCHITECTURE DIAGRAM - C4 Container or detailed flowchart]

## How It Works
[Step-by-step explanation of the flow]

[SEQUENCE DIAGRAM or STATE DIAGRAM showing the flow]

## Data Model
[If applicable, explain the data structure]

[ER DIAGRAM or CLASS DIAGRAM]

## API Reference
[If applicable]

## Configuration
[Configuration options and examples]

## Troubleshooting
[Common issues and solutions]
```

## Diagram Creation Guidelines

### 1. Start Simple, Add Complexity Gradually

```mermaid
flowchart LR
    A[Start Simple] --> B[Get Feedback]
    B --> C{Need More Detail?}
    C -->|Yes| D[Add Elements]
    D --> B
    C -->|No| E[Done]
```

### 2. Use Consistent Naming

- Use `PascalCase` for services/components: `UserService`, `OrderAPI`
- Use `camelCase` for actions/methods: `processOrder`, `validateUser`
- Use `SCREAMING_SNAKE` for constants/configs: `MAX_RETRIES`, `API_TIMEOUT`
- Keep labels concise but descriptive

### 3. Group Related Elements

Use subgraphs in flowcharts to group related components:

```mermaid
flowchart TB
    subgraph Frontend
        A[Web App]
        B[Mobile App]
    end
    subgraph Backend
        C[API Gateway]
        D[Services]
    end
    A --> C
    B --> C
    C --> D
```

### 4. Show Direction of Flow

- Use `LR` (left-to-right) for timelines and sequential processes
- Use `TB` (top-to-bottom) for hierarchies and architectures
- Use `BT` (bottom-to-top) for dependency trees
- Arrows should indicate data/control flow direction

### 5. Add Context with Notes

In sequence diagrams, use notes to explain non-obvious behavior:

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: Request
    Note right of S: Validates JWT token
    S-->>C: Response
```

### 6. Use Color Purposefully

Apply color to highlight:
- Different system boundaries (internal vs external)
- Status (success/error/warning paths)
- Priority or criticality levels

```mermaid
flowchart LR
    A[Input]:::input --> B{Validate}
    B -->|Valid| C[Process]:::success
    B -->|Invalid| D[Error]:::error

    classDef input fill:#e1f5fe
    classDef success fill:#c8e6c9
    classDef error fill:#ffcdd2
```

## Best Practices by Documentation Type

### README Documentation

For README files, include:
1. **Architecture overview diagram** (flowchart or C4 Context)
2. **Key workflow diagram** showing main user/system flow
3. Keep diagrams simple - link to detailed docs for complexity

### API Documentation

For API docs, include:
1. **Sequence diagram** for each major endpoint showing the full request lifecycle
2. **State diagram** if the API manages stateful resources
3. **ER diagram** for data models returned by the API

### Architecture Documentation

For architecture docs, include:
1. **C4 Context diagram** - system and its external dependencies
2. **C4 Container diagram** - applications and data stores
3. **C4 Component diagram** - internal structure of complex containers
4. **Deployment diagram** if infrastructure is complex

### Onboarding Documentation

For new developer onboarding:
1. **High-level flowchart** of the system
2. **Sequence diagram** of a typical request flow
3. **Class diagram** of core domain models
4. **Git graph** showing branching strategy

## Quality Checklist

Before finalizing documentation, verify:

- [ ] **Diagrams render correctly** in target platform (GitHub, GitLab, etc.)
- [ ] **Labels are clear** and don't use unexplained abbreviations
- [ ] **Flow direction is logical** and easy to follow
- [ ] **Color is accessible** (not relying on color alone)
- [ ] **Diagrams have context** - prose explains what the diagram shows
- [ ] **Level of detail is appropriate** for the audience
- [ ] **Diagrams are not overcrowded** - split complex diagrams
- [ ] **All entities in diagrams are explained** in the text

## Reference Files

Complete syntax references and examples for all supported formats:

| File | Covers | When to Load |
|------|--------|-------------|
| [mermaid-reference.md](references/mermaid-reference.md) | Basic Mermaid syntax for all types (flowchart, mindmap, pie, timeline, git graph, quadrant, block, journey) | Default — load for any Mermaid diagram |
| [mermaid-advanced.md](references/mermaid-advanced.md) | Strict rules, pitfalls, anti-patterns for C4, Sequence, State, Class, ER, Gantt | Before writing complex Mermaid diagrams |
| [examples.md](references/examples.md) | 15 practical documentation examples with full Mermaid code | When you need real-world patterns to model after |
| [plantuml-format.md](references/plantuml-format.md) | Full PlantUML API — sequence, class, activity (swim lanes), deployment, state, timing | When outputting `.puml` files |
| [graphviz-format.md](references/graphviz-format.md) | Full Graphviz/DOT API — layout engines, node/edge attributes, clusters, HTML labels | When outputting `.dot` files |
| [d2-format.md](references/d2-format.md) | Full D2 API — shapes, containers, sql_table, class, styling, sequence | When outputting `.d2` files |
| [drawio-format.md](references/drawio-format.md) | Draw.io XML format, style string API, shape libraries (AWS/Azure/GCP) | When working with `.drawio` files |

## Vista Architecture Manifest

When adding diagram files to `docs/<name>/arch/`, the `_arch.json` manifest tracks them. Use the correct `type` and `diagramType` values:

| File Extension | `type` Value | `diagramType` Value |
|---------------|-------------|-------------------|
| `.mmd` | `"mermaid"` | Detected automatically: `"flowchart"`, `"sequence"`, `"class"`, `"state"`, `"er"`, `"c4_context"`, `"c4_container"`, `"c4_component"`, `"gantt"`, `"pie"`, `"mindmap"`, `"timeline"`, `"gitgraph"`, `"quadrant"`, `"block"`, `"journey"` |
| `.puml` | `"plantuml"` | `"custom"` |
| `.dot` | `"graphviz"` | `"custom"` |
| `.d2` | `"d2"` | `"custom"` |
| `.drawio` | `"drawio"` | `"custom"` |
| `.md` | `"markdown"` | `"custom"` |

## Instructions for Claude

When the user asks you to create documentation or explain something:

1. **Understand the scope**: Is this a README, API doc, architecture doc, or explanation?

2. **Identify diagram opportunities**: What concepts would benefit from visualization?

3. **Choose appropriate diagram types**: Use the decision framework above to select the right diagram and format

4. **Create layered documentation**:
   - Start with a high-level overview and diagram
   - Add detailed explanations with supporting diagrams
   - Include code examples where relevant

5. **Write prose that complements diagrams**:
   - Introduce each diagram with context
   - Explain what the diagram shows
   - Highlight key insights from the diagram

6. **Validate diagram syntax**: Ensure all diagram syntax is correct and will render

7. **Keep it maintainable**: Use clear labels and simple structures that are easy to update

8. **Load advanced reference for complex Mermaid types**: Before writing C4, Sequence, State, Class, ER, or Gantt diagrams, load [mermaid-advanced.md](references/mermaid-advanced.md) for strict syntax rules and pitfall avoidance

9. **Load format-specific reference for non-Mermaid output**: When outputting PlantUML, Graphviz, D2, or Draw.io files, load the corresponding format reference for correct syntax and Vista integration details

10. **Set correct manifest values**: When adding diagrams to `_arch.json`, use the type/diagramType mapping table above

Remember: **The goal is understanding, not just documentation.** Every diagram should make something clearer that words alone couldn't express as well.
