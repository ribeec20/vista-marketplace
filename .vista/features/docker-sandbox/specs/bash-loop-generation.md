# Spec: Bash Loop Generation

## Overview
Generates Linux bash loop scripts for containerized execution, translating the existing PowerShell template into bash with provider-specific invocation blocks.

## Changelog
| Date | ID | Change | Reason | Commit |
|------|-----|--------|--------|--------|
| 2026-02-12 | --- | Created | Initial spec generation | --- |

## Parent JTBD
Produce executable bash scripts that run inside Linux Docker containers, enabling the same agent loop logic currently implemented in PowerShell to work in the sandboxed environment.

## Scope
**In Scope:**
- BashLoopGenerator class that produces bash script content from parameters
- Bash template equivalent to the existing PowerShell LOOP_SCRIPT_TEMPLATE
- Provider-specific invocation blocks for Claude Code and OpenCode (bash variants)
- Variable substitution: project root, feature dir, model, iterations, provider
- Script uses Linux paths (`/workspace/...`) as baked-in absolute paths
- Generated script is syntactically valid bash executable in a Linux shell

**Out of Scope:**
- PowerShell script generation (existing code, unchanged)
- Script execution or launching (see container-lifecycle and ralph-sandbox-integration specs)
- Prompt template content generation (existing PROMPT_{plan,build}_adhoc.md logic)
- Agent CLI installation inside containers (handled by Docker image)
- Git operations within the script (handled by agent, not loop script)

## Requirements
### Functional
1. **DS-F34:** BashLoopGenerator SHALL produce a bash script string from the following parameters: `mode`, `max_iterations`, `model`, `feature_name`, `feature_dir_abs`, `project_root_abs`, `provider_name`, `invocation_block`.
2. **DS-F35:** The generated bash script SHALL include a shebang line (`#!/bin/bash`) and `set -e` for fail-fast behavior.
3. **DS-F36:** The generated script SHALL set variables for `FeatureDir`, `ProjectRoot`, `PromptFile`, `ProgressFile`, and `TaskFile` using Linux path syntax.
4. **DS-F37:** The generated script SHALL implement an iteration loop that respects `MaxIterations` (0 = unlimited) and increments a counter each pass.
5. **DS-F38:** The generated script SHALL include the provider-specific invocation block that calls the agent CLI (claude or opencode) with the correct arguments.
6. **DS-F39:** Provider.get_invocation("sh") SHALL return a bash invocation block for Claude Code that calls `claude -p --dangerously-skip-permissions` with the prompt file content piped or passed as argument.
7. **DS-F40:** Provider.get_invocation("sh") SHALL return a bash invocation block for OpenCode that calls `opencode run` with the appropriate prompt argument.
8. **DS-F41:** The generated script SHALL read the current git branch and display a startup banner with feature name, provider, mode, model, branch, and iteration limit.
9. **DS-F42:** The generated script SHALL verify the prompt file exists before entering the loop, exiting with code 1 if missing.
10. **DS-F43:** All paths in the generated script SHALL use `/workspace` as the project root prefix, matching the container mount point.
11. **DS-F44:** The generated script SHALL append iteration output to `output.log` in the job directory so that the dashboard can parse activity.

### Non-Functional
1. **DS-NF8:** BashLoopGenerator SHALL be a pure function (or stateless class) with no filesystem or Docker dependencies.
2. **DS-NF9:** Generated scripts SHALL use POSIX-compatible bash syntax to work in any standard Linux container.

## User Workflows
### Workflow: Bash Script Generated for Sandboxed Job
**Actor:** RalphService (internal caller)
**Trigger:** `create_job()` with `sandbox=true`
**Steps:**
1. RalphService determines job parameters (mode, iterations, model, provider, paths)
2. RalphService computes container-relative paths: feature_dir_abs = `/workspace/.vista/ralph/{job}/`, project_root_abs = `/workspace`
3. RalphService calls `BashLoopGenerator.generate(params)` (or `Provider.get_invocation("sh")` for invocation block)
4. BashLoopGenerator substitutes parameters into bash template
5. Returns bash script string
6. RalphService writes script to `{job_dir}/loop.sh` on host filesystem
7. ContainerManager starts container with command `bash /workspace/.vista/ralph/{job}/loop.sh`
**Error Cases:**
- Invalid mode: raises ValueError (same validation as native path)
- Empty invocation block: raises ValueError

