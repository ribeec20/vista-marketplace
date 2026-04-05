---
name: explain
description: |
  Explain a Vista feature's architecture, requirements, and implementation. Produces a clear narrative from planning artifacts and code. Use when: (1) User runs /vista:explain, (2) User wants to understand a planned or implemented feature, (3) Onboarding someone to an existing feature.
disable-model-invocation: true
argument-hint: <feature-name>
---

# Vista Explain

Generate a clear, structured explanation of a Vista feature by synthesizing its planning artifacts, architecture diagrams, and implementation code.

## Invocation

```
/vista:explain <feature-name>
```

## Prerequisites

- Feature must exist at `.vista/features/<name>/`
- At minimum, `domain-requirements.md` should be filled (run `/vista:plan` first)

## Workflow

### Step 1: Load All Available Artifacts

Read whatever exists for the feature:

1. `.vista/features/<name>/domain-requirements.md` — requirements and context
2. `arch/_arch.json` and all diagram files in `arch/` — architecture and TDD diagrams
3. `specs/*.md` — topic specifications
4. `IMPLEMENTATION_PLAN.md` — implementation plan (if populated)
5. `progress.txt` — progress tracking

Also scan the codebase for implementation files related to this feature using Explore agents.

### Step 2: Ask What to Explain

Use **AskUserQuestion**:
```
I found these artifacts for <feature-name>:

- Domain requirements: [present/absent]
- Architecture diagrams: [N] diagrams
- Specs: [N] topic specs
- Implementation: [found/not found]
- Progress: [status]

What would you like me to explain?
```

**Options:**
- **Overview** — "High-level summary of the feature"
- **Architecture** — "How components fit together and why"
- **Requirements** — "What this feature does and its business rules"
- **Implementation** — "How the code implements the specs"
- **Data model** — "Entities, relationships, and data flow"
- **Everything** — "Full walkthrough from requirements to code"

### Step 3: Generate Explanation

Based on the user's selection, produce a structured explanation.

#### Overview

- What problem the feature solves (from domain requirements)
- Who the users are and what they need
- Key components at a glance (from system architecture diagram)
- Current status (from progress.txt)

#### Architecture

- Walk through the system architecture diagram, explaining each component's role
- Explain data flow using sequence diagrams
- Describe state management using state diagrams (if any)
- Call out key design decisions (from design-rationale.md if present)

#### Requirements

- Summarize functional requirements grouped by topic/spec
- List business rules with their IDs
- Highlight non-functional requirements (performance, security, etc.)
- Note any TDD candidates and why they were flagged

#### Implementation

- Map specs to implementation files — which code implements which requirements
- Explain key patterns and abstractions used
- Highlight how TDD-flagged components were implemented
- Note any deviations from the original plan

#### Data Model

- Walk through the ER diagram explaining entities and relationships
- Describe data flow through the system
- Note validation rules and constraints

### Step 4: Offer Follow-Up

After the explanation, offer next steps via **AskUserQuestion**:
- **Dive deeper** — "Explain a specific component or spec in more detail"
- **Diagrams** — "Open the Vista dashboard to explore diagrams visually"
- **Modify** — "Update specs or requirements based on new understanding"
- **Done** — "That's all I needed"

If the user wants to dive deeper, repeat Step 3 focused on the specific area.
