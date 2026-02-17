# Implementation Plan: Docker Sandbox for Ralph Loops

## Overview

This plan implements Docker-based sandboxing for Ralph loop execution. The sandbox wraps existing loop execution in per-loop Docker containers with credential mounting, isolating agent activity to the project directory. Two execution paths are supported:

- **Claude Code loops**: Claude CLI runs natively inside the container with mounted credentials
- **OpenCode loops**: `opencode serve` runs on the host; the container calls Vista's proxy endpoint via HTTP

The sandbox is opt-in (`sandbox.enabled` toggle in the dashboard), fully transparent to the MCP tool interface, and degrades gracefully when Docker is unavailable.

### Specs Covered

| Spec | Key Concerns |
|------|-------------|
| `settings.md` | `ralph.sandbox` settings schema, defaults, validation |
| `credential-management.md` | Credential providers, path translation, UID/GID |
| `access-profiles.md` | Named mount profiles, variable substitution |
| `container-lifecycle.md` | ContainerManager, OpenCodeServeManager, orphan cleanup |
| `ralph-mcp-integration.md` | RalphService sandbox branch, loop templates, job metadata |
| `dashboard-ui.md` | Sandbox toggle, inline Docker status |

### Codebase Context

Current state of key files that will be modified:

- **`vista/server/config.py`** — Has `_RALPH_DEFAULTS`, `get_ralph_settings()`, `save_ralph_settings()`, `_merge_dicts()`. Pattern: defaults dict + merge function + getter/setter.
- **`vista/server/services/ralph_service.py`** — `RalphService` class with `create_job()` (subprocess.Popen), `stop_job()` (os.kill), `get_job_status()` (PID check + output parsing). Single module-level instance: `ralph_service`.
- **`vista/portable/ralph.py`** — Contains `LOOP_SCRIPT_TEMPLATE` (PowerShell). Used by both standalone CLI and `RalphService`. Claude invocation in template: `$PromptContent | claude -p --dangerously-skip-permissions --output-format=stream-json --model $Model`.
- **`vista/server/app.py`** — FastAPI app with lifespan context manager. Startup: ensure paths. Shutdown: stop loops. Routes registered via `app.include_router()`.
- **`vista/server/routes/ralph_settings.py`** — `GET/PUT /api/settings/ralph` for ralph settings management.

---

## Phase 1: Settings & Data Models

**Goal:** Extend config system with sandbox settings schema and create shared data models. This is the foundation all subsequent phases depend on.

### Step 1.1: Sandbox defaults in `config.py`

**File:** `vista/server/config.py` (modify)

Add `_SANDBOX_DEFAULTS` following the existing pattern of `_RALPH_DEFAULTS`:

```python
_SANDBOX_DEFAULTS = {
    "enabled": False,
    "image": "vista-ralph:latest",
    "network": True,
    "opencode_serve": {"port": 4096, "auto_start": True},
    "credentials": {
        "claude_auth": True,
        "git_ssh": True,
        "git_config": True,
        "github_cli": False,
        "custom": [],
    },
    "profiles": {
        "full-access": {"mounts": [{"path": ".", "mode": "rw"}]},
        "feature-scoped": {"mounts": [
            {"path": ".vista/features/${FEATURE}", "mode": "rw"},
            {"path": ".vista/ralph/${FEATURE}", "mode": "rw"},
            {"path": "src", "mode": "rw"},
            {"path": "tests", "mode": "rw"},
            {"path": ".git", "mode": "rw"},
        ]},
        "research-only": {"mounts": [{"path": ".", "mode": "ro"}], "network": False},
    },
    "model_defaults": {},
}
```

Add functions (following existing `get_ralph_settings` / `get_ralph_defaults` patterns):

