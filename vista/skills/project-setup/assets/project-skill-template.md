---
name: project
description: {PROJECT_NAME} project context. MANDATORY - invoke /project at session start. Contains project structure, tech stack, patterns, and lists available feature skills.
---

# {PROJECT_NAME}

## Overview

**Type:** {PROJECT_TYPE}
**Language:** {PRIMARY_LANGUAGE}
**Architecture:** {ARCHITECTURE_PATTERN}

## Tech Stack

### Core
{CORE_TECH_LIST}

### Dev/Build
{DEV_BUILD_TOOLS}

## Structure

```
{DIRECTORY_TREE}
```

### Key Directories
{KEY_DIRECTORIES}

## Patterns

{CODE_PATTERNS}

## Commands

| Task | Command |
|------|---------|
| Run | `{RUN_COMMAND}` |
| Test | `{TEST_COMMAND}` |
| Build | `{BUILD_COMMAND}` |

## Entry Points

- Main: `{MAIN_ENTRY}`
- Config: `{CONFIG_FILES}`

## Spec Conventions

- Requirements use IDs: `{PREFIX}-F1`, `{PREFIX}-NF1`, `{PREFIX}-BR1`
- Prefix derived from feature name (first letter of each word, e.g., `user-auth` -> `UA`)
- Update specs via `/vista:spec-update <feature> [topic]` -- adds changelog entry + traceable commit
- Commit prefix: `spec(feature/topic): description`
- Code traceability: `# Implements {ID}: description`

## Feature Skills

Available in `.claude/skills/project/`:

{FEATURE_SKILL_LIST}

Load feature skill when working on that feature for detailed context.
