# Topic Spec Template

Use this template when creating `specs/{topic-name}.md` files during spec generation.

**Filename format:** `{topic-name}.md` (kebab-case, e.g., `image-upload.md`)

---

## Template

```markdown
# Spec: {Topic Name}

## Overview
[One sentence description without "and" - validates topic scope]

## Changelog

| Date | ID | Change | Reason | Commit |
|------|-----|--------|--------|--------|
| {TODAY} | --- | Created | Initial spec generation | --- |

## Parent JTBD
[Which job to be done does this topic support?]

## Scope

**In Scope:**
- [What this topic covers]
- [Specific functionality included]

**Out of Scope:**
- [What is explicitly NOT covered]
- [Related topics handled elsewhere]

## Requirements

### Functional
1. **{PREFIX}-F1:** [Requirement 1]
2. **{PREFIX}-F2:** [Requirement 2]
3. **{PREFIX}-F3:** [Requirement 3]

### Non-Functional
1. **{PREFIX}-NF1:** **Performance:** [Specific metrics, e.g., "< 2s response time"]
2. **{PREFIX}-NF2:** **Platform:** [Web / Mobile / Both]
3. **{PREFIX}-NF3:** **Offline:** [Requirements and sync behavior]

## User Workflows

### Workflow 1: {Name}
**Actor:** [User role]
**Trigger:** [What initiates this workflow]

**Steps:**
1. [Step 1]
2. [Step 2]
3. [Expected outcome]

**Error Cases:**
- [Error 1]: [How to handle]
- [Error 2]: [How to handle]

## Data Model

**Entities:**
- {Entity1}: [description, key fields]
- {Entity2}: [description, key fields]

**Relationships:**
- [Entity1 relates to Entity2 how?]

## Integration Points

**Dependencies:**
- {Topic/Feature 1}: [What it provides]

**Provides to:**
- {Topic/Feature 2}: [What this topic provides]

## Technical Considerations

### Architecture
[Which layers involved: UI, Service, Data]

### Patterns
[State management, repositories, etc.]

### Libraries/APIs
[Third-party dependencies, external APIs]

## Related Diagrams

- `arch/system-architecture.mmd` — [How this component appears in the system architecture]
- `arch/data-model.mmd` — [Which entities from this spec appear in the data model]
- `arch/sequence-{flow}.mmd` — [Which interaction flow relates to this spec's workflows]

Only reference diagrams actually relevant to this spec's topic. Remove entries that don't apply.

## Acceptance Criteria
- [ ] [Criterion 1 — specific and testable]
- [ ] [Criterion 2 — specific and testable]
- [ ] [Criterion 3 — specific and testable]

## Testing Strategy

> **Include this section ONLY if the spec covers a TDD-flagged component.**
> Delete this section entirely for non-TDD specs.

**TDD Required:** Yes (flagged during planning)
**TDD Diagrams:** `arch/tdd-{component}-logic.mmd`, `arch/tdd-{component}-decision.mmd`

### Test Cases (from TDD diagrams)

#### Happy Path
1. **[Test name]** — Input: [inputs] → Expected: [outputs]
2. **[Test name]** — Input: [inputs] → Expected: [outputs]

#### Edge Cases
3. **[Test name]** — Input: [boundary input] → Expected: [behavior]
4. **[Test name]** — Input: [boundary input] → Expected: [behavior]

#### Error Conditions
5. **[Test name]** — Input: [invalid input] → Expected: [error behavior]
6. **[Test name]** — Input: [invalid input] → Expected: [error behavior]

### Test Data Requirements
- [Mock objects or fixtures needed]
- [Edge case data values]

## Requirement Index

| ID | Section | Status |
|----|---------|--------|
| {PREFIX}-F1 | Functional | Active |
| {PREFIX}-F2 | Functional | Active |
| {PREFIX}-F3 | Functional | Active |
| {PREFIX}-NF1 | Non-Functional | Active |
| {PREFIX}-NF2 | Non-Functional | Active |
| {PREFIX}-NF3 | Non-Functional | Active |

## Open Questions
- [ ] Question 1?
- [ ] Question 2?
```

---

## Topic Scope Validation

**"One Sentence Without 'And'" Test:**

Before writing a spec, validate the topic scope:

- **Can you describe it in one sentence without using "and" to join unrelated capabilities?**

**Pass:**
- "The color extraction system analyzes images to identify dominant colors"
- "Image upload handles file selection and validates uploaded images" (related capabilities)

**Fail - Split into multiple topics:**
- "The user system handles authentication, profiles, and billing" → 3 topics
- "The data layer manages storage and synchronization and caching" → 3 topics

---

## Section Reference

| Section | Required | Notes |
|---------|----------|-------|
| Overview | Always | Must pass "one sentence without and" test |
| Changelog | Always | Track all spec changes; "Created" entry on generation |
| Parent JTBD | Always | Links spec to business value |
| Scope | Always | Prevents scope creep |
| Requirements | Always | Functional + non-functional, each with `{PREFIX}-{CAT}{N}` ID |
| User Workflows | Always | At least one workflow per spec |
| Data Model | Always | Even if "no new entities" |
| Integration Points | Always | Dependencies and provides-to |
| Technical Considerations | Always | Architecture, patterns, libraries |
| Related Diagrams | Always | Cross-reference to `arch/*.mmd` files |
| Acceptance Criteria | Always | Every functional requirement must have at least one |
| Testing Strategy | TDD only | Only for TDD-flagged components |
| Requirement Index | Always | Maps all IDs to section and status (Active/Deprecated) |
| Open Questions | If needed | Must be resolved before implementation |