- `get_sandbox_settings() -> dict` — `_merge_dicts(_SANDBOX_DEFAULTS, get_ralph_settings().get("sandbox", {}))`
- `is_sandbox_enabled() -> bool` — `get_sandbox_settings().get("enabled", False)`
- `get_sandbox_profile(name: str) -> dict | None` — lookup in `sandbox.profiles`
- `get_sandbox_credentials() -> dict` — return `sandbox.credentials` section
- `get_opencode_serve_settings() -> dict` — return `sandbox.opencode_serve` section
- `save_sandbox_settings(sandbox_config: dict)` — read full settings, set `ralph.sandbox`, write back (same atomic pattern as `save_ralph_settings`)

### Step 1.2: Settings validation

**File:** `vista/server/services/sandbox_settings.py` (new)

Validation functions:

```python
def validate_sandbox_settings(config: dict) -> list[str]:
    """Return list of validation error strings. Empty = valid."""
```

Rules from the settings spec:
- `enabled` is bool
- `image` is non-empty string
- `network` is bool
- `opencode_serve.port` is int 1024–65535
- `opencode_serve.auto_start` is bool
- Each credential toggle is bool
- Custom mounts have required fields: `name`, `host_path`, `container_path`
- Each profile has at least one mount
- Mount paths relative (no absolute paths, no `..` traversal)
- Mount modes are `"rw"` or `"ro"`
- Profile names match `^[a-z0-9-]+$`
- `model_defaults` values reference existing profile names

On load: log warnings for invalid fields, apply defaults. On save: reject with errors.

### Step 1.3: Data models

**File:** `vista/server/models/sandbox.py` (new)

```python
from dataclasses import dataclass, field

@dataclass
class MountSpec:
    path: str        # Relative to project root, supports ${FEATURE}
    mode: str        # "rw" or "ro"

@dataclass
class AccessProfile:
    name: str
    mounts: list[MountSpec]
    network: bool | None = None  # None = inherit global

@dataclass
class CredentialDetection:
    found: bool
    method: str           # "env_var", "config_dir", "config_file", "not_found"
    source_path: str
    display_info: str

@dataclass
class DockerMount:
    host_path: str
    container_path: str
    mode: str             # "ro" or "rw"

@dataclass
class DockerCredentialConfig:
    env_vars: dict[str, str] = field(default_factory=dict)
    mounts: list[DockerMount] = field(default_factory=list)

@dataclass
class ContainerInfo:
    name: str
    job_id: str
    provider: str
    status: str
    session_id: str
```

### Step 1.4: Tests

**File:** `vista/tests/test_sandbox_settings.py` (new)

- Defaults application: missing `sandbox` section, partial section, empty section
- Validation: invalid modes, missing fields, path traversal (`../../../etc`), port out of range
- Write-back: preserves existing `ralph.defaults`, `ralph.summarizer`, `server.*`
- `is_sandbox_enabled()` returns correct bool

---

## Phase 2: Credential Management

**Goal:** Implement credential providers that detect host credentials, generate Docker mount/env configs, and support validation.

### Step 2.1: Path translator

**File:** `vista/server/services/sandbox/path_translator.py` (new)

```python
class PathTranslator:
    def translate(self, host_path: str) -> str:
        """Windows: C:\\Users\\Grove\\.ssh → /c/Users/Grove/.ssh
        Linux/macOS: passthrough"""

    def get_host_uid_gid(self) -> tuple[int, int]:
        """Windows/WSL2: (1000, 1000). Linux/macOS: os.getuid(), os.getgid()"""
```

Implementation:
- Use `platform.system()` for detection
- Windows path translation: regex `^([A-Za-z]):\\(.*)` → `/$1_lower/$rest_with_forward_slashes`
- UID/GID: Windows always returns (1000, 1000) since Docker Desktop handles translation. Unix uses `os.getuid()`, `os.getgid()`.

### Step 2.2: Credential providers

**File:** `vista/server/services/sandbox/credential_providers.py` (new)

Base class:
```python
class CredentialProvider:
    name: str
    display_name: str
    description: str
    applies_to: list[str]  # ["claude"], ["*"], etc.

    def detect(self) -> CredentialDetection: ...
    def get_docker_config(self) -> DockerCredentialConfig: ...
    def get_validation_command(self) -> str: ...
```

