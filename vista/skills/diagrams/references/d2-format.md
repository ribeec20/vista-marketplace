# D2 Format Reference

> Complete reference for creating D2 diagrams in Vista.
> Use D2 when the project already uses it or when you prefer its clean declarative syntax for architecture diagrams.

## Table of Contents

- [File Format](#file-format)
- [When to Choose D2](#when-to-choose-d2)
- [Basic Syntax](#basic-syntax)
- [Connections](#connections)
- [Shapes](#shapes)
- [Containers](#containers)
- [Labels and Text](#labels-and-text)
- [Styling](#styling)
- [Special Objects](#special-objects)
- [Imports and Composition](#imports-and-composition)
- [Layout Engines](#layout-engines)
- [Vista Integration](#vista-integration)
- [Complete Examples](#complete-examples)

---

## File Format

- **Extension:** `.d2`
- **Wrapper:** None needed — D2 files have no start/end markers
- **Comments:** `#` for single line
- **Encoding:** UTF-8
- **Semicolons:** Not needed — newline-separated

```d2
# This is a comment
server -> database: queries
database -> cache: populates
```

---

## When to Choose D2

| Feature | D2 | Mermaid | Recommendation |
|---------|-----|---------|----------------|
| Declarative syntax | Clean, minimal | Keyword-heavy | **D2** for readability |
| Container nesting | Native, unlimited depth | Subgraphs (1-2 levels) | **D2** for deep nesting |
| SQL table shapes | Built-in | Not available | **D2** |
| Class shapes | Built-in | Class diagram only | **D2** for mixed diagrams |
| Icons | Native support | Not supported | **D2** |
| Tooltips/links | Native | Limited | **D2** |
| Browser rendering | Requires Kroki | Native JS | **Mermaid** |
| Platform support | Limited | GitHub, GitLab, etc. | **Mermaid** |
| Ecosystem maturity | Newer | Established | **Mermaid** |

**Rule of thumb:** Use D2 when the project already uses it, or when you need deep container nesting and clean declarative syntax. Default to Mermaid otherwise.

---

## Basic Syntax

### Shapes (Nodes)

```d2
# Implicit creation — just use the name
server
database
cache

# With labels
server: Application Server
database: PostgreSQL 15
cache: Redis Cache
```

### Connections

```d2
# Basic connection
server -> database

# With label
server -> database: SQL queries

# Reverse direction
database <- server: SQL queries

# Bidirectional
server <-> cache: read/write

# Connection chain
client -> server -> database -> cache
```

### Multiple Connections

```d2
server -> database: reads
server -> database: writes
# D2 renders both edges (no dedup)

# Self-referencing
server -> server: health check
```

---

## Connections

### Arrow Types

```d2
# Standard arrow
a -> b: default

# No arrowhead
a -- b: line only

# Both directions
a <-> b: bidirectional
```

### Connection Labels

```d2
a -> b: This is the label
a -> b: {
    style.stroke: red
    style.font-color: red
}
```

### Multi-step Connections

```d2
# Chain syntax
a -> b -> c -> d

# Multiple from same source
a -> b
a -> c
a -> d
```

---

## Shapes

D2 supports a rich set of built-in shapes.

### Shape Types

```d2
# Rectangle (default)
service: My Service
service.shape: rectangle

# Common shapes
cloud: AWS Cloud {shape: cloud}
db: PostgreSQL {shape: cylinder}
queue: Kafka {shape: queue}
person: User {shape: person}
pkg: Module {shape: package}
page: Document {shape: page}
oval: Process {shape: oval}
circle: Node {shape: circle}
diamond: Decision {shape: diamond}
hexagon: Worker {shape: hexagon}
parallelogram: IO {shape: parallelogram}
stored_data: Cache {shape: stored_data}
step: Step 1 {shape: step}
callout: Note {shape: callout}
document: Doc {shape: document}
square: Block {shape: square}
```

### Shape Reference Table

| Shape | Use For |
|-------|---------|
| `rectangle` | Services, apps, default |
| `square` | Equal-dimension blocks |
| `circle` | Network nodes, endpoints |
| `oval` | Processes |
| `diamond` | Decisions, conditions |
| `cylinder` | Databases, storage |
| `queue` | Message queues, buffers |
| `package` | Modules, packages |
| `cloud` | Cloud providers, external |
| `person` | Users, actors |
| `page` | Documents, web pages |
| `document` | Documents (curled bottom) |
| `parallelogram` | Input/output |
| `hexagon` | Workers, processing |
| `step` | Sequential steps |
| `callout` | Annotations, notes |
| `stored_data` | Data stores, caches |

---

## Containers

D2's killer feature is natural container nesting. Any shape can be a container.

### Basic Nesting

```d2
# Automatic container — just nest inside
backend: Backend {
    api: API Gateway
    auth: Auth Service
    user: User Service

    api -> auth: validates
    api -> user: forwards
}

frontend: Frontend {
    web: Web App
    mobile: Mobile App
}

frontend.web -> backend.api: HTTPS
frontend.mobile -> backend.api: HTTPS
```

### Deep Nesting

```d2
aws: AWS {
    vpc: VPC {
        public: Public Subnet {
            alb: ALB
            nat: NAT Gateway
        }
        private: Private Subnet {
            ecs: ECS Cluster {
                service_a: Service A
                service_b: Service B
            }
            rds: RDS PostgreSQL
        }
    }
    s3: S3 Bucket
    cf: CloudFront
}

aws.cf -> aws.vpc.public.alb: HTTPS
aws.vpc.public.alb -> aws.vpc.private.ecs.service_a: HTTP
aws.vpc.private.ecs.service_a -> aws.vpc.private.rds: SQL
aws.vpc.private.ecs.service_a -> aws.s3: S3 API
```

### Container Styling

```d2
backend: Backend {
    style.fill: "#E8F5E9"
    style.stroke: "#2E7D32"
    style.border-radius: 8

    api: API Gateway
    db: Database {
        style.fill: "#FFF3E0"
    }
}
```

---

## Labels and Text

### Multi-line Labels

```d2
server: |md
    # Application Server
    - Port: 8080
    - Runtime: Node.js 20
    - Status: **Healthy**
|
```

### Icons

```d2
# URL-based icons
server: Application Server {
    icon: https://icons.terrastruct.com/essentials/004-server.svg
}

# Shape + icon
database: PostgreSQL {
    shape: cylinder
    icon: https://icons.terrastruct.com/dev/postgresql.svg
}
```

### Tooltips and Links

```d2
server: Application Server {
    tooltip: Handles API requests on port 8080
    link: https://docs.example.com/server
}
```

---

## Styling

### Element Styling

```d2
server: Application Server {
    style.fill: "#E3F2FD"
    style.stroke: "#1565C0"
    style.stroke-width: 2
    style.font-color: "#0D47A1"
    style.border-radius: 8
    style.shadow: true
    style.opacity: 0.9
    style.font-size: 14
    style.bold: true
    style.italic: false
}
```

### Connection Styling

```d2
a -> b: {
    style.stroke: "#E65100"
    style.stroke-width: 2
    style.stroke-dash: 5
    style.font-color: "#E65100"
    style.animated: true
}
```

### Style Reference

| Property | Values | Applies To |
|----------|--------|-----------|
| `style.fill` | Color hex/name | Shapes |
| `style.stroke` | Color hex/name | Shapes, connections |
| `style.stroke-width` | Number (px) | Shapes, connections |
| `style.stroke-dash` | Number | Shapes, connections |
| `style.font-color` | Color hex/name | All |
| `style.font-size` | Number | All |
| `style.bold` | `true`/`false` | Text |
| `style.italic` | `true`/`false` | Text |
| `style.border-radius` | Number (px) | Rectangles |
| `style.shadow` | `true`/`false` | Shapes |
| `style.opacity` | 0.0 - 1.0 | All |
| `style.animated` | `true`/`false` | Connections |
| `style.filled` | `true`/`false` | Shapes |
| `style.3d` | `true`/`false` | Rectangles |
| `style.multiple` | `true`/`false` | Shapes (stacked look) |
| `style.double-border` | `true`/`false` | Shapes |

---

## Special Objects

### SQL Tables

```d2
users: {
    shape: sql_table
    id: int {constraint: primary_key}
    email: varchar(255) {constraint: unique}
    password_hash: varchar(255)
    role: enum
    created_at: timestamp
    updated_at: timestamp
}

posts: {
    shape: sql_table
    id: int {constraint: primary_key}
    author_id: int {constraint: foreign_key}
    title: varchar(255)
    content: text
    status: enum
    published_at: timestamp
}

comments: {
    shape: sql_table
    id: int {constraint: primary_key}
    post_id: int {constraint: foreign_key}
    author_id: int {constraint: foreign_key}
    body: text
    created_at: timestamp
}

users.id <-> posts.author_id
users.id <-> comments.author_id
posts.id <-> comments.post_id
```

### Class Shapes

```d2
User: {
    shape: class

    # Fields
    -id: UUID
    -email: String
    -passwordHash: String
    +role: UserRole

    # Methods
    +authenticate(password String): bool
    +changePassword(old String, new String): void
    #hashPassword(plain String): String
}

Order: {
    shape: class

    -id: UUID
    -status: OrderStatus
    -items: List<OrderItem>

    +addItem(product Product, qty int): void
    +calculateTotal(): Money
    +submit(): void
}

User -> Order: places
```

### Sequence Diagrams

```d2
shape: sequence_diagram

client: Client
server: Server
db: Database

client -> server: HTTP Request
server -> db: SQL Query
db -> server: Result Set
server -> client: JSON Response

# Groups
client -> server: POST /login {
    server -> db: SELECT user
    db -> server: user row
    server -> server: validate password
    server -> client: JWT token
}
```

---

## Imports and Composition

### File Imports

```d2
# Import another D2 file
...@./shared/styles.d2

# Import specific element
backend: {
    ...@./components/backend.d2
}
```

### Themes

D2 supports built-in themes:
- `0` — Default
- `1` — Neutral Grey
- `3` — Flagship Terrastruct
- `4` — Cool Classics
- `5` — Mixed Berry Blue
- `6` — Grape Soda
- `8` — Aubergine
- `100` — Colorblind Clear
- `200` — Dark Mauve (dark mode)
- `201` — Dark Flagship Terrastruct (dark mode)

Set via CLI: `d2 --theme 3 input.d2 output.svg`

---

## Layout Engines

| Engine | Best For | Notes |
|--------|----------|-------|
| `dagre` | General purpose, hierarchical | **Default** — good for most diagrams |
| `elk` | Large graphs, complex layouts | Better edge routing for 50+ nodes |

Set via CLI: `d2 --layout elk input.d2 output.svg`

---

## Vista Integration

### Rendering

D2 diagrams in Vista are displayed as raw source code by default. For rendered output, Vista can optionally use Kroki (a diagram rendering service).

The rendering pipeline:
1. Vista reads the `.d2` file content
2. If Kroki is configured: sends source to Kroki server, receives SVG
3. If Kroki is not configured: displays syntax-highlighted source

### Manifest Configuration

In `_arch.json`:

```json
{
    "diagrams": [
        {
            "id": "architecture-overview",
            "title": "System Architecture",
            "file": "architecture.d2",
            "type": "d2",
            "diagramType": "custom"
        }
    ]
}
```

- **`type`**: Must be `"d2"`
- **`diagramType`**: Use `"custom"` for all D2 diagrams

### File Organization

```
docs/<feature>/arch/
├── _arch.json
├── overview.mmd          (Mermaid for simple diagrams)
├── architecture.d2       (D2 for architecture overview)
├── sql-schema.d2         (D2 for SQL table visualization)
└── README.md
```

### Best Practices

1. **Use D2 for container-heavy architectures** — Deep nesting is D2's strength
2. **Use `sql_table` for schema diagrams** — Cleaner than Mermaid ER for DB documentation
3. **Keep consistent styling** — Extract shared styles to an imported file
4. **Use markdown labels** for rich text content
5. **Leverage icons** for instantly recognizable service types
6. **Test locally** — D2 CLI renders faster than Kroki round-trips

---

## Complete Examples

### Architecture Overview

```d2
direction: right

frontend: Frontend {
    style.fill: "#E3F2FD"

    web: Web App {
        shape: page
        tooltip: React SPA on port 3000
    }
    mobile: Mobile App {
        shape: package
    }
}

backend: Backend {
    style.fill: "#E8F5E9"

    gateway: API Gateway {
        tooltip: Kong on port 8000
    }

    services: Microservices {
        auth: Auth Service
        users: User Service
        orders: Order Service
        payments: Payment Service
    }

    gateway -> services.auth: validate
    gateway -> services.users: forward
    gateway -> services.orders: forward
    services.orders -> services.payments: process
}

data: Data Layer {
    style.fill: "#FFF3E0"

    pg: PostgreSQL {shape: cylinder}
    redis: Redis {shape: cylinder}
    kafka: Kafka {shape: queue}
}

external: External {
    style.fill: "#F3E5F5"
    style.stroke-dash: 5

    stripe: Stripe {shape: cloud}
    sendgrid: SendGrid {shape: cloud}
}

frontend.web -> backend.gateway: HTTPS
frontend.mobile -> backend.gateway: HTTPS

backend.services.users -> data.pg: SQL
backend.services.orders -> data.pg: SQL
backend.services.auth -> data.redis: sessions
backend.services.orders -> data.kafka: events
backend.services.payments -> external.stripe: API
data.kafka -> external.sendgrid: notifications
```

### SQL Tables

```d2
users: {
    shape: sql_table
    id: int {constraint: primary_key}
    email: varchar(255) {constraint: unique}
    name: varchar(100)
    role: enum('admin','user','guest')
    created_at: timestamp
}

teams: {
    shape: sql_table
    id: int {constraint: primary_key}
    name: varchar(100)
    slug: varchar(50) {constraint: unique}
    owner_id: int {constraint: foreign_key}
}

team_members: {
    shape: sql_table
    id: int {constraint: primary_key}
    team_id: int {constraint: foreign_key}
    user_id: int {constraint: foreign_key}
    role: enum('owner','admin','member')
    joined_at: timestamp
}

projects: {
    shape: sql_table
    id: int {constraint: primary_key}
    team_id: int {constraint: foreign_key}
    name: varchar(100)
    description: text
    status: enum('active','archived')
}

users.id <-> teams.owner_id
users.id <-> team_members.user_id
teams.id <-> team_members.team_id
teams.id <-> projects.team_id
```

### Class Diagram

```d2
EventEmitter: {
    shape: class

    +on(event string, handler Handler): void
    +off(event string, handler Handler): void
    +emit(event string, data any): void
}

Handler: {
    shape: class
    style.font-color: "#666"

    +handle(data any): void
}

ConcreteEmitter: {
    shape: class

    -handlers: Map<string, Handler[]>
    +on(event string, handler Handler): void
    +off(event string, handler Handler): void
    +emit(event string, data any): void
}

LogHandler: {
    shape: class
    -logger: Logger
    +handle(data any): void
}

MetricsHandler: {
    shape: class
    -metrics: MetricsClient
    +handle(data any): void
}

EventEmitter <-> ConcreteEmitter: implements {
    style.stroke-dash: 5
}
Handler <-> LogHandler: implements {
    style.stroke-dash: 5
}
Handler <-> MetricsHandler: implements {
    style.stroke-dash: 5
}
ConcreteEmitter -> Handler: notifies
```

---

*This reference is part of the docs-with-mermaid Vista skill. For Mermaid diagrams, see [mermaid-reference.md](mermaid-reference.md). For Graphviz, see [graphviz-format.md](graphviz-format.md).*
