# Vista Plugin - Implementation Plan

## Summary

Build "Vista" - a Claude Code plugin that adds a visual review gate to the existing feature planning workflow. All artifacts move from `.claude/features/` to `.vista/features/` to avoid permission prompts. The workflow becomes:

```
/vista:plan <name>    -> scaffold -> domain-reqs -> specs -> plan.json -> preview
                      -> user approves/rejects sections in browser
/vista:revise <name>  -> reads review JSON -> fixes rejected sections -> re-preview
                      -> when all approved: JTBD -> IMPLEMENTATION_PLAN.md
/vista:add <name>     -> load existing feature -> expand with new detail -> update plan.json
```

---

## Plugin Structure

```
vista/
+-- .claude-plugin/
|   +-- plugin.json
+-- skills/
|   +-- plan/
|   |   +-- SKILL.md              (new plan: scaffold + domain-reqs + specs + plan.json + preview)
|   |   +-- references/           (copied from existing planning-features)
|   |   |   +-- spec-template.md
|   |   |   +-- domain-requirements-template.md
|   |   |   +-- prd-format.md
|   |   |   +-- discovery-process.md
|   |   |   +-- agent-prompts.md
|   |   |   +-- examples.md
|   |   |   +-- test-planning.md
|   |   +-- templates/
|   |       +-- standard.md       (copied from existing)
|   +-- revise/
|   |   +-- SKILL.md              (read review JSON, fix rejections, re-preview, approve flow)
|   +-- add/
|       +-- SKILL.md              (load existing feature, expand, update plan.json)
+-- scripts/
|   +-- setup-feature.py
|   +-- preview.py
|   +-- collect-review.py
|   +-- visualizer/
|       +-- template.html
+-- templates/
|   +-- plan-schema.json
|   +-- review-schema.json
```

---

## Phase 1: Foundation (manifest + scaffold + schemas)

### 1.1 Create `vista/.claude-plugin/plugin.json`
```json
{
  "name": "vista",
  "version": "1.0.0",
  "description": "Visual feature planning with review gate between specs and implementation",
  "author": { "name": "Grove" },
  "keywords": ["planning", "visualization", "review", "feature", "jtbd"]
}
```

### 1.2 Create `vista/scripts/setup-feature.py`
Adapt from: `plugin_1/skills/planning-features/scripts/setup-feature.ps1` (rewritten in Python)

Changes:
- Base path: `.vista/features/` instead of `.claude/features/`
- Add `<name>_plan.json` initialization (empty `{}`)
- Args: `--name` (required), `--parent` (optional)
- Uses `pathlib` + `os` (stdlib only, no dependencies)

Output structure:
```
.vista/features/<name>/
+-- specs/
+-- domain-requirements.md
+-- progress.txt
+-- <name>_prd.json
+-- <name>_plan.json          # NEW
+-- IMPLEMENTATION_PLAN.md
```

### 1.3 Create `vista/templates/plan-schema.json`

Five sections, each independently reviewable:

```
{
  meta: { feature, version, created, lastModified, status, description }
  sections: {
    uiFlows: {
      screens: [{ id, name, description, components[], entryPoint }]
      transitions: [{ from, to, trigger, condition }]
    }
    dataModels: {
      entities: [{ id, name, description, fields: [{ name, type, required, primaryKey }] }]
      relationships: [{ from, to, type(1:1/1:N/M:N), label }]
    }
    dataFlow: {
      sequences: [{
        id, name, description,
        actors: [{ id, name, type(user/ui/provider/service/database/external) }]
        steps: [{ from, to, action, response, isAsync, errorCase }]
      }]
    }
    services: {
      serviceList: [{ id, name, description, responsibilities[], dependencies[], methods[] }]
      integrations: [{ from, to, protocol, description }]
    }
    implementationPhases: {
      phases: [{
        id, name, description, order, dependencies[],
        tasks: [{ name, description, files[] }],
        acceptanceCriteria[]
      }]
    }
  }
}
```

### 1.4 Create `vista/templates/review-schema.json`

Two-level review: section-level status (derived) + item-level feedback.

```
{
  meta: { feature, planVersion, reviewDate, overallStatus }
  sections: {
    uiFlows: {
      status,                                          // derived: approved only if ALL items approved
      items: {
        "<screen-id>":     { status, notes }           // per screen
        "<transition-id>": { status, notes }           // per transition (optional)
      }
    }
    dataModels: {
      status,
      items: {
        "<entity-id>":       { status, notes }         // per entity
        "<relationship-id>": { status, notes }          // per relationship (optional)
      }
    }
    dataFlow: {
      status,
      items: {
        "<sequence-id>": { status, notes }             // per sequence
      }
    }
    services: {
      status,
      items: {
        "<service-id>":     { status, notes }          // per service
        "<integration-id>": { status, notes }           // per integration (optional)
      }
    }
    implementationPhases: {
      status,
      items: {
        "<phase-id>": { status, notes }                // per phase
      }
    }
  }
}
```

