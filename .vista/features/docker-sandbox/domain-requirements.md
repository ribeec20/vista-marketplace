# Domain Requirements: Docker Sandbox

## Problem Statement

Ralph agent loops currently execute as direct OS subprocesses with full host access. An agent running `claude -p --dangerously-skip-permissions` or `opencode run` can read, write, and delete any file the user can access. There is no filesystem, network, or process isolation between the agent and the host system.

Docker sandbox mode adds opt-in per-job containerized execution, isolating agent loops inside ephemeral Docker containers while maintaining full project access through volume mounts.

## Users & Personas

- **Vista plugin user** — developer running Ralph loops for automated coding tasks. Wants confidence that agent mistakes (accidental deletions, runaway processes) are contained. Technical enough to have Docker installed.

## Business Objectives

- Provide security isolation as the primary value — prevent agent code execution from affecting files/processes outside the project
- Maintain the existing native execution path for users without Docker
- Keep the developer experience simple — sandbox should "just work" with minimal configuration

## Success Metrics

- Sandboxed jobs produce identical output.log / dashboard activity as native jobs
- Container startup adds < 10 seconds to job launch (with cached image)
- Orphan containers are never left running after Vista shuts down or crashes
- Zero credential leakage between containers or to host processes

## Functional Requirements

### Core Functionality

1. **Per-job sandbox toggle** — each Ralph job can be started with `sandbox: true/false`. No global mode; each job chooses independently.
2. **Full project mount** — the entire project root is mounted read-write at a fixed path inside the container (e.g., `/workspace`). Since `.vista/ralph/{job}/` lives inside the project, `output.log` and other job artifacts are automatically visible on the host filesystem through this single mount.
4. **Credential mounting** — host credential directories mounted read-only into the container:
   - `~/.claude/` — Claude Code auth state
   - `~/.ssh/` — Git SSH keys
   - `~/.gitconfig` — Git configuration
   - `~/.config/gh/` — GitHub CLI auth
   - `~/.config/opencode/` (or equivalent) — OpenCode auth/config
5. **Ephemeral containers** — fresh container created per job, auto-removed on completion. Docker image is cached for fast startup.
6. **Claudebox-based image** — use RchGrav/claudebox as the base Docker image, extended with Vista-specific tooling if needed.
7. **Auto-build on first use** — if the Docker image doesn't exist locally, build it automatically before running the first sandboxed job.
8. **Bash loop script generation** — always generate a bash (Linux) loop script for containerized execution, regardless of host OS (Windows/macOS).
9. **Both providers supported** — Claude Code and OpenCode can both run inside containers.
10. **Configurable network access** — default to full internet access; allow restricting to host-only network in settings.

### User Workflows

1. **Start sandboxed job**: User invokes Ralph MCP tool with `sandbox=true` → Vista checks Docker availability → builds image if missing → creates container with mounts → runs bash loop script inside container → job appears in dashboard with "Sandboxed" badge.
2. **Start native job**: User invokes Ralph with `sandbox=false` (or omits) → existing native execution path, unchanged.
3. **Stop sandboxed job**: User stops job → Vista issues `docker stop` on the container → container auto-removes → job marked stopped.
4. **View sandboxed job status**: Dashboard reads `output.log` from shared volume (same path as native) → parser produces activity → displayed with sandbox badge.

### Business Rules

- Docker must be installed and running to use sandbox mode. If unavailable, return a clear error — never silently fall back to native execution.
- Containers auto-expire via TTL (e.g., `--stop-timeout` or healthcheck-based) to prevent orphans if Vista crashes.
- Container labels (`managed-by=vista`, `vista-job-id=...`) enable cleanup and identification.
- No resource limits in v1 — containers use host resources freely.

## Non-Functional Requirements

- **Performance**: Container startup < 10s with cached image. Image build may take 2-5 minutes on first use (acceptable).
- **Platform**: Windows (Docker Desktop), macOS (Docker Desktop), Linux (Docker Engine). All hosts run Linux containers.
- **Security**: Credential directories mounted read-only. Container runs as non-root user with UID/GID matching host user. No `--privileged` flag.
- **Reliability**: Orphan cleanup via container TTL. Vista startup can optionally scan for and remove stale vista-labeled containers.

## Constraints & Dependencies

