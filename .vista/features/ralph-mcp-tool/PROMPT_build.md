**CRITICAL**: This is a BUILD iteration. You MUST write code. Analysis-only iterations are FAILURES.

PROJECT: vista
FEATURE: ralph-mcp-tool
FEATURE_DIR: C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/features/ralph-mcp-tool

## Step 0: Study Planning Artifacts

0a. Read `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/features/ralph-mcp-tool/arch/_arch.json` to discover all architecture and TDD diagrams.
0b. Read ALL `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/features/ralph-mcp-tool/arch/*.mmd` files — architecture diagrams for system context, TDD diagrams for test contracts.
0c. Study `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/features/ralph-mcp-tool/specs/*` with up to 500 parallel Sonnet subagents to learn the application specifications.
0d. Study @IMPLEMENTATION_PLAN.md.
0e. For reference, the application source code is in src/*.

## TDD-First Discipline

Check `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/features/ralph-mcp-tool/domain-requirements.md` for `## TDD Candidates` and `## Test Expectations` sections. Check each spec's `## Testing Strategy` section.

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

## Step 1: Implement

Your task is to implement functionality per the specifications using parallel subagents. Follow @IMPLEMENTATION_PLAN.md and choose the most important item to address. Before making changes, search the codebase (don't assume not implemented) using Sonnet subagents. You may use up to 500 parallel Sonnet subagents for searches/reads and only 1 Sonnet subagent for build/tests. Use Opus subagents when complex reasoning is needed (debugging, architectural decisions).

After implementing functionality or resolving problems, run the tests for that unit of code that was improved. If functionality is missing then it's your job to add it as per the application specifications. Ultrathink.

When you discover issues, immediately update @IMPLEMENTATION_PLAN.md with your findings using a subagent. When resolved, update and remove the item.

When the tests pass, update @IMPLEMENTATION_PLAN.md, then git add -A then git commit with a message describing the changes. After the commit, git push.

Important: When authoring documentation, capture the why — tests and implementation importance.

Important: Single sources of truth, no migrations/adapters. If tests unrelated to your work fail, resolve them as part of the increment.

As soon as there are no build or test errors create a git tag. If there are no git tags start at 0.0.0 and increment patch by 1 for example 0.0.1 if 0.0.0 does not exist.

You may add extra logging if required to debug issues.

Keep @IMPLEMENTATION_PLAN.md current with learnings using a subagent — future work depends on this to avoid duplicating efforts. Update especially after finishing your turn. 9999999999. When you learn something new about how to run the application, update @AGENTS.md using a subagent but keep it brief. For example if you run commands multiple times before learning the correct command then that file should be updated. 99999999999. For any bugs you notice, resolve them or document them in @IMPLEMENTATION_PLAN.md using a subagent even if it is unrelated to the current piece of work. 999999999999. Implement functionality completely. Placeholders and stubs waste efforts and time redoing the same work. 9999999999999. When @IMPLEMENTATION_PLAN.md becomes large periodically clean out the items that are completed from the file using a subagent. 99999999999999. If you find inconsistencies in the specs/* then use an Opus 4.5 subagent with 'ultrathink' requested to update the specs. 999999999999999. IMPORTANT: Keep @AGENTS.md operational only — status updates and progress notes belong in IMPLEMENTATION_PLAN.md. A bloated AGENTS.md pollutes every future loop's context.


# Post-Implementation (Only after code is written)

## 1. Update progress.txt
APPEND to `C:/Users/Grove/OneDrive/Documents/PYTHON/claude_plugins/vista/.vista/features/ralph-mcp-tool/progress.txt`:
```
---
Time: [timestamp]
Iteration: [number]

CODE CHANGES MADE:
- [file]: [what you changed]
- [file]: [what you changed]

Tests: [pass/fail]
Commit: [commit hash or "pending"]
---
```

# RALPH_CONTROL

End your response with:
```
# RALPH_CONTROL
status: done
files_changed: [count]
```
