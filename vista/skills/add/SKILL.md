---
name: add
description: Expand an existing Vista feature with new requirements and architecture diagrams.
disable-model-invocation: true
argument-hint: <feature-name>
---

# Vista Add

Expand an existing feature with new requirements and updated architecture diagrams.

## Invocation

```
/vista:add <feature-name>
```

## Prerequisites

- `docs/<name>/` must exist with:
  - `domain-requirements.md` — Existing domain requirements (run `/vista:plan` first)
  - `arch/` — Architecture diagrams directory with `_arch.json` manifest

## Workflow

### Step 1: Load Current State

Read and summarize the current feature state:

1. Read `docs/<name>/domain-requirements.md` — show key JTBD and requirements summary
2. Read `arch/_arch.json` — list all existing diagrams (architecture and TDD)
3. Read all diagram files in `arch/` (`.mmd`, `.puml`, `.d2`, `.excalidraw`, `.txt`) — understand current architecture
4. List existing specs in `docs/<name>/specs/`
5. Present a concise summary to the user of what exists

### Step 2: Gather New Requirements

Ask the user what they want to add or expand using **AskUserQuestion**:

- New user stories or jobs to be done?
- New UI workflows or screens?
- New data entities or relationships?
- New services or integrations?
- Extensions to existing components?
- New non-functional requirements?

Be specific about what already exists to avoid duplication.

### Step 3: Update Documentation

Based on user input:

1. **Append** new content to `domain-requirements.md` (don't overwrite existing content)
2. **Flag new TDD candidates** — if new requirements involve heavy logic, append to the `## TDD Candidates` section
3. Note which existing specs will need updating and which new specs will be needed (actual spec generation is done by `/vista:specs`)

### Step 4: Update Architecture Diagrams

Generate new or updated diagram files in `arch/`. New diagrams can use any supported format — not just Mermaid. Choose the best format based on what you're representing (see `vista/skills/diagrams/SKILL.md` for format selection guidance).

1. **Update** existing diagrams if new requirements extend existing components
2. **Create** new diagrams for newly introduced components or flows (in the best format for the content)
3. **Update** `arch/_arch.json` manifest with any new diagram entries

Follow the same conventions as `/vista:plan` Step 3 for diagram generation.

### Step 5: Report

Tell the user:

1. **Requirements updated** — what was appended to domain-requirements.md
2. **Diagrams updated** — which diagrams were modified or created
3. **New TDD candidates** — any newly flagged components
4. **Next steps:**
   - Review diagrams in the web dashboard or terminal
   - `/vista:tdd <name>` — Generate TDD diagrams for any new TDD candidates
   - `/vista:specs <name>` — Regenerate specs to incorporate new requirements

## Output

After expansion:
- `domain-requirements.md` — Appended with new requirements
- `arch/*` — New or updated architecture diagrams (`.mmd`, `.puml`, `.d2`, `.excalidraw`, `.txt`)
- `arch/_arch.json` — Updated manifest