Built-in providers:

| Provider | `applies_to` | Detects | Mount | Mode |
|----------|-------------|---------|-------|------|
| `ClaudeAuthProvider` | `["claude"]` | `ANTHROPIC_API_KEY` env, `~/.claude/` dir | `~/.claude/` → `/home/{user}/.claude/` | **rw** |
| `GitSshProvider` | `["*"]` | `~/.ssh/` with key files | `~/.ssh/` → `/home/{user}/.ssh/` | ro |
| `GitConfigProvider` | `["*"]` | `~/.gitconfig` file | `~/.gitconfig` → `/home/{user}/.gitconfig` | ro |
| `GitHubCliProvider` | `["*"]` | `~/.config/gh/` or `%APPDATA%\GitHub CLI\` | → `/home/{user}/.config/gh/` | ro |
| `CustomMountProvider` | `["*"]` | host_path exists | as specified in settings | as specified |

Gathering function:
```python
def gather_credentials(provider_name: str, settings: dict) -> list[DockerCredentialConfig]:
    """Filter by applies_to + settings toggles, detect, return configs."""
```

All providers use `PathTranslator` for host path → Docker path conversion.

### Step 2.3: Tests

**File:** `vista/tests/test_credential_providers.py` (new)
**File:** `vista/tests/test_path_translator.py` (new)

- Per-provider detection with mocked filesystem (monkeypatch `Path.home()`, `os.environ`)
- Path translation: `C:\Users\Grove\.ssh` → `/c/Users/Grove/.ssh`
- Docker config generation: correct mounts and env vars
- `applies_to` filtering: Claude-only creds skipped for OpenCode loops
- UID/GID per platform
- `gather_credentials` end-to-end

---

## Phase 3: Access Profiles

**Goal:** Profile resolution, variable substitution, and Docker mount generation.

Can be developed in parallel with Phase 2 (no interdependency).

### Step 3.1: Profile service

**File:** `vista/server/services/sandbox/access_profiles.py` (new)

```python
def resolve_profile(
    explicit: str | None, model: str, settings: dict
) -> AccessProfile:
    """Priority: explicit override > model_defaults mapping > 'full-access'"""

def substitute_variables(mount_path: str, feature: str | None) -> str:
    """Replace ${FEATURE} and ${PROJECT_ROOT} in mount paths."""

def to_docker_mounts(
    profile: AccessProfile,
    project_root: Path,
    feature: str | None,
    translator: PathTranslator,
) -> list[dict]:
    """Convert profile mounts to Docker bind mount specs.
    Special case: path '.' → mount entire project root as /workspace/
    Skip non-existent paths with warning (not error).
    """

def validate_profile(profile_dict: dict) -> list[str]:
    """Validate: ≥1 mount, paths relative, no '..', valid modes."""

def check_network_compatibility(
    profile: AccessProfile, provider_name: str, global_network: bool
) -> None:
    """Raise ValueError if OpenCode + network disabled."""
