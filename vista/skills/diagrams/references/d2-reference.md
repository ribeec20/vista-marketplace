# D2 Diagram Reference for AI Agents

## When to Use D2

- **Infrastructure/rack layouts** — grid layout with spatial positioning
- **Hardware wiring diagrams** — multiple simultaneous connections, bus architecture
- **System architecture with custom icons** — built-in icon support
- **Complex container nesting** — first-class support for nested grouping
- **Network topology** — when PlantUML nwdiag isn't appropriate

### Advantages Over Mermaid
- Grid layout for spatial diagrams (rack layouts, cabinet views)
- Nested containers with dot notation
- Built-in icon support
- Multiple layout engines (dagre, elk, tala)
- Better control over connection routing

### File Extension
Always use `.d2` for D2 files.

---

## Basic Syntax

### Shapes and Labels

```d2
# Simple shape with label
server: Web Server

# Shape with explicit type
database: PostgreSQL {
  shape: cylinder
}

# Multiple shapes
client: Browser
api: API Server
cache: Redis Cache
```

### Available Shapes

```d2
rectangle: Rectangle
square: Square {shape: square}
page: Document {shape: page}
parallelogram: I/O {shape: parallelogram}
hexagon: Process {shape: hexagon}
oval: Start/End {shape: oval}
circle: Node {shape: circle}
diamond: Decision {shape: diamond}
cylinder: Database {shape: cylinder}
queue: Message Queue {shape: queue}
package: Package {shape: package}
cloud: Cloud {shape: cloud}
person: User {shape: person}
```

---

## Connections

### Basic Connections

```d2
# Directed (arrow)
a -> b: request
b -> a: response

# Bidirectional
client <-> server: sync

# Undirected (no arrow)
a -- b: connected
```

### Arrow Styles

```d2
# Solid arrow (default)
a -> b: solid

# Dashed arrow
a -> b: dashed {
  style.stroke-dash: 5
}

# Bold arrow
a -> b: bold {
  style.stroke-width: 3
}

# Colored arrow
a -> b: critical {
  style.stroke: red
}
```

### Connection Labels

```d2
client -> server: HTTP GET /api/users
server -> database: SELECT * FROM users
database -> server: ResultSet
server -> client: 200 OK JSON
```

---

## Containers (Grouping)

### Dot Notation

```d2
# Nested using dots
server.api: REST API
server.auth: Auth Service
server.database: PostgreSQL {shape: cylinder}

# Connections between nested elements
client -> server.api: request
server.api -> server.auth: validate
server.api -> server.database: query
```

### Curly Brace Notation

```d2
server: Backend {
  api: REST API
  auth: Auth Service
  db: PostgreSQL {shape: cylinder}

  api -> auth: validate
  api -> db: query
}

client: Browser
client -> server.api: HTTP
```

### Deeply Nested

```d2
cloud: AWS {
  vpc: VPC 10.0.0.0/16 {
    public: Public Subnet {
      lb: Load Balancer
    }
    private: Private Subnet {
      app1: App Server 1
      app2: App Server 2
    }
    data: Data Subnet {
      rds: RDS PostgreSQL {shape: cylinder}
    }
  }
}

cloud.vpc.public.lb -> cloud.vpc.private.app1
cloud.vpc.public.lb -> cloud.vpc.private.app2
cloud.vpc.private.app1 -> cloud.vpc.data.rds
cloud.vpc.private.app2 -> cloud.vpc.data.rds
```

---

## Grid Layout

Grid layout is D2's killer feature for spatial diagrams like rack layouts and infrastructure views.

### Basic Grid

```d2
grid-rows: 3
grid-columns: 4

cell1: Server A
cell2: Server B
cell3: Server C
cell4: Server D
cell5: Switch 1
cell6: Switch 2
cell7: ""
cell8: ""
cell9: Router
cell10: Firewall
cell11: ""
cell12: ""
```

### Rack Layout Example

