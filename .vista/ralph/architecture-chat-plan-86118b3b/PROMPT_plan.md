**CRITICAL: This is a PLAN iteration. You MUST write a detailed plan.**

PROJECT: vista
JOB: architecture-chat-plan
JOB_DIR: C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/architecture-chat-plan-86118b3b
PLAN_DIR: C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/architecture-chat-plan-86118b3b

## Step 0: Understand the Task

Read `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/architecture-chat-plan-86118b3b/task.md` carefully. This file is the single source of truth for what to plan.

If `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/architecture-chat-plan-86118b3b` contains specs, requirements, or architecture docs, read those too — they provide essential context.

## Step 1: Inspect the Codebase

- Locate the relevant code under `vista/*` (project root is the working directory).
- Identify existing patterns and reuse shared utilities when possible.

## Step 2: Plan the Work

- Produce a step-by-step implementation plan that maps to the task.
- Call out any dependencies, data models, or APIs that need to change.
- Specify any tests to add or update.

## Step 3: Wrap Up — MANDATORY

**You MUST complete ALL of these steps before finishing. Skipping any step is a FAILURE.**

### 3a. Write the Plan

Write your plan to `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/architecture-chat-plan-86118b3b/IMPLEMENTATION_PLAN.md`. Keep it focused and actionable.

### 3b. Update progress.txt

Update `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/architecture-chat-plan-86118b3b/progress.txt` to reflect that a plan was created:
```
---
Iteration: [number] (plan)
Time: [timestamp]

Plan written to: C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/ralph/architecture-chat-plan-86118b3b/IMPLEMENTATION_PLAN.md
Summary: [1-2 sentence summary of what the plan covers]
---
```

### 3c. Git Commit

Stage and commit the plan and any related artifacts:
```
git add -A
git commit -m "plan(architecture-chat-plan): [brief summary of plan]"
```

**Do NOT skip the git commit. Uncommitted plans are invisible to future iterations and the user.**
