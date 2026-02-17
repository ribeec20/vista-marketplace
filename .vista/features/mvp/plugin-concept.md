# Plugin Concept: Visual Feature Planning

## Problem

1. **Portability** - Planning workflows (commands, skills, templates, scripts) are scattered across `~/.claude/` and tied to one machine. No way to bundle and reuse across devices or share as a cohesive unit.

2. **Blind plan review** - Plans are approved by reading raw markdown. For UI flows, data models, entity relationships, and data flow, this is a poor medium. Architecture is parsed mentally instead of seen visually.

## What This Plugin Does

Bundles feature planning workflows into a portable plugin with a visual review gate between planning and implementation.

### Core Loop

```
/feature new <name>     → Interactive planning session (uses context)
                        → Outputs structured JSON + markdown

/feature preview <name> → Script reads JSON, generates HTML, opens browser
                        → Zero context cost

                        → User reviews visual diagrams
                        → Approves/rejects sections with checkboxes
                        → Adds notes on rejected sections
                        → Submits → writes <feature>_review.json

/feature revise <name>  → Agent reads review JSON (minimal context)
                        → Only asks about rejected sections
                        → Updates plan JSON
                        → Cycle back to preview

/feature approve <name> → All sections green → proceed to implementation
```

## Components

### 1. Planning Skill (existing, to be packaged)

The JTBD-based planning workflow that already exists:
- Domain requirements gathering via interactive questions
- JTBD analysis and topic decomposition
- Spec generation per topic
- PRD generation (JSON)

**Change needed:** Also emit a structured `<feature>_plan.json` sidecar alongside the markdown files. This is the machine-readable input for the visualizer.

### 2. Plan JSON Schema

Structured output covering all visualizable areas:

- **UI Flows** - Screens, navigation paths, component hierarchy
- **Data Models** - Entities, fields, relationships between models
- **Data Flow** - User action → provider → service → model → DB and back
- **Services** - Service boundaries, responsibilities, integration points
- **Implementation Phases** - Phase breakdown with dependencies

### 3. Visualizer Script

A standalone script (zero context cost) that:
- Reads `<feature>_plan.json`
- Generates a self-contained HTML file (no server, no external dependencies)
- Embeds JS for rendering diagrams (flow charts, entity diagrams, sequence flows)
- Opens in default browser

### 4. Review Interface (in the HTML)

The browser visualization includes:
- Section-by-section checkboxes (approve / reject)
- Optional notes field on each rejected section
- Submit button that writes `<feature>_review.json`

### 5. Review Feedback Command

Agent reads `<feature>_review.json`:
- Loads only rejected sections + notes
- Asks targeted questions about what needs to change
- Updates `<feature>_plan.json`
- User re-previews until all sections approved

## Output Structure

```
.claude/features/<feature-name>/
├── specs/                        # Topic specs (markdown, human-readable)
├── domain-requirements.md        # Business requirements
├── <feature>_prd.json            # Testable items (existing)
├── <feature>_plan.json           # NEW: Machine-readable plan for visualizer
├── <feature>_review.json         # NEW: Review feedback from browser
├── progress.txt                  # Tracking
└── IMPLEMENTATION_PLAN.md        # Generated after approval
```

## Plugin Package Structure

```
<plugin-name>/
├── SKILL.md                      # Main skill definition
├── commands/
│   └── feature.md                # Command routing
├── templates/
│   ├── plan-schema.json          # JSON schema for plan output
│   └── review-schema.json        # JSON schema for review feedback
├── scripts/
│   ├── setup-feature.ps1         # Scaffold script (existing)
│   ├── preview.ps1               # Generate HTML + open browser
│   └── visualizer/
│       └── template.html         # HTML template with embedded JS
├── references/
│   ├── spec-template.md          # Spec writing template
│   ├── domain-requirements-template.md
│   └── prd-format.md             # PRD JSON format
└── README.md
```

## Key Design Decisions

- **JSON sidecar over markdown parsing** - Reliable input for the visualizer. Markdown stays for humans, JSON for machines.
- **Self-contained HTML** - No server, no npm install, no dependencies. One HTML file with embedded CSS/JS.
- **Review JSON as contract** - The agent knows exactly what's approved and what needs work. No ambiguity.
- **Zero context for visualization** - The expensive part (planning) uses context. The review part is free.

## Name Options

| Name | Reasoning |
|------|-----------|
| `planview` | Direct - plan + view. Clear what it does. `/planview preview auth` |
| `blueprint` | Architectural metaphor. Visual plans before building. `/blueprint new auth` |
| `vista` | Short, means "view/vision". Easy to type. `/vista preview auth` |
| `plancheck` | Plan + checkpoint/checklist. Captures the approval gate. `/plancheck new auth` |
| `lens` | Looking at plans through a lens. Very short. `/lens preview auth` |