```d2
rack: Server Rack {
  grid-rows: 8
  grid-columns: 1

  u1: 1U - PDU {
    style.fill: "#e0e0e0"
  }
  u2: 2U - Patch Panel {
    style.fill: "#e0e0e0"
  }
  u3: 3U - Core Switch (Cisco 48p) {
    style.fill: "#cce5ff"
  }
  u4: 4U - Firewall (pfSense) {
    style.fill: "#ffcccc"
  }
  u5: 5-6U - Dell R740 (ESXi) {
    style.fill: "#ccffcc"
  }
  u6: 7-8U - Dell R740 (ESXi) {
    style.fill: "#ccffcc"
  }
  u7: 9-10U - NetApp FAS {
    style.fill: "#ffffcc"
  }
  u8: 11-14U - UPS (APC) {
    style.fill: "#f0e0ff"
  }
}
```

### Data Center Floor Grid

```d2
datacenter: Data Center Floor {
  grid-rows: 2
  grid-columns: 4

  rack-a1: Rack A1 {
    style.fill: "#cce5ff"
  }
  rack-a2: Rack A2 {
    style.fill: "#cce5ff"
  }
  rack-a3: Rack A3 {
    style.fill: "#ccffcc"
  }
  rack-a4: Rack A4 {
    style.fill: "#ccffcc"
  }
  rack-b1: Rack B1 {
    style.fill: "#ffffcc"
  }
  rack-b2: Rack B2 {
    style.fill: "#ffffcc"
  }
  cooling: Cooling Unit {
    style.fill: "#e0e0ff"
  }
  ups: UPS Room {
    style.fill: "#ffe0e0"
  }
}
```

---

## Styling

### Shape Styling

```d2
server: Web Server {
  style: {
    fill: "#cce5ff"
    stroke: "#0066cc"
    stroke-width: 2
    border-radius: 8
    font-size: 16
    font-color: "#003366"
    bold: true
    shadow: true
  }
}
```

### Available Style Properties

| Property | Values | Description |
|----------|--------|-------------|
| `fill` | CSS color | Background color |
| `stroke` | CSS color | Border color |
| `stroke-width` | 1-15 | Border thickness |
| `stroke-dash` | 0-10 | Dashed border (0 = solid) |
| `border-radius` | 0-20 | Rounded corners |
| `font-size` | 8-100 | Text size |
| `font-color` | CSS color | Text color |
| `bold` | true/false | Bold text |
| `italic` | true/false | Italic text |
| `shadow` | true/false | Drop shadow |
| `opacity` | 0-1 | Transparency |
| `3d` | true/false | 3D effect (rectangles only) |

### Connection Styling

```d2
a -> b: critical {
  style: {
    stroke: red
    stroke-width: 3
    stroke-dash: 0
    font-color: red
  }
}
```

---

## Icons

D2 supports icons on shapes:

```d2
server: Web Server {
  icon: https://icons.terrastruct.com/essentials%2F112-server.svg
}

database: PostgreSQL {
  shape: cylinder
  icon: https://icons.terrastruct.com/dev%2Fpostgresql.svg
}

cloud: AWS {
  icon: https://icons.terrastruct.com/aws%2F_Group%20Icons%2FAWS-Cloud-alt_light-bg.svg
}
```

### Common Icon URLs (Terrastruct CDN)

- Server: `https://icons.terrastruct.com/essentials%2F112-server.svg`
- Database: `https://icons.terrastruct.com/dev%2Fpostgresql.svg`
- Cloud: `https://icons.terrastruct.com/aws%2F_Group%20Icons%2FAWS-Cloud-alt_light-bg.svg`
- User: `https://icons.terrastruct.com/essentials%2F359-users.svg`
- Lock: `https://icons.terrastruct.com/essentials%2F145-lock.svg`

---

## SQL Tables

D2 has native SQL table rendering:

```d2
users: {
  shape: sql_table
  id: int {constraint: primary_key}
  email: varchar(255) {constraint: unique}
  name: varchar(100)
  created_at: timestamp
}

orders: {
  shape: sql_table
  id: int {constraint: primary_key}
  user_id: int {constraint: foreign_key}
  total: decimal(10,2)
  status: varchar(20)
  created_at: timestamp
}

users.id <-> orders.user_id
```

