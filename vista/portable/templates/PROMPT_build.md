**CRITICAL**: This is a BUILD iteration. You MUST write code. Analysis-only iterations are FAILURES.

PROJECT: {{PROJECT_NAME}}
FEATURE: {{FEATURE_NAME}}
FEATURE_DIR: {{FEATURE_DIR}}

## Step 0: Study Planning Artifacts

0a. Read `{{FEATURE_DIR}}/arch/_arch.json` to discover all architecture and TDD diagrams.
0b. Read ALL `{{FEATURE_DIR}}/arch/*.mmd` files — architecture diagrams for system context, TDD diagrams for test contracts.
0c. Study `{{FEATURE_DIR}}/specs/*` with up to 500 parallel Sonnet subagents to learn the application specifications.
0d. Study `{{FEATURE_DIR}}/IMPLEMENTATION_PLAN.md`.
0e. For reference, the application source code is in src/*.

## TDD-First Discipline

Check `{{FEATURE_DIR}}/domain-requirements.md` for `## TDD Candidates` and `## Test Expectations` sections. Check each spec's `## Testing Strategy` section.

### For TDD-flagged components:
1. **Read the TDD diagrams** (`arch/tdd-*.mmd`) for the component
2. **Write tests FIRST** based on the TDD diagram paths and the spec's Testing Strategy section
3. **Run the tests** — they MUST fail (red phase)
4. **Implement the component** to make the tests pass
5. **Run the tests again** — they MUST pass (green phase)
6. **Refactor** if needed while keeping tests green

Do NOT skip the red phase. If tests pass before implementation, the tests are wrong — they aren't testing anything meaningful.

### For non-TDD components:
Implement normally — write code, then add tests if specified in the spec's acceptance criteria.

## Pacing — READ THIS FIRST

You are one iteration in a multi-iteration loop. Do NOT try to complete the entire plan in one pass.

- **Pick 1-3 items** from the plan in priority order. Implement them fully (no stubs).
- **Commit after each completed item** so work is never lost.
- **When your context is getting long**, stop taking on new items. Finish what you started, wrap up (Step 2), and exit cleanly. The next iteration will continue where you left off.
- A clean partial iteration with good commits and updated progress is far more valuable than an overloaded iteration that runs out of context mid-task.

## Step 1: Implement

Follow `{{FEATURE_DIR}}/IMPLEMENTATION_PLAN.md` and pick the highest-priority incomplete item. Before making changes, search the codebase (don't assume not implemented) using Sonnet subagents. You may use up to 500 parallel Sonnet subagents for searches/reads and only 1 Sonnet subagent for build/tests. Use Opus subagents when complex reasoning is needed (debugging, architectural decisions).

After implementing, run the tests for that unit of code. If functionality is missing then add it as per the specs. Commit, then pick the next item if context allows.

Important: Single sources of truth, no migrations/adapters. Implement completely — no placeholders or stubs. If tests unrelated to your work fail, resolve them.

Keep `{{FEATURE_DIR}}/IMPLEMENTATION_PLAN.md` current with learnings using a subagent. When `IMPLEMENTATION_PLAN.md` becomes large, clean out completed items. Keep @AGENTS.md operational only — status updates belong in IMPLEMENTATION_PLAN.md.

## Step 2: Wrap Up — MANDATORY

**CRITICAL: You MUST complete ALL of these steps before finishing. Skipping any step is a FAILURE equivalent to not writing code at all. These steps are how your work becomes visible to future iterations and the user.**

### 2a. Update progress.txt

APPEND to `{{FEATURE_DIR}}/progress.txt`:
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

### 2b. Update the Implementation Plan

Update `{{FEATURE_DIR}}/IMPLEMENTATION_PLAN.md` to reflect current status:
- Mark completed phases/steps (e.g. prefix with "DONE:" or strikethrough)
- Add any learnings, issues discovered, or deviations from the plan
- Note any remaining work for future iterations

### 2c. Git Commit and Push

Stage and commit ALL changes with a descriptive message:
```
git add -A
git commit -m "feat({{FEATURE_NAME}}): [summary of what was built]"
```

**Do NOT skip the git commit. Uncommitted work is invisible to future iterations and the user. The loop script will push after you finish — but only if you commit first.**

# RALPH_CONTROL

End your response with:
```
# RALPH_CONTROL
status: done
files_changed: [count]
commit: [commit hash]
```
