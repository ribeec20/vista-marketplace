# Acceptance Criteria Format

Guide for writing acceptance criteria in topic specifications.

---

## Purpose

Acceptance criteria define **specific, testable checkpoints** that verify a spec's requirements are met. Every functional requirement in a spec must have at least one corresponding acceptance criterion.

---

## Format

Each acceptance criterion is a checkbox item with a clear, verifiable statement:

```markdown
## Acceptance Criteria
- [ ] [Specific testable statement]
- [ ] [Specific testable statement]
```

---

## Categories

Organize acceptance criteria by category when a spec has many:

| Category | Purpose | Example |
|----------|---------|---------|
| Functional | Core feature behavior | "User can upload images from device gallery" |
| Performance | Speed, load, throughput | "Image upload completes within 2 seconds for 5MB files" |
| Security | Auth, permissions, data | "Unauthenticated users are redirected to login" |
| Error Handling | Error states, recovery | "Network error displays retry option" |
| UI/UX | Design, interaction | "Upload button shows loading state during transfer" |
| Accessibility | A11y compliance | "Screen reader announces upload progress" |

---

## Writing Rules

1. **Be specific** — "User can upload images" not "Upload feature works"
2. **Be testable** — Can someone verify this with a yes/no answer?
3. **Include boundaries** — "Handles files up to 10MB" not "Handles large files"
4. **Cover error paths** — Not just happy paths
5. **One criterion per item** — Don't combine multiple checks

---

## Good vs Bad Examples

### Bad (Vague)
```markdown
- [ ] The feature works correctly
- [ ] Performance is acceptable
- [ ] Errors are handled
```

### Good (Specific + Testable)
```markdown
- [ ] User can select 1-10 images from device gallery in a single selection
- [ ] 5MB image uploads complete within 2 seconds on broadband connection
- [ ] When upload fails due to network error, a retry button appears with the error message
- [ ] Uploaded images appear in the mood board within 500ms of upload completion
- [ ] Attempting to upload a file > 10MB shows "File too large (max 10MB)" error
```

---

## Deriving Criteria from Spec Sections

### From Functional Requirements
Each requirement → at least one criterion.

```markdown
## Requirements
### Functional
1. Users can select images from their device gallery

## Acceptance Criteria
- [ ] User can select images from device gallery
- [ ] Multiple image selection (up to 10) is supported
- [ ] Selected images show preview thumbnails before upload
```

### From User Workflows
Each workflow step → verify it works. Each error case → verify handling.

```markdown
## User Workflows
### Workflow: Image Upload
Error Cases:
- Network timeout: Show retry option

## Acceptance Criteria
- [ ] Network timeout during upload shows retry button
- [ ] Retrying a timed-out upload resumes from where it left off
```

### From Non-Functional Requirements
Each metric → criterion with specific number.

```markdown
## Requirements
### Non-Functional
- Performance: < 2s upload time for 5MB images

## Acceptance Criteria
- [ ] 5MB image uploads complete within 2 seconds
```

---

## Completeness Checklist

Before finalizing acceptance criteria for a spec:

- [ ] Every functional requirement has at least one criterion
- [ ] Every non-functional requirement with a metric has a criterion
- [ ] Every error case from user workflows has a criterion
- [ ] Criteria are specific enough to verify with yes/no
- [ ] No criterion combines multiple unrelated checks
- [ ] Edge cases from domain requirements are covered
