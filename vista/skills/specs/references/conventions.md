# Spec Management Conventions

Reference for requirement IDs, changelog tables, commit prefixes, and code traceability.

## Requirement ID Format

```
{FEATURE_PREFIX}-{CATEGORY}{NUMBER}
```

### Feature Prefix Derivation

Take the first letter of each hyphenated word in the feature name:
- `ralph-mcp-tool` -> `RMT`
- `spec-management` -> `SM`
- `payment-flow` -> `PF`
- `user-auth` -> `UA`

Uppercase always. If a single word, use first 2-3 letters (e.g., `dashboard` -> `DSH`).

### Category Codes

| Category | Code | Used For |
|----------|------|----------|
| Functional | F | Core functionality requirements |
| Non-Functional | NF | Performance, platform, security requirements |
| Business Rule | BR | Business logic and constraints |

### Numbering

- Sequential within each category, starting at 1
- Never reuse an ID -- deprecated requirements keep their number
- Example sequence: `SM-F1`, `SM-F2`, `SM-F3` (if F2 deprecated, next is still `SM-F4`)

### Requirement Line Format

```markdown
### Functional
1. **SM-F1:** The system shall accept feature name and optional topic
2. **SM-F2:** Changelog entries shall include date, ID, change, and reason
3. **SM-F3:** [DEPRECATED] Original text (replaced by SM-F7)
```

### Deprecation

Never delete a requirement. Mark with `[DEPRECATED]` and note what replaced it:
```markdown
3. **SM-F3:** [DEPRECATED] Original text (replaced by SM-F7)
```

Update the Requirement Index status to `Deprecated`.

---

## Changelog Table Format

Placed immediately after `## Overview` in each spec file.

```markdown
## Changelog

| Date | ID | Change | Reason | Commit |
|------|-----|--------|--------|--------|
| 2026-02-12 | SM-F8 | Added retry limit | Edge case in implementation | abc1234 |
| 2026-02-10 | --- | Created | Initial spec generation | --- |
```

### Rules

- Newest entries at top
- `ID` column: affected requirement ID, or `---` for structural/non-requirement changes
- `Commit` column: short hash, or `---` if not yet committed
- `Date` format: `YYYY-MM-DD`
- Initial "Created" entry added by `/vista:specs` during generation

---

## Requirement Index Format

Placed at the end of each spec file, before `## Open Questions`.

```markdown
## Requirement Index

| ID | Section | Status |
|----|---------|--------|
| SM-F1 | Functional | Active |
| SM-F2 | Functional | Active |
| SM-F3 | Functional | Deprecated |
| SM-NF1 | Non-Functional | Active |
| SM-BR1 | Business Rule | Active |
```

---

## Commit Prefix Convention

```
spec(<feature>[/<topic>]): <description>
```

### Examples

```
spec(ralph-mcp-tool/mcp-tools): added retry limit requirement RMT-F12
spec(ralph-mcp-tool/dashboard): deprecated RMT-F3, replaced with RMT-F7
spec(payment-flow): initial spec generation with 4 topics
spec(user-auth/session): updated NF requirement UA-NF2 timeout value
```

### Rules

- Feature name always present
- Topic name present when change affects a single spec file
- Topic name omitted for cross-cutting or initial generation commits
- Include affected requirement IDs in description

---

## Code Traceability Convention

```python
# Implements SM-F1: The system shall accept feature name and optional topic
def update_spec(feature_name: str, topic_name: str | None = None):
```

### Format

```
# Implements {ID}: {brief description from spec}
```

### Rules

- Place directly above the function/class/block implementing the requirement
- Use the exact requirement ID from the spec
- Brief description can be shortened from the full spec text
- One comment per requirement (a function may have multiple if it implements several)
- Convention only -- not enforced by tooling