### Workflow: Script Executes Inside Container
**Actor:** Docker container
**Trigger:** Container started with loop.sh command
**Steps:**
1. Bash interpreter reads loop.sh from mounted volume
2. Script sets variables using `/workspace` paths
3. Script verifies prompt file exists at `/workspace/.vista/ralph/{job}/PROMPT_{mode}.md`
4. Script displays startup banner
5. Script enters iteration loop
6. Each iteration: calls agent CLI with prompt, appends output to output.log
7. Loop exits when max iterations reached or agent signals completion
**Error Cases:**
- Prompt file not found: script exits with code 1
- Agent CLI not found in container: bash reports command not found, loop exits with error
- Agent returns non-zero: script continues to next iteration (agent errors are expected sometimes)

## Data Model
**Entities:**
- `BashLoopParams`: `mode` (str: "plan" or "build"), `max_iterations` (int), `model` (str), `feature_name` (str), `feature_dir_abs` (str, Linux path), `project_root_abs` (str, `/workspace`), `provider_name` (str), `invocation_block` (str, bash code)

**Relationships:**
- BashLoopParams is constructed by RalphService from job configuration
- The generated script is written to the job directory and executed by the container

## Integration Points
**Dependencies:**
- Provider.get_invocation("sh"): returns bash invocation block per provider
- RalphService: provides job parameters and writes generated script to disk
- Existing LOOP_SCRIPT_TEMPLATE: reference for logic parity with PowerShell version

**Provides to:**
- RalphService: bash script content for sandboxed job creation
- Container: executable loop.sh that drives the agent loop

## Technical Considerations
### Architecture
- BashLoopGenerator can be implemented as:
  - A `BASH_LOOP_SCRIPT_TEMPLATE` constant (parallel to existing `LOOP_SCRIPT_TEMPLATE`) with `.format()` substitution, OR
  - A class with a `generate()` method for more complex logic
- Location: `portable/ralph.py` (alongside existing template) or dedicated `server/services/bash_loop_generator.py`
- Provider invocation blocks: extend existing `Provider.get_invocation()` to support "sh" format parameter

### Patterns
- Template method pattern: same logical structure as PowerShell template, different syntax
- String formatting with `.format()` and double-brace escaping for bash syntax (same as existing PS1 template)

### Libraries/APIs
- No external dependencies; pure string generation
- Consider `textwrap.dedent` for template readability

### Template Structure (bash equivalent of existing PS1)
```
#!/bin/bash
set -e

# Feature Loop - Auto-generated by ralph.py
MODE="{mode}"
MAX_ITERATIONS={max_iterations}
MODEL="{model}"
FEATURE_DIR="{feature_dir_abs}"
PROJECT_ROOT="{project_root_abs}"
PROMPT_FILE="$FEATURE_DIR/PROMPT_$MODE.md"
PROGRESS_FILE="$FEATURE_DIR/progress.txt"
TASK_FILE="$FEATURE_DIR/task.md"

CURRENT_BRANCH=$(git branch --show-current)

# Startup banner
echo "..."

# Verify prompt
[ -f "$PROMPT_FILE" ] || { echo "Error: $PROMPT_FILE not found"; exit 1; }

ITERATION=0
while true; do
    if [ $MAX_ITERATIONS -gt 0 ] && [ $ITERATION -ge $MAX_ITERATIONS ]; then
        echo "Reached max iterations: $MAX_ITERATIONS"
        break
    fi
    ITERATION=$((ITERATION + 1))
    echo "=== Iteration $ITERATION ==="

    {invocation_block}

    # Post-iteration: git add/commit/push handled by agent
done
```

### Provider Invocation Blocks (bash)
**Claude Code:**
```bash
claude -p --dangerously-skip-permissions -m "$MODEL" < "$PROMPT_FILE" 2>&1 | tee -a "$FEATURE_DIR/output.log"
```

**OpenCode:**
```bash
opencode run -m "$MODEL" "$(cat $PROMPT_FILE)" 2>&1 | tee -a "$FEATURE_DIR/output.log"
```

## Related Diagrams
- `arch/user-flow.mmd` -- "Generate bash loop script for Linux container" step in sandboxed path
- `arch/sequence-sandboxed-job.mmd` -- Script generation step between job directory setup and container creation