- **Docker SDK**: `docker` Python package (pip install docker) — imported lazily to avoid breaking the plugin when Docker isn't installed.
- **ClaudeBox**: Base Docker image from github.com/RchGrav/claudebox. Need to evaluate if it ships pre-built images or requires local Dockerfile build.
- **Credential paths**: Vary by OS — need path translation (e.g., Windows `C:\Users\X\.ssh` → Linux `/home/user/.ssh` inside container).
- **Git operations**: Loop scripts push to git remotes — container needs network access and valid git credentials.
- **Docker Desktop licensing**: Users are responsible for their own Docker Desktop license compliance.

## User Experience Requirements

- **Discovery**: Sandbox option exposed as a parameter on the `ralph_start` MCP tool and visible in the dashboard job creation UI.
- **Feedback**: "Building Docker image..." progress message on first use. "Sandboxed" badge on running/completed jobs in dashboard.
- **Error handling**:
  - Docker not installed → clear error message with install instructions link
  - Docker not running → "Docker daemon is not running. Please start Docker Desktop."
  - Image build failure → show build logs, suggest `rebuild` action
  - Container crash → mark job as failed, preserve output.log for debugging

## API Design

Extend existing `/api/ralph/` routes:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ralph/jobs` | POST | Extended: accept `sandbox: true` in job creation payload |
| `/api/ralph/jobs/{id}` | GET | Extended: include `sandbox`, `container_id` in response |
| `/api/ralph/jobs/{id}/stop` | POST | Extended: issue `docker stop` for sandboxed jobs |
| `/api/ralph/sandbox/status` | GET | Docker availability check (installed, running, image exists) |
| `/api/ralph/sandbox/build` | POST | Trigger image build/rebuild |

MCP tools updated later once API is validated.

## Testing & Debugging Strategy

### Development Workflow — No Plugin Reload Required

All sandbox code lives in `server/services/` and can be imported and tested directly with pytest. No commit-push-reload cycle needed during development:

```bash
# From vista/ directory — runs tests directly against source
python -m pytest tests/test_container_manager.py -v
python -m pytest tests/test_credential_mounter.py -v
```

The existing test infrastructure (conftest.py fixtures, patched_config, tmp_path) supports this. Services are standalone Python — no MCP or FastAPI dependency.

### Test Layers (Build Incrementally)

**Layer 1: Docker SDK connection** (first thing to validate)
- Can we import the `docker` Python package?
- Can we connect to the Docker daemon (`docker.from_env()`)?
- Can we list images, pull/build an image?
- Test: `test_docker_connection.py` — skipped if Docker not installed (`@pytest.mark.skipif`)

**Layer 2: Container lifecycle with mocked Docker**
- ContainerManager creates container with correct mounts and labels
- Container start/stop/remove calls are issued correctly
- TTL expiry triggers cleanup
- Error paths: daemon unreachable, image not found, container crash
- Test: `test_container_manager.py` — uses `unittest.mock` to mock `docker.DockerClient`

**Layer 3: Credential mounting**
- Host credential paths resolve correctly per OS
- Mount specs generated with correct source/target/mode
- Missing credential dirs handled gracefully (skip, don't fail)
- Path translation: Windows `C:\Users\X\.ssh` → container `/home/user/.ssh`
- Test: `test_credential_mounter.py` — pure logic, no Docker needed

**Layer 4: Bash loop script generation**
- Template produces valid bash syntax
- Provider-specific invocation blocks are correct (claude vs opencode)
- Variable substitution works (project root, feature dir, model, iterations)
- Generated script is executable in a Linux shell
- Test: `test_bash_loop_generator.py` — string output validation

**Layer 5: Integration with real Docker** (requires Docker running)
- Build image from Dockerfile
- Create container with real project mount
- Verify files visible inside container (`docker exec ls /workspace`)
- Verify credential mounts are read-only
- Verify output.log written inside container appears on host
- Run a trivial bash script and capture output
- Test: `tests/integration/test_docker_sandbox.py` — marked `@pytest.mark.docker`

**Layer 6: End-to-end sandboxed Ralph job**
- create_job with sandbox=true → container runs → output.log populated → dashboard parses activity
- stop_job → container stopped and removed
- Test: `tests/integration/test_sandboxed_ralph.py` — marked `@pytest.mark.docker`

### Running Integration Tests

```bash
# Unit tests only (no Docker needed, fast)
python -m pytest tests/test_container_manager.py tests/test_credential_mounter.py -v

# Integration tests (Docker must be running)
python -m pytest tests/integration/test_docker_sandbox.py -v -m docker

