---
name: project-setup
description: Initialize Claude Code project management system. Creates .claude/skills/project/ with project-specific context skill, .claude/features/_planning/ for feature planning, and CLAUDE.md entry point. Use when setting up a new project for Claude Code workflows.
disable-model-invocation: true
---

# Project Setup

Initialize skill-based project context management.

**Required:** You MUST invoke the `skill-creator` skill (via `Skill tool`) when creating any skills in this process. Do not create skill files directly without going through skill-creator first.

## Created Structure

```
.claude/
  skills/
    project/
      SKILL.md            # Main project skill (/project)
      <feature>.md        # Feature skills (created later)
  features/
    _planning/            # Features being planned
    <feature>/            # Feature specs/domain docs (created later)
.vista/
  features/               # Feature planning artifacts
  ralph/                  # Ralph job working directories
CLAUDE.md                 # Mandates project skill at session start
```

## Process

### 1. Check Existing

If `.claude/skills/project/SKILL.md` or `CLAUDE.md` exists, ask: Skip | Backup & Replace | Cancel

### 2. Create Directories

```bash
mkdir -p .claude/skills/project
mkdir -p .claude/features/_planning
mkdir -p .vista/features
mkdir -p .vista/ralph
```

If `.vista/` already exists, skip `.vista/` creation (same pattern as the existing check for `.claude/`).

### 3. Analyze Codebase

Use Explore agent to gather:
- Project name, type, primary language
- Architecture pattern
- Tech stack (core + dev/build tools)
- Directory structure, key directories
- Entry points, config locations
- Build/test/run commands
- Code patterns and conventions

### 4. Create Project Skill

**IMPORTANT: Invoke the skill-creator skill** using the Skill tool with `skill: "skill-creator"` to create `.claude/skills/project/SKILL.md`.

Provide the skill-creator with:
- The analysis gathered in step 3
- The template from [assets/project-skill-template.md](assets/project-skill-template.md)
- Target path: `.claude/skills/project/SKILL.md`

The skill-creator will ensure proper skill structure and best practices are followed.

### 5. Create CLAUDE.md

Write `CLAUDE.md` in project root using [assets/claude-md-template.md](assets/claude-md-template.md).

### 6. Report

Show created files and next steps.

## Feature Skill Creation

When adding features later:

**Invoke the skill-creator skill** using `Skill tool` with `skill: "skill-creator"` to create `.claude/skills/project/<feature>.md`.

Provide the skill-creator with:
- Feature requirements and context
- The template from [assets/feature-skill-template.md](assets/feature-skill-template.md)
- Target path: `.claude/skills/project/<feature>.md`

Feature skills contain:
- Brief overview
- Key patterns and entry points
- Dependencies
- Pointer to `.claude/features/<feature>/` for specs/domain requirements

## Flags

| Flag | Effect |
|------|--------|
| `--minimal` | Structure only, no analysis |
| `--force` | Overwrite with .bak backups |