Item keys match the `id` field from plan-schema.json. Section `status` is computed: `approved` only when every item is `approved`, otherwise `rejected`.

---

## Phase 2: Skills

### 2.1 Copy reference files
From `skills/planning-features/references/` to `vista/skills/plan/references/`:
- spec-template.md
- domain-requirements-template.md
- prd-format.md
- discovery-process.md
- agent-prompts.md
- examples.md
- test-planning.md

From `skills/planning-features/templates/` to `vista/skills/plan/templates/`:
- standard.md

### 2.2 Write `vista/skills/plan/SKILL.md`

```yaml
---
name: plan
description: Create a new Vista feature plan with domain requirements, specs, and visual review
argument-hint: <feature-name>
disable-model-invocation: true
---
```

Invoked as: `/vista:plan auth-flow` (where `$ARGUMENTS` = `auth-flow`)

Workflow:
1. Run `python setup-feature.py --name $ARGUMENTS` to scaffold `.vista/features/<name>/`
2. Discovery: domain-requirements.md (using references/domain-requirements-template.md)
3. Specs: generate specs/*.md (using references/spec-template.md, discovery-process.md)
4. PRD: generate `<name>_prd.json` (using references/prd-format.md)
5. **Plan JSON generation**: read all specs + domain-reqs + PRD, synthesize into `<name>_plan.json` conforming to plan-schema.json
   - Extract: UI flows, data models, sequences, services, implementation phases
6. Update progress.txt to "Ready for Review"
7. Run `python preview.py --name $ARGUMENTS` to open HTML visualization in browser
8. Instruct user: review in browser, then run `/vista:revise <name>` when done

### 2.3 Write `vista/skills/revise/SKILL.md`

```yaml
---
name: revise
description: Revise a Vista plan based on browser review feedback, or approve and generate implementation plan
argument-hint: <feature-name>
disable-model-invocation: true
---
```

Invoked as: `/vista:revise auth-flow`

Workflow:
1. Read `.vista/features/$ARGUMENTS/${ARGUMENTS}_review.json`
2. Check `planVersion` matches current plan version
3. For each rejected **item** (grouped by section): show item name + reviewer notes, AskUserQuestion to discuss, then update that specific item in plan JSON
4. Increment plan version
5. Run `python preview.py --name $ARGUMENTS` to re-preview updated plan
6. If all items across all sections approved: generate JTBD from approved plan, then generate IMPLEMENTATION_PLAN.md informed by both the approved plan and JTBD

### 2.4 Write `vista/skills/add/SKILL.md`

```yaml
---
name: add
description: Add new features or details to an existing Vista feature plan
argument-hint: <feature-name>
disable-model-invocation: true
---
```

Invoked as: `/vista:add auth-flow`

Workflow:
1. Load existing `.vista/features/$ARGUMENTS/` context (plan JSON, specs, domain-reqs)
2. Ask user what to add or expand
3. Update relevant specs, domain-reqs, PRD
4. Re-synthesize plan JSON with additions
5. Run `python preview.py --name $ARGUMENTS` to preview updated plan

All skills use `.vista/features/` instead of `.claude/features/`.

---

## Phase 3: HTML Visualizer

### 3.1 Write `vista/scripts/visualizer/template.html`

Self-contained HTML with embedded CSS/JS. No external dependencies.

**Placeholder tokens** (replaced by preview.py at runtime):
- `__PLAN_JSON__` - actual plan data
- `__FEATURE_NAME__` - feature name
- `__FEATURE_DIR__` - absolute path to feature directory

**Rendering per section:**

| Section | Diagram Type | Approach |
|---------|-------------|----------|
| UI Flows | Flow chart | SVG boxes (screens) + labeled arrows (transitions) |
| Data Models | ER diagram | Table-style boxes with fields + relationship lines |
| Data Flow | Sequence diagram | Vertical lifelines + horizontal step arrows |
| Services | Dependency diagram | Service boxes + integration arrows |
| Implementation Phases | Timeline | Horizontal bars with dependency arrows |

All rendering uses inline SVG with JavaScript for layout. Simple layered layout algorithm (no external library).

**Review controls (per item within each section):**
- Each rendered item (screen, entity, sequence, service, phase) gets its own:
  - Approve / Reject radio buttons
  - Notes textarea (visible when Reject selected)
  - Color-coded border (green=approved, red=rejected, gray=pending)
- Section header shows derived status: approved only if all items approved
- "Approve All" / "Reject All" bulk toggle per section for convenience

**Submit button:**
- Primary: copies review JSON to clipboard via `navigator.clipboard.writeText()`
- Fallback: `data:` URI download link
- Displays command to run: `python .vista/scripts/collect-review.py --name '<feature>'`

### 3.2 Write `vista/scripts/preview.py`

Args: `--name` (required)

Logic:
1. Resolve `feature_dir = ".vista/features/{name}"`
2. Read `<name>_plan.json`
3. Read `template.html`
4. Replace `__PLAN_JSON__`, `__FEATURE_NAME__`, `__FEATURE_DIR__`
5. Write `<name>_preview.html` to feature directory
6. `webbrowser.open()` to open in browser

### 3.3 Write `vista/scripts/collect-review.py`

Args: `--name` (required)

Logic:
1. Read clipboard via `subprocess` calling platform clipboard command (`pbpaste` / `xclip` / `powershell Get-Clipboard`)
2. Validate JSON structure
3. Write to `.vista/features/{name}/{name}_review.json`

---

## Phase 4: Integration Testing

### 4.1 End-to-end test flow
1. `claude --plugin-dir ./vista` loads without errors
2. `/vista:plan test-feature` - verify scaffold at `.vista/features/test-feature/`
3. Verify domain-reqs + specs + `test-feature_plan.json` generated
4. Verify HTML preview opens in browser
5. Submit review with one rejection
6. `/vista:revise test-feature` - verify agent asks about rejected section, re-previews
7. Submit review with all approved
8. `/vista:revise test-feature` - verify JTBD + IMPLEMENTATION_PLAN.md generated
9. `/vista:add test-feature` - verify plan JSON updated with new detail

---

## Key Design Decisions

1. **Three focused skills** (`vista:plan`, `vista:revise`, `vista:add`) instead of a single command router. Each skill has its own frontmatter and can be independently configured. All are `disable-model-invocation: true` (user-triggered only).

2. **`.vista/` directory** at project root, NOT inside `.claude/`. Eliminates permission prompts entirely.

3. **Clipboard + script for review collection** because `file://` HTML pages can't write to disk directly. Fallback download link provided.

4. **No external JS libraries** - custom SVG renderers. Keeps the HTML self-contained and under control. Simple layouts first, improve iteratively.

5. **Plan JSON version tracking** - review JSON includes `planVersion` to ensure review matches the plan version being reviewed. Revise command checks this.

---

## Files to Create (19 files total)

| # | File | Source |
|---|------|--------|
| 1 | `vista/.claude-plugin/plugin.json` | New |
| 2 | `vista/skills/plan/SKILL.md` | New (adapts `planning-features/SKILL.md`) |
| 3 | `vista/skills/plan/references/spec-template.md` | Copy |
| 4 | `vista/skills/plan/references/domain-requirements-template.md` | Copy |
| 5 | `vista/skills/plan/references/prd-format.md` | Copy |
| 6 | `vista/skills/plan/references/discovery-process.md` | Copy |
| 7 | `vista/skills/plan/references/agent-prompts.md` | Copy |
| 8 | `vista/skills/plan/references/examples.md` | Copy |
| 9 | `vista/skills/plan/references/test-planning.md` | Copy |
| 10 | `vista/skills/plan/templates/standard.md` | Copy |
| 11 | `vista/skills/revise/SKILL.md` | New |
| 12 | `vista/skills/add/SKILL.md` | New |
| 13 | `vista/templates/plan-schema.json` | New |
| 14 | `vista/templates/review-schema.json` | New |
| 15 | `vista/scripts/setup-feature.py` | Adapted from existing |
| 16 | `vista/scripts/preview.py` | New |
| 17 | `vista/scripts/collect-review.py` | New |
| 18 | `vista/scripts/visualizer/template.html` | New (largest file) |
| 19 | `vista/README.md` | New |

---

## Verification

After implementation:
1. `claude --plugin-dir ./vista` loads without errors
2. `/vista:plan`, `/vista:revise`, `/vista:add` appear in skill list
3. Scaffold creates `.vista/features/<name>/` with all files
4. Plan JSON validates against schema
5. HTML opens in browser with all 5 diagram types rendered
6. Review submit copies valid JSON to clipboard
7. `collect-review.py` writes review JSON correctly
8. Full plan/revise cycle works end-to-end
