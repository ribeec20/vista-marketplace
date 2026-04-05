---
name: test
description: |
  Generate and run tests for a Vista feature based on its specs, TDD diagrams, and implementation. Use when: (1) User runs /vista:test, (2) User wants to generate tests for a planned feature, (3) User wants to validate implementation against specs and acceptance criteria.
disable-model-invocation: true
argument-hint: <feature-name>
---

# Vista Test

Generate and run tests for a Vista feature using its planning artifacts (specs, TDD diagrams, acceptance criteria) as the test contract.

## Invocation

```
/vista:test <feature-name>
```

## Prerequisites

- Feature must exist at `.vista/features/<name>/`
- Specs should exist in `specs/` (run `/vista:specs` first)
- Implementation code should exist (run Ralph build loop first)

## Workflow

### Step 1: Load Planning Artifacts

1. Read `.vista/features/<name>/domain-requirements.md`
2. Read all spec files in `.vista/features/<name>/specs/*.md`
3. Read `arch/_arch.json` and any TDD diagrams (`arch/tdd-*.mmd`)
4. Scan the codebase for implementation files related to this feature

Present a summary:
```
Loaded artifacts for <feature-name>:
- Specs: [N] topic specs
- TDD diagrams: [M] diagrams (components: A, B, C)
- Acceptance criteria: [X] total criteria across specs
- Implementation files found: [list key files]
```

### Step 2: Identify Test Targets

#### 2a. Extract testable contracts

From the planning artifacts, extract:
- **Acceptance criteria** from each spec's `## Acceptance Criteria` section
- **Test cases** from any `## Testing Strategy` sections (TDD-flagged components)
- **Business rules** from spec requirements (IDs like `PREFIX-BR1`)
- **User workflows** from spec workflow definitions
- **State transitions** from state diagrams (`arch/tdd-*-states.mmd`)
- **Decision paths** from decision trees (`arch/tdd-*-decision.mmd`)

#### 2b. Confirm scope with user

Use **AskUserQuestion**:
```
I identified these test targets:

1. **[Component]** — [N] test cases from TDD diagrams + [M] acceptance criteria
2. **[Workflow]** — [N] workflow steps to validate
3. **[Integration]** — [N] integration points to test

Should I generate tests for all of these, or focus on specific areas?
```

### Step 3: Detect Test Framework

Examine the project to determine the testing setup:
- Look for existing test files, `pytest.ini`, `vitest.config`, `jest.config`, `package.json` test scripts
- Check language/framework (Python → pytest, TypeScript/JS → vitest/jest, etc.)
- Match existing test patterns (file naming, directory structure, assertion style)

If no test framework is configured, ask the user which framework to use via **AskUserQuestion**.

### Step 4: Generate Tests

For each confirmed test target, generate test files following the project's existing patterns.

#### TDD-flagged components (highest priority)

Use the TDD diagrams as the primary test contract:
- Each path through a logic flow diagram → one test case
- Each state transition → one test case (valid + invalid transitions)
- Each leaf in a decision tree → one test case

#### Acceptance criteria

Convert each acceptance criterion into a test:
- Map criterion text to concrete assertions
- Include setup/teardown for required test data

#### Workflow tests

For each user workflow in specs:
- Test the happy path end-to-end
- Test error cases documented in the workflow

Write test files to the project's test directory, following existing conventions for file naming and organization.

### Step 5: Run Tests

Execute the test suite:

```bash
# Python
pytest <test-files> -v

# JavaScript/TypeScript
bun run test <test-files>
# or: npx vitest run <test-files>
```

### Step 6: Report Results

Report to the user:

1. **Tests generated:** [N] test files with [M] total test cases
2. **Coverage:** Which specs/acceptance criteria are covered
3. **Results:** Pass/fail summary
4. **Gaps:** Any acceptance criteria or TDD cases not yet testable (e.g., requires manual testing, external service)
5. **Next steps:**
   - Fix failing tests or update implementation
   - Run `/vista:spec-update <feature> [topic]` if specs need updating based on test findings
