---
name: legacy
description: Reverse-engineer an existing codebase into Vista planning artifacts, or convert old Vista features into the current arch schema.
disable-model-invocation: true
argument-hint: <feature-name>
---

# Vista Legacy

Reverse-engineer an existing codebase into Vista planning artifacts (domain requirements + architecture diagrams), or convert old-format Vista features into the current `/arch` planning schema.

## Invocation

```
/vista:legacy <feature-name>
```

## Use Cases

- Onboarding a feature that was built without Vista planning
- Documenting an existing system for handoff or review
- Creating a baseline before extending a feature with `/vista:add`
- **Converting old Vista features** that have inline plan JSON sections (`uiFlows`, `dataModels`, `dataFlow`, `services`) into the new `arch/` directory format with native `.mmd` diagrams

## Workflow

### Step 1: Scaffold Directory

Create the feature directory if it doesn't exist:

```bash
python vista/scripts/setup-feature.py --name $ARGUMENTS
```

If the directory already exists, proceed. Existing files won't be overwritten.

### Step 2: Scan Existing Artifacts and Detect Mode

Check `docs/<name>/` for pre-existing documentation:

- `domain-requirements.md` — Domain requirements (may be template-only)
- `arch/_arch.json` — Architecture manifest (may be empty)
- `arch/*.mmd` — Any existing diagrams
- `specs/*.md` — Any specification documents
- `IMPLEMENTATION_PLAN.md` — Implementation plan (may be template-only)
- `<name>_plan.json` — Old-format plan JSON (check for inline architecture sections)
- `<name>_prd.json` — Old-format PRD JSON
- `AGENTS.md` — Old build agent config (deprecated)

Report what was found.

**Detect mode:** If the feature directory contains a `<name>_plan.json` with any of these inline sections — `uiFlows`, `dataModels`, `dataFlow`, `services` — this is an **old-format Vista feature** that needs conversion. Follow **Path A: Convert Old Vista Feature** below.

Otherwise, this is a fresh reverse-engineering task. Follow **Path B: Reverse-Engineer from Source Code**.

---

## Path A: Convert Old Vista Feature

Use this path when a `<name>_plan.json` exists with inline architecture sections.

### Step A1: Extract Architecture from Plan JSON

Read `<name>_plan.json` and extract data from the inline sections:

| Plan JSON Section | What to Extract |
|-------------------|-----------------|
| `uiFlows.screens` | Screen names, components, descriptions, entry points |
| `uiFlows.transitions` | Screen-to-screen navigation triggers and conditions |
| `dataModels.entities` | Entity names, fields, types, relationships |
| `dataFlow` | API endpoints, request/response sequences, data pipelines |
| `services` | Service names, responsibilities, dependencies, integrations |

Also read `<name>_prd.json` if present — it may contain additional context (success criteria, test scenarios, functional requirements) that enriches diagram generation.

### Step A2: Generate Architecture Diagrams from Extracted Data

Convert the extracted sections into native Mermaid `.mmd` files in `arch/`:

| Source Section | Output Diagram | Diagram Type |
|----------------|----------------|--------------|
| `services` + overall structure | `system-architecture.mmd` | `flowchart` — Components, services, and their relationships |
| `uiFlows.screens` + `transitions` | `user-flow.mmd` | `flowchart` — Screen navigation and user journeys |
| `dataModels.entities` | `data-model.mmd` | `er` — Entity-relationship diagram with fields |
| `dataFlow` (per key flow) | `sequence-{flow}.mmd` | `sequence` — Request/response sequences between components |
| Stateful components (if any) | `state-{component}.mmd` | `state` — State transitions |

Follow the same Mermaid conventions as `/vista:plan` Step 3:
- Use clear, descriptive node labels
- Include notes where relationships are non-obvious
- Group related elements with subgraphs where helpful
- Keep diagrams focused — one concern per diagram

Set all diagram descriptions to note they are "converted from old-format plan JSON" so reviewers know the source.

### Step A3: Write Architecture Manifest

Write `arch/_arch.json` referencing all generated diagrams (conforming to `vista/templates/arch-schema.json`):

```json
{
  "feature": "<name>",
  "diagrams": [
    {
      "name": "System Architecture",
      "file": "system-architecture.mmd",
      "type": "mermaid",
      "diagramType": "flowchart",
      "category": "architecture",
      "description": "System components and relationships (converted from old-format plan JSON)"
    }
  ]
}
```

### Step A4: Update Plan JSON

Update the `<name>_plan.json` to reference the new arch directory:

1. **Add** an `architecture` section with `"ref": "./arch/_arch.json"`
2. **Remove** the old inline sections: `uiFlows`, `dataModels`, `dataFlow`, `services`
3. Keep `meta` and `implementationPhases` intact

The updated plan JSON should conform to `vista/templates/plan-schema.json`.

### Step A5: Clean Up Deprecated Files

Check for and remove deprecated artifacts:

- `AGENTS.md` — Old build agent config, no longer used
- `<name>_preview.html` — Old preview file (the web dashboard replaces this)

Ask the user before deleting anything.

### Step A6: Backfill Domain Requirements (if needed)

If `domain-requirements.md` is template-only or sparse, enrich it using data from:

1. **PRD JSON** (`<name>_prd.json`) — Extract user stories, success criteria, functional requirements
2. **Plan JSON** — Infer requirements from the implementation phases and old inline sections
3. **Source code** — Scan the codebase for additional context (same approach as Path B Step 3)

