# Excalidraw Reference for AI Agents

## When to Use Excalidraw

Excalidraw excels at:
- **Freeform spatial diagrams** where precise positioning matters (PCB layouts, hardware schematics)
- **Hand-drawn aesthetic** for brainstorming, whiteboarding, or informal documentation
- **Complex connectivity** - elements can have multiple simultaneous connections (unlike Mermaid's tree-based layouts)
- **Hardware and physical layouts** - circuit boards, rack diagrams, floor plans
- **Network topologies** with custom positioning
- **Mixed element types** - combine shapes, arrows, freehand drawing, and images

**Advantages over Mermaid:**
- Precise X/Y coordinate control
- Multiple arrows to/from same element
- Freehand drawing capability
- Image embedding
- Grouping and frames
- More visual flexibility

**When NOT to use Excalidraw:**
- Simple flowcharts (use Mermaid flowchart)
- Sequence diagrams (use Mermaid sequence)
- Auto-layout sufficient (Mermaid handles this better)
- Text-heavy documentation (Mermaid is more readable as text)

## File Format

Excalidraw files are JSON with this top-level structure:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [...],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

**Required fields:**
- `type`: Always `"excalidraw"`
- `version`: Always `2`
- `source`: Usually `"https://excalidraw.com"`
- `elements`: Array of shape/arrow/text objects
- `appState`: Minimal: `{"gridSize": 20, "viewBackgroundColor": "#ffffff"}`
- `files`: Object for embedded images (can be `{}`)

## Element Types

All elements share common properties, but each type has specific requirements:

### Rectangle
```json
{
  "type": "rectangle",
  "id": "abc123def456ghi789012",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 100,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#a5d8ff",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null
}
```

### Diamond
```json
{
  "type": "diamond",
  "id": "xyz789abc123def456789",
  "x": 400,
  "y": 100,
  "width": 150,
  "height": 150,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#ffec99",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null
}
```

### Ellipse
```json
{
  "type": "ellipse",
  "id": "circle123456789012345",
  "x": 700,
  "y": 100,
  "width": 120,
  "height": 120,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#b2f2bb",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null
}
```

### Arrow
```json
{
  "type": "arrow",
  "id": "arrow123456789012345",
  "x": 300,
  "y": 150,
  "width": 100,
  "height": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null,
  "points": [[0, 0], [100, 0]],
  "lastCommittedPoint": null,
  "startBinding": {
    "elementId": "source-element-id",
    "focus": 0,
    "gap": 8
  },
  "endBinding": {
    "elementId": "target-element-id",
    "focus": 0,
    "gap": 8
  },
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```

### Text (Standalone)
```json
{
  "type": "text",
  "id": "text123456789012345",
  "x": 150,
  "y": 130,
  "width": 100,
  "height": 25,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 0,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null,
  "text": "Label",
  "fontSize": 20,
  "fontFamily": 1,
  "textAlign": "center",
  "verticalAlign": "middle",
  "baseline": 18,
  "containerId": null,
  "originalText": "Label",
  "lineHeight": 1.25
}
```

### Line (Multi-point)
```json
{
  "type": "line",
  "id": "line123456789012345",
  "x": 100,
  "y": 300,
  "width": 200,
  "height": 100,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null,
  "points": [[0, 0], [100, 50], [200, 100]],
  "lastCommittedPoint": null,
  "startBinding": null,
  "endBinding": null,
  "startArrowhead": null,
  "endArrowhead": null
}
```

### Freedraw
```json
{
  "type": "freedraw",
  "id": "freedraw12345678901234",
  "x": 500,
  "y": 500,
  "width": 150,
  "height": 80,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 0,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null,
  "points": [[0, 0], [10, 15], [25, 30], [50, 40], [80, 45], [120, 50], [150, 80]],
  "pressures": [],
  "simulatePressure": true,
  "lastCommittedPoint": null
}
```

### Frame (Container)
```json
{
  "type": "frame",
  "id": "frame123456789012345",
  "x": 0,
  "y": 0,
  "width": 800,
  "height": 600,
  "strokeColor": "transparent",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 0,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null,
  "name": "Diagram Frame"
}
```

## Common Properties

All elements must have these properties:

| Property | Type | Description | Common Values |
|----------|------|-------------|---------------|
| `type` | string | Element type | `rectangle`, `diamond`, `ellipse`, `arrow`, `line`, `text`, `freedraw`, `frame`, `image` |
| `id` | string | Unique ID (nanoid, 21 chars) | `"abc123def456ghi789012"` |
| `x` | number | Left position (pixels) | `100`, `250.5` |
| `y` | number | Top position (pixels) | `100`, `320.75` |
| `width` | number | Width (pixels) | `200`, `150` |
| `height` | number | Height (pixels) | `100`, `80` |
| `strokeColor` | string | Border color (hex) | `"#1e1e1e"`, `"#e03131"` |
| `backgroundColor` | string | Fill color (hex or transparent) | `"#a5d8ff"`, `"transparent"` |
| `fillStyle` | string | Fill pattern | `"solid"`, `"hachure"`, `"cross-hatch"` |
| `strokeWidth` | number | Border thickness | `1`, `2`, `4` |
| `strokeStyle` | string | Border style | `"solid"`, `"dashed"`, `"dotted"` |
| `roughness` | number | Hand-drawn effect | `0` (smooth), `1` (normal), `2` (rough) |
| `opacity` | number | Transparency | `100` (opaque), `50` (half), `0` (invisible) |
| `groupIds` | array | Groups this belongs to | `[]`, `["group-id-1"]` |
| `boundElements` | array | Connected elements | See Arrow Binding section |
| `locked` | boolean | Prevent editing | `false`, `true` |
| `link` | string/null | Hyperlink | `null`, `"https://example.com"` |

## Arrow Binding

Arrows connect elements via `startBinding` and `endBinding`. **Critical:** You must update BOTH the arrow and the target elements.

### Complete Arrow Example

```json
{
  "elements": [
    {
      "type": "rectangle",
      "id": "box-A-id-123456789012",
      "x": 100,
      "y": 100,
      "width": 150,
      "height": 80,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#a5d8ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "arrow-id-567890123456",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "rectangle",
      "id": "box-B-id-789012345678",
      "x": 400,
      "y": 100,
      "width": 150,
      "height": 80,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#b2f2bb",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "arrow-id-567890123456",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "arrow",
      "id": "arrow-id-567890123456",
      "x": 250,
      "y": 140,
      "width": 150,
      "height": 0,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "points": [[0, 0], [150, 0]],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "box-A-id-123456789012",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "box-B-id-789012345678",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    }
  ]
}
```

### Binding Properties

- `elementId`: ID of the connected element
- `focus`: Vertical offset from center (-1 to 1, usually 0)
- `gap`: Distance from element edge (pixels, usually 8)

### Arrow Points Array

- First point MUST be `[0, 0]`
- Subsequent points are relative to arrow's `(x, y)`
- For horizontal arrow: `[[0, 0], [width, 0]]`
- For vertical arrow: `[[0, 0], [0, height]]`
- For diagonal: `[[0, 0], [dx, dy]]`

### Arrowhead Types

- `null`: No arrowhead
- `"arrow"`: Standard arrow
- `"bar"`: Line cap
- `"dot"`: Circle cap

## Text Binding

Text can be bound inside a container (rectangle, diamond, ellipse):

```json
{
  "elements": [
    {
      "type": "rectangle",
      "id": "container-id-1234567",
      "x": 100,
      "y": 100,
      "width": 200,
      "height": 100,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#a5d8ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-id-7890123456",
          "type": "text"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-id-7890123456",
      "x": 150,
      "y": 137.5,
      "width": 100,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "Server",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "container-id-1234567",
      "originalText": "Server",
      "lineHeight": 1.25
    }
  ]
}
```

**Key points:**
- Text element sets `containerId` to the container's ID
- Container adds text to its `boundElements` array
- Text position should be centered in container
- Text `verticalAlign` should be `"middle"`
- Text `textAlign` should be `"center"`

## Styling

### Fill Styles
- `"solid"`: Solid color fill
- `"hachure"`: Diagonal line pattern
- `"cross-hatch"`: Crossed line pattern

### Stroke Styles
- `"solid"`: Solid line
- `"dashed"`: Dashed line
- `"dotted"`: Dotted line

### Font Families
- `1`: Virgil (hand-drawn)
- `2`: Helvetica (clean, sans-serif)
- `3`: Cascadia (monospace)

### Common Colors (Hex)
- Black: `#1e1e1e`
- Blue: `#a5d8ff`
- Green: `#b2f2bb`
- Red: `#ffc9c9`
- Yellow: `#ffec99`
- Orange: `#ffd8a8`
- Purple: `#e5dbff`
- Gray: `#e9ecef`
- Transparent: `"transparent"`

### Font Sizes
Common: `16`, `20`, `24`, `28`, `36`

## Coordinate System

- **Origin**: Top-left corner at `(0, 0)`
- **X-axis**: Increases to the right
- **Y-axis**: Increases downward
- **Units**: Pixels
- **Decimals**: Allowed (e.g., `150.5`, `200.75`)

### Positioning Strategy

1. **Start from top-left** - First element near `(100, 100)`
2. **Horizontal spacing** - Add `width + 100` for next element
3. **Vertical spacing** - Add `height + 80` for rows
4. **Center alignment** - Calculate: `parentX + (parentWidth - childWidth) / 2`

## ID Generation

IDs use the **nanoid** format:
- **Length**: Exactly 21 characters
- **Character set**: `A-Za-z0-9_-` (URL-safe Base64)
- **Example**: `"abc123_DEF-456ghi789"`

### Simple ID Generator (Pseudocode)
```python
import random
import string

def generate_id():
    chars = string.ascii_letters + string.digits + '_-'
    return ''.join(random.choices(chars, k=21))
```

**Important**: Each element must have a unique ID. Never reuse IDs.

## Practical Examples

### Example 1: Simple Box with Text

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "type": "rectangle",
      "id": "rect-simple-123456789",
      "x": 100,
      "y": 100,
      "width": 200,
      "height": 100,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#a5d8ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-simple-987654321",
          "type": "text"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-simple-987654321",
      "x": 150,
      "y": 137.5,
      "width": 100,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "Server",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "rect-simple-123456789",
      "originalText": "Server",
      "lineHeight": 1.25
    }
  ],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

