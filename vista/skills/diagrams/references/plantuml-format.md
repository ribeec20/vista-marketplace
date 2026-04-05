# PlantUML Format Reference

> Complete reference for creating PlantUML diagrams in Vista.
> Use PlantUML when Mermaid syntax is too limiting — especially for deployment diagrams, complex activity diagrams with swim lanes, and detailed UML with notes on associations.

## Table of Contents

- [File Format](#file-format)
- [When to Choose PlantUML over Mermaid](#when-to-choose-plantuml-over-mermaid)
- [Sequence Diagrams](#sequence-diagrams)
- [Class Diagrams](#class-diagrams)
- [Activity Diagrams](#activity-diagrams)
- [Component Diagrams](#component-diagrams)
- [Deployment Diagrams](#deployment-diagrams)
- [Use Case Diagrams](#use-case-diagrams)
- [State Diagrams](#state-diagrams)
- [Object Diagrams](#object-diagrams)
- [Timing Diagrams](#timing-diagrams)
- [Preprocessing and Includes](#preprocessing-and-includes)
- [Styling with skinparam](#styling-with-skinparam)
- [Vista Integration](#vista-integration)

---

## File Format

- **Extension:** `.puml`
- **Wrapper:** Every diagram MUST be wrapped in `@startuml` / `@enduml`
- **Comments:** Single line `' comment` or block `/' comment '/`
- **Encoding:** UTF-8

```plantuml
@startuml
' Your diagram here
title My Diagram
Alice -> Bob: Hello
@enduml
```

---

## When to Choose PlantUML over Mermaid

| Feature | Mermaid | PlantUML | Recommendation |
|---------|---------|----------|----------------|
| Deployment diagrams | Not supported | Full support | **PlantUML** |
| Activity swim lanes | Not supported | Full support | **PlantUML** |
| Notes on associations | Limited | Full support | **PlantUML** |
| `!include` modularity | Not supported | Full support | **PlantUML** |
| C4 Deployment level | Not supported | Via C4-PlantUML | **PlantUML** |
| Timing diagrams | Not supported | Full support | **PlantUML** |
| Object diagrams | Not supported | Full support | **PlantUML** |
| Browser rendering | Native JS | Requires server | **Mermaid** |
| GitHub/GitLab native | Yes | No | **Mermaid** |
| Simpler syntax | Yes | No | **Mermaid** |

**Rule of thumb:** Default to Mermaid. Switch to PlantUML when you need a diagram type or feature Mermaid doesn't support.

---

## Sequence Diagrams

PlantUML sequence diagrams support the same concepts as Mermaid but with richer features.

### Basic Syntax

```plantuml
@startuml
participant "Client" as C
participant "Server" as S
database "Database" as DB

C -> S: HTTP Request
activate S
S -> DB: Query
activate DB
DB --> S: Results
deactivate DB
S --> C: JSON Response
deactivate S
@enduml
```

### Participant Types

```plantuml
@startuml
actor User
boundary "API Gateway" as GW
control "Controller" as Ctrl
entity "Service" as Svc
database "PostgreSQL" as DB
collections "Workers" as W
queue "Kafka" as Q
@enduml
```

### Arrow Types

```plantuml
@startuml
A -> B: Solid with arrow
A --> B: Dotted with arrow
A ->> B: Thin arrow
A -\ B: Half arrow (lost)
A ->o B: Circle endpoint
A ->x B: Cross endpoint
A -[#red]> B: Colored arrow
A -[bold]> B: Bold arrow
@enduml
```

### Control Flow

```plantuml
@startuml
participant Client
participant Auth
participant API

Client -> Auth: Login

alt Valid Credentials
    Auth --> Client: JWT Token
    Client -> API: Request + Token
    API --> Client: Data
else Invalid
    Auth --> Client: 401 Error
end

opt Remember Me
    Auth -> Auth: Store session
end

loop Every 30s
    API -> API: Health check
end

par Parallel
    Client -> API: Fetch profile
else
    Client -> API: Fetch settings
end

group Critical section [mutex]
    API -> API: Lock resource
    API -> API: Process
    API -> API: Unlock
end
@enduml
```

### Notes

```plantuml
@startuml
participant A
participant B

A -> B: Request
note left: Sent from client
note right: Received by server

A -> B: Another
note over A,B
    This note spans
    multiple participants
    and multiple lines
end note

hnote over A: Hexagonal note
rnote over B: Rectangular note
@enduml
```

### Advanced Features

```plantuml
@startuml
' Auto-numbering
autonumber

' Dividers and spacing
== Initialization ==
Alice -> Bob: init()
|||
Alice -> Bob: configure()

== Processing ==
Alice -> Bob: process()

' Reference to another diagram
ref over Alice, Bob: See auth flow diagram

' Delay notation
...5 minutes later...
Alice -> Bob: timeout?
@enduml
```

---

## Class Diagrams

### Basic Syntax

```plantuml
@startuml
class User {
    -id: UUID
    -email: String
    -passwordHash: String
    +authenticate(password: String): boolean
    +changePassword(old: String, new: String): void
    #{static} findByEmail(email: String): User
}

interface Repository<T> {
    +findById(id: UUID): T
    +save(entity: T): void
    +delete(entity: T): void
}

abstract class BaseEntity {
    #id: UUID
    #createdAt: DateTime
    #updatedAt: DateTime
}

enum UserRole {
    ADMIN
    USER
    GUEST
}
@enduml
```

### Visibility Modifiers

| Symbol | Meaning |
|--------|---------|
| `-` | Private |
| `#` | Protected |
| `~` | Package |
| `+` | Public |

### Relationships

```plantuml
@startuml
' Inheritance
Animal <|-- Dog
Animal <|-- Cat

' Implementation
Serializable <|.. User

' Composition (filled diamond)
Car *-- Engine
Car *-- "4" Wheel

' Aggregation (hollow diamond)
University o-- Student

' Association
Teacher --> Student: teaches

' Dependency
Client ..> Service: uses

' Note on relationship
(Teacher, Student) .. teaches_note
note "Max 30 students\nper teacher" as teaches_note
@enduml
```

### Notes and Constraints

```plantuml
@startuml
class Order {
    -items: List<OrderItem>
    +calculateTotal(): Money
}

note right of Order
    Domain aggregate root.
    Invariant: total must equal
    sum of item subtotals.
end note

note left of Order::calculateTotal
    Uses strategy pattern
    for tax calculation
end note

class OrderItem {
    -quantity: int
    -unitPrice: Money
}

Order *-- OrderItem
note on link: ordered collection
@enduml
```

### Packages and Namespaces

```plantuml
@startuml
package "Domain Layer" {
    class Order
    class Product
    class Customer
}

package "Infrastructure" {
    class OrderRepository
    class PostgresConnection
}

package "Application" {
    class OrderService
    class OrderController
}

OrderService --> Order
OrderService --> OrderRepository
OrderRepository --> PostgresConnection
OrderController --> OrderService
@enduml
```

---

## Activity Diagrams

PlantUML activity diagrams support swim lanes — a key advantage over Mermaid.

### Basic Syntax

```plantuml
@startuml
start
:Initialize system;
:Load configuration;

if (Config valid?) then (yes)
    :Start services;
else (no)
    :Log error;
    :Use defaults;
    :Start services;
endif

:Accept connections;
stop
@enduml
```

### Swim Lanes

```plantuml
@startuml
|Customer|
start
:Browse products;
:Add to cart;
:Proceed to checkout;

|System|
:Validate cart;
:Calculate totals;

|Payment Provider|
:Process payment;

if (Payment successful?) then (yes)
    |System|
    :Create order;
    :Reserve inventory;
    :Send confirmation;

    |Customer|
    :Receive confirmation;
else (no)
    |Customer|
    :See error message;
    :Retry or cancel;
endif

stop
@enduml
```

### Control Flow

```plantuml
@startuml
start

' Fork/Join (parallel)
fork
    :Task A;
fork again
    :Task B;
fork again
    :Task C;
end fork

' While loop
while (more items?) is (yes)
    :Process item;
endwhile (no)

' Repeat loop
repeat
    :Attempt connection;
repeat while (connected?) is (no) not (yes)

' Switch
switch (status)
case (active)
    :Process normally;
case (pending)
    :Queue for later;
case (error)
    :Handle error;
endswitch

stop
@enduml
```

### Partitions and Colors

```plantuml
@startuml
start

partition "Validation" #LightBlue {
    :Check input;
    :Validate schema;
    :Sanitize data;
}

partition "Processing" #LightGreen {
    :Transform data;
    :Apply business rules;
    :Calculate results;
}

partition "Persistence" #LightYellow {
    :Save to database;
    :Update cache;
    :Publish event;
}

stop
@enduml
```

---

## Component Diagrams

```plantuml
@startuml
package "Frontend" {
    [Web App] as web
    [Mobile App] as mobile
}

package "Backend" {
    [API Gateway] as gateway
    [Auth Service] as auth
    [User Service] as user
    [Order Service] as order
}

package "Data" {
    database "PostgreSQL" as db
    database "Redis" as cache
    queue "Kafka" as mq
}

cloud "External" {
    [Stripe] as stripe
    [SendGrid] as email
}

web --> gateway: HTTPS
mobile --> gateway: HTTPS
gateway --> auth: gRPC
gateway --> user: gRPC
gateway --> order: gRPC

user --> db
user --> cache
order --> db
order --> mq
order --> stripe

mq --> email
@enduml
```

---

## Deployment Diagrams

This is PlantUML's killer feature — Mermaid has no equivalent.

### Basic Deployment

```plantuml
@startuml
node "Load Balancer" as lb {
    [nginx]
}

node "Web Server 1" as web1 {
    [Node.js App] as app1
}

node "Web Server 2" as web2 {
    [Node.js App] as app2
}

node "Database Server" as dbserver {
    database "PostgreSQL" as db
    database "Redis" as cache
}

lb --> app1: HTTP
lb --> app2: HTTP
app1 --> db: TCP/5432
app2 --> db: TCP/5432
app1 --> cache: TCP/6379
app2 --> cache: TCP/6379
@enduml
```

### Cloud Deployment

```plantuml
@startuml
!define AWSPuml https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/v18.0/dist

cloud "AWS" {
    node "VPC" {
        node "Public Subnet" {
            [ALB] as alb
            [NAT Gateway] as nat
        }

        node "Private Subnet - App" {
            node "ECS Cluster" {
                [Service A] as svcA
                [Service B] as svcB
            }
        }

        node "Private Subnet - Data" {
            database "RDS PostgreSQL" as rds
            database "ElastiCache Redis" as redis
            queue "SQS" as sqs
        }
    }

    storage "S3" as s3
    [CloudFront] as cf
}

actor User

User --> cf: HTTPS
cf --> alb: HTTPS
alb --> svcA: HTTP
alb --> svcB: HTTP
svcA --> rds: SQL
svcB --> rds: SQL
svcA --> redis
svcB --> sqs
svcA --> s3
@enduml
```

### Kubernetes Deployment

```plantuml
@startuml
node "Kubernetes Cluster" {
    node "Namespace: production" {
        rectangle "Ingress Controller" as ingress

        node "Deployment: api" {
            rectangle "Pod" as pod1 {
                [api-container] as api1
                [sidecar-proxy] as proxy1
            }
            rectangle "Pod" as pod2 {
                [api-container] as api2
                [sidecar-proxy] as proxy2
            }
        }

        node "Deployment: worker" {
            rectangle "Pod" as pod3 {
                [worker-container] as worker
            }
        }

        rectangle "Service: api-svc" as svc
        rectangle "ConfigMap" as cm
        rectangle "Secret" as secret
    }

    node "Namespace: monitoring" {
        [Prometheus] as prom
        [Grafana] as graf
    }
}

database "External RDS" as rds
queue "External SQS" as sqs

ingress --> svc
svc --> pod1
svc --> pod2
api1 --> rds
worker --> sqs
worker --> rds
prom --> pod1
prom --> pod2
prom --> pod3
graf --> prom
cm --> api1
secret --> api1
@enduml
```

---

## Use Case Diagrams

```plantuml
@startuml
left to right direction

actor "Customer" as customer
actor "Admin" as admin
actor "Payment System" as payment <<system>>

rectangle "E-Commerce Platform" {
    usecase "Browse Products" as UC1
    usecase "Search Products" as UC2
    usecase "Add to Cart" as UC3
    usecase "Checkout" as UC4
    usecase "Process Payment" as UC5
    usecase "Track Order" as UC6
    usecase "Manage Products" as UC7
    usecase "View Reports" as UC8
    usecase "Manage Users" as UC9
}

customer --> UC1
customer --> UC2
customer --> UC3
customer --> UC4
customer --> UC6

UC4 --> UC5: <<include>>
UC5 --> payment

admin --> UC7
admin --> UC8
admin --> UC9

UC1 <.. UC2: <<extend>>
@enduml
```

---

## State Diagrams

```plantuml
@startuml
[*] --> Draft

state Draft {
    [*] --> Editing
    Editing --> Saving: auto-save
    Saving --> Editing: saved
}

Draft --> Submitted: submit()
Submitted --> InReview: assign_reviewer()

state InReview {
    [*] --> Reading
    Reading --> Commenting: add_comment()
    Commenting --> Reading: done
}

InReview --> Approved: approve()
InReview --> Rejected: reject()
Rejected --> Draft: revise()

state Approved {
    [*] --> Scheduling
    Scheduling --> Queued: schedule()
}

Approved --> Published: publish()
Published --> Archived: archive()
Archived --> [*]

note right of Draft: Author working
note right of InReview: Reviewer feedback loop
note right of Approved: Ready for publication
@enduml
```

---

## Object Diagrams

Object diagrams show instances at a specific point in time — useful for illustrating runtime state.

```plantuml
@startuml
object "order1: Order" as o1 {
    id = "ORD-001"
    status = CONFIRMED
    total = $149.97
    createdAt = "2024-03-15"
}

object "item1: OrderItem" as i1 {
    quantity = 2
    unitPrice = $49.99
}

object "item2: OrderItem" as i2 {
    quantity = 1
    unitPrice = $49.99
}

object "product1: Product" as p1 {
    name = "Widget Pro"
    sku = "WDG-001"
}

object "product2: Product" as p2 {
    name = "Gadget Plus"
    sku = "GDG-002"
}

o1 *-- i1
o1 *-- i2
i1 --> p1: references
i2 --> p2: references
@enduml
```

---

## Timing Diagrams

Timing diagrams show state changes over time — ideal for protocol documentation.

```plantuml
@startuml
robust "Web Server" as WS
concise "Client" as C
clock clk with period 1

@0
WS is Idle
C is Idle

@1
C is Requesting
WS is Idle

@2
WS is Processing
C is Waiting

@4
WS is Responding
C is Waiting

@5
C is Receiving
WS is Idle

@7
C is Idle
WS is Idle

highlight 2 to 4 #LightGreen: Server processing time
highlight 1 to 5 #LightBlue: Total request lifecycle
@enduml
```

---

## Preprocessing and Includes

PlantUML includes a preprocessor for reusable diagram components.

### Variables and Macros

```plantuml
@startuml
!define PRIMARY_COLOR #4A90D9
!define SUCCESS_COLOR #7ED321
!define ERROR_COLOR #D0021B

!define SERVICE(name, desc) rectangle name as name <<service>> #PRIMARY_COLOR [desc]
!define DATABASE(name, desc) database name as name <<database>> [desc]

SERVICE(auth, "Auth Service")
SERVICE(api, "API Service")
DATABASE(db, "PostgreSQL")

auth --> api
api --> db
@enduml
```

### File Includes

```plantuml
@startuml
' Include shared styles
!include styles/theme.puml

' Include partial diagrams
!include components/auth-module.puml
!include components/api-module.puml

' Conditional inclusion
!ifdef SHOW_DETAILS
    !include components/internals.puml
!endif
@enduml
```

### Themes

```plantuml
@startuml
!theme cerulean
' Available themes: cerulean, materia, minty, sandstone, superhero, united, etc.

class MyClass {
    +method(): void
}
@enduml
```

---

## Styling with skinparam

`skinparam` controls the visual appearance of every diagram element.

### Global Styling

```plantuml
@startuml
skinparam backgroundColor #FEFEFE
skinparam defaultFontName "Segoe UI"
skinparam defaultFontSize 12
skinparam shadowing false
skinparam roundcorner 8

skinparam class {
    BackgroundColor #E1F5FE
    BorderColor #0288D1
    ArrowColor #01579B
    FontColor #01579B
}

skinparam package {
    BackgroundColor #F3E5F5
    BorderColor #7B1FA2
}

skinparam note {
    BackgroundColor #FFF9C4
    BorderColor #F9A825
}
@enduml
```

### Component-Specific Styling

```plantuml
@startuml
skinparam component {
    BackgroundColor #E8F5E9
    BorderColor #2E7D32
    FontColor #1B5E20
}

skinparam database {
    BackgroundColor #FFF3E0
    BorderColor #E65100
}

skinparam queue {
    BackgroundColor #E3F2FD
    BorderColor #1565C0
}

skinparam arrow {
    Color #37474F
    FontColor #546E7A
    Thickness 1.5
}
@enduml
```

### Common skinparam Properties

| Property | Applies To | Example |
|----------|-----------|---------|
| `BackgroundColor` | All elements | `#E1F5FE` |
| `BorderColor` | All elements | `#0288D1` |
| `FontColor` | All elements | `#01579B` |
| `FontSize` | All elements | `14` |
| `FontName` | All elements | `"Arial"` |
| `ArrowColor` | Relationships | `#333333` |
| `ArrowThickness` | Relationships | `2` |
| `Shadowing` | Global | `false` |
| `RoundCorner` | Rectangles | `10` |
| `Padding` | Containers | `10` |
| `LineType` | Relationships | `ortho` |

---

## Vista Integration

### Rendering

PlantUML diagrams are rendered server-side via a PlantUML server. The server URL is configurable in Vista settings.

The rendering pipeline:
1. Vista reads the `.puml` file content
2. Encodes it using PlantUML's deflate encoding
3. Sends to the PlantUML server (default: `https://www.plantuml.com/plantuml`)
4. Receives SVG/PNG back for display

The `plantuml-encoder` CDN (~10KB) handles client-side encoding.

### Manifest Configuration

In `_arch.json`:

```json
{
    "diagrams": [
        {
            "id": "deployment-diagram",
            "title": "Production Deployment",
            "file": "deployment.puml",
            "type": "plantuml",
            "diagramType": "custom"
        }
    ]
}
```

- **`type`**: Must be `"plantuml"`
- **`diagramType`**: Use `"custom"` for all PlantUML diagrams

### File Organization

Place PlantUML files in the architecture directory:
```
docs/<feature>/arch/
├── _arch.json
├── overview.mmd          (Mermaid for simple diagrams)
├── deployment.puml       (PlantUML for deployment)
├── activity-swim.puml    (PlantUML for swim lanes)
└── README.md             (Prose documentation)
```

### Best Practices

1. **Use PlantUML only when Mermaid can't do the job** — Mermaid is simpler and renders client-side
2. **Include `@startuml`/`@enduml`** — Always wrap content; Vista strips these for encoding
3. **Use `skinparam shadowing false`** — Shadows render poorly in small viewports
4. **Keep font sizes ≥ 12** — PlantUML server renders at fixed resolution
5. **Prefer SVG output** — Better scaling than PNG in the dashboard
6. **Break large diagrams** — PlantUML server has URL length limits (~8000 chars encoded)

---

*This reference is part of the docs-with-mermaid Vista skill. For Mermaid diagrams, see [mermaid-reference.md](mermaid-reference.md) and [mermaid-advanced.md](mermaid-advanced.md).*
