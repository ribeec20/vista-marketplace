# PlantUML Reference for AI Agents

## When to Use PlantUML

### Advantages Over Mermaid
- **Network topology diagrams** (nwdiag) - superior for multi-interface devices, VLANs, and physical network layouts
- **Component diagrams** - better interface notation (lollipop/socket), ports, and hardware modeling
- **Deployment diagrams** - richer node and artifact representation
- **Wireframes** - salt syntax for UI mockups
- **Standard library** - built-in AWS, Azure, GCP icons
- **Advanced styling** - CSS-style themes and skinparam customization

### Best Use Cases
- Network architecture with multiple subnets and interfaces
- Hardware/IoT system architecture (sensors, microcontrollers, interfaces)
- Server rack and physical deployment layouts
- Component interactions with explicit interface contracts
- UI wireframes and mockups

---

## Network Diagrams (nwdiag)

### Basic Syntax
```plantuml
@startuml
nwdiag {
  network dmz {
    address = "10.0.1.0/24"

    web01 [address = "10.0.1.10"];
    web02 [address = "10.0.1.11"];
  }

  network internal {
    address = "192.168.1.0/24"

    web01 [address = "192.168.1.10"];
    db01 [address = "192.168.1.20"];
  }
}
@enduml
```

### Multi-Interface Devices
Devices appearing in multiple networks automatically get multiple interfaces:

```plantuml
@startuml
nwdiag {
  network wan {
    address = "203.0.113.0/24"
    firewall [address = "203.0.113.1"];
  }

  network dmz {
    address = "10.0.1.0/24"
    firewall [address = "10.0.1.1"];
    webserver [address = "10.0.1.10"];
  }

  network lan {
    address = "192.168.0.0/24"
    firewall [address = "192.168.0.1"];
    fileserver [address = "192.168.0.10"];
    workstation [address = "192.168.0.100"];
  }
}
@enduml
```

### VLAN Grouping
Use `group` to visually separate VLANs or logical segments:

```plantuml
@startuml
nwdiag {
  network switch {
    switch [shape = box];

    group {
      color = "#FFE0E0";
      description = "VLAN 10 - Management";
      mgmt01;
      mgmt02;
    }

    group {
      color = "#E0E0FF";
      description = "VLAN 20 - Production";
      prod01;
      prod02;
    }
  }
}
@enduml
```

### Network Properties
```plantuml
@startuml
nwdiag {
  network datacenter {
    address = "10.10.0.0/16"
    color = "#lightblue"
    description = "Primary Datacenter"

    server01 [address = "10.10.1.10", description = "Web Server"];
    server02 [address = "10.10.1.11", shape = database];
  }
}
@enduml
```

**Available shapes**: `box`, `cloud`, `database`, `actor`, `node`, `folder`, `frame`, `storage`, `component`

---

## Component Diagrams

### Interface Notation
```plantuml
@startuml
interface HTTP
interface Database

[WebServer] --> HTTP : provides
[Browser] ..> HTTP : uses
[WebServer] ..> Database : uses
[MySQL] --> Database : provides
@enduml
```

**Lollipop (provided) vs Socket (required)**:
- `-->` from component = provides interface (lollipop)
- `..>` to interface = requires/uses interface (socket)

### Ports and Nested Components
```plantuml
@startuml
package "IoT Gateway" {
  [MQTT Broker]
  [HTTP API]

  database "Time Series DB" {
    [InfluxDB]
  }
}

[Sensor Network] --> [MQTT Broker] : publish
[MQTT Broker] --> [InfluxDB] : store
[HTTP API] --> [InfluxDB] : query
[Dashboard] ..> [HTTP API] : REST
@enduml
```

### Hardware/IoT Example
```plantuml
@startuml
skinparam componentStyle rectangle

component "ESP32 Module" {
  port WiFi
  port GPIO_1
  port GPIO_2
  port I2C
  port SPI

  [Main Controller]
}

component "BME280 Sensor" {
  port I2C_interface
}

component "SD Card Module" {
  port SPI_interface
}

GPIO_1 --> [LED]
GPIO_2 --> [Button]
I2C --> I2C_interface : temperature/humidity
SPI --> SPI_interface : data logging
WiFi --> [MQTT Broker] : telemetry
@enduml
```

### Stereotypes
```plantuml
@startuml
component [Application] <<service>>
component [Logger] <<utility>>
database [PostgreSQL] <<database>>
component [Cache] <<Redis>>

[Application] ..> [Logger]
[Application] --> [PostgreSQL]
[Application] --> [Cache]
@enduml
```

---

## Deployment Diagrams