### Example 2: Two Boxes Connected by Arrow

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "type": "rectangle",
      "id": "box-client-1234567890",
      "x": 100,
      "y": 100,
      "width": 150,
      "height": 80,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#a5d8ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-client-0987654321",
          "type": "text"
        },
        {
          "id": "arrow-conn-5555555555",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-client-0987654321",
      "x": 125,
      "y": 127.5,
      "width": 100,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "Client",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "box-client-1234567890",
      "originalText": "Client",
      "lineHeight": 1.25
    },
    {
      "type": "rectangle",
      "id": "box-server-9876543210",
      "x": 400,
      "y": 100,
      "width": 150,
      "height": 80,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#b2f2bb",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-server-1231231231",
          "type": "text"
        },
        {
          "id": "arrow-conn-5555555555",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-server-1231231231",
      "x": 425,
      "y": 127.5,
      "width": 100,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "Server",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "box-server-9876543210",
      "originalText": "Server",
      "lineHeight": 1.25
    },
    {
      "type": "arrow",
      "id": "arrow-conn-5555555555",
      "x": 250,
      "y": 140,
      "width": 150,
      "height": 0,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "points": [[0, 0], [150, 0]],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "box-client-1234567890",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "box-server-9876543210",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    }
  ],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

### Example 3: Network Topology (Router + 3 Devices)

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "type": "diamond",
      "id": "router-center-diamond1",
      "x": 300,
      "y": 200,
      "width": 120,
      "height": 120,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#ffec99",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-router-label-txt1",
          "type": "text"
        },
        {
          "id": "arrow-to-pc1-arr1",
          "type": "arrow"
        },
        {
          "id": "arrow-to-pc2-arr2",
          "type": "arrow"
        },
        {
          "id": "arrow-to-pc3-arr3",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-router-label-txt1",
      "x": 330,
      "y": 247.5,
      "width": 60,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "Router",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "router-center-diamond1",
      "originalText": "Router",
      "lineHeight": 1.25
    },
    {
      "type": "rectangle",
      "id": "pc1-top-rectangle-pc1",
      "x": 280,
      "y": 50,
      "width": 160,
      "height": 80,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#a5d8ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-pc1-label-txt2",
          "type": "text"
        },
        {
          "id": "arrow-to-pc1-arr1",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-pc1-label-txt2",
      "x": 320,
      "y": 77.5,
      "width": 80,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "PC 1",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "pc1-top-rectangle-pc1",
      "originalText": "PC 1",
      "lineHeight": 1.25
    },
    {
      "type": "arrow",
      "id": "arrow-to-pc1-arr1",
      "x": 360,
      "y": 130,
      "width": 0,
      "height": 70,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "points": [[0, 0], [0, 70]],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "pc1-top-rectangle-pc1",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "router-center-diamond1",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "type": "rectangle",
      "id": "pc2-left-rectangle-pc2",
      "x": 50,
      "y": 220,
      "width": 160,
      "height": 80,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#b2f2bb",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-pc2-label-txt3",
          "type": "text"
        },
        {
          "id": "arrow-to-pc2-arr2",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-pc2-label-txt3",
      "x": 90,
      "y": 247.5,
      "width": 80,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "PC 2",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "pc2-left-rectangle-pc2",
      "originalText": "PC 2",
      "lineHeight": 1.25
    },
    {
      "type": "arrow",
      "id": "arrow-to-pc2-arr2",
      "x": 210,
      "y": 260,
      "width": 90,
      "height": 0,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "points": [[0, 0], [90, 0]],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "pc2-left-rectangle-pc2",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "router-center-diamond1",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "type": "rectangle",
      "id": "pc3-right-rectangle-pc3",
      "x": 510,
      "y": 220,
      "width": 160,
      "height": 80,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#ffc9c9",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-pc3-label-txt4",
          "type": "text"
        },
        {
          "id": "arrow-to-pc3-arr3",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-pc3-label-txt4",
      "x": 550,
      "y": 247.5,
      "width": 80,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "PC 3",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "pc3-right-rectangle-pc3",
      "originalText": "PC 3",
      "lineHeight": 1.25
    },
    {
      "type": "arrow",
      "id": "arrow-to-pc3-arr3",
      "x": 420,
      "y": 260,
      "width": 90,
      "height": 0,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "points": [[0, 0], [90, 0]],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "router-center-diamond1",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "pc3-right-rectangle-pc3",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    }
  ],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

