**CRITICAL**: This is a BUILD iteration. You MUST write code. Analysis-only iterations are FAILURES.

PROJECT: {{PROJECT_NAME}}
JOB: {{FEATURE_NAME}}
JOB_DIR: {{FEATURE_DIR}}
PLAN_DIR: {{PLAN_DIR}}

## Step 0: Understand the Task

Read `{{FEATURE_DIR}}/task.md` carefully. This file is the single source of truth for what to build.

## Step 1: Read the Implementation Plan

Read `{{PLAN_DIR}}/IMPLEMENTATION_PLAN.md` for the detailed implementation plan. Follow it step by step.

If the plan file is not found at that path, search for `IMPLEMENTATION_PLAN.md` in:
1. `.vista/features/{{FEATURE_NAME}}/`
2. `.vista/ralph/{{FEATURE_NAME}}-*/` (most recent match)

## Pacing

You are one iteration in a multi-iteration loop. Do NOT try to complete everything in one pass.

- Pick 1-3 items from the plan in priority order. Implement them fully (no stubs).
- Commit after each completed item so work is never lost.
- When your context is getting long, stop taking on new items — finish what you started, wrap up (Step 4), and exit cleanly. The next iteration continues where you left off.

## Step 2: Implement

- Search the codebase for existing related functionality before writing new code.
- Implement the requested functionality completely (no placeholders).
- Add or update tests when appropriate.

## Step 3: Validate

- Run the relevant tests for the code you changed.
- Fix any failures in the same iteration.

## Step 4: Wrap Up — MANDATORY

**You MUST complete ALL of these steps before finishing. Skipping any step is a FAILURE.**

### 4a. Update progress.txt

APPEND to `{{FEATURE_DIR}}/progress.txt` with a detailed summary:
```
---
Iteration: [number]
Time: [timestamp]

WHAT WAS DONE:
- [file path]: [what you created/changed and why]
- [file path]: [what you created/changed and why]

WHAT WAS NOT DONE:
- [item from plan]: [reason it was skipped or deferred]

Tests: [X passing, Y failing — list test files run]
---
```

If all work in the plan is complete, add `ALL PHASES COMPLETE` at the end.

### 4b. Update the Implementation Plan

Update `{{PLAN_DIR}}/IMPLEMENTATION_PLAN.md` to reflect current status:
- Mark completed phases/steps (e.g. prefix with "DONE:" or strikethrough)
- Add any learnings, issues discovered, or deviations from the plan
- Note any remaining work for future iterations

### 4c. Git Commit and Push

Stage and commit ALL changes with a descriptive message:
```
git add -A
git commit -m "feat({{FEATURE_NAME}}): [summary of what was built]"
```

**Do NOT skip the git commit. Uncommitted work is invisible to future iterations and the user.**