```

Network policy resolution: `profile.network if profile.network is not None else global_network`

### Step 3.2: Tests

**File:** `vista/tests/test_access_profiles.py` (new)

- Resolution chain: explicit > model_defaults > fallback
- Variable substitution: `${FEATURE}` → slug, `${PROJECT_ROOT}` → `/workspace`
- Mount translation: `"."` → full project root, relative paths → `/workspace/{path}`
- Validation: reject `..`, reject absolute paths, require ≥1 mount
- Network: OpenCode + `network: false` → error with clear message
- Missing path: skipped with warning

---

## Phase 4: Container Lifecycle Management

**Goal:** Docker container creation, execution, monitoring, teardown, and image management.

### Step 4.1: ContainerManager

**File:** `vista/server/services/sandbox/container_manager.py` (new)

**New dependency:** `docker` Python SDK (`pip install docker`). Import lazily to avoid breaking the plugin when Docker SDK is not installed.

```python
class ContainerManager:
    def __init__(self, session_id: str):
        import docker
        self.docker = docker.from_env()
        self.session_id = session_id

    async def create_loop_container(
        self,
        job_id: str,
        provider_name: str,
        project_root: Path,
        profile_mounts: list[dict],
        credentials: list[DockerCredentialConfig],
        image: str,
        network: bool = True,
        env_extra: dict | None = None,
    ) -> ContainerInfo:
        """
        1. Combine profile_mounts + credential mounts
        2. Combine credential env_vars + env_extra + DEVCONTAINER=true
        3. docker.containers.create() with labels, user, extra_hosts
        4. container.start()
        """

    async def exec_in_container(
        self,
        container_name: str,
        command: list[str],
        workdir: str = "/workspace",
        env: dict | None = None,
        stdout_handle=None,
    ) -> int:  # returns host PID
        """docker exec — run command inside running container."""

    async def remove_container(self, container_name: str) -> None:
        """Stop (timeout=10) + remove container."""

    async def cleanup_orphans(self) -> list[str]:
        """Find containers with managed-by=vista-ralph where
        vista-session != self.session_id. Stop + remove. Return names."""

    async def shutdown_all(self) -> None:
        """Stop + remove all containers with managed-by=vista-ralph
        AND vista-session == self.session_id."""

    def list_containers(self) -> list[ContainerInfo]:
        """List all managed containers with status."""

    def is_docker_available(self) -> tuple[bool, str]:
        """Try docker.ping(). Return (True, "Docker running") or (False, reason)."""

    async def ensure_image(self, image_name: str = "vista-ralph:latest") -> str:
        """Check if image exists locally. If not, build from bundled Dockerfile.
        Store Dockerfile hash to detect changes."""
```

Container creation details (from container-lifecycle spec):
- Name: `vista-ralph-{job_id[:8]}`
- Labels: `managed-by=vista-ralph`, `vista-job-id={job_id}`, `vista-provider={provider}`, `vista-session={session_id}`, `vista-project={hash(project_root)[:8]}`
- Command: `sleep infinity` (keeps container alive for exec)
- `extra_hosts={"host.docker.internal": "host-gateway"}` (Linux compatibility)
- `user=f"{uid}:{gid}"`
- `working_dir="/workspace"`
- `network_mode="bridge" if network else "none"`

### Step 4.2: Docker image

**File:** `vista/docker/Dockerfile` (new)

Based on claudebox reference (`reference/claudebox/build/Dockerfile`) with simplifications:

- Base: `debian:bookworm`
- Build args: `USER_ID`, `GROUP_ID`, `NODE_VERSION`
- Install: git, node (via nvm), claude-code CLI, python3, uv, gh CLI, jq, curl, bash
- User creation with UID/GID matching
- `DEVCONTAINER=true`
- `WORKDIR /workspace`
- Remove: zsh/fzf customization, tmux config, delta, firewall scripts, entrypoint scripts
- Simple entrypoint: just `sleep infinity` (Vista uses `docker exec`)

**File:** `vista/docker/.dockerignore` (new)

### Step 4.3: Tests

**File:** `vista/tests/test_container_manager.py` (new)

- Container naming and label generation (unit, no Docker)
- Volume mount construction from profile + credentials (unit)
- Docker availability check (mock docker client)
- Create → exec → remove flow (mock docker client)
- Orphan cleanup: mock containers from "old session" are removed, current session containers preserved

---

## Phase 5: OpenCode Serve Management & Proxy

**Goal:** Host-side `opencode serve` process management and Vista proxy endpoint.

### Step 5.1: OpenCodeServeManager

**File:** `vista/server/services/sandbox/opencode_serve_manager.py` (new)

```python
class OpenCodeServeManager:
    def __init__(self, port: int = 4096):
        self.port = port
        self.process: subprocess.Popen | None = None
        self.sessions: dict[str, str] = {}  # job_id → session_id

    async def ensure_running(self) -> None:
        """Start 'opencode serve --port {port} --hostname 127.0.0.1'
        if not running. Health check: GET http://localhost:{port}/doc"""

    async def create_session(self, job_id: str, cwd: str) -> str:
        """POST to opencode serve to create session. Return session_id."""

    async def close_session(self, job_id: str) -> None:
        """Close session. Remove from self.sessions."""

    async def stop(self) -> None:
        """Terminate opencode serve process."""

    def is_running(self) -> bool:
        """Process alive + health check passes."""