### Basic Node Structure
```plantuml
@startuml
node "Web Server" {
  artifact "nginx.conf"
  component [Nginx]
}

node "App Server" {
  artifact "app.jar"
  component [Spring Boot]
}

node "Database Server" {
  database [PostgreSQL]
}

[Nginx] --> [Spring Boot] : proxy
[Spring Boot] --> [PostgreSQL] : jdbc
@enduml
```

### Nested Nodes (Server Rack Example)
```plantuml
@startuml
node "Rack 1" {
  node "1U - Firewall" {
    component [pfSense]
  }

  node "2U - Core Switch" {
    component [Switch] <<Cisco>>
  }

  node "3U - Server 1" {
    artifact "hypervisor"
    component [ESXi]

    node "VM1" {
      component [Web]
    }
    node "VM2" {
      component [App]
    }
  }

  node "4U - Server 2" {
    database [PostgreSQL]
    database [Redis]
  }
}
@enduml
```

### Cloud Deployment
```plantuml
@startuml
cloud "AWS" {
  node "VPC 10.0.0.0/16" {
    node "Public Subnet" {
      component [Load Balancer] <<ELB>>
    }

    node "Private Subnet" {
      node "Auto Scaling Group" {
        component [Web1]
        component [Web2]
        component [Web3]
      }
    }

    node "Database Subnet" {
      database [RDS] <<PostgreSQL>>
    }
  }
}

[Load Balancer] --> [Web1]
[Load Balancer] --> [Web2]
[Load Balancer] --> [Web3]
[Web1] --> [RDS]
[Web2] --> [RDS]
[Web3] --> [RDS]
@enduml
```

---

## Arrow Types Reference

| Syntax | Description | Visual |
|--------|-------------|--------|
| `-->` | Solid arrow | ──────> |
| `..>` | Dotted arrow | ┈┈┈┈┈> |
| `--` | Solid line (no arrow) | ────── |
| `..` | Dotted line (no arrow) | ┈┈┈┈┈┈ |
| `<-->` | Bidirectional solid | <────> |
| `<..>` | Bidirectional dotted | <┈┈┈> |
| `-down->` | Force direction | ↓ |
| `-up->` | Force direction | ↑ |
| `-left->` | Force direction | ← |
| `-right->` | Force direction | → |
| `-[bold]->` | Bold arrow | ━━━━━> |
| `-[dashed]->` | Dashed arrow | ─ ─ ─> |
| `-[dotted]->` | Dotted arrow | ┈┈┈┈┈> |
| `-[hidden]->` | Invisible (spacing) | (none) |
| `-[#red]->` | Colored arrow | (red) |
| `-[thickness=4]->` | Thick arrow | ━━━━━> |

### Arrow with Labels
```plantuml
@startuml
[Client] --> [Server] : HTTP GET
[Server] ..> [Database] : query
[Database] --> [Server] : result set
[Server] --> [Client] : JSON response
@enduml
```

---

## Styling

### Modern CSS-Style (Recommended)
```plantuml
@startuml
<style>
node {
  BackgroundColor lightblue
  BorderColor navy
  FontSize 14
  FontColor darkblue
}

component {
  BackgroundColor lightyellow
  BorderColor orange
  RoundCorner 15
}

database {
  BackgroundColor lightgreen
  BorderColor darkgreen
}
</style>

node "Server" {
  component [App]
  database [DB]
}
@enduml
```

### Legacy skinparam
```plantuml
@startuml
skinparam node {
  BackgroundColor lightblue
  BorderColor navy
  FontSize 14
}

skinparam component {
  BackgroundColor lightyellow
  BorderColor orange
  Style rectangle
}

skinparam database {
  BackgroundColor lightgreen
  BorderColor darkgreen
}

node "Server" {
  component [App]
  database [DB]
}
@enduml
```

### Common skinparam Options
```plantuml
@startuml
skinparam monochrome true
skinparam shadowing false
skinparam defaultFontName Arial
skinparam defaultFontSize 12
skinparam backgroundColor white
skinparam ArrowColor black
@enduml
```

---

## Standard Library (Icons)

### AWS Icons
```plantuml
@startuml
!include <awslib/AWSCommon>
!include <awslib/Compute/EC2>
!include <awslib/Database/RDS>
!include <awslib/Storage/S3>
!include <awslib/NetworkingContentDelivery/ELB>

ELB(lb, "Load Balancer", "Application LB")
EC2(web1, "Web Server 1", "t3.medium")
EC2(web2, "Web Server 2", "t3.medium")
RDS(db, "Database", "PostgreSQL")
S3(storage, "Static Assets", "S3 Bucket")

lb --> web1
lb --> web2
web1 --> db
web2 --> db
web1 --> storage
web2 --> storage
@enduml
```

