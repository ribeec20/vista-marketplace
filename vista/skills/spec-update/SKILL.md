---
name: spec-update
description: "Update spec files with tracked changes, requirement IDs, and changelog entries. Use when requirements change during implementation, new requirements emerge, or existing requirements need deprecation. Manages bidirectional traceability between specs and code via requirement IDs and git-searchable commit prefixes."
---

# Spec Update

Update spec files with proper change tracking: requirement IDs, changelog entries, and traceable commits.

## Invocation

```
/vista:spec-update <feature-name> [topic-name]
```

## Prerequisites

- Feature must exist at `.vista/features/<name>/`
- Spec files must exist in `.vista/features/<name>/specs/` (run `/vista:specs` first)
- Git repository (for commit prefix convention; gracefully skipped if unavailable)

## Workflow

### Step 1: Validate and Load

1. Verify `.vista/features/<feature>/` exists. If not: error, suggest `/vista:plan`.
2. If `topic-name` provided, verify `specs/{topic}.md` exists. If not: error, list available specs.
3. If no `topic-name`, list available spec files and ask which to update via **AskUserQuestion**.
4. Read the target spec file and `domain-requirements.md`.
5. Check if spec has requirement IDs. If not, offer to retroactively assign them before proceeding.

### Step 2: Determine Change

Ask the user via **AskUserQuestion**:

**Question 1: What type of change?**
- **Add** -- New requirement discovered during implementation
- **Update** -- Modify an existing requirement (wording, detail, scope)
- **Deprecate** -- Mark a requirement as no longer applicable

**Question 2: Describe the change.**
Free text: what specifically changed or needs to be added.

**Question 3: Why?**
Free text: the reason (e.g., "edge case found during implementation", "user feedback", "architecture decision").

### Step 3: Apply Changes

**Reference**: `vista/skills/spec-update/references/conventions.md`

Based on change type:

#### Add
1. Determine the next sequential ID for the category (parse existing IDs in the spec)
2. Add the requirement line in the correct section (Functional, Non-Functional, or Business Rule)
3. Add acceptance criteria for the new requirement
4. Add changelog row (newest first) with today's date, new ID, change description, reason
5. Add entry to Requirement Index with status `Active`

#### Update
1. Modify the requirement text, keeping the same ID
2. Update related acceptance criteria if affected
3. Add changelog row with the existing ID, description of what changed, reason

#### Deprecate
1. Add `[DEPRECATED]` marker to the requirement text, noting what replaces it (if applicable)
2. Do NOT delete the requirement or reuse its ID
3. Update Requirement Index status to `Deprecated`
4. Add changelog row with the ID, "Deprecated" change, reason

### Step 4: Commit

If git is available:
1. Stage the modified spec file
2. Commit with prefix: `spec(<feature>/<topic>): <description with IDs>`
3. Backfill the commit hash into the changelog entry
4. Stage and amend with the backfilled hash

If git is not available: warn and skip.

### Step 5: Report

1. Show the changes made (requirement ID, text, changelog entry)
2. Grep the codebase for references to any affected requirement IDs
3. If code references exist, list them so the user knows what may need updating
4. Suggest next action if applicable (e.g., "update the code comment at src/service.py:42")

## Retroactive ID Assignment

When a spec file has no requirement IDs (legacy or pre-convention):

1. Parse all numbered requirements in Functional, Non-Functional, Business Rule sections
2. Derive the feature prefix from the feature name
3. Assign sequential IDs to each requirement
4. Add a Changelog table with a single "Created (retroactive ID assignment)" entry
5. Add a Requirement Index at the end of the file
6. Commit with: `spec(<feature>/<topic>): retroactive requirement ID assignment`

## Conventions

All format details (ID format, changelog table, commit prefix, code traceability) are in:
`vista/skills/spec-update/references/conventions.md`