```

### Step 5.2: Sandbox API routes

**File:** `vista/server/routes/sandbox.py` (new)

```python
router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

@router.post("/opencode/{session_id}/message")
async def opencode_proxy_message(session_id: str, request: Request):
    """Forward message from container to opencode serve on host.
    1. Validate session_id exists
    2. Forward request body to http://localhost:{port}/...
    3. Stream response back to caller
    """

@router.get("/status")
async def sandbox_status():
    """Returns { docker_available, docker_running, image_built, image_name }"""

@router.put("/settings")
async def update_sandbox_settings(body: dict):
    """Toggle sandbox.enabled. Writes to settings.json."""

@router.post("/credentials/validate")
async def validate_credentials():
    """Spin up temp container, run validation commands, tear down."""

@router.post("/image/build")
async def build_image():
    """Trigger sandbox image rebuild."""
```

### Step 5.3: Tests

**File:** `vista/tests/test_opencode_serve_manager.py` (new)

- `ensure_running` with mock subprocess
- Session create/close with mock HTTP
- Health check logic
- Process lifecycle

**File:** `vista/tests/test_sandbox_api.py` (new)

- `GET /api/sandbox/status` returns correct Docker/image state
- `PUT /api/sandbox/settings` with enabled true/false
- Proxy endpoint forwards correctly (mock opencode serve)

---

## Phase 6: RalphService Integration

**Goal:** Add sandbox branch to `RalphService` so `create_job()` routes through Docker when enabled. This is the core integration point.

### Step 6.1: Sandbox branch in `create_job()`

**File:** `vista/server/services/ralph_service.py` (modify)

Add at the top of `create_job()`:

```python
sandbox_settings = config.get_sandbox_settings()
if sandbox_settings.get("enabled"):
    return self._create_sandbox_job(
        job_dir, project_root, slug, mode, task_description,
        provider, model, iterations, sandbox_settings, job_id
    )
# else: existing local subprocess code stays unchanged
```

**New method `_create_sandbox_job()` (Claude Code path):**

1. Generate `loop.sh` (always bash — container is Linux)
   - Use existing `LOOP_SCRIPT_TEMPLATE` content but get invocation via `provider.get_invocation("sh")`
   - The Claude invocation block already supports bash: `printf "%s" "$PROMPT_CONTENT" | claude -p ...`
2. Resolve access profile: `resolve_profile(explicit=None, model=model, settings=sandbox_settings)`
3. Convert profile to Docker mounts: `to_docker_mounts(profile, project_root, slug, translator)`
4. Gather credentials: `gather_credentials("claude", sandbox_settings)`
5. Check network compatibility
6. `container_manager.create_loop_container(job_id, "claude", project_root, profile_mounts, credentials, image, network)`
7. `pid = container_manager.exec_in_container(container_name, ["bash", f"/workspace/.vista/ralph/{slug}-{job_id[:8]}/loop.sh"], stdout_handle=output_log)`
8. Save job.json with: `sandbox: True, container: "vista-ralph-{job_id[:8]}", pid: exec_pid`

**New method `_create_sandbox_job()` (OpenCode path):**

Same as Claude but additionally:
1. `opencode_serve_manager.ensure_running()`
2. `session_id = opencode_serve_manager.create_session(job_id, str(project_root))`
3. Generate `loop.sh` from **new** `OPENCODE_SANDBOX_LOOP_TEMPLATE`
4. Gather credentials: `gather_credentials("opencode", sandbox_settings)` — no AI creds
5. Exec with extra env: `VISTA_HOST=host.docker.internal, VISTA_PORT={port}, OPENCODE_SESSION={session_id}, MODEL={model}`
6. Save job.json with additional `opencode_session` field

### Step 6.2: OpenCode sandbox loop template

**File:** `vista/portable/ralph.py` (modify — add constant)

Add `OPENCODE_SANDBOX_LOOP_TEMPLATE` — a bash script that:
- Reads PROMPT + task.md + progress.txt (same compose logic as current template)
- Uses `curl -s -X POST "$VISTA_API/message" -H "Content-Type: application/json" -d ...` to call Vista proxy
- Pushes via git after each iteration
- Checks completion markers (`ALL PHASES COMPLETE`, `Reached max iterations`)
- Variables: `VISTA_HOST`, `VISTA_PORT`, `OPENCODE_SESSION`, `MODEL` from env

Full template content is in the ralph-mcp-integration spec (lines 95-185).

### Step 6.3: Modify `stop_job()`

**File:** `vista/server/services/ralph_service.py` (modify)

```python
def stop_job(self, project_root, job_id):
    # ... load job ...
    if job.get("sandbox"):
        self._kill_pid(job["pid"])  # Kill exec process
        if job.get("opencode_session"):
            await opencode_serve_manager.close_session(job_id)
        await container_manager.remove_container(f"vista-ralph-{job_id[:8]}")
    else:
        # Current behavior unchanged