### Azure Icons
```plantuml
@startuml
!include <azure/AzureCommon>
!include <azure/Compute/AzureVirtualMachine>
!include <azure/Databases/AzureSqlDatabase>
!include <azure/Networking/AzureLoadBalancer>

AzureLoadBalancer(lb, "Load Balancer", "Standard")
AzureVirtualMachine(vm1, "Web VM 1", "D2s_v3")
AzureVirtualMachine(vm2, "Web VM 2", "D2s_v3")
AzureSqlDatabase(db, "SQL Database", "S1")

lb --> vm1
lb --> vm2
vm1 --> db
vm2 --> db
@enduml
```

---

## Rendering Methods

### 1. CLI (Local Java)
```bash
# Install PlantUML
wget https://github.com/plantuml/plantuml/releases/download/v1.2024.0/plantuml-1.2024.0.jar

# Render diagram
java -jar plantuml.jar diagram.puml

# Specify output format
java -jar plantuml.jar -tsvg diagram.puml
java -jar plantuml.jar -tpng diagram.puml
java -jar plantuml.jar -tpdf diagram.puml
```

### 2. Docker Server
```bash
# Run PlantUML server
docker run -d -p 8080:8080 plantuml/plantuml-server:jetty

# Access at http://localhost:8080
```

### 3. Public HTTP API
**Encode and render via URL**:

Base URL: `https://www.plantuml.com/plantuml/svg/`

```python
import zlib
import base64

def encode_plantuml(source):
    """Encode PlantUML source for URL"""
    compressed = zlib.compress(source.encode('utf-8'))[2:-4]
    return base64.urlsafe_b64encode(compressed).decode('ascii')

source = """
@startuml
Alice -> Bob: Hello
@enduml
"""

encoded = encode_plantuml(source)
url = f"https://www.plantuml.com/plantuml/svg/{encoded}"
print(url)
```

**Direct POST** (if server supports):
```bash
curl -X POST --data-binary @diagram.puml https://www.plantuml.com/plantuml/svg/ > output.svg
```

### 4. Output Formats
- **SVG** (`-tsvg`) - scalable, recommended for web
- **PNG** (`-tpng`) - raster, good for documents
- **PDF** (`-tpdf`) - print-ready
- **LaTeX** (`-tlatex`) - integration with TeX
- **ASCII Art** (`-ttxt`) - terminal-friendly

---

## Rack Diagrams (Limitation & Workaround)

### No Native Rack Support
PlantUML does **not** have dedicated rack diagram syntax (unlike specialized tools like rackdiag). However, you can approximate rack layouts using deployment diagrams.

### Workaround: Deployment Diagram
```plantuml
@startuml
skinparam node {
  BackgroundColor lightgray
  BorderColor black
}

node "Server Rack - 42U" {
  node "01U - PDU" {
    component [Power Distribution]
  }

  node "02U - Patch Panel" {
    component [24-Port Cat6]
  }

  node "03U - Core Switch" {
    component [Cisco 48-Port] <<switch>>
  }

  node "04U - Firewall" {
    component [pfSense] <<security>>
  }

  node "05-06U - Storage" {
    database [NetApp FAS] <<2U>>
  }

  node "07-08U - Server 1" {
    component [Dell R740] <<2U>>
    artifact "ESXi 7.0"
  }

  node "09-10U - Server 2" {
    component [Dell R740] <<2U>>
    artifact "ESXi 7.0"
  }

  node "11-14U - UPS" {
    component [APC Smart-UPS] <<4U>>
  }
}
@enduml
```

**Tip**: For true rack diagrams with U-measurements and rear/front views, use specialized tools or consider generating ASCII-art representations.

---

## Practical Examples

### Example 1: Multi-VLAN Network Topology
```plantuml
@startuml
nwdiag {
  network internet {
    internet [shape = cloud];
    firewall [address = "203.0.113.1"];
  }

  network dmz {
    address = "10.0.1.0/24"
    color = "#FFE0E0"

    firewall [address = "10.0.1.1"];
    webserver [address = "10.0.1.10"];
    mailserver [address = "10.0.1.20"];
  }

  network internal {
    address = "192.168.0.0/16"

    firewall [address = "192.168.0.1"];

    group {
      color = "#E0E0FF";
      description = "VLAN 10 - Management";
      mgmt_server [address = "192.168.10.5"];
      monitoring [address = "192.168.10.10"];
    }

    group {
      color = "#E0FFE0";
      description = "VLAN 20 - Production";
      appserver1 [address = "192.168.20.10"];
      appserver2 [address = "192.168.20.11"];
      dbserver [address = "192.168.20.20", shape = database];
    }

    group {
      color = "#FFFFE0";
      description = "VLAN 30 - Guest WiFi";
      wireless_ap [address = "192.168.30.1"];
    }
  }
}
@enduml
```