---

## Rendering

### CLI

```bash
# Install D2
curl -fsSL https://d2lang.com/install.sh | sh -s --

# Render to SVG (default)
d2 input.d2 output.svg

# Render to PNG
d2 input.d2 output.png

# Watch mode (auto-reload)
d2 --watch input.d2 output.svg

# Choose layout engine
d2 --layout elk input.d2 output.svg
```

### Layout Engines

| Engine | Description |
|--------|-------------|
| `dagre` | Default, fast, good for most diagrams |
| `elk` | Eclipse Layout Kernel, good for complex graphs |
| `tala` | Terrastruct's proprietary engine (requires license) |

---

## Practical Examples

### Network Topology

```d2
internet: Internet {shape: cloud}

firewall: Firewall {
  style.fill: "#ffcccc"
}

dmz: DMZ {
  web1: Web Server 1
  web2: Web Server 2
  lb: Load Balancer
  lb -> web1
  lb -> web2
}

internal: Internal Network {
  app: App Server
  db: Database {shape: cylinder}
  cache: Redis {shape: cylinder}
  app -> db: SQL
  app -> cache: cache
}

internet -> firewall: HTTPS
firewall -> dmz.lb: HTTP
dmz.web1 -> internal.app: gRPC
dmz.web2 -> internal.app: gRPC
```

### Hardware Block Diagram

```d2
cpu: CPU {
  style.fill: "#cce5ff"
  core1: Core 1
  core2: Core 2
  l2: L2 Cache
  core1 -> l2
  core2 -> l2
}

ram: DDR4 RAM {
  style.fill: "#ccffcc"
  dimm1: DIMM 1 (8GB)
  dimm2: DIMM 2 (8GB)
}

storage: Storage {
  style.fill: "#ffffcc"
  ssd: NVMe SSD (512GB)
  hdd: HDD (2TB)
}

pch: PCH (Chipset) {
  style.fill: "#e0e0e0"
}

cpu -> ram: DDR4 Bus
cpu -> pch: DMI 3.0
pch -> storage.ssd: PCIe x4
pch -> storage.hdd: SATA III
pch -> usb: USB 3.0 {shape: rectangle}
pch -> ethernet: GbE NIC {shape: rectangle}
```

### Microservices Architecture

```d2
gateway: API Gateway {
  style.fill: "#cce5ff"
}

services: Microservices {
  auth: Auth Service {
    style.fill: "#ccffcc"
  }
  users: User Service {
    style.fill: "#ccffcc"
  }
  orders: Order Service {
    style.fill: "#ccffcc"
  }
  notify: Notification Service {
    style.fill: "#ccffcc"
  }
}

data: Data Layer {
  userdb: Users DB {shape: cylinder}
  orderdb: Orders DB {shape: cylinder}
  redis: Redis {shape: cylinder}
  kafka: Kafka {shape: queue}
}

gateway -> services.auth: JWT
gateway -> services.users: REST
gateway -> services.orders: REST

services.auth -> data.redis: sessions
services.users -> data.userdb: SQL
services.orders -> data.orderdb: SQL
services.orders -> data.kafka: events
data.kafka -> services.notify: consume
```

---

## Quick Tips for AI Agents

1. **Containers**: Use dot notation (`cloud.vpc.subnet`) for flat definitions, curly braces for nested blocks
2. **Grid layout**: Set `grid-rows` and `grid-columns` on a container for spatial layouts
3. **Cross-container connections**: Always use full dotted paths (`a.b -> c.d`)
4. **Colors**: Use hex codes in quotes (`"#cce5ff"`) — CSS color names also work
5. **Icons**: Reference via URL — Terrastruct CDN has common icons
6. **Shapes**: Default is rectangle; use `shape: cylinder` for DBs, `shape: cloud` for clouds, `shape: queue` for message queues
7. **File extension**: Always `.d2`
8. **Rendering**: `d2` CLI must be installed locally; no public API fallback