```

### Step 6.4: Modify `get_job_status()`

**File:** `vista/server/services/ralph_service.py` (modify)

When `job.get("sandbox")` and PID is not running:
- Also check if container still exists (container_manager.list_containers)
- If container gone + PID gone: apply existing completion detection logic

### Step 6.5: Job metadata extension

When sandbox active, `job.json` includes:
```json
{
  "sandbox": true,
  "container": "vista-ralph-{job_id[:8]}",
  "opencode_session": "sess_xyz"  // OpenCode only
}
```

When sandbox disabled: `sandbox` key absent (backward compatible).

### Step 6.6: Tests

**File:** `vista/tests/test_ralph_service.py` (modify — add test cases)

- `create_job()` routes to ContainerManager when `sandbox.enabled = true`
- `create_job()` uses local subprocess when `sandbox.enabled = false`
- Claude loops generate bash `loop.sh` with native `claude -p`
- OpenCode loops generate bash `loop.sh` with `curl` calls
- `job.json` includes `sandbox`, `container`, `opencode_session` when active
- `stop_job()` kills PID + removes container + closes session

---

## Phase 7: App Lifecycle Integration

**Goal:** Wire sandbox managers into Vista's startup/shutdown and register routes.

### Step 7.1: Sandbox initialization module

**File:** `vista/server/services/sandbox/__init__.py` (modify to add global accessors)

```python
_container_manager: ContainerManager | None = None
_opencode_serve_manager: OpenCodeServeManager | None = None

async def init_sandbox() -> None:
    """Called during app startup. Initializes managers if sandbox enabled."""
    global _container_manager, _opencode_serve_manager
    if not config.is_sandbox_enabled():
        return
    session_id = str(uuid4())
    try:
        _container_manager = ContainerManager(session_id)
        orphans = await _container_manager.cleanup_orphans()
        if orphans:
            logger.info(f"Cleaned up {len(orphans)} orphaned containers: {orphans}")
        await _container_manager.ensure_image()
    except Exception as e:
        logger.error(f"Sandbox init failed: {e}. Sandbox will be unavailable.")
        _container_manager = None
    serve_settings = config.get_opencode_serve_settings()
    _opencode_serve_manager = OpenCodeServeManager(serve_settings["port"])

async def shutdown_sandbox() -> None:
    """Called during app shutdown."""
    if _container_manager:
        await _container_manager.shutdown_all()
    if _opencode_serve_manager:
        await _opencode_serve_manager.stop()

def get_container_manager() -> ContainerManager | None:
    return _container_manager

def get_opencode_serve_manager() -> OpenCodeServeManager | None:
    return _opencode_serve_manager
