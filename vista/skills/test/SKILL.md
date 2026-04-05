---
name: test
description: Generate tests for a feature or component. Tests exercise the real codebase — no duplicated logic or re-implementations. Use when the user wants to add tests.
disable-model-invocation: true
argument-hint: <feature-or-file>
---

# Test

Generate tests for the specified feature or component.

## Rules

- Tests must call the real code — never duplicate or re-implement the logic under test
- Match the project's existing test framework, file naming, and patterns
- Read the source code first to understand what to test
- Focus on behavior and edge cases, not implementation details
- Use **AskUserQuestion** if scope is unclear
- Run the tests after generating them and fix any failures