### Example 2: IoT Device Architecture
```plantuml
@startuml
skinparam componentStyle rectangle

package "Edge Device - ESP32" {
  component "Main MCU" {
    port WiFi
    port GPIO
    port I2C
    port SPI
    port UART
  }

  component [BME280] <<I2C Sensor>> {
    port I2C_bus
  }

  component [SD Card] <<SPI Storage>> {
    port SPI_bus
  }

  component [GPS Module] <<UART>> {
    port UART_bus
  }

  I2C --> I2C_bus : temp/humidity/pressure
  SPI --> SPI_bus : data logging
  UART --> UART_bus : location
  GPIO --> [LED Indicator]
  GPIO --> [Reset Button]
}

cloud "AWS IoT Core" {
  component [MQTT Broker]
  component [IoT Rules Engine]
  database [DynamoDB]
  component [Lambda]
}

WiFi --> [MQTT Broker] : TLS 1.2
[MQTT Broker] --> [IoT Rules Engine]
[IoT Rules Engine] --> [DynamoDB] : store
[IoT Rules Engine] --> [Lambda] : trigger
@enduml
```

### Example 3: Microcontroller Pinout
```plantuml
@startuml
skinparam componentStyle rectangle

component "Arduino Mega 2560" {
  port "D0 (RX0)" as d0
  port "D1 (TX0)" as d1
  port "D2 (INT0)" as d2
  port "D3 (PWM)" as d3
  port "D13 (LED)" as d13
  port "A0 (ADC)" as a0
  port "A1 (ADC)" as a1
  port "SDA (20)" as sda
  port "SCL (21)" as scl
  port "5V" as v5
  port "GND" as gnd

  [ATmega2560]
}

component [LCD Display] {
  port SDA_lcd
  port SCL_lcd
  port VCC
  port GND_lcd
}

component [Ultrasonic Sensor] {
  port TRIG
  port ECHO
  port VCC_us
  port GND_us
}

component [Servo Motor] {
  port SIGNAL
  port VCC_servo
  port GND_servo
}

sda --> SDA_lcd
scl --> SCL_lcd
v5 --> VCC
gnd --> GND_lcd

d2 --> TRIG
d3 --> ECHO
v5 --> VCC_us
gnd --> GND_us

d13 --> SIGNAL
v5 --> VCC_servo
gnd --> GND_servo
@enduml
```

### Example 4: Data Center Deployment
```plantuml
@startuml
node "Data Center A" {
  node "DMZ Zone" {
    component [Load Balancer 1] <<F5>>
    component [Load Balancer 2] <<F5>>
  }

  node "Web Tier" {
    component [Web1]
    component [Web2]
    component [Web3]
  }

  node "App Tier" {
    component [App1]
    component [App2]
  }

  node "Data Tier" {
    database [Primary DB] <<PostgreSQL>>
    database [Replica DB] <<PostgreSQL>>
    database [Cache] <<Redis>>
  }
}

node "Data Center B (DR)" {
  database [Standby DB] <<PostgreSQL>>
}

[Load Balancer 1] --> [Web1]
[Load Balancer 1] --> [Web2]
[Load Balancer 2] --> [Web2]
[Load Balancer 2] --> [Web3]

[Web1] --> [App1]
[Web2] --> [App1]
[Web2] --> [App2]
[Web3] --> [App2]

[App1] --> [Primary DB]
[App1] --> [Cache]
[App2] --> [Primary DB]
[App2] --> [Cache]

[Primary DB] ..> [Replica DB] : streaming replication
[Primary DB] ..> [Standby DB] : async replication
@enduml
```

---

## Quick Tips for AI Agents

1. **Network diagrams**: Always use `nwdiag` for multi-subnet topologies
2. **Hardware/IoT**: Component diagrams with ports are ideal
3. **Server racks**: Use nested deployment nodes with U-height in descriptions
4. **Interfaces**: Use `-->` for "provides", `..>` for "requires"
5. **Styling**: Prefer `<style>` blocks over `skinparam` for modern diagrams
6. **Icons**: Include AWS/Azure libraries when cloud architecture is involved
7. **File extension**: Always use `.puml` for PlantUML files
8. **Rendering**: Public API is fastest for one-off renders; local CLI for batch processing

