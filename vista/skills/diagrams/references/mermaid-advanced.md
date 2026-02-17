# Mermaid Advanced Diagrams — Strict Reference

> Load this file when creating C4, sequence, state, class, ER, or Gantt diagrams in Mermaid.
> For basic Mermaid syntax (flowcharts, mindmaps, pie, timeline, git graph, etc.), see [mermaid-reference.md](mermaid-reference.md).

## Table of Contents

- [C4 Architecture Diagrams](#c4-architecture-diagrams)
- [Sequence Diagrams](#sequence-diagrams)
- [State Diagrams](#state-diagrams)
- [Class Diagrams](#class-diagrams)
- [ER Diagrams](#er-diagrams)
- [Gantt Charts](#gantt-charts)

---

## C4 Architecture Diagrams

### When to Use C4

Use C4 diagrams when documenting software architecture at different abstraction levels. The C4 model defines four levels:

1. **Context** — Shows the system in its environment (users, external systems)
2. **Container** — Shows the high-level tech choices (apps, databases, message brokers)
3. **Component** — Shows the internals of a single container
4. **Deployment** — Shows infrastructure mapping (Mermaid lacks this — use PlantUML)

### The Four Levels

| Level | Mermaid Keyword | Shows | Audience |
|-------|----------------|-------|----------|
| Context | `C4Context` | System + external actors | Everyone |
| Container | `C4Container` | Applications, databases, queues | Technical staff |
| Component | `C4Component` | Internal modules/services | Developers |
| Deployment | N/A | Infrastructure nodes | DevOps |

### Strict Syntax Rules

1. **Diagram declaration** — Must be one of: `C4Context`, `C4Container`, `C4Component`
2. **Element functions** — Use function-call syntax with parentheses:
   - `Person(alias, "Label", "Description")`
   - `System(alias, "Label", "Description")`
   - `System_Ext(alias, "Label", "Description")`
   - `Container(alias, "Label", "Technology", "Description")`
   - `ContainerDb(alias, "Label", "Technology", "Description")`
   - `ContainerQueue(alias, "Label", "Technology", "Description")`
   - `Component(alias, "Label", "Technology", "Description")`
3. **Boundaries** — Use `_Boundary` variants with curly braces:
   - `System_Boundary(alias, "Label") { ... }`
   - `Container_Boundary(alias, "Label") { ... }`
   - `Enterprise_Boundary(alias, "Label") { ... }`
4. **Relationships** — `Rel(from, to, "Label", "Technology")` — always 4 arguments
5. **IDs** — Must be unique alphanumeric strings (no spaces, no special characters)
6. **Title** — `title System Context Diagram - My System` (optional but recommended)

### Required Elements Checklist

**Context Diagram:**
- [ ] At least one `Person()` (the primary user)
- [ ] The `System()` being documented (exactly one)
- [ ] All `System_Ext()` dependencies
- [ ] `Rel()` for every interaction

**Container Diagram:**
- [ ] `System_Boundary()` wrapping all containers
- [ ] `Container()` for each application
- [ ] `ContainerDb()` for databases
- [ ] `ContainerQueue()` for message brokers
- [ ] External systems outside the boundary

**Component Diagram:**
- [ ] `Container_Boundary()` wrapping all components
- [ ] `Component()` for each internal module
- [ ] Sibling containers shown outside the boundary

### Common Pitfalls and Anti-Patterns

| Pitfall | Wrong | Right |
|---------|-------|-------|
| Using flowchart subgraphs | `subgraph "My System"` | `System_Boundary(sys, "My System")` |
| Missing `_Ext` for external | `System(stripe, "Stripe")` | `System_Ext(stripe, "Stripe", "Payment")` |
| Mixing abstraction levels | Container inside C4Context | One level per diagram |
| Forgetting technology arg | `Container(api, "API")` | `Container(api, "API", "Node.js", "Desc")` |
| Using `Container` for a DB | `Container(db, "DB", "PG")` | `ContainerDb(db, "DB", "PostgreSQL", "Stores data")` |
| IDs with spaces | `Person(my user, ...)` | `Person(myUser, ...)` |
| Missing Rel technology | `Rel(a, b, "Calls")` | `Rel(a, b, "Calls", "HTTPS/JSON")` |

### Complete Examples

#### Context Level

```mermaid
C4Context
    title System Context — Online Banking

    Person(customer, "Bank Customer", "Views accounts, transfers money")
    Person(admin, "Bank Admin", "Manages accounts and compliance")

    System(banking, "Online Banking System", "Core banking web application")

    System_Ext(email, "Email Service", "Sends transactional emails")
    System_Ext(kyc, "KYC Provider", "Identity verification")
    System_Ext(swift, "SWIFT Network", "International transfers")

    Rel(customer, banking, "Uses", "HTTPS")
    Rel(admin, banking, "Manages", "HTTPS")
    Rel(banking, email, "Sends emails via", "SMTP")
    Rel(banking, kyc, "Verifies identity via", "REST API")
    Rel(banking, swift, "Transfers via", "ISO 20022")
```

#### Container Level

```mermaid
C4Container
    title Container Diagram — Online Banking

    Person(customer, "Bank Customer", "Views accounts, transfers money")

    System_Boundary(banking, "Online Banking System") {
        Container(spa, "Single-Page App", "React", "Customer-facing web UI")
        Container(api, "API Gateway", "Node.js/Express", "Routes and authenticates requests")
        Container(accounts, "Accounts Service", "Java/Spring", "Account management and balances")
        Container(transfers, "Transfer Service", "Go", "Processes money transfers")
        ContainerDb(db, "Main Database", "PostgreSQL", "Stores accounts, transactions, users")
        ContainerDb(cache, "Session Cache", "Redis", "Stores session data and OTPs")
        ContainerQueue(events, "Event Bus", "Kafka", "Async event processing")
    }

    System_Ext(email, "Email Service", "SendGrid")
    System_Ext(swift, "SWIFT Network", "International transfers")

    Rel(customer, spa, "Uses", "HTTPS")
    Rel(spa, api, "Calls", "JSON/HTTPS")
    Rel(api, accounts, "Reads/Writes", "gRPC")
    Rel(api, transfers, "Submits", "gRPC")
    Rel(accounts, db, "Reads/Writes", "SQL/TCP")
    Rel(transfers, db, "Reads/Writes", "SQL/TCP")
    Rel(api, cache, "Sessions", "Redis protocol")
    Rel(transfers, events, "Publishes", "Kafka protocol")
    Rel(events, email, "Triggers", "SMTP")
    Rel(transfers, swift, "Transfers", "ISO 20022")
```

#### Component Level

```mermaid
C4Component
    title Component Diagram — Transfer Service

    Container_Boundary(transfers, "Transfer Service") {
        Component(controller, "Transfer Controller", "Go/Chi", "Handles HTTP/gRPC requests")
        Component(validator, "Transfer Validator", "Go", "Validates transfer rules and limits")
        Component(processor, "Transfer Processor", "Go", "Orchestrates transfer execution")
        Component(fxService, "FX Service", "Go", "Currency conversion rates")
        Component(repo, "Transfer Repository", "Go/sqlx", "Data access layer")
        Component(publisher, "Event Publisher", "Go/sarama", "Publishes domain events")
    }

    ContainerDb(db, "Main Database", "PostgreSQL")
    ContainerQueue(events, "Event Bus", "Kafka")
    System_Ext(swift, "SWIFT Network", "International transfers")

    Rel(controller, validator, "Validates via", "Function call")
    Rel(controller, processor, "Processes via", "Function call")
    Rel(processor, fxService, "Gets rates from", "Function call")
    Rel(processor, repo, "Persists via", "Function call")
    Rel(processor, publisher, "Publishes events via", "Function call")
    Rel(repo, db, "Reads/Writes", "SQL/TCP")
    Rel(publisher, events, "Sends events to", "Kafka protocol")
    Rel(processor, swift, "Submits transfers to", "ISO 20022")
```

> **Note:** Mermaid does not support C4 Deployment diagrams (`Deployment_Node` is not available). For deployment-level diagrams, use PlantUML — see [plantuml-format.md](plantuml-format.md).

---

## Sequence Diagrams

### When to Use Sequences

- API request/response flows
- Authentication/authorization protocols
- Service-to-service communication
- Event-driven message flows
- Any interaction pattern over time

### Strict Syntax Rules

1. **Declare participants before messages** — Always declare all participants at the top:
   ```
   participant A as "Service A"
   actor U as "User"
   ```
2. **Participant vs Actor** — `actor` renders a stick figure, `participant` renders a box
3. **Arrow types** (memorize these):
   | Arrow | Meaning | When to Use |
   |-------|---------|-------------|
   | `->>` | Solid + filled arrowhead | Synchronous request |
   | `-->>` | Dotted + filled arrowhead | Return/response |
   | `-)` | Solid + open arrowhead | Fire-and-forget (async) |
   | `--)` | Dotted + open arrowhead | Async response |
   | `-x` | Solid + cross | Lost/failed message |
   | `--x` | Dotted + cross | Failed response |

4. **Activation shorthand** — Use `+`/`-` on arrows instead of separate activate/deactivate:
   ```
   A->>+B: Request    %% activates B
   B-->>-A: Response   %% deactivates B
   ```
5. **All control flow blocks must end with `end`**:
   ```
   alt / else / end
   opt / end
   loop / end
   par / and / end
   critical / option / end
   break / end
   ```
6. **Notes** — Three placement options:
   ```
   Note right of A: Text
   Note left of A: Text
   Note over A,B: Text spanning participants
   ```

### Advanced Patterns

#### alt/opt/par/critical/break

```mermaid
sequenceDiagram
    participant C as Client
    participant GW as Gateway
    participant Auth as Auth Service
    participant API as Core API

    C->>+GW: POST /checkout

    critical Validate Session
        GW->>+Auth: Verify token
        Auth-->>-GW: Token valid
    option Token expired
        Auth-->>GW: 401 Expired
        GW-->>C: 401 — Re-authenticate
        break Session invalid
            GW->>GW: Log security event
        end
    end

    par Process order components
        GW->>+API: Reserve inventory
        API-->>-GW: Reserved
    and
        GW->>+API: Calculate shipping
        API-->>-GW: Shipping quote
    and
        GW->>+API: Apply discounts
        API-->>-GW: Final price
    end

    GW-->>-C: 200 Checkout ready
```

#### rect Highlighting and autonumber

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant DB as Database

    rect rgb(200, 220, 255)
        Note over U,FE: User interaction layer
        U->>FE: Submit form
        FE->>FE: Client-side validation
    end

    rect rgb(220, 255, 220)
        Note over FE,DB: Server processing layer
        FE->>+BE: POST /api/data
        BE->>+DB: INSERT record
        DB-->>-BE: Confirmation
        BE-->>-FE: 201 Created
    end

    FE-->>U: Show success toast
```

### Common Pitfalls and Anti-Patterns

| Pitfall | Problem | Fix |
|---------|---------|-----|
| Missing `end` keyword | Diagram won't render | Every `alt`, `opt`, `loop`, `par`, `critical`, `break` needs `end` |
| >7 participants | Diagram becomes unreadable | Split into multiple diagrams or merge participants |
| Open activation bars | Bar extends to diagram bottom | Match every `+` with a `-` on the return arrow |
| Undeclared participants | Implicit ordering, aliasing fails | Always declare `participant`/`actor` at top |
| Wrong arrow for return | Using `->>` for responses | Use `-->>` (dotted) for all return/response messages |
| Notes on undeclared | `Note right of X` where X not declared | Declare participant first |
| Nested alt without clarity | Deep nesting becomes confusing | Use `rect` highlighting or split diagrams |

---

## State Diagrams

### When to Use State Diagrams

- Object lifecycle (order, ticket, user account)
- UI state machines
- Protocol states (connection, authentication)
- Workflow engines
- Approval processes

### Strict Syntax Rules

1. **Always use v2** — Start with `stateDiagram-v2` (not `stateDiagram`)
2. **Initial/terminal states** — `[*]` represents both:
   - `[*] --> FirstState` (initial)
   - `LastState --> [*]` (terminal)
3. **Transitions** — `StateA --> StateB : event [guard] / action`
4. **Composite states** — Use `state Parent { }` with nested `[*]`:
   ```
   state Parent {
       [*] --> Child1
       Child1 --> Child2
   }
   ```
5. **Parallel regions** — Separate with `--` inside composite:
   ```
   state Parallel {
       [*] --> A
       --
       [*] --> B
   }
   ```
6. **Choice pseudo-state** — `state name <<choice>>`
7. **Fork/Join** — `state name <<fork>>` and `state name <<join>>`
8. **Notes** — `note right of State : Text` or `note left of State : Text`
9. **State descriptions** — `StateName : This is a description`

### Common Pitfalls and Anti-Patterns

| Pitfall | Problem | Fix |
|---------|---------|-----|
| Using v1 syntax | `stateDiagram` lacks features | Always use `stateDiagram-v2` |
| Orphaned states | States with no transitions in/out | Every state needs at least one transition |
| Composite without inner `[*]` | No clear starting state inside | Add `[*] --> FirstChild` inside composite |
| Fork without join | Parallel paths never converge | Every `<<fork>>` should have a matching `<<join>>` |
| Too many top-level states | Flat diagram > 8 states is unreadable | Group into composite states |
| Missing terminal `[*]` | Diagram has no end state | Add `FinalState --> [*]` for completed flows |
| Choice with single branch | `<<choice>>` with only one output | Use `<<choice>>` only for 2+ branches |

### Complete Examples

#### Simple Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted : submit()
    Submitted --> InReview : assign_reviewer()
    InReview --> Approved : approve()
    InReview --> Rejected : reject()
    Rejected --> Draft : revise()
    Approved --> Published : publish()
    Published --> Archived : archive()
    Archived --> [*]

    Draft : Author editing
    Submitted : Awaiting reviewer
    InReview : Reviewer evaluating
```

#### Composite States

```mermaid
stateDiagram-v2
    [*] --> Idle

    state "Order Processing" as Processing {
        [*] --> Validating
        Validating --> Pricing : valid
        Pricing --> Confirmed : priced

        state Validating {
            [*] --> CheckStock
            CheckStock --> CheckCredit : in stock
            CheckCredit --> [*] : approved
        }
    }

    Idle --> Processing : place_order()
    Processing --> Fulfilled : ship()
    Processing --> Cancelled : cancel()
    Fulfilled --> [*]
    Cancelled --> [*]
```

#### Parallel with Fork/Join

```mermaid
stateDiagram-v2
    [*] --> Received

    state fork_processing <<fork>>
    Received --> fork_processing

    state "Background Check" as BgCheck {
        [*] --> VerifyIdentity
        VerifyIdentity --> VerifyEmployment
        VerifyEmployment --> [*]
    }

    state "Technical Assessment" as TechAssess {
        [*] --> CodingTest
        CodingTest --> SystemDesign
        SystemDesign --> [*]
    }

    state "Culture Interview" as Culture {
        [*] --> PanelInterview
        PanelInterview --> [*]
    }

    fork_processing --> BgCheck
    fork_processing --> TechAssess
    fork_processing --> Culture

    state join_results <<join>>
    BgCheck --> join_results
    TechAssess --> join_results
    Culture --> join_results

    state decision <<choice>>
    join_results --> decision
    decision --> Offer : all passed
    decision --> Rejected : any failed

    Offer --> [*]
    Rejected --> [*]
```

---

## Class Diagrams

### When to Use Class Diagrams

- Domain model documentation
- API type definitions
- Design pattern illustration
- Object-oriented architecture
- Type hierarchy documentation

### Strict Syntax Rules

1. **Visibility markers** (prefix on members):
   | Marker | Meaning |
   |--------|---------|
   | `+` | Public |
   | `-` | Private |
   | `#` | Protected |
   | `~` | Package/Internal |

2. **Method classifiers** (suffix on methods):
   | Marker | Meaning |
   |--------|---------|
   | `*` | Abstract |
   | `$` | Static |

3. **Relationship arrows** (memorize direction and meaning):
   | Arrow | Meaning | Read as |
   |-------|---------|---------|
   | `A <\|-- B` | Inheritance | B extends A |
   | `A <\|.. B` | Implementation | B implements A |
   | `A *-- B` | Composition | A owns B (B dies with A) |
   | `A o-- B` | Aggregation | A has B (B can exist alone) |
   | `A --> B` | Association | A uses B |
   | `A ..> B` | Dependency | A depends on B |
   | `A -- B` | Link | A related to B |

4. **Generics** — Use tilde: `List~T~`, `Map~K, V~` (NOT angle brackets `<T>`)
5. **Annotations** — Use `<<interface>>`, `<<abstract>>`, `<<enumeration>>`, `<<service>>`
6. **Cardinality** — Add to relationships: `A "1" --> "*" B`
7. **Namespace** — Group classes with `namespace`:
   ```
   namespace Domain {
       class Order
       class Product
   }
   ```

### Common Pitfalls and Anti-Patterns

| Pitfall | Problem | Fix |
|---------|---------|-----|
| Angle brackets for generics | `List<T>` breaks Mermaid | Use `List~T~` with tildes |
| Composition vs aggregation confusion | Wrong diamond type | Composition (filled `*`): part dies with whole. Aggregation (hollow `o`): part survives |
| Too many classes | >12 classes is unreadable | Split into domain-focused diagrams |
| Missing visibility | No `+`/`-` prefix | Always specify visibility for real designs |
| Enum as class | Using `class Status` for enums | Use `<<enumeration>>` annotation |
| Methods without return types | `+process()` | `+process() void` or `+process() Order` |
| Bidirectional arrows | `A <--> B` | Use two separate arrows with different labels |

### Complete Examples

#### Simple Hierarchy

```mermaid
classDiagram
    class Shape {
        <<abstract>>
        #double x
        #double y
        +area()* double
        +perimeter()* double
        +move(dx: double, dy: double) void
    }

    class Circle {
        -double radius
        +area() double
        +perimeter() double
        +getRadius() double
    }

    class Rectangle {
        -double width
        -double height
        +area() double
        +perimeter() double
    }

    class Square {
        +Square(side: double)
    }

    Shape <|-- Circle
    Shape <|-- Rectangle
    Rectangle <|-- Square
```

#### Domain Model

```mermaid
classDiagram
    class Order {
        -UUID id
        -DateTime createdAt
        -OrderStatus status
        -Money totalAmount
        +addItem(product: Product, qty: int) void
        +removeItem(itemId: UUID) void
        +calculateTotal() Money
        +submit() void
        +cancel() void
    }

    class OrderItem {
        -UUID id
        -int quantity
        -Money unitPrice
        +getSubtotal() Money
    }

    class Product {
        -UUID id
        -String name
        -String sku
        -Money price
        -int stockLevel
        +isAvailable() bool
        +reserve(qty: int) void
    }

    class Customer {
        -UUID id
        -String email
        -String name
        -Address shippingAddress
        +placeOrder(items: List~OrderItem~) Order
        +getOrderHistory() List~Order~
    }

    class Money {
        -BigDecimal amount
        -Currency currency
        +add(other: Money) Money
        +multiply(factor: int) Money
    }

    class OrderStatus {
        <<enumeration>>
        DRAFT
        SUBMITTED
        CONFIRMED
        SHIPPED
        DELIVERED
        CANCELLED
    }

    Customer "1" --> "*" Order : places
    Order "1" *-- "1..*" OrderItem : contains
    OrderItem "*" --> "1" Product : references
    Order --> OrderStatus : has
    Order --> Money : totalAmount
    OrderItem --> Money : unitPrice
    Product --> Money : price
```

#### Design Pattern — Observer

```mermaid
classDiagram
    class EventEmitter~T~ {
        <<interface>>
        +on(event: string, handler: Handler~T~) void
        +off(event: string, handler: Handler~T~) void
        +emit(event: string, data: T) void
    }

    class Handler~T~ {
        <<interface>>
        +handle(data: T) void
    }

    class OrderEventEmitter {
        -Map~string, List~Handler~OrderEvent~~~ handlers
        +on(event: string, handler: Handler~OrderEvent~) void
        +off(event: string, handler: Handler~OrderEvent~) void
        +emit(event: string, data: OrderEvent) void
    }

    class EmailNotifier {
        -EmailService emailService
        +handle(data: OrderEvent) void
    }

    class InventoryUpdater {
        -InventoryService inventory
        +handle(data: OrderEvent) void
    }

    class AnalyticsTracker {
        -AnalyticsClient client
        +handle(data: OrderEvent) void
    }

    EventEmitter~T~ <|.. OrderEventEmitter
    Handler~T~ <|.. EmailNotifier
    Handler~T~ <|.. InventoryUpdater
    Handler~T~ <|.. AnalyticsTracker
    OrderEventEmitter --> Handler~T~ : notifies
```

---

## ER Diagrams

### When to Use ER Diagrams

- Database schema documentation
- Data model design
- API response type relationships
- Domain entity mapping
- Migration planning

### Strict Syntax Rules

1. **Entity definition** with typed attributes:
   ```
   ENTITY_NAME {
       type attribute_name PK/FK/UK "comment"
   }
   ```
2. **Attribute key markers**:
   | Marker | Meaning |
   |--------|---------|
   | `PK` | Primary Key |
   | `FK` | Foreign Key |
   | `UK` | Unique Key |

3. **Crow's foot cardinality symbols**:
   | Symbol | Meaning |
   |--------|---------|
   | `\|\|` | Exactly one |
   | `o\|` | Zero or one |
   | `\|{` | One or more |
   | `o{` | Zero or more |

4. **Relationship lines**:
   | Style | Meaning |
   |-------|---------|
   | Solid (`--`) | Identifying relationship (child depends on parent) |
   | Dashed (`..`) | Non-identifying relationship (both can exist independently) |

5. **Relationship labels** — Always use quoted strings: `ENTITY_A \|\|--o{ ENTITY_B : "has many"`
6. **Entity names** — UPPER_SNAKE_CASE by convention

### How to Read Cardinality

Read from the entity outward toward the line:

```
CUSTOMER ||--o{ ORDER : "places"
```

- Left side (CUSTOMER): `||` = exactly one customer
- Right side (ORDER): `o{` = zero or more orders
- Reads: "One customer places zero or more orders"

**Critical:** `{` and `}` look directional but they always mean "many":
- `o{` on the right = zero-or-more
- `}o` on the left = zero-or-more

### Common Pitfalls and Anti-Patterns

| Pitfall | Problem | Fix |
|---------|---------|-----|
| Missing relationship label | Diagram won't render | Always add `: "label"` with quotes |
| `{`/`}` confusion | Getting cardinality backwards | `{` = many (right side), `}` = many (left side) |
| Methods on entities | ER is for data, not behavior | Only include data attributes |
| Missing PK/FK annotations | Schema is ambiguous | Always mark PK, FK, and UK |
| Attribute types don't match DB | Using `String` instead of `varchar` | Use actual DB types: `uuid`, `varchar`, `int`, `timestamp`, `text`, `jsonb` |
| Too many entities | >10 entities is unreadable | Split into domain-bounded diagrams |
| No FK for relationships | Relationship shown but FK missing | Add FK attribute matching the relationship |

### Complete Examples

#### 3-Entity Blog

```mermaid
erDiagram
    USER {
        uuid id PK
        varchar email UK
        varchar display_name
        varchar password_hash
        timestamp created_at
    }

    POST {
        uuid id PK
        uuid author_id FK
        varchar title
        text content
        varchar slug UK
        enum status
        timestamp published_at
        timestamp created_at
    }

    COMMENT {
        uuid id PK
        uuid post_id FK
        uuid author_id FK
        text body
        timestamp created_at
    }

    USER ||--o{ POST : "writes"
    USER ||--o{ COMMENT : "authors"
    POST ||--o{ COMMENT : "has"
```

#### E-Commerce Schema

```mermaid
erDiagram
    CUSTOMER {
        uuid id PK
        varchar email UK
        varchar name
        varchar phone
        timestamp created_at
    }

    ADDRESS {
        uuid id PK
        uuid customer_id FK
        varchar street
        varchar city
        varchar state
        varchar postal_code
        varchar country
        boolean is_default
    }

    ORDER {
        uuid id PK
        uuid customer_id FK
        uuid shipping_address_id FK
        decimal total_amount
        varchar currency
        enum status
        timestamp placed_at
    }

    ORDER_ITEM {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
        decimal unit_price
        decimal subtotal
    }

    PRODUCT {
        uuid id PK
        uuid category_id FK
        varchar name
        varchar sku UK
        text description
        decimal price
        int stock_level
        boolean is_active
    }

    CATEGORY {
        uuid id PK
        uuid parent_id FK
        varchar name
        varchar slug UK
        int sort_order
    }

    PAYMENT {
        uuid id PK
        uuid order_id FK
        varchar provider
        varchar provider_ref UK
        decimal amount
        varchar currency
        enum status
        timestamp processed_at
    }

    CUSTOMER ||--o{ ADDRESS : "has"
    CUSTOMER ||--o{ ORDER : "places"
    ORDER ||--|{ ORDER_ITEM : "contains"
    ORDER ||--o| PAYMENT : "paid via"
    ORDER }o--|| ADDRESS : "ships to"
    ORDER_ITEM }o--|| PRODUCT : "references"
    PRODUCT }o--|| CATEGORY : "belongs to"
    CATEGORY |o--o{ CATEGORY : "parent of"
```

#### Multi-Tenant SaaS

```mermaid
erDiagram
    TENANT {
        uuid id PK
        varchar name
        varchar slug UK
        varchar plan
        jsonb settings
        timestamp created_at
    }

    USER {
        uuid id PK
        uuid tenant_id FK
        varchar email UK
        varchar password_hash
        enum role
        boolean is_active
        timestamp last_login
    }

    API_KEY {
        uuid id PK
        uuid tenant_id FK
        uuid created_by FK
        varchar key_hash UK
        varchar name
        jsonb permissions
        timestamp expires_at
        timestamp created_at
    }

    WORKSPACE {
        uuid id PK
        uuid tenant_id FK
        varchar name
        text description
        timestamp created_at
    }

    WORKSPACE_MEMBER {
        uuid id PK
        uuid workspace_id FK
        uuid user_id FK
        enum role
        timestamp joined_at
    }

    AUDIT_LOG {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        varchar action
        varchar resource_type
        uuid resource_id
        jsonb metadata
        timestamp created_at
    }

    TENANT ||--|{ USER : "has"
    TENANT ||--o{ API_KEY : "owns"
    TENANT ||--|{ WORKSPACE : "contains"
    TENANT ||--o{ AUDIT_LOG : "logs"
    USER ||--o{ API_KEY : "creates"
    USER ||--o{ WORKSPACE_MEMBER : "belongs to"
    USER ||--o{ AUDIT_LOG : "performs"
    WORKSPACE ||--|{ WORKSPACE_MEMBER : "has"
```

---

## Gantt Charts

### When to Use Gantt Charts

- Project roadmaps and timelines
- Sprint planning visualization
- Release scheduling
- Dependency tracking between work items
- Milestone tracking

### Strict Syntax Rules

1. **Declaration** — Start with `gantt`
2. **Date format** — `dateFormat YYYY-MM-DD` (REQUIRED — always include)
3. **Axis format** — `axisFormat %Y-%m-%d` (optional, controls x-axis labels)
4. **Sections** — `section Section Name` (group tasks)
5. **Task syntax**:
   ```
   Task Name :status, id, start, duration
   Task Name :status, id, after dep_id, duration
   ```
   Where status is one of: `done`, `active`, `crit`, or omitted for default.
6. **Dependencies** — `after task_id` references a previous task's id
7. **Milestones** — `Milestone Name :milestone, id, after dep_id, 0d`
8. **Excludes** — `excludes weekends` or `excludes 2024-12-25`

### Task Status Markers

| Marker | Meaning | Visual |
|--------|---------|--------|
| `done` | Completed | Filled/dark |
| `active` | In progress | Highlighted |
| `crit` | Critical path | Red/emphasized |
| (none) | Future/planned | Default style |

### Common Pitfalls and Anti-Patterns

| Pitfall | Problem | Fix |
|---------|---------|-----|
| Missing `dateFormat` | Dates won't parse | Always include `dateFormat YYYY-MM-DD` |
| Commas in task names | Mermaid misparses the task | Avoid commas in names, or restructure |
| Circular dependencies | `a after b`, `b after a` | Review dependency chain for cycles |
| Non-zero milestone | `Milestone :milestone, m1, after t1, 5d` | Milestones must be `0d` |
| No task IDs | Can't reference dependencies | Always assign IDs: `:done, taskId, start, dur` |
| Overlapping sections | Tasks in wrong section visually | Ensure tasks are listed under correct `section` |
| Invalid date format | Using `MM/DD/YYYY` or `DD-MM-YYYY` | Match the declared `dateFormat` exactly |
| Missing `after` keyword | `task :t2, t1, 5d` (ambiguous) | Use `task :t2, after t1, 5d` explicitly |

### Complete Examples

#### Simple Project

```mermaid
gantt
    title Website Redesign
    dateFormat YYYY-MM-DD

    section Design
        Wireframes           :done, d1, 2024-03-01, 7d
        Mockups              :done, d2, after d1, 5d
        Design review        :done, d3, after d2, 2d

    section Development
        Frontend setup       :active, dev1, after d3, 3d
        Homepage             :dev2, after dev1, 5d
        Inner pages          :dev3, after dev2, 7d
        Responsive fixes     :dev4, after dev3, 3d

    section Testing
        QA testing           :t1, after dev4, 5d
        Bug fixes            :t2, after t1, 3d

    section Launch
        Launch               :milestone, launch, after t2, 0d
```

#### Multi-Section with Dependencies

```mermaid
gantt
    title Mobile App Development
    dateFormat YYYY-MM-DD
    excludes weekends

    section Backend
        API design           :done, api1, 2024-04-01, 5d
        Auth endpoints       :done, api2, after api1, 5d
        Core endpoints       :active, api3, after api2, 10d
        API documentation    :api4, after api3, 3d

    section Mobile - iOS
        Project setup        :ios1, after api2, 3d
        Auth screens         :ios2, after ios1, 5d
        Core features        :ios3, after api3, 10d
        Polish & animations  :ios4, after ios3, 5d

    section Mobile - Android
        Project setup        :and1, after api2, 3d
        Auth screens         :and2, after and1, 5d
        Core features        :and3, after api3, 10d
        Polish & animations  :and4, after and3, 5d

    section QA & Release
        iOS TestFlight       :crit, qa1, after ios4, 5d
        Android Beta         :crit, qa2, after and4, 5d
        Bug fixes            :qa3, after qa1, 5d
        App Store submission :milestone, release, after qa3, 0d
```

#### Sprint Roadmap

```mermaid
gantt
    title Q2 Sprint Roadmap
    dateFormat YYYY-MM-DD
    axisFormat %b %d

    section Sprint 7 (Apr 1-14)
        User auth refactor       :done, s7_1, 2024-04-01, 10d
        Password reset flow      :done, s7_2, 2024-04-01, 7d
        Auth tests               :done, s7_3, after s7_2, 3d
        Sprint 7 Review          :milestone, s7r, 2024-04-14, 0d

    section Sprint 8 (Apr 15-28)
        Dashboard redesign       :active, s8_1, 2024-04-15, 10d
        Chart components         :active, s8_2, 2024-04-15, 8d
        Dashboard API            :s8_3, after s8_2, 4d
        Sprint 8 Review          :milestone, s8r, 2024-04-28, 0d

    section Sprint 9 (Apr 29 - May 12)
        Notification system      :s9_1, 2024-04-29, 7d
        Email templates          :s9_2, after s9_1, 5d
        Push notifications       :s9_3, 2024-04-29, 10d
        Sprint 9 Review          :milestone, s9r, 2024-05-12, 0d

    section Milestones
        Q2 Feature Freeze        :milestone, ff, 2024-05-12, 0d
        Q2 Release               :milestone, rel, 2024-05-26, 0d
```

---

*This reference is part of the docs-with-mermaid Vista skill. For basic syntax, see [mermaid-reference.md](mermaid-reference.md). For practical examples, see [examples.md](examples.md).*
