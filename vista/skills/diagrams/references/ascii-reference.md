# ASCII Art Diagram Reference for AI Agents

## When to Use ASCII Art

- **Pinout diagrams** — chip/connector pin assignments
- **Timing diagrams** — signal waveforms, protocol timing
- **Connector tables** — cable wiring, interface mappings
- **Simple block diagrams** — when rendering in terminals, PRs, or plain-text contexts
- **Quick sketches** — when no rendering tool is needed

### Advantages
- Universal — works in any terminal, editor, or markdown renderer
- Zero dependencies — no rendering engine required
- Git-friendly — clean diffs
- Copy-paste ready — no conversion needed

### File Extension
Always use `.txt` for ASCII art diagram files.

---

## Box Drawing Characters

### Unicode Box Drawing (Recommended)

```
┌──────────┐    ┏━━━━━━━━━━┓    ╔══════════╗
│  Light   │    ┃   Bold   ┃    ║  Double  ║
│   Box    │    ┃   Box    ┃    ║   Box    ║
└──────────┘    ┗━━━━━━━━━━┛    ╚══════════╝
```

**Characters:**
- Light: `┌ ┐ └ ┘ │ ─ ├ ┤ ┬ ┴ ┼`
- Bold: `┏ ┓ ┗ ┛ ┃ ━ ┣ ┫ ┳ ┻ ╋`
- Double: `╔ ╗ ╚ ╝ ║ ═ ╠ ╣ ╦ ╩ ╬`

### ASCII-Only Fallback

```
+----------+    +----------+
|  Simple  |    |  Simple  |
|   Box    |--->|   Box    |
+----------+    +----------+
```

**Characters:** `+ - | /  \`

---

## Arrows and Connections

```
Horizontal:   ──────>    <──────    <─────>
              ━━━━━━>    -------->  ========>

Vertical:     │          ┃          |
              │          ┃          |
              ▼          ▼          v

Diagonal:     ╲          ╱
               ╲        ╱
                ╲      ╱

Connectors:   ──┐      ┌──
                │      │
                ▼      ▼

T-junctions:  ──┬──    ──┴──    ├──    ──┤
```

---

## Block Diagrams

### Simple Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────>│  API Server │────>│  Database   │
│             │<────│             │<────│             │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   Cache     │
                    │  (Redis)    │
                    └─────────────┘
```

### Layered Architecture

```
┌─────────────────────────────────────────┐
│              Presentation               │
│  ┌──────────┐  ┌──────────┐            │
│  │  Web UI  │  │ Mobile   │            │
│  └────┬─────┘  └────┬─────┘            │
└───────┼──────────────┼──────────────────┘
        │              │
┌───────┼──────────────┼──────────────────┐
│       ▼    Application Layer    ▼       │
│  ┌──────────┐  ┌──────────┐            │
│  │  Auth    │  │  Orders  │            │
│  └────┬─────┘  └────┬─────┘            │
└───────┼──────────────┼──────────────────┘
        │              │
┌───────┼──────────────┼──────────────────┐
│       ▼      Data Layer         ▼       │
│  ┌──────────┐  ┌──────────┐            │
│  │ Postgres │  │  Redis   │            │
│  └──────────┘  └──────────┘            │
└─────────────────────────────────────────┘
```

---

## Pinout Diagrams

### Chip/IC Pinout

```
                 ATmega328P
            ┌────────┬────────┐
  (RESET)  ─┤ 1  PC6 │ PC5 28 ├─  (SCL/A5)
     (RX)  ─┤ 2  PD0 │ PC4 27 ├─  (SDA/A4)
     (TX)  ─┤ 3  PD1 │ PC3 26 ├─  (A3)
    (INT0) ─┤ 4  PD2 │ PC2 25 ├─  (A2)
    (INT1) ─┤ 5  PD3 │ PC1 24 ├─  (A1)
      (D4) ─┤ 6  PD4 │ PC0 23 ├─  (A0)
      VCC  ─┤ 7      │     22 ├─  GND
      GND  ─┤ 8      │     21 ├─  AREF
   (XTAL1) ─┤ 9  PB6 │     20 ├─  AVCC
   (XTAL2) ─┤10  PB7 │ PB5 19 ├─  (SCK/D13)
      (D5) ─┤11  PD5 │ PB4 18 ├─  (MISO/D12)
      (D6) ─┤12  PD6 │ PB3 17 ├─  (MOSI/D11)
      (D7) ─┤13  PD7 │ PB2 16 ├─  (SS/D10)
      (D8) ─┤14  PB0 │ PB1 15 ├─  (D9)
            └─────────┴────────┘
```

### Connector Pinout

