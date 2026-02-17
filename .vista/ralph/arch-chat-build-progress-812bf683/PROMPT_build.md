**CRITICAL**: This is a BUILD iteration. You MUST write code. Analysis-only iterations are FAILURES.

PROJECT: vista
JOB: arch-chat-build-progress
JOB_DIR: C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/arch-chat-build-progress-812bf683
PLAN_DIR: C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/arch-chat-build-progress-812bf683

## Step 0: Understand the Task

Read `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/arch-chat-build-progress-812bf683/task.md` carefully. This file is the single source of truth for what to build.

## Step 1: Read the Implementation Plan

Read `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/arch-chat-build-progress-812bf683/IMPLEMENTATION_PLAN.md` for the detailed implementation plan. Follow it step by step.

If the plan file is not found at that path, search for `IMPLEMENTATION_PLAN.md` in:
1. `.vista/features/arch-chat-build-progress/`
2. `.vista/ralph/arch-chat-build-progress-*/` (most recent match)

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

APPEND to `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/arch-chat-build-progress-812bf683/progress.txt` with a detailed summary:
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

Update `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/arch-chat-build-progress-812bf683/IMPLEMENTATION_PLAN.md` to reflect current status:
- Mark completed phases/steps (e.g. prefix with "DONE:" or strikethrough)
- Add any learnings, issues discovered, or deviations from the plan
- Note any remaining work for future iterations

### 4c. Git Commit and Push

Stage and commit ALL changes with a descriptive message:
```
git add -A
git commit -m "feat(arch-chat-build-progress): [summary of what was built]"
```

**Do NOT skip the git commit. Uncommitted work is invisible to future iterations and the user.**