### Example 4: Hardware Block Diagram (CPU/RAM/Storage)

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "type": "rectangle",
      "id": "cpu-block-hw-cpu-001",
      "x": 100,
      "y": 100,
      "width": 200,
      "height": 120,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#ffd8a8",
      "fillStyle": "hachure",
      "strokeWidth": 3,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-cpu-hw-cpu-txt",
          "type": "text"
        },
        {
          "id": "arrow-cpu-ram-hw-ar1",
          "type": "arrow"
        },
        {
          "id": "arrow-cpu-stor-hw-ar2",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-cpu-hw-cpu-txt",
      "x": 165,
      "y": 147.5,
      "width": 70,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "CPU",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "cpu-block-hw-cpu-001",
      "originalText": "CPU",
      "lineHeight": 1.25
    },
    {
      "type": "rectangle",
      "id": "ram-block-hw-ram-002",
      "x": 100,
      "y": 280,
      "width": 200,
      "height": 100,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#a5d8ff",
      "fillStyle": "hachure",
      "strokeWidth": 3,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-ram-hw-ram-txt",
          "type": "text"
        },
        {
          "id": "arrow-cpu-ram-hw-ar1",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-ram-hw-ram-txt",
      "x": 165,
      "y": 317.5,
      "width": 70,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "RAM",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "ram-block-hw-ram-002",
      "originalText": "RAM",
      "lineHeight": 1.25
    },
    {
      "type": "arrow",
      "id": "arrow-cpu-ram-hw-ar1",
      "x": 200,
      "y": 220,
      "width": 0,
      "height": 60,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 3,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "points": [[0, 0], [0, 60]],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "cpu-block-hw-cpu-001",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "ram-block-hw-ram-002",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": "arrow",
      "endArrowhead": "arrow"
    },
    {
      "type": "rectangle",
      "id": "stor-block-hw-stor-003",
      "x": 400,
      "y": 100,
      "width": 200,
      "height": 120,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#b2f2bb",
      "fillStyle": "hachure",
      "strokeWidth": 3,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [
        {
          "id": "text-stor-hw-stor-txt",
          "type": "text"
        },
        {
          "id": "arrow-cpu-stor-hw-ar2",
          "type": "arrow"
        }
      ],
      "locked": false,
      "link": null
    },
    {
      "type": "text",
      "id": "text-stor-hw-stor-txt",
      "x": 445,
      "y": 147.5,
      "width": 110,
      "height": 25,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "text": "Storage",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 18,
      "containerId": "stor-block-hw-stor-003",
      "originalText": "Storage",
      "lineHeight": 1.25
    },
    {
      "type": "arrow",
      "id": "arrow-cpu-stor-hw-ar2",
      "x": 300,
      "y": 160,
      "width": 100,
      "height": 0,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 3,
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "boundElements": [],
      "locked": false,
      "link": null,
      "points": [[0, 0], [100, 0]],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "cpu-block-hw-cpu-001",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "stor-block-hw-stor-003",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    }
  ],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