Mark any inferred content as "backfilled from old-format artifacts."

### Step A7: Review and Next Steps

Discover the dashboard URL by calling the `ralph_providers` MCP tool and reading `dashboard_url` from the response.

Tell the user:

1. **Conversion complete** — summarize what was converted:
   - Which diagrams were generated from which plan JSON sections
   - What was removed from the plan JSON
   - What deprecated files were cleaned up

2. **Review diagrams** in the web dashboard:
   ```
   <dashboard_url>/project/<project-id>/arch/<feature-name>
   ```
   Use the AI chat panel to discuss and iterate on diagrams.

3. Pay special attention to:
   - Whether the converted diagrams accurately represent the original inline data
   - Missing relationships that were implicit in the old format
   - Opportunities to add diagrams that the old format didn't capture

4. **Next steps:**
   - Edit diagrams and domain-requirements.md to fix inaccuracies
   - `/vista:tdd <name>` — Generate TDD diagrams for heavy-logic components
   - `/vista:specs <name>` — Generate or regenerate specifications
   - `/vista:add <name>` — Extend the feature with new capabilities

---

## Path B: Reverse-Engineer from Source Code

Use this path when no old-format plan JSON exists (or it has no inline architecture sections).

### Step B1: Scan Source Code

Use subagents to scan the actual codebase for implementation artifacts. Search for:

**Data Models / Entities:**
- Database models, schemas, migrations
- TypeScript/Python/etc. type definitions and interfaces
- ORM model classes

**Services / Business Logic:**
- Service classes and modules
- API route handlers
- Business logic functions
- External service integrations

**UI Components:**
- Page/screen components
- Form components
- Navigation and routing definitions
- State management

**Data Flow:**
- API endpoint definitions
- Event handlers and message queues
- Database queries and mutations
- External API calls

Ask the user for guidance on where to look if the codebase structure is unclear.

### Step B2: Categorize Findings

Organize discovered code into architectural categories:

1. **Components/Services** — Major system components and their responsibilities
2. **Data Model** — Entities, fields, relationships discovered from code
3. **User Flows** — UI screens, navigation, user journeys
4. **Interaction Flows** — Key request/response sequences between components
5. **State Management** — Stateful components with their transitions

Present the categorized findings to the user for validation before proceeding.

### Step B3: Generate Architecture Diagrams

Generate Mermaid `.mmd` files in `arch/` from the categorized findings:

- `system-architecture.mmd` — Flowchart of discovered components and their relationships
- `user-flow.mmd` — Flowchart of discovered user journeys
- `data-model.mmd` — ER diagram of discovered entities and relationships
- `sequence-{flow}.mmd` — Sequence diagrams for key interaction flows
- `state-{component}.mmd` — State diagrams for stateful components (if any)

Write `arch/_arch.json` manifest referencing all generated diagrams (conforming to `vista/templates/arch-schema.json`).

Set all diagram descriptions to note they are "reverse-engineered from existing codebase" so reviewers know these are inferences.

### Step B4: Backfill Domain Requirements

Fill in `domain-requirements.md` from code analysis:

1. **Infer JTBD and user stories** from what the code actually does
2. **Document functional requirements** discovered from service logic
3. **Document non-functional requirements** from configuration, caching, error handling patterns
4. **Flag TDD candidates** — identify components with complex logic that should have been tested

Mark all backfilled content clearly as "reverse-engineered" so reviewers know these are inferences.

### Step B5: Review and Next Steps

Discover the dashboard URL by calling the `ralph_providers` MCP tool and reading `dashboard_url` from the response.

Tell the user:

1. **Review diagrams** in the web dashboard:
   ```
   <dashboard_url>/project/<project-id>/arch/<feature-name>
   ```
   Use the AI chat panel to discuss and iterate on diagrams.

2. **Or review directly** by reading the `.mmd` files in the terminal.

3. Pay special attention to:
   - Missing components or flows that exist but weren't detected
   - Incorrect relationships between entities
   - Missing service dependencies

4. **Next steps:**
   - Edit diagrams and domain-requirements.md to fix inaccuracies
   - `/vista:tdd <name>` — Generate TDD diagrams for flagged heavy-logic components
   - `/vista:specs <name>` — Generate specifications from the reverse-engineered artifacts
   - `/vista:add <name>` — Extend the feature with new capabilities

---

## Output

After legacy import (either path):
```
docs/<name>/
├── arch/
│   ├── _arch.json              # Diagram manifest
│   ├── system-architecture.mmd # Components and relationships
│   ├── user-flow.mmd           # User journeys
│   ├── data-model.mmd          # Entity-relationship diagram
│   ├── sequence-*.mmd          # Interaction flows
│   └── state-*.mmd             # State machines (if any)
├── specs/                      # Existing or empty (populated by /vista:specs)
├── domain-requirements.md      # Backfilled or enriched
├── progress.txt                # Progress tracking
└── IMPLEMENTATION_PLAN.md      # Template (populated by Ralph loops)
```

**Removed after conversion (Path A only):**
- `AGENTS.md` — Deprecated build agent config
- `<name>_preview.html` — Replaced by web dashboard
- Inline sections from `<name>_plan.json` (`uiFlows`, `dataModels`, `dataFlow`, `services`)