# All sandbox tests
python -m pytest tests/ -k sandbox -v
```

### Debugging Checklist

When something fails, check in this order:

1. **Docker reachable?** — `docker info` from host terminal
2. **Image exists?** — `docker images | grep vista-ralph`
3. **Container created?** — `docker ps -a --filter label=managed-by=vista`
4. **Mounts correct?** — `docker inspect <container_id>` → check Mounts section
5. **Script runs?** — `docker exec <container_id> cat /workspace/.vista/ralph/{job}/loop.sh`
6. **Output flowing?** — check `output.log` on host filesystem in the job directory
7. **Credentials accessible?** — `docker exec <container_id> ls /home/user/.claude/`

### Key Principle

Each layer can be developed and tested independently. Start at Layer 1, get it green, move to Layer 2. A failure at any layer has a clear, narrow scope to debug.

## TDD Candidates

- **ContainerManager**: Core lifecycle logic (create, start, stop, cleanup) with Docker SDK calls — many failure modes, needs thorough testing with mocked Docker client
- **CredentialMounter**: Path translation across OS + mount specification generation — complex cross-platform logic with security implications
- **SandboxJobCreator**: Branching logic between native and sandboxed execution paths — integration point with many edge cases (Docker unavailable, image missing, mount failures)
- **BashLoopGenerator**: Generating Linux bash scripts from the existing PowerShell template — template substitution with provider-specific invocation blocks

## Test Expectations

Derived from TDD diagrams in `arch/tdd-*.mmd`. Each subsection maps directly to testable assertions.

### ContainerManager

**Source diagrams**: `tdd-container-manager-states.mmd`, `tdd-container-manager-logic.mmd`

**Inputs**:
- `image_name: str` (default `"vista-ralph:latest"`)
- `mounts: list[MountSpec]` (project mount + credential mounts)
- `labels: dict[str, str]` (`managed-by`, `vista-job-id`)
- `env_vars: dict[str, str]` (optional)
- `network_mode: str` (`"bridge"` or `"host"`)
- `ttl_seconds: int` (default `7200`)

**Happy path**:
- `create_and_start()` with valid inputs returns `ContainerResult(container_id, image, status="running", expires_at)`
- Docker client receives `containers.create()` with correct image, mounts, labels, auto_remove=True, detach=True
- Docker client receives `container.start()`
- Container registered in `_active_containers` with TTL expiry time
- State transitions: Uninitialized -> ImageChecking -> Creating -> Starting -> Running

**Edge cases**:
- Image not found locally triggers `images.build()` then proceeds to create
- `stop_container()` from Running state issues `container.stop()` and transitions to Removed
- TTL expiry transitions Running -> Expired -> Removed via `force_remove_container()`
- Calling `stop_container()` on an already-stopped container is idempotent (no error)
- Empty mounts list is valid (no credential mounts, only project mount externally added)

**Error conditions**:
- Docker daemon unreachable -> `DockerNotAvailableError` with message "Docker daemon is not running. Please start Docker Desktop."
- Image build failure -> `ImageBuildError` with build log output
- Invalid mount path (host_path does not exist) -> `MountValidationError` with the specific path
- Container create fails -> `ContainerCreateError` with Docker API error detail
- Container start fails -> `ContainerStartError`, cleanup attempted via `container.remove(force=True)`
- Container crash during execution -> `ContainerCrashedError`, output.log preserved for debugging

**State machine rejection tests** (from states diagram):
- Calling `start_container()` from Uninitialized -> rejected
- Calling `create_container()` from Running -> rejected
- Calling `ensure_image()` from Running -> rejected
- Calling `stop_container()` from Uninitialized -> rejected

### CredentialMounter

**Source diagrams**: `tdd-credential-mounter-logic.mmd`, `tdd-credential-mounter-decision.mmd`

**Inputs**:
- `host_os: str` (`"windows"`, `"darwin"`, or `"linux"`)
- `credential_config: dict` (per-credential enabled flag + optional host_path_override)

**Happy path**:
- All 5 credentials enabled + paths exist -> returns 5 `MountSpec` objects, each with `mode="ro"`
- Each MountSpec has correct `source` (host path), `target` (container path), `type="bind"`
- `.gitconfig` is mounted as a file (not directory)
- All other credentials mounted as directories

**Edge cases — path resolution per OS** (one test per leaf in decision tree):

| Credential | Windows host | macOS host | Linux host | Container target |
|---|---|---|---|---|
| claude_auth | `%USERPROFILE%\.claude` | `~/.claude` | `~/.claude` | `/home/user/.claude` |
| git_ssh | `%USERPROFILE%\.ssh` | `~/.ssh` | `~/.ssh` | `/home/user/.ssh` |
| gitconfig | `%USERPROFILE%\.gitconfig` | `~/.gitconfig` | `~/.gitconfig` | `/home/user/.gitconfig` |
| github_cli | `%APPDATA%\GitHub CLI` | `~/.config/gh` | `~/.config/gh` | `/home/user/.config/gh` |
| opencode | `%APPDATA%\opencode` | `~/.config/opencode` | `~/.config/opencode` | `/home/user/.config/opencode` |

**Edge cases — missing and disabled**:
- Credential path does not exist on disk -> skip gracefully, log warning, do not fail
- Credential explicitly disabled in config -> skip, no path resolution attempted
- All credentials missing -> return empty list (valid result, not an error)
- `host_path_override` in config -> use override instead of default path for that OS
- `~` expansion works correctly on all platforms

**Error conditions**:
- None that raise exceptions. All failures are graceful skips. The return is always a valid list (possibly empty).

### SandboxJobCreator

**Source diagram**: `tdd-sandbox-job-creator-logic.mmd`

**Inputs**:
- `task: str`, `provider: str`, `model: str`, `mode: str`, `max_iterations: int`
- `sandbox: bool` (must be `True` for sandbox flow)
- `feature_dir: str`

**Happy path**:
- `sandbox=True` -> Docker available -> image exists -> job dir created -> bash loop.sh generated -> credential mounts resolved -> container created with project mount + cred mounts + labels -> container started -> job.json written with `container_id` and `sandbox: true` -> returns `JobResult`
- Job directory contains: `task.md`, `PROMPT_{mode}.md`, `loop.sh`
- Container command is `["bash", "/workspace/.vista/ralph/{job_id}/loop.sh"]`
- Container labels include `managed-by=vista` and `vista-job-id={job_id}`
- Project root mounted at `/workspace` read-write

**Edge cases**:
- `sandbox=False` -> delegates to native `create_job()` (no Docker interaction at all)
- Image does not exist but builds successfully -> proceeds normally
- Some credential paths missing -> container created with partial credential mounts (no failure)
- `max_iterations=0` -> script generated with unlimited loop

**Error conditions**:
- Docker not available -> `DockerNotAvailableError`, no job directory created
- Image build fails -> `ImageBuildError`, no job directory created
- Script generation fails -> `ScriptGenerationError`, job directory cleaned up
- Container create fails -> `ContainerCreateError`, job directory cleaned up
- Container start fails -> `ContainerStartError`, container removed, job directory cleaned up
- Each error condition must not leave orphan resources (directories, containers)

### BashLoopGenerator

**Source diagram**: `tdd-bash-loop-logic.mmd`

**Inputs**:
- `provider: str` (`"claude"` or `"opencode"`)
- `model: str`, `mode: str` (`"plan"` or `"build"`)
- `max_iterations: int` (>= 0)
- `feature_dir: str`, `project_root: str` (default `/workspace`)
- `job_dir: str`, `feature_name: str`

**Happy path**:
- Claude provider -> generates script with `printf '%s' "$PROMPT_CONTENT" | claude -p --dangerously-skip-permissions --output-format=stream-json --model "$MODEL" --verbose`
- OpenCode provider -> generates script with `opencode run --model "$MODEL" "$PROMPT_CONTENT"`
- Script starts with `#!/bin/bash` and includes `set -e`
- Script contains iteration loop with counter
- Script composes prompt from PROMPT file + task.md + progress.txt
- Script runs `git push` after each iteration
- Build mode checks for "ALL PHASES COMPLETE" in progress.txt
- All template variables substituted (no `{...}` placeholders remain)

**Edge cases**:
- `max_iterations=0` -> while loop has no iteration cap (unlimited mode)
- `max_iterations=1` -> loop body executes exactly once then exits
- Feature name with spaces or special characters -> properly quoted in script
- Long task descriptions -> no truncation in generated script

**Error conditions**:
- Invalid mode (not "plan" or "build") -> `ValueError` with specific message
- Negative `max_iterations` -> `ValueError` with specific message
- Unknown provider -> `ValueError` listing supported providers
- Generated script with unresolved placeholders -> `ScriptGenerationError`

**Validation checks on generated output**:
- No Windows paths (no backslash path separators)
- No PowerShell syntax (`$Var` capitalized, `Write-Host`, `Test-Path`, `Get-Content`, `Join-Path`)
- No unresolved `{template_var}` patterns
- Valid bash syntax: uses `$VARIABLE` (uppercase), `echo`, `cat`, `[[ ]]` tests