```
    DB-9 Serial (Male)
    ┌─────────────────┐
    │ 1   2   3   4   5 │
    │  6   7   8   9    │
    └───────────────────┘

    Pin  Signal   Dir   Description
    ───  ───────  ────  ───────────
     1   DCD      IN    Data Carrier Detect
     2   RXD      IN    Receive Data
     3   TXD      OUT   Transmit Data
     4   DTR      OUT   Data Terminal Ready
     5   GND      ---   Signal Ground
     6   DSR      IN    Data Set Ready
     7   RTS      OUT   Request to Send
     8   CTS      IN    Clear to Send
     9   RI       IN    Ring Indicator
```

---

## Timing Diagrams

### Digital Signal Timing

```
CLK     ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐
     ───┘  └──┘  └──┘  └──┘  └──┘  └──┘  └──

CS      ┌───────────────────────────┐
     ───┘                           └─────────

MOSI    ╳ D7 ╳ D6 ╳ D5 ╳ D4 ╳ D3 ╳ D2 ╳ D1 ╳
     ───╳────╳────╳────╳────╳────╳────╳────╳──

MISO         ╳ R7 ╳ R6 ╳ R5 ╳ R4 ╳ R3 ╳ R2 ╳
     ────────╳────╳────╳────╳────╳────╳────╳──
```

### Protocol Timing

```
     ┌──────┐     ┌──────┐     ┌──────┐
SDA  │ ADDR │     │ DATA │     │ ACK  │
     └──────┘     └──────┘     └──────┘
        ▲            ▲            ▲
        │            │            │
     ┌──┴──┐     ┌──┴──┐     ┌──┴──┐
SCL  │     │     │     │     │     │
     └─────┘     └─────┘     └─────┘

     |START|     |       |    |STOP |
     |     |     | DATA  |    |     |
     |<--->|     |<----->|    |<--->|
       t1          t2          t3
```

---

## Tables

### Wiring Table

```
┌──────────┬──────────┬──────────┬──────────┐
│  Source  │  Signal  │  Target  │  Color   │
├──────────┼──────────┼──────────┼──────────┤
│ MCU.PA0  │  SDA     │ OLED.SDA │  Blue    │
│ MCU.PA1  │  SCL     │ OLED.SCL │  Yellow  │
│ MCU.PA2  │  TX      │ GPS.RX   │  Green   │
│ MCU.PA3  │  RX      │ GPS.TX   │  White   │
│ PSU.5V   │  VCC     │ MCU.VIN  │  Red     │
│ PSU.GND  │  GND     │ MCU.GND  │  Black   │
└──────────┴──────────┴──────────┴──────────┘
```

### Register Map

```
Register: STATUS (0x01) - Read Only
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ Bit7│ Bit6│ Bit5│ Bit4│ Bit3│ Bit2│ Bit1│ Bit0│
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│BUSY │ ERR │ RDY │  -  │  -  │  -  │ OVF │ INT │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
  R     R     R    Rsvd  Rsvd  Rsvd   R     R
```

---

## Network/Tree Diagrams

### Tree Structure

```
                    ┌──────────┐
                    │  Router  │
                    └────┬─────┘
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌──────────┐ ┌──────┐ ┌──────────┐
        │ Switch A │ │ WiFi │ │ Switch B │
        └────┬─────┘ └──┬───┘ └────┬─────┘
         ┌───┴───┐    ┌─┴──┐    ┌──┴───┐
         ▼       ▼    ▼    ▼    ▼      ▼
       [PC1]  [PC2] [Ph1][Ph2] [SRV] [NAS]
```

### Flow with Decision

```
      ┌─────────┐
      │  Start  │
      └────┬────┘
           ▼
      ┌─────────┐
      │  Input  │
      └────┬────┘
           ▼
       ╱────────╲     Yes    ┌──────────┐
      ╱  Valid?   ╲────────>│  Process  │
      ╲           ╱          └────┬─────┘
       ╲────────╱                 │
           │ No                   ▼
           ▼                ┌──────────┐
      ┌─────────┐          │  Output  │
      │  Error  │          └────┬─────┘
      └────┬────┘               │
           │                    ▼
           └──────────>   ┌──────────┐
                          │   End    │
                          └──────────┘
```

---

## Best Practices

1. **Use monospace fonts** — ASCII art only aligns with fixed-width fonts
2. **Prefer Unicode box drawing** over ASCII `+|-` for cleaner appearance
3. **Keep lines short** — aim for 80 characters max width for terminal compatibility
4. **Use consistent spacing** — align boxes and text for readability
5. **Add legends** for non-obvious symbols
6. **Test in plain text** — paste into a terminal or `<pre>` block to verify alignment
7. **Use horizontal layouts** for sequential flows, vertical for hierarchies

## Quick Tips for AI Agents

1. **Pinouts**: Use the DIP package template — numbered pins on left/right with signal names
2. **Timing**: Use `┌──┐` for high, `└──┘` for low, `╳` for data transitions
3. **Tables**: Unicode box drawing (`┌┬┐├┼┤└┴┘`) for clean borders
4. **Block diagrams**: Keep it simple — boxes with arrows, max 6-8 elements
5. **Always wrap in code blocks** (triple backticks) in markdown to preserve alignment
