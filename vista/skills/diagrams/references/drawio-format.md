# Draw.io Format Reference

> Reference for working with Draw.io (diagrams.net) files in Vista.
> Draw.io is **import-only** — do not generate `.drawio` files programmatically. Create them using the Draw.io editor, then import into Vista.

## Table of Contents

- [File Format](#file-format)
- [When to Use Draw.io](#when-to-use-drawio)
- [XML Structure](#xml-structure)
- [Cell Types](#cell-types)
- [Style String API](#style-string-api)
- [Geometry and Positioning](#geometry-and-positioning)
- [Shape Libraries](#shape-libraries)
- [Multi-Page Support](#multi-page-support)
- [Layers](#layers)
- [Compressed vs Uncompressed](#compressed-vs-uncompressed)
- [Vista Integration](#vista-integration)
- [Working with Draw.io Files](#working-with-drawio-files)

---

## File Format

- **Extension:** `.drawio` (or `.drawio.xml`, `.dio`)
- **Format:** XML-based
- **Encoding:** UTF-8
- **Editor:** [diagrams.net](https://app.diagrams.net) (web) or Draw.io VS Code extension
- **Note:** `.drawio` files can also be saved as `.drawio.png` or `.drawio.svg` with embedded XML

---

## When to Use Draw.io

| Scenario | Use Draw.io | Use Code-Based |
|----------|-------------|----------------|
| Existing `.drawio` files | Yes — import directly | No |
| Complex visual diagrams with precise positioning | Yes — manual layout is better | No |
| AWS/Azure/GCP architecture with official icons | Yes — extensive shape libraries | Limited |
| Quick iteration with visual feedback | Yes — WYSIWYG editor | No |
| Version-controlled documentation | No — XML diffs are hard to review | Yes (Mermaid, D2) |
| Auto-generated diagrams | No — XML is fragile to generate | Yes (any code format) |
| CI/CD diagram generation | No — requires editor | Yes (Mermaid, PlantUML) |

**Rule of thumb:** Use Draw.io only for importing existing diagrams or when you need the visual editor's precise layout control with cloud provider shape libraries. Never generate `.drawio` XML programmatically — it's too complex and fragile.

---

## XML Structure

A `.drawio` file follows this hierarchy:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" type="device">
    <diagram id="unique-id" name="Page-1">
        <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10"
                       guides="1" tooltips="1" connect="1"
                       arrows="1" fold="1" page="1"
                       pageScale="1" pageWidth="1169" pageHeight="827">
            <root>
                <!-- Layer 0 (default) — always present -->
                <mxCell id="0"/>
                <!-- Layer 1 (default drawing layer) — always present -->
                <mxCell id="1" parent="0"/>

                <!-- Your shapes and connections go here -->
                <mxCell id="2" value="Web App"
                        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
                        vertex="1" parent="1">
                    <mxGeometry x="120" y="80" width="120" height="60" as="geometry"/>
                </mxCell>
            </root>
        </mxGraphModel>
    </diagram>
</mxfile>
```

### Key Elements

| Element | Purpose |
|---------|---------|
| `<mxfile>` | Root element, contains metadata |
| `<diagram>` | One per page/tab |
| `<mxGraphModel>` | Graph configuration (canvas settings) |
| `<root>` | Container for all cells |
| `<mxCell>` | Every shape, connection, or layer |
| `<mxGeometry>` | Position and size of a cell |

### mxGraphModel Attributes

| Attribute | Description | Default |
|-----------|-------------|---------|
| `dx` | Horizontal offset | — |
| `dy` | Vertical offset | — |
| `grid` | Show grid (0/1) | `1` |
| `gridSize` | Grid spacing in px | `10` |
| `guides` | Snap guides (0/1) | `1` |
| `tooltips` | Show tooltips (0/1) | `1` |
| `connect` | Allow connections (0/1) | `1` |
| `arrows` | Show arrows (0/1) | `1` |
| `fold` | Allow folding (0/1) | `1` |
| `page` | Show page boundary (0/1) | `1` |
| `pageScale` | Page zoom | `1` |
| `pageWidth` | Page width in px | `1169` (A4 landscape) |
| `pageHeight` | Page height in px | `827` |
| `math` | Enable LaTeX math (0/1) | `0` |
| `shadow` | Global shadow (0/1) | `0` |

---

## Cell Types

Every element in Draw.io is an `<mxCell>`. The cell type is determined by attributes:

### Vertex (Shape)

```xml
<mxCell id="2" value="My Shape"
        style="rounded=1;whiteSpace=wrap;html=1;"
        vertex="1" parent="1">
    <mxGeometry x="100" y="50" width="120" height="60" as="geometry"/>
</mxCell>
```

Key attributes:
- `vertex="1"` — Makes this a shape
- `value` — The label text (supports HTML when `html=1` in style)
- `style` — Visual appearance (see Style String API)
- `parent` — Parent cell ID (`"1"` = default layer)

### Edge (Connection)

```xml
<mxCell id="3" value="HTTP"
        style="endArrow=classic;html=1;"
        edge="1" parent="1"
        source="2" target="4">
    <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

Key attributes:
- `edge="1"` — Makes this a connection
- `source` — Source cell ID
- `target` — Target cell ID
- `value` — Edge label

### Group (Container)

```xml
<!-- Group container -->
<mxCell id="5" value="Backend"
        style="group;rounded=1;fillColor=#f5f5f5;"
        vertex="1" connectable="0" parent="1">
    <mxGeometry x="50" y="50" width="300" height="200" as="geometry"/>
</mxCell>

<!-- Child shapes with parent pointing to group -->
<mxCell id="6" value="API" style="..." vertex="1" parent="5">
    <mxGeometry x="20" y="40" width="100" height="40" as="geometry"/>
</mxCell>
```

---

## Style String API

Styles are semicolon-separated key=value pairs. This is the core of Draw.io's visual system.

### Common Style Properties

| Property | Values | Description |
|----------|--------|-------------|
| `rounded` | `0`/`1` | Rounded corners |
| `whiteSpace` | `wrap` | Enable text wrapping |
| `html` | `0`/`1` | Enable HTML labels |
| `fillColor` | `#hex` / `none` | Background color |
| `strokeColor` | `#hex` / `none` | Border color |
| `fontColor` | `#hex` | Text color |
| `fontSize` | number | Font size (pt) |
| `fontFamily` | name | Font family |
| `fontStyle` | bitmask | 1=bold, 2=italic, 4=underline (combine: 3=bold+italic) |
| `align` | `left`/`center`/`right` | Horizontal text alignment |
| `verticalAlign` | `top`/`middle`/`bottom` | Vertical text alignment |
| `opacity` | 0-100 | Opacity percentage |
| `shadow` | `0`/`1` | Drop shadow |
| `dashed` | `0`/`1` | Dashed border |
| `dashPattern` | pattern | Dash pattern (e.g., `8 8`) |
| `strokeWidth` | number | Border width (px) |
| `arcSize` | number | Corner radius (when rounded=1) |
| `spacing` | number | Padding (all sides) |
| `spacingTop` | number | Top padding |
| `spacingBottom` | number | Bottom padding |
| `spacingLeft` | number | Left padding |
| `spacingRight` | number | Right padding |
| `aspect` | `fixed` | Maintain aspect ratio |
| `resizable` | `0`/`1` | Allow resizing |
| `movable` | `0`/`1` | Allow moving |
| `rotatable` | `0`/`1` | Allow rotation |
| `rotation` | degrees | Rotation angle |

### Shape-Specific Styles

| Style Prefix | Description |
|-------------|-------------|
| `shape=mxgraph.aws4.` | AWS architecture icons |
| `shape=mxgraph.azure.` | Azure architecture icons |
| `shape=mxgraph.gcp2.` | Google Cloud icons |
| `shape=mxgraph.kubernetes.` | Kubernetes icons |
| `shape=mxgraph.docker.` | Docker icons |
| `shape=cylinder3` | Database cylinder |
| `shape=hexagon` | Hexagon |
| `shape=process` | Process (double vertical lines) |
| `shape=parallelogram` | Parallelogram |
| `shape=cloud` | Cloud shape |
| `shape=actor` | UML actor (stick figure) |
| `shape=umlLifeline` | UML sequence lifeline |
| `shape=folder` | Folder tab |
| `shape=note` | Note shape |
| `shape=document` | Document (wavy bottom) |
| `shape=callout` | Speech callout |

### Edge Style Properties

| Property | Values | Description |
|----------|--------|-------------|
| `endArrow` | `classic`/`block`/`open`/`oval`/`diamond`/`none` | Arrowhead type |
| `startArrow` | Same as endArrow | Tail arrow |
| `endFill` | `0`/`1` | Filled arrowhead |
| `startFill` | `0`/`1` | Filled tail arrow |
| `edgeStyle` | See below | Edge routing |
| `curved` | `0`/`1` | Curved edges |
| `jettySize` | `auto`/number | Stub length |
| `orthogonalLoop` | `0`/`1` | Perpendicular loops |
| `exitX`/`exitY` | 0-1 | Source anchor point |
| `entryX`/`entryY` | 0-1 | Target anchor point |

### Edge Styles (Routing)

| `edgeStyle` Value | Description |
|-------------------|-------------|
| `orthogonalEdgeStyle` | Right-angle routing |
| `elbowEdgeStyle` | Single elbow |
| `entityRelationEdgeStyle` | ER-style routing |
| `isometricEdgeStyle` | Isometric 3D routing |
| `segmentEdgeStyle` | Manual segment routing |
| `straightEdgeStyle` | Straight line |
| (none / default) | Smart routing |

### Example Style Strings

```
# Blue rounded rectangle
rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;

# Red dashed border, no fill
fillColor=none;strokeColor=#b85450;dashed=1;strokeWidth=2;

# Database cylinder
shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#fff2cc;strokeColor=#d6b656;

# AWS EC2 instance
shape=mxgraph.aws4.ec2_instance;fillColor=#ED7100;fontColor=#ffffff;

# Bold text, centered
fontStyle=1;fontSize=14;align=center;verticalAlign=middle;
```

---

## Geometry and Positioning

### mxGeometry for Vertices

```xml
<mxGeometry x="100" y="50" width="120" height="60" as="geometry"/>
```

| Attribute | Description |
|-----------|-------------|
| `x` | Left edge position (px from parent origin) |
| `y` | Top edge position (px from parent origin) |
| `width` | Width in pixels |
| `height` | Height in pixels |

### mxGeometry for Edges

```xml
<mxGeometry relative="1" as="geometry">
    <!-- Optional: waypoints for edge routing -->
    <Array as="points">
        <mxPoint x="200" y="150"/>
        <mxPoint x="300" y="150"/>
    </Array>
    <!-- Optional: label offset -->
    <mxPoint x="-20" y="-10" as="offset"/>
</mxGeometry>
```

---

## Shape Libraries

Draw.io includes extensive shape libraries for cloud providers and technologies.

### AWS Architecture

```
shape=mxgraph.aws4.ec2_instance      # EC2
shape=mxgraph.aws4.lambda_function   # Lambda
shape=mxgraph.aws4.s3               # S3
shape=mxgraph.aws4.rds              # RDS
shape=mxgraph.aws4.dynamodb         # DynamoDB
shape=mxgraph.aws4.sqs             # SQS
shape=mxgraph.aws4.sns             # SNS
shape=mxgraph.aws4.api_gateway     # API Gateway
shape=mxgraph.aws4.cloudfront      # CloudFront
shape=mxgraph.aws4.vpc            # VPC
shape=mxgraph.aws4.elb            # ELB/ALB
shape=mxgraph.aws4.ecs            # ECS
shape=mxgraph.aws4.eks            # EKS
shape=mxgraph.aws4.fargate        # Fargate
shape=mxgraph.aws4.cognito        # Cognito
shape=mxgraph.aws4.route_53       # Route 53
```

### Azure Architecture

```
shape=mxgraph.azure.virtual_machine    # VM
shape=mxgraph.azure.app_services       # App Service
shape=mxgraph.azure.azure_functions    # Functions
shape=mxgraph.azure.sql_database       # SQL Database
shape=mxgraph.azure.cosmos_db          # Cosmos DB
shape=mxgraph.azure.storage_blob       # Blob Storage
shape=mxgraph.azure.aks               # AKS
shape=mxgraph.azure.api_management    # API Management
shape=mxgraph.azure.service_bus       # Service Bus
shape=mxgraph.azure.front_door        # Front Door
shape=mxgraph.azure.key_vault         # Key Vault
```

### Google Cloud

```
shape=mxgraph.gcp2.compute_engine     # Compute Engine
shape=mxgraph.gcp2.cloud_functions    # Cloud Functions
shape=mxgraph.gcp2.cloud_run          # Cloud Run
shape=mxgraph.gcp2.cloud_sql          # Cloud SQL
shape=mxgraph.gcp2.cloud_storage      # Cloud Storage
shape=mxgraph.gcp2.bigquery           # BigQuery
shape=mxgraph.gcp2.pub_sub            # Pub/Sub
shape=mxgraph.gcp2.gke               # GKE
shape=mxgraph.gcp2.cloud_cdn         # Cloud CDN
```

### Kubernetes

```
shape=mxgraph.kubernetes.pod          # Pod
shape=mxgraph.kubernetes.deploy       # Deployment
shape=mxgraph.kubernetes.svc          # Service
shape=mxgraph.kubernetes.ing          # Ingress
shape=mxgraph.kubernetes.ns           # Namespace
shape=mxgraph.kubernetes.node         # Node
shape=mxgraph.kubernetes.pv           # Persistent Volume
shape=mxgraph.kubernetes.cm           # ConfigMap
shape=mxgraph.kubernetes.secret       # Secret
shape=mxgraph.kubernetes.cronjob      # CronJob
```

---

## Multi-Page Support

Draw.io files can contain multiple pages (tabs), each as a separate `<diagram>` element:

```xml
<mxfile>
    <diagram id="page1-id" name="Overview">
        <mxGraphModel>
            <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <!-- Page 1 content -->
            </root>
        </mxGraphModel>
    </diagram>
    <diagram id="page2-id" name="Details">
        <mxGraphModel>
            <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <!-- Page 2 content -->
            </root>
        </mxGraphModel>
    </diagram>
</mxfile>
```

Vista renders the first page by default. Multi-page navigation is supported in the viewer.

---

## Layers

Layers allow organizing content at different visual levels (like Photoshop layers).

```xml
<root>
    <!-- Root layer (always present) -->
    <mxCell id="0"/>

    <!-- Default layer -->
    <mxCell id="1" value="Default" parent="0"/>

    <!-- Additional layer -->
    <mxCell id="100" value="Annotations" parent="0" visible="1"/>

    <!-- Shape on default layer -->
    <mxCell id="2" value="Server" style="..." vertex="1" parent="1"/>

    <!-- Shape on annotations layer -->
    <mxCell id="3" value="Note" style="..." vertex="1" parent="100"/>
</root>
```

Layers are controlled by setting a cell's `parent` to the layer's cell ID.

---

## Compressed vs Uncompressed

Draw.io can save in two XML formats:

### Uncompressed (Human-Readable)

The `<mxGraphModel>` is stored as plain XML inside `<diagram>`:

```xml
<diagram id="..." name="Page-1">
    <mxGraphModel ...>
        <root>
            <mxCell id="0"/>
            ...
        </root>
    </mxGraphModel>
</diagram>
```

### Compressed (Default)

The content is deflate-compressed and base64-encoded:

```xml
<diagram id="..." name="Page-1">
    7V1Zc6M4EP41VO0+OIUQl... (base64 string)
</diagram>
```

**For version control:** Use Edit > Settings > Uncompressed XML in Draw.io to save human-readable XML. This makes diffs reviewable.

---

## Vista Integration

### Rendering

Draw.io files are rendered in Vista using an iframe pointing to the diagrams.net viewer.

The rendering pipeline:
1. Vista reads the `.drawio` file content
2. Base64-encodes the full XML content
3. Constructs a viewer URL: `https://viewer.diagrams.net/?...`
4. Loads the viewer in an iframe
5. The viewer renders the diagram client-side

### Manifest Configuration

In `_arch.json`:

```json
{
    "diagrams": [
        {
            "id": "aws-architecture",
            "title": "AWS Production Architecture",
            "file": "aws-architecture.drawio",
            "type": "drawio",
            "diagramType": "custom"
        }
    ]
}
```

- **`type`**: Must be `"drawio"`
- **`diagramType`**: Use `"custom"` for all Draw.io diagrams

### File Organization

```
.vista/features/<feature>/arch/
├── _arch.json
├── overview.mmd                (Mermaid for code-gen diagrams)
├── aws-architecture.drawio     (Draw.io for visual diagrams)
└── README.md
```

### Best Practices

1. **Never generate `.drawio` XML programmatically** — Use the visual editor
2. **Save as uncompressed XML** for version control (Edit > Settings)
3. **Use one page per concern** — Separate overview, details, and network diagrams
4. **Enable "Extras > Edit Diagram"** to fine-tune XML when needed
5. **Export to PNG/SVG** for documentation that doesn't support iframe embedding
6. **Use cloud shape libraries** — AWS, Azure, GCP icons are built-in
7. **Keep file sizes reasonable** — Large files (>1MB) slow iframe loading
8. **Use layers** for complex diagrams — Toggle visibility for different audiences

---

## Working with Draw.io Files

### Creating New Diagrams

1. Open [app.diagrams.net](https://app.diagrams.net)
2. Choose "Device" storage for local files
3. Create your diagram using the visual editor
4. Save as `.drawio` in your feature's `arch/` directory
5. Update `_arch.json` manifest

### Editing Existing Diagrams

- **VS Code:** Install the "Draw.io Integration" extension — opens `.drawio` files in the visual editor
- **Web:** Open [app.diagrams.net](https://app.diagrams.net) and load the file
- **CLI:** Draw.io Desktop app available for all platforms

### Converting to Other Formats

Draw.io can export to:
- **PNG** — File > Export As > PNG
- **SVG** — File > Export As > SVG
- **PDF** — File > Export As > PDF
- **HTML** — File > Export As > HTML (self-contained viewer)

For programmatic conversion, use the Draw.io CLI:
```bash
# Export to PNG
drawio --export --format png --output diagram.png diagram.drawio

# Export to SVG
drawio --export --format svg --output diagram.svg diagram.drawio
```

### Annotated XML Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- Root container with editor metadata -->
<mxfile host="app.diagrams.net" type="device" version="24.0.0">

    <!-- First page/tab -->
    <diagram id="abc123" name="Architecture Overview">
        <!-- Canvas settings -->
        <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10"
                       guides="1" tooltips="1" connect="1"
                       arrows="1" fold="1" page="1"
                       pageScale="1" pageWidth="1169" pageHeight="827">
            <root>
                <!-- Required: root layer -->
                <mxCell id="0"/>
                <!-- Required: default drawing layer -->
                <mxCell id="1" parent="0"/>

                <!-- Blue rounded rectangle: "Web App" -->
                <mxCell id="web" value="Web App"
                        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;"
                        vertex="1" parent="1">
                    <mxGeometry x="120" y="80" width="120" height="60" as="geometry"/>
                </mxCell>

                <!-- Database cylinder: "PostgreSQL" -->
                <mxCell id="db" value="PostgreSQL"
                        style="shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#fff2cc;strokeColor=#d6b656;"
                        vertex="1" parent="1">
                    <mxGeometry x="120" y="240" width="120" height="80" as="geometry"/>
                </mxCell>

                <!-- Arrow connecting web to db -->
                <mxCell id="conn1" value="SQL"
                        style="endArrow=classic;html=1;strokeColor=#666666;fontSize=10;"
                        edge="1" parent="1" source="web" target="db">
                    <mxGeometry relative="1" as="geometry"/>
                </mxCell>
            </root>
        </mxGraphModel>
    </diagram>
</mxfile>
```

---

*This reference is part of the docs-with-mermaid Vista skill. For code-based diagram formats, see [mermaid-reference.md](mermaid-reference.md), [plantuml-format.md](plantuml-format.md), [graphviz-format.md](graphviz-format.md), or [d2-format.md](d2-format.md).*
