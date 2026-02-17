**CRITICAL: Specs are the AUTHORITATIVE SOURCE OF TRUTH. When specs and an existing plan conflict, specs WIN. Rewrite the plan — do not patch it.**

PROJECT: {{PROJECT_NAME}}
FEATURE: {{FEATURE_NAME}}
FEATURE_DIR: {{FEATURE_DIR}}

## Step 0: Study All Planning Artifacts

0a. Read `{{FEATURE_DIR}}/arch/_arch.json` to discover all architecture and TDD diagrams.
0b. Read ALL `{{FEATURE_DIR}}/arch/*.mmd` files — both architecture diagrams and TDD diagrams. Study them thoroughly with up to 250 parallel subagents.
0c. Study `{{FEATURE_DIR}}/specs/*` and `{{FEATURE_DIR}}/domain-requirements.md` THOROUGHLY with up to 250 parallel subagents to understand the full requirements.
0d. Study src/lib/* with up to 250 parallel Sonnet subagents to understand shared utilities & components.
0e. For reference, the application source code is in src/*.

### TDD Diagram Awareness

Pay special attention to `arch/tdd-*.mmd` files — these are TDD diagrams that define test contracts for heavy-logic components:
- `tdd-*-logic.mmd` — Logic flow diagrams showing input→processing→output paths
- `tdd-*-states.mmd` — State diagrams showing valid transitions
- `tdd-*-decision.mmd` — Decision trees showing branching business rules

Each path through a TDD diagram maps to a test case. When planning implementation phases for TDD-flagged components, ensure the plan includes:
1. Writing tests FIRST based on the TDD diagrams
2. Running tests (expecting failure)
3. Implementing the component
4. Running tests (expecting pass)

Check `domain-requirements.md` for `## TDD Candidates` and `## Test Expectations` sections to identify which components require TDD discipline.

## Step 1: Versioned Plan Check

Read `IMPLEMENTATION_PLAN.md` if it exists. Check its `## Spec Versions` table against the current `## Changelog` in each spec file.

- **If spec versions match**: the plan is current — update only the phases/tasks that need refinement.
- **If any spec has newer changelog entries**: the plan is STALE. Compact the old plan — carry forward what's still valid, discard what conflicts, and rewrite as a clean new version.
- **If no plan exists**: create one from scratch.

## Pacing

You are one iteration in a multi-iteration loop. If context gets long, stop and wrap up (Step 4). A partial plan with accurate findings is better than a bloated iteration that runs out of context. The next iteration will refine what you started.

## Step 2: Analyze and Plan

Use up to 500 Sonnet subagents to study existing source code and compare it against specs/*. Ultrathink. Consider searching for TODO, minimal implementations, placeholders, skipped/flaky tests, and inconsistent patterns. Prioritize tasks and create/update `IMPLEMENTATION_PLAN.md` as a bullet point list sorted in priority of items yet to be implemented.

IMPORTANT: Plan only. Do NOT implement anything. Do NOT assume functionality is missing; confirm with code search first. Treat src/lib as the project's standard library for shared utilities and components. Include tests for each phase that incorporates the test specifications from specs (especially `## Testing Strategy` sections for TDD-flagged components).

## Step 3: Operational Docs

If `{{FEATURE_DIR}}/AGENTS.md` does not exist, create it with basic operational info about how to run/test the application. Update it as you discover new tools or commands.

## Step 4: Wrap Up — MANDATORY

**CRITICAL: You MUST complete ALL of these steps before finishing. Skipping any step is a FAILURE.**

### 4a. Write the Plan with Spec Versions

Write `IMPLEMENTATION_PLAN.md` with this header format:

```markdown
# Implementation Plan: [feature name]

Plan Version: [N] — [date]
Previous Version: [N-1 or "none"]

## Spec Versions
| Spec | Last Changelog Date | Key Change |
|------|-------------------|------------|
| container-lifecycle.md | 2026-02-12 | Initial spec |
| credential-management.md | 2026-02-12 | Initial spec |

## Overview
[plan content...]
```

The `## Spec Versions` table is how future plan iterations detect staleness. Always populate it from the latest `## Changelog` entry in each spec file.

### 4b. Update progress.txt

APPEND to `{{FEATURE_DIR}}/progress.txt`:
```
---
Iteration: [number] (plan)
Time: [timestamp]
Plan version: [N]
Spec drift: [none | list of specs with newer changelogs]
Summary: [what you analyzed/planned this iteration]
Remaining: [what areas still need planning attention]
---
```

### 4c. Git Commit and Push

Stage and commit ALL changes:
```
git add -A
git commit -m "plan({{FEATURE_NAME}}): [brief summary of planning work]"
```

**Do NOT skip the git commit. Uncommitted work is invisible to future iterations and the user. The loop script will push after you finish — but only if you commit first.**
