# Graphviz (DOT) Format Reference

> Complete reference for creating Graphviz diagrams in Vista.
> Use Graphviz when you need automatic graph layout for dependency graphs, network topology, tree structures, or any graph-structured data.

## Table of Contents

- [File Format](#file-format)
- [When to Choose Graphviz](#when-to-choose-graphviz)
- [Graph Types](#graph-types)
- [Node Attributes](#node-attributes)
- [Edge Attributes](#edge-attributes)
- [Graph Attributes](#graph-attributes)
- [Layout Engines](#layout-engines)
- [Subgraph Clusters](#subgraph-clusters)
- [Rank Constraints](#rank-constraints)
- [HTML-Like Labels](#html-like-labels)
- [Record Shapes](#record-shapes)
- [Styling Patterns](#styling-patterns)
- [Vista Integration](#vista-integration)
- [Complete Examples](#complete-examples)

---

## File Format

- **Extension:** `.dot`
- **Encoding:** UTF-8
- **Comments:** C-style `//` single line or `/* ... */` block
- **Statement terminator:** Semicolons are optional but recommended

```dot
// Directed graph
digraph G {
    A -> B;
    B -> C;
}

// Undirected graph
graph G {
    A -- B;
    B -- C;
}
```

---

## When to Choose Graphviz

| Use Case | Why Graphviz | Alternative |
|----------|-------------|-------------|
| Dependency graphs | Automatic hierarchical layout | Mermaid flowchart (manual layout) |
| Network topology | `neato`/`fdp` spring layout | None — Mermaid has no spring layout |
| Large node counts (50+) | Handles hundreds of nodes | Mermaid struggles >30 nodes |
| Tree structures | `dot` engine optimized for trees | Mermaid mindmap (limited) |
| Circular layouts | `circo` engine | None in Mermaid |
| Radial layouts | `twopi` engine | None in Mermaid |
| Custom shapes (record/HTML) | Rich label formatting | Mermaid (limited shapes) |

**Rule of thumb:** Use Graphviz when graph structure matters more than semantic diagram types (sequence, state, ER).

---

## Graph Types

### Directed Graph (`digraph`)

```dot
digraph DependencyGraph {
    rankdir=LR;

    A -> B;
    A -> C;
    B -> D;
    C -> D;
}
```

### Undirected Graph (`graph`)

```dot
graph Network {
    layout=neato;

    A -- B;
    A -- C;
    B -- C;
    B -- D;
}
```

### Strict Graphs (no duplicate edges)

```dot
strict digraph G {
    A -> B;
    A -> B;  // ignored — strict prevents duplicates
    B -> C;
}
```

---

## Node Attributes

### Common Attributes

| Attribute | Values | Default | Description |
|-----------|--------|---------|-------------|
| `shape` | See shapes below | `ellipse` | Node shape |
| `label` | string | node name | Display text |
| `color` | color | `black` | Border color |
| `fillcolor` | color | `lightgrey` | Fill color (requires `style=filled`) |
| `style` | `filled`, `dashed`, `dotted`, `bold`, `rounded`, `invis` | — | Visual style |
| `fontname` | font name | `Times-Roman` | Font family |
| `fontsize` | number | `14` | Font size in points |
| `fontcolor` | color | `black` | Text color |
| `width` | inches | — | Minimum width |
| `height` | inches | — | Minimum height |
| `penwidth` | number | `1.0` | Border thickness |
| `tooltip` | string | — | Hover text (SVG output) |
| `URL` | URL | — | Clickable link (SVG output) |

### Node Shapes

**Basic shapes:**
```dot
digraph Shapes {
    a [shape=box, label="box"];
    b [shape=ellipse, label="ellipse"];
    c [shape=circle, label="circle"];
    d [shape=diamond, label="diamond"];
    e [shape=triangle, label="triangle"];
    f [shape=pentagon, label="pentagon"];
    g [shape=hexagon, label="hexagon"];
    h [shape=octagon, label="octagon"];
    i [shape=doublecircle, label="doublecircle"];
    j [shape=doubleoctagon, label="doubleoctagon"];
    k [shape=cylinder, label="cylinder"];
    l [shape=note, label="note"];
    m [shape=folder, label="folder"];
    n [shape=component, label="component"];
    o [shape=tab, label="tab"];
    p [shape=box3d, label="box3d"];
    q [shape=house, label="house"];
    r [shape=parallelogram, label="parallelogram"];
    s [shape=plain, label="plain (no border)"];
    t [shape=point]; // tiny dot
}
```

**Special shapes:**
- `record` / `Mrecord` — Structured fields (see [Record Shapes](#record-shapes))
- `plaintext` — Label only, no border
- `point` — Tiny dot (used for routing edges)

### Setting Default Node Attributes

```dot
digraph G {
    // All nodes default to filled boxes
    node [shape=box, style=filled, fillcolor="#E1F5FE", fontname="Arial"];

    A [label="Service A"];
    B [label="Service B"];
    C [label="Service C", fillcolor="#C8E6C9"]; // override for this node

    A -> B -> C;
}
```

---

## Edge Attributes

| Attribute | Values | Default | Description |
|-----------|--------|---------|-------------|
| `label` | string | — | Edge label |
| `color` | color | `black` | Edge color |
| `style` | `solid`, `dashed`, `dotted`, `bold`, `invis` | `solid` | Line style |
| `dir` | `forward`, `back`, `both`, `none` | `forward` | Arrow direction |
| `arrowhead` | See arrows below | `normal` | Head arrow shape |
| `arrowtail` | See arrows below | — | Tail arrow shape |
| `penwidth` | number | `1.0` | Line thickness |
| `weight` | number | `1` | Layout priority (higher = shorter/straighter) |
| `constraint` | `true`/`false` | `true` | Affects rank layout |
| `headlabel` | string | — | Label near arrowhead |
| `taillabel` | string | — | Label near tail |
| `fontname` | font name | — | Label font |
| `fontsize` | number | `14` | Label font size |
| `fontcolor` | color | `black` | Label color |

### Arrow Shapes

| Shape | Description |
|-------|-------------|
| `normal` | Standard filled arrow |
| `dot` | Filled circle |
| `odot` | Open circle |
| `diamond` | Filled diamond |
| `odiamond` | Open diamond |
| `box` | Filled square |
| `obox` | Open square |
| `vee` | Open V arrow |
| `inv` | Inverted arrow |
| `none` | No arrowhead |
| `crow` | Crow's foot |
| `tee` | Flat bar |

**Combine modifiers:** `arrowhead=odiamond` (hollow diamond for UML aggregation)

### Setting Default Edge Attributes

```dot
digraph G {
    edge [color="#666666", fontname="Arial", fontsize=10];

    A -> B [label="HTTP"];
    B -> C [label="gRPC"];
    C -> D [label="SQL", style=dashed];
}
```

---

## Graph Attributes

| Attribute | Values | Default | Description |
|-----------|--------|---------|-------------|
| `rankdir` | `TB`, `BT`, `LR`, `RL` | `TB` | Graph direction |
| `splines` | `true`, `ortho`, `polyline`, `curved`, `line`, `false` | `true` | Edge routing |
| `bgcolor` | color | `white` | Background color |
| `fontname` | font name | — | Default font |
| `fontsize` | number | — | Default font size |
| `label` | string | — | Graph title |
| `labelloc` | `t`, `b` | `b` | Title position |
| `nodesep` | inches | `0.25` | Horizontal spacing |
| `ranksep` | inches | `0.5` | Vertical spacing (rank gap) |
| `ratio` | `fill`, `compress`, `auto`, number | — | Aspect ratio |
| `size` | `"w,h"` | — | Maximum size in inches |
| `compound` | `true`/`false` | `false` | Allow edges between clusters |
| `concentrate` | `true`/`false` | `false` | Merge parallel edges |
| `overlap` | `true`, `false`, `scale`, `prism` | — | Node overlap handling |
| `pad` | inches | `0.0555` | Margin around graph |

### Rankdir Examples

```dot
// Left to Right
digraph G { rankdir=LR; A -> B -> C; }

// Bottom to Top
digraph G { rankdir=BT; A -> B -> C; }
```

### Spline Types

```dot
digraph G {
    splines=ortho;  // Right-angle edges (clean for architecture)
    // splines=polyline;  // Straight segments
    // splines=curved;    // Smooth curves
    // splines=line;      // Straight lines only
}
```

---

## Layout Engines

Graphviz provides multiple layout algorithms. Choose based on your graph structure.

| Engine | Best For | Algorithm | When to Use |
|--------|----------|-----------|-------------|
| `dot` | Hierarchies, trees, DAGs | Layered/Sugiyama | **Default** — directed acyclic graphs, org charts, dependency trees |
| `neato` | Undirected graphs | Spring model (Kamada-Kawai) | Network topology, peer relationships, small graphs |
| `fdp` | Large undirected graphs | Force-directed (Fruchterman-Reingold) | Large networks (100+ nodes), cluster visualization |
| `circo` | Circular layouts | Circular | Ring topology, protocol state machines, cyclic relationships |
| `twopi` | Radial hierarchies | Radial | Broadcast trees, influence maps, hub-spoke architectures |
| `sfdp` | Very large graphs | Scalable force-directed | Graphs with 1000+ nodes |
| `osage` | Array/grid layouts | Tree map | Regular grid arrangements |
| `patchwork` | Treemaps | Squarified treemap | Disk usage, proportional visualization |

### Setting the Engine

```dot
digraph G {
    layout=neato;  // or fdp, circo, twopi, sfdp

    A -- B;
    B -- C;
    C -- A;
}
```

**Note:** In Vista, the layout engine defaults to `dot`. Specify `layout=` explicitly for other engines.

---

## Subgraph Clusters

Clusters group nodes visually with a bounding box. The subgraph name **must** start with `cluster`.

```dot
digraph Architecture {
    rankdir=TB;

    subgraph cluster_frontend {
        label="Frontend";
        style=filled;
        color="#E3F2FD";
        fontname="Arial Bold";

        web [label="Web App", shape=box];
        mobile [label="Mobile App", shape=box];
    }

    subgraph cluster_backend {
        label="Backend Services";
        style=filled;
        color="#E8F5E9";

        api [label="API Gateway", shape=box];
        auth [label="Auth Service", shape=box];
        user [label="User Service", shape=box];
    }

    subgraph cluster_data {
        label="Data Layer";
        style=filled;
        color="#FFF3E0";

        db [label="PostgreSQL", shape=cylinder];
        cache [label="Redis", shape=cylinder];
    }

    web -> api;
    mobile -> api;
    api -> auth;
    api -> user;
    user -> db;
    auth -> cache;
}
```

### Nested Clusters

```dot
digraph G {
    subgraph cluster_outer {
        label="Production";

        subgraph cluster_app {
            label="Application";
            A; B;
        }

        subgraph cluster_db {
            label="Database";
            C; D;
        }
    }

    A -> C;
    B -> D;
}
```

### Edges Between Clusters

```dot
digraph G {
    compound=true;  // Required for cluster-to-cluster edges

    subgraph cluster_A {
        label="Group A";
        a1; a2;
    }

    subgraph cluster_B {
        label="Group B";
        b1; b2;
    }

    a1 -> b1 [lhead=cluster_B, ltail=cluster_A];
}
```

---

## Rank Constraints

Control vertical positioning of nodes within the `dot` layout.

```dot
digraph G {
    // Force nodes to same rank (horizontal alignment)
    { rank=same; B; C; D; }

    // Source rank (top)
    { rank=source; Start; }

    // Sink rank (bottom)
    { rank=sink; End; }

    // Min rank (as high as possible)
    { rank=min; Header; }

    // Max rank (as low as possible)
    { rank=max; Footer; }

    Start -> B;
    Start -> C;
    Start -> D;
    B -> End;
    C -> End;
    D -> End;
}
```

---

## HTML-Like Labels

For rich formatting inside nodes, use HTML-like labels enclosed in `< >`.

```dot
digraph G {
    node [shape=plaintext];

    service [label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
            <TR><TD BGCOLOR="#4A90D9" COLSPAN="2"><FONT COLOR="white"><B>User Service</B></FONT></TD></TR>
            <TR><TD ALIGN="LEFT">Port:</TD><TD ALIGN="LEFT">8080</TD></TR>
            <TR><TD ALIGN="LEFT">Language:</TD><TD ALIGN="LEFT">Go</TD></TR>
            <TR><TD ALIGN="LEFT">Status:</TD><TD ALIGN="LEFT"><FONT COLOR="green">Healthy</FONT></TD></TR>
        </TABLE>
    >];

    db [label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
            <TR><TD BGCOLOR="#E65100" COLSPAN="2"><FONT COLOR="white"><B>PostgreSQL</B></FONT></TD></TR>
            <TR><TD ALIGN="LEFT">Version:</TD><TD ALIGN="LEFT">15.4</TD></TR>
            <TR><TD ALIGN="LEFT">Size:</TD><TD ALIGN="LEFT">42 GB</TD></TR>
        </TABLE>
    >];

    service -> db [label="SQL/TCP"];
}
```

### HTML Label Tags

| Tag | Purpose |
|-----|---------|
| `<TABLE>` | Table container |
| `<TR>` | Table row |
| `<TD>` | Table cell |
| `<B>` | Bold |
| `<I>` | Italic |
| `<U>` | Underline |
| `<FONT>` | Font styling (`COLOR`, `FACE`, `POINT-SIZE`) |
| `<BR/>` | Line break |
| `<IMG>` | Image (SVG only) |

### TD Attributes

| Attribute | Values |
|-----------|--------|
| `BGCOLOR` | Color |
| `COLSPAN` | Number |
| `ROWSPAN` | Number |
| `ALIGN` | `LEFT`, `CENTER`, `RIGHT` |
| `VALIGN` | `TOP`, `MIDDLE`, `BOTTOM` |
| `PORT` | Port name (for edge targeting) |
| `BORDER` | Border width |

---

## Record Shapes

Record shapes create structured nodes with named fields (ports).

```dot
digraph G {
    node [shape=record];

    // Simple record
    struct1 [label="left|middle|right"];

    // Nested record
    struct2 [label="{header|{col1|col2|col3}|footer}"];

    // With ports (for precise edge targeting)
    struct3 [label="<f0> id: int|<f1> name: string|<f2> email: string"];

    // Rounded variant
    node [shape=Mrecord];
    struct4 [label="<f0> start|<f1> process|<f2> end"];

    struct3:f1 -> struct4:f0;
}
```

### Class-like Records

```dot
digraph G {
    node [shape=record, fontname="Courier"];

    User [label="{User|+ id: UUID\l+ email: String\l+ role: UserRole\l|+ authenticate(): bool\l+ updateProfile(): void\l}"];

    Order [label="{Order|+ id: UUID\l+ status: OrderStatus\l+ total: Money\l|+ addItem(): void\l+ submit(): void\l}"];

    User -> Order [label="places", arrowhead=vee];
}
```

> **Note:** `\l` = left-align, `\r` = right-align, `\n` = center. These control text alignment inside record fields.

---

## Styling Patterns

### Color Specifications

```dot
digraph G {
    // Named colors (X11 color names)
    A [color=red, fontcolor=blue];

    // Hex colors
    B [color="#4A90D9", fillcolor="#E1F5FE", style=filled];

    // RGB
    C [color="/blues9/3"];  // Color scheme

    // HSV
    D [color="0.5 0.5 1.0"];
}
```

### Consistent Architecture Style

```dot
digraph G {
    rankdir=TB;
    splines=ortho;
    nodesep=0.8;
    ranksep=1.0;

    // Style defaults
    node [shape=box, style="filled,rounded", fontname="Arial", fontsize=11, penwidth=1.5];
    edge [fontname="Arial", fontsize=9, color="#666666"];

    // Service nodes
    node [fillcolor="#E3F2FD", color="#1565C0"];
    api [label="API Gateway"];
    auth [label="Auth Service"];

    // Database nodes
    node [shape=cylinder, fillcolor="#FFF3E0", color="#E65100"];
    db [label="PostgreSQL"];
    cache [label="Redis"];

    // External nodes
    node [shape=box, fillcolor="#F3E5F5", color="#7B1FA2", style="filled,dashed"];
    stripe [label="Stripe"];

    api -> auth [label="gRPC"];
    auth -> db [label="SQL"];
    auth -> cache [label="Sessions"];
    api -> stripe [label="REST"];
}
```

---

## Vista Integration

### Rendering

Graphviz diagrams are rendered client-side using `@viz-js/viz`, a WebAssembly port of Graphviz (~2.5MB, lazy-loaded on first use).

The rendering pipeline:
1. Vista reads the `.dot` file content
2. Loads viz.js WASM module (cached after first load)
3. Renders to SVG in the browser
4. Displays in the architecture viewer

### Manifest Configuration

In `_arch.json`:

```json
{
    "diagrams": [
        {
            "id": "dependency-graph",
            "title": "Module Dependencies",
            "file": "dependencies.dot",
            "type": "graphviz",
            "diagramType": "custom"
        }
    ]
}
```

- **`type`**: Must be `"graphviz"`
- **`diagramType`**: Use `"custom"` for all Graphviz diagrams

### File Organization

```
docs/<feature>/arch/
├── _arch.json
├── overview.mmd           (Mermaid for simple diagrams)
├── dependencies.dot       (Graphviz for dependency graph)
├── network-topology.dot   (Graphviz for network layout)
└── README.md
```

### Best Practices

1. **Set `rankdir`** explicitly — Don't rely on the default `TB`
2. **Use `splines=ortho`** for architecture diagrams — Clean right-angle edges
3. **Use `splines=true`** for dependency graphs — Curved edges reduce visual clutter
4. **Always set `fontname`** — Default Times-Roman looks dated; use `"Arial"` or `"Helvetica"`
5. **Use clusters for grouping** — Name must start with `cluster_`
6. **Keep node count reasonable** — viz.js handles hundreds but rendering slows past ~200 nodes
7. **Use `concentrate=true`** for dense graphs — Merges parallel edges
8. **Specify `layout=`** when not using `dot` — Engine choice matters for readability

---

## Complete Examples

### Dependency Graph

```dot
digraph Dependencies {
    rankdir=LR;
    splines=true;
    node [shape=box, style="filled,rounded", fontname="Arial", fontsize=10, fillcolor="#E8EAF6", color="#3F51B5"];
    edge [color="#78909C", arrowsize=0.7];

    // Application layer
    subgraph cluster_app {
        label="Application";
        style=filled;
        color="#E3F2FD";
        app [label="app.ts"];
        router [label="router.ts"];
        middleware [label="middleware.ts"];
    }

    // Domain layer
    subgraph cluster_domain {
        label="Domain";
        style=filled;
        color="#E8F5E9";
        user_svc [label="user.service.ts"];
        order_svc [label="order.service.ts"];
        payment_svc [label="payment.service.ts"];
    }

    // Infrastructure layer
    subgraph cluster_infra {
        label="Infrastructure";
        style=filled;
        color="#FFF3E0";
        db [label="database.ts", shape=cylinder];
        cache [label="cache.ts", shape=cylinder];
        queue [label="queue.ts", shape=box3d];
    }

    app -> router;
    app -> middleware;
    router -> user_svc;
    router -> order_svc;
    middleware -> user_svc;
    order_svc -> payment_svc;
    user_svc -> db;
    user_svc -> cache;
    order_svc -> db;
    order_svc -> queue;
    payment_svc -> queue;
}
```

### Network Topology

```dot
graph NetworkTopology {
    layout=neato;
    overlap=false;
    splines=true;

    node [shape=box, style=filled, fontname="Arial", fontsize=10];
    edge [color="#78909C", len=2.0];

    // Core
    node [fillcolor="#FFCDD2", color="#C62828"];
    core1 [label="Core\nSwitch 1"];
    core2 [label="Core\nSwitch 2"];

    // Distribution
    node [fillcolor="#FFF9C4", color="#F57F17"];
    dist1 [label="Dist 1"];
    dist2 [label="Dist 2"];
    dist3 [label="Dist 3"];

    // Access
    node [fillcolor="#C8E6C9", color="#2E7D32"];
    acc1 [label="Floor 1"];
    acc2 [label="Floor 2"];
    acc3 [label="Floor 3"];
    acc4 [label="Floor 4"];
    acc5 [label="Floor 5"];
    acc6 [label="Floor 6"];

    // Redundant core link
    core1 -- core2 [style=bold, color="#C62828", penwidth=3];

    // Distribution links
    core1 -- dist1;
    core1 -- dist2;
    core2 -- dist2;
    core2 -- dist3;
    core1 -- dist3;
    core2 -- dist1;

    // Access links
    dist1 -- acc1;
    dist1 -- acc2;
    dist2 -- acc3;
    dist2 -- acc4;
    dist3 -- acc5;
    dist3 -- acc6;
}
```

### Tree with Record Shapes

```dot
digraph AST {
    rankdir=TB;
    node [shape=record, fontname="Courier", fontsize=10, style=filled, fillcolor="#FAFAFA"];
    edge [arrowsize=0.7];

    program [label="<f0> Program|<f1> body: [2 statements]", fillcolor="#E3F2FD"];

    vardecl [label="<f0> VariableDeclaration|<f1> kind: const|<f2> id: greeting|<f3> init: StringLiteral"];
    strlit [label="<f0> StringLiteral|<f1> value: \"hello\"", fillcolor="#E8F5E9"];

    exprstmt [label="<f0> ExpressionStatement|<f1> expression: CallExpression"];
    call [label="<f0> CallExpression|<f1> callee: console.log|<f2> args: [1]"];
    ident [label="<f0> Identifier|<f1> name: greeting", fillcolor="#FFF3E0"];

    program:f1 -> vardecl:f0;
    program:f1 -> exprstmt:f0;
    vardecl:f3 -> strlit:f0;
    exprstmt:f1 -> call:f0;
    call:f2 -> ident:f0;
}
```

---

*This reference is part of the docs-with-mermaid Vista skill. For Mermaid diagrams, see [mermaid-reference.md](mermaid-reference.md). For PlantUML, see [plantuml-format.md](plantuml-format.md).*