```

### Step 7.2: Modify app lifespan

**File:** `vista/server/app.py` (modify)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_full_path()
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / "sessions").mkdir(exist_ok=True)
    # NEW: sandbox initialization
    from server.services.sandbox import init_sandbox, shutdown_sandbox
    await init_sandbox()
    yield
    await loop_service.stop_all()
    await diagram_watcher.stop()
    keepalive_manager.stop_all()
    # NEW: sandbox shutdown
    await shutdown_sandbox()
```

Register sandbox routes:
```python
from server.routes import sandbox
app.include_router(sandbox.router)
```

### Step 7.3: Credential validation at startup

Inside `init_sandbox()`, after image is ensured:
- Run `validate_credentials()` — creates temp container, runs validation commands per enabled provider
- Log results (pass/fail per credential) to server output
- Non-blocking: validation failures are warnings, not startup failures

---

## Phase 8: Dashboard UI

**Goal:** Single toggle + inline Docker status in Ralph settings page.

### Step 8.1: Frontend

**File:** `vista/server/views/ralph_settings.html` (modify)

Add "Docker Sandbox" section after existing ralph settings controls:

```
Docker Sandbox  [toggle: OFF/ON]   {inline status text}
```

Behavior:
- Toggle reads/writes `sandbox.enabled` via `PUT /api/sandbox/settings`
- When toggled ON: call `GET /api/sandbox/status`, display status:
  - Green dot + "Docker running" (available + image built)
  - Amber dot + "Building image..." (available + image building)
  - Red dot + "Docker not running" (installed but stopped)
  - Red dot + "Docker Desktop required" (not installed)
- When toggled OFF: hide status text
- Status checked on page load (if ON) and on toggle change
- No polling — manual refresh

### Step 8.2: Tests

**File:** `vista/tests/test_sandbox_api.py` (extend from Phase 5.3)

- `GET /api/sandbox/status` returns correct states
- `PUT /api/sandbox/settings` toggles correctly
- Error states display actionable guidance

---

## Phase 9: Integration Testing

**File:** `vista/tests/integration/test_sandbox_lifecycle.py` (new)

Requires Docker to be installed and running:

- Full `ralph_start → ralph_status → ralph_stop` with sandbox (Claude path)
- Full cycle with sandbox (OpenCode path via serve proxy)
- `ralph_summary` reads artifacts produced inside container
- Orphan cleanup across Vista restarts
- Concurrent loops in separate containers
- Bypass mode: `sandbox.enabled = false` runs identically to pre-sandbox
- Agent can access `.vista/features/`, source code, `.git/` from inside container
- Agent can `git push` from inside container (SSH keys mounted)

---

## File Summary

### New Files (17)

| File | Phase | Purpose |
|------|-------|---------|
| `vista/server/models/sandbox.py` | 1 | Data models (MountSpec, AccessProfile, DockerMount, etc.) |
| `vista/server/services/sandbox_settings.py` | 1 | Settings validation |
| `vista/server/services/sandbox/__init__.py` | 2+ | Package init + global accessors + init/shutdown |
| `vista/server/services/sandbox/path_translator.py` | 2 | Host→Docker path conversion + UID/GID |
| `vista/server/services/sandbox/credential_providers.py` | 2 | 5 credential providers + gathering |
| `vista/server/services/sandbox/access_profiles.py` | 3 | Profile resolution, variable substitution, mount translation |
| `vista/server/services/sandbox/container_manager.py` | 4 | Container lifecycle (create, exec, remove, cleanup, image) |
| `vista/server/services/sandbox/opencode_serve_manager.py` | 5 | Host-side `opencode serve` management |
| `vista/server/routes/sandbox.py` | 5 | API endpoints (status, settings, proxy, validate, build) |
| `vista/docker/Dockerfile` | 4 | Modified claudebox image for Vista sandbox |
| `vista/docker/.dockerignore` | 4 | Build context ignore |
| `vista/tests/test_sandbox_settings.py` | 1 | Settings tests |
| `vista/tests/test_path_translator.py` | 2 | Path translation tests |
| `vista/tests/test_credential_providers.py` | 2 | Credential provider tests |
| `vista/tests/test_access_profiles.py` | 3 | Access profile tests |
| `vista/tests/test_container_manager.py` | 4 | Container lifecycle tests |
| `vista/tests/test_opencode_serve_manager.py` | 5 | OpenCode serve tests |