## Rendering in Dashboard

The Vista dashboard renders Excalidraw diagrams using the official React component from CDN.

### React Component Usage

```jsx
import { Excalidraw } from "https://cdn.jsdelivr.net/npm/@excalidraw/excalidraw@latest/dist/excalidraw.min.js";

function DiagramViewer({ diagramData }) {
  return (
    <Excalidraw
      initialData={diagramData}
      viewModeEnabled={true}
      zenModeEnabled={false}
      gridModeEnabled={false}
      theme="light"
    />
  );
}
```

### Key Configuration

- **`viewModeEnabled={true}`**: Read-only mode (no editing)
- **`zenModeEnabled={false}`**: Show UI elements
- **`gridModeEnabled={false}`**: Hide grid overlay
- **`theme`**: `"light"` or `"dark"`

### Constraints

- **No SSR**: Excalidraw requires browser environment
- **Client-side only**: Must render in browser, not on server
- **CDN bundle**: Use ESM version from jsdelivr

## Best Practices

### 1. Element Ordering
Place elements in this order for clarity:
1. Containers (rectangles, diamonds, ellipses)
2. Text bound to containers
3. Arrows connecting elements
4. Standalone text or annotations

### 2. ID Management
- Generate unique IDs for each element
- Use descriptive prefixes (e.g., `"arrow-cpu-ram-..."`, `"text-label-..."`)
- Never duplicate IDs across elements