## Acceptance Criteria
- [ ] DS-F34: Generated script includes all substituted parameters (mode, iterations, model, paths, provider)
- [ ] DS-F35: Script starts with `#!/bin/bash` and includes `set -e`
- [ ] DS-F36: All path variables use Linux syntax with forward slashes
- [ ] DS-F37: Iteration loop respects max_iterations=5 (exits after 5), max_iterations=0 (runs indefinitely)
- [ ] DS-F38: Script contains the provider-specific invocation block
- [ ] DS-F39: Claude invocation uses `claude -p --dangerously-skip-permissions -m "$MODEL"`
- [ ] DS-F40: OpenCode invocation uses `opencode run -m "$MODEL"`
- [ ] DS-F41: Startup banner includes feature name, provider, mode, model, branch, iteration limit
- [ ] DS-F42: Script exits with code 1 if prompt file does not exist
- [ ] DS-F43: feature_dir_abs and project_root_abs use `/workspace` prefix
- [ ] DS-F44: Output is appended to output.log in the job directory
- [ ] DS-NF8: BashLoopGenerator has no filesystem or Docker imports
- [ ] DS-NF9: Generated script uses POSIX-compatible bash syntax

## Testing Strategy
> BashLoopGenerator is a TDD-flagged component

**TDD Required:** Yes
**TDD Diagrams:** N/A (string output validation, no state machine)

### Test Cases (from domain requirements Layer 4)
#### Happy Path
- `test_generates_valid_bash_syntax`: Output starts with shebang, includes set -e, valid bash structure
- `test_claude_invocation_block`: Claude provider produces correct `claude -p` invocation in bash
- `test_opencode_invocation_block`: OpenCode provider produces correct `opencode run` invocation in bash
- `test_variable_substitution_complete`: All format placeholders replaced (no `{` or `}` remaining)
- `test_linux_paths_used`: feature_dir_abs and project_root_abs contain `/workspace` prefix
- `test_iteration_limit_set`: max_iterations=5 produces correct loop condition
- `test_unlimited_iterations`: max_iterations=0 produces unlimited loop
- `test_startup_banner_present`: Output contains feature name, provider name, mode, model
- `test_prompt_file_check_present`: Script contains prompt file existence check with exit 1
- `test_output_log_append`: Invocation block includes append to output.log

#### Edge Cases
- `test_special_characters_in_feature_name`: Feature name with spaces/dashes handled correctly
- `test_model_name_with_slashes`: Model names like "claude-3.5-sonnet" substituted correctly
- `test_empty_invocation_block_rejected`: Raises ValueError
- `test_mode_plan_vs_build`: Different modes produce different prompt file paths
- `test_bash_escaping`: Double braces in template do not conflict with bash syntax

#### Error Conditions
- `test_invalid_mode_rejected`: Mode other than "plan" or "build" raises ValueError
- `test_missing_required_parameter`: Missing feature_dir_abs raises error
- `test_windows_path_rejected`: Path containing backslash raises error (must use Linux paths)

### Test Data Requirements
- Test parameter sets for Claude and OpenCode providers
- Expected bash output strings for comparison
- Known-good invocation blocks for each provider
- Edge case strings: names with special characters, models with dots/slashes

## Requirement Index
| ID | Section | Status |
|----|---------|--------|
| DS-F34 | Functional | Active |
| DS-F35 | Functional | Active |
| DS-F36 | Functional | Active |
| DS-F37 | Functional | Active |
| DS-F38 | Functional | Active |
| DS-F39 | Functional | Active |
| DS-F40 | Functional | Active |
| DS-F41 | Functional | Active |
| DS-F42 | Functional | Active |
| DS-F43 | Functional | Active |
| DS-F44 | Functional | Active |
| DS-NF8 | Non-Functional | Active |
| DS-NF9 | Non-Functional | Active |

## Open Questions
- [ ] Should the bash template live in `portable/ralph.py` alongside the PS1 template, or in a separate file?
- [ ] Should `tee -a` be used for output.log, or should stdout/stderr be redirected with `>>`?
- [ ] How should the script handle agent CLI not found (e.g., claude not on PATH in container)?
- [ ] Should the script source any container-specific environment setup (e.g., `/etc/profile`)?