### Modified Files (5)

| File | Phase | Changes |
|------|-------|---------|
| `vista/server/config.py` | 1 | Add `_SANDBOX_DEFAULTS` + getter/setter functions |
| `vista/server/services/ralph_service.py` | 6 | Sandbox branch in `create_job()`, `stop_job()`, `get_job_status()` |
| `vista/portable/ralph.py` | 6 | Add `OPENCODE_SANDBOX_LOOP_TEMPLATE` |
| `vista/server/app.py` | 7 | Lifespan: init/shutdown sandbox. Register sandbox routes. |
| `vista/server/views/ralph_settings.html` | 8 | Sandbox toggle + inline Docker status |

### New Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| `docker` | Python Docker SDK for container management | `pip install docker` |

Import lazily — if not installed, sandbox features disabled with clear error. Plugin still functions for non-sandbox usage.

---

## Build Order

```
Phase 1 (Settings + Models)         ← Foundation
  ↓
Phase 2 (Credentials) ─────┐
Phase 3 (Access Profiles) ──┤       ← Parallel (no interdependency)
  ↓                         ↓
Phase 4 (ContainerManager)          ← Core infrastructure
  ↓
Phase 5 (OpenCode Serve + API)      ← Second execution path
  ↓
Phase 6 (RalphService Integration)  ← Ties everything together
  ↓
Phase 7 (App Lifecycle)             ← Startup/shutdown wiring
  ↓
Phase 8 (Dashboard UI) ────┐
Phase 9 (Integration Tests) ┤      ← Parallel (independent)
```

---

## Spec Alignment Matrix

| Domain Requirement | Implementing Spec | Phase |
|---|---|---|
| Prevent file access outside project | access-profiles (container isolation) | 3, 4 |
| Eliminate credential complexity for OpenCode | credential-management (host-side serve) | 2, 5 |
| Claudebox as base image | container-lifecycle | 4 |
| Transparent sandbox (no MCP changes) | ralph-mcp-integration | 6 |
| Agent access to feature specs | access-profiles ("full-access" default) | 3 |
| Full bypass when disabled | settings, ralph-mcp-integration | 1, 6 |
| Container-per-loop isolation | container-lifecycle | 4 |
| Orphan cleanup on startup | container-lifecycle | 7 |
| Single dashboard toggle | dashboard-ui | 8 |
| Zero Docker knowledge required | dashboard-ui, settings | 1, 8 |
| Credential auto-detection | credential-management | 2 |
| Credential validation at startup | credential-management | 7 |
| OpenCode serve management | container-lifecycle | 5 |
| Vista proxy for OpenCode | ralph-mcp-integration | 5 |
| Path translation (Windows→Docker) | credential-management | 2 |
| UID/GID matching | credential-management | 2 |
| Docker availability check | dashboard-ui, container-lifecycle | 4, 8 |
| Settings validation | settings | 1 |
| No changes to MCP tool interface | ralph-mcp-integration | 6 (transparent) |

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Docker not installed | Lazy import of `docker` SDK. Sandbox marked unavailable. Loops run locally. |
| Docker not running | `is_docker_available()` check. Dashboard shows actionable guidance. |
| WSL2 bind mount performance | Acceptable per NFR. Document in known limitations. |
| Port conflict for opencode serve | Log error, try next available port. |
| Concurrent loops git conflicts | Documented: separate containers, shared files. Users should use separate branches. |
| Orphaned containers after crash | Session-based cleanup on every Vista startup. |
| UID/GID mismatch | Host UID/GID as build args. Windows defaults to 1000:1000. |
| `~/.claude/` must be rw | Explicitly mounted read-write (differs from claudebox copy pattern). |
| SSH agent forwarding | Not supported in v1. Only file-based SSH keys. Documented. |