### 3. Positioning Strategy
```
Start position: (100, 100)
Horizontal gap: 100px between elements
Vertical gap: 80px between rows

Example layout:
Row 1: (100, 100), (350, 100), (600, 100)
Row 2: (100, 280), (350, 280), (600, 280)
```

### 4. Arrow Binding Checklist
When creating arrows, always:
- [ ] Set arrow's `startBinding` with correct `elementId`
- [ ] Set arrow's `endBinding` with correct `elementId`
- [ ] Add arrow to source element's `boundElements`
- [ ] Add arrow to target element's `boundElements`
- [ ] Ensure first point in `points` array is `[0, 0]`
- [ ] Set `gap` to reasonable value (typically 8)

### 5. Text Binding Checklist
When binding text to containers:
- [ ] Set text's `containerId` to container ID
- [ ] Add text to container's `boundElements`
- [ ] Set text `textAlign` to `"center"`
- [ ] Set text `verticalAlign` to `"middle"`
- [ ] Position text centered in container

### 6. Minimal Required Properties
For rapid prototyping, these are the absolute minimum:
```json
{
  "type": "rectangle",
  "id": "unique-id-21-chars-long",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 100,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#a5d8ff",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "boundElements": [],
  "locked": false,
  "link": null
}
```

### 7. Common Mistakes to Avoid
- **Missing boundElements**: Always update both arrow and target
- **Wrong first point**: Arrow points must start with `[0, 0]`
- **Short IDs**: Must be exactly 21 characters
- **Missing containerId**: Bound text needs this set
- **Wrong text alignment**: Container text needs `center`/`middle`
- **Negative dimensions**: Width and height must be positive
- **Missing required fields**: All elements need `type`, `id`, `x`, `y`, etc.

### 8. Validation Checklist
Before saving an Excalidraw file:
- [ ] All IDs are unique and 21 characters long
- [ ] All arrows have valid start/end bindings
- [ ] All bound text has `containerId` set
- [ ] All containers with text have text in `boundElements`
- [ ] No negative widths or heights
- [ ] First point of all arrows/lines is `[0, 0]`
- [ ] All required properties present
- [ ] Valid JSON structure

## Summary

Excalidraw is ideal for precise spatial diagrams where you need exact control over element positioning and connections. The JSON format is straightforward but requires careful attention to:
- ID generation (21-char nanoid)
- Arrow binding (update both arrow and targets)
- Text binding (containerId + boundElements)
- Coordinate positioning (top-left origin)
- Required properties (all elements need full property set)

Use the examples above as templates and adapt coordinates, IDs, and content as needed.
