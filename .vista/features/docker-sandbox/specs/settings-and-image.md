# Spec: Settings and Image

## Overview
Defines sandbox configuration in settings.json and manages Docker image auto-build from the claudebox base image for Vista-sandboxed execution.

## Changelog
| Date | ID | Change | Reason | Commit |
|------|-----|--------|--------|--------|
| 2026-02-12 | --- | Created | Initial spec generation | --- |

## Parent JTBD
Provide configurable sandbox settings and a ready-to-use Docker image so that sandboxed jobs can launch quickly with minimal user setup.

## Scope
**In Scope:**
- SANDBOX_CONFIG section within settings.json schema
- Configuration fields: image name, network mode, TTL, credential mount enable/disable
- Docker image management: check existence, auto-build on first use, rebuild on demand
- Claudebox base image integration and extension with Vista tooling
- Image caching for fast subsequent job launches
- Docker SDK connection validation (Layer 1 testing)
- `GET /api/ralph/sandbox/status` response data (Docker installed, daemon running, image exists)
- `POST /api/ralph/sandbox/build` handler logic

**Out of Scope:**
- Container creation and lifecycle (see container-lifecycle spec)
- Credential mount path resolution (see credential-management spec)
- Loop script generation (see bash-loop-generation spec)
- RalphService integration logic (see ralph-sandbox-integration spec)
- Docker Desktop installation or licensing
- Custom Dockerfile authoring by users
- Multi-image support (single image in v1)

## Requirements
### Functional
1. **DS-F45:** settings.json SHALL support a `sandbox` section under the `ralph` configuration key with the following fields: `image` (str, default "vista-ralph:latest"), `network_enabled` (bool, default true), `ttl_seconds` (int, default 7200), `credential_mounts` (object).
2. **DS-F46:** The `credential_mounts` config object SHALL contain entries for each credential type (`claude_auth`, `git_ssh`, `git_config`, `gh_cli`, `opencode`) each with an `enabled` (bool, default true) field.
3. **DS-F47:** ContainerManager SHALL expose an `ensure_image(check_only=False)` method that checks if the configured image exists locally and, when `check_only=False` and image is missing, triggers an automatic build.
4. **DS-F48:** The Docker image SHALL be built from the RchGrav/claudebox base image, extended with any Vista-specific tooling (e.g., git, curl) if not already present in claudebox.
5. **DS-F49:** Image build progress SHALL be reported via a callback mechanism so callers (MCP tools, API) can surface "Building Docker image..." status to the user.
6. **DS-F50:** The `POST /api/ralph/sandbox/build` endpoint SHALL force a rebuild of the Docker image even if one already exists, replacing the previous image.
7. **DS-F51:** The `GET /api/ralph/sandbox/status` endpoint SHALL return a JSON object with `docker_installed` (bool), `daemon_running` (bool), `image_exists` (bool), and `image_name` (str).
8. **DS-F52:** When the Docker Python SDK (`docker` package) is not installed, `docker_installed` SHALL be False and all sandbox operations SHALL raise a clear error: "Docker SDK not installed. Run: pip install docker".
9. **DS-F53:** When the Docker daemon is not running, `daemon_running` SHALL be False and sandbox operations SHALL raise: "Docker daemon is not running. Please start Docker Desktop."
10. **DS-F54:** The image build SHALL use a Dockerfile stored within the Vista plugin directory (e.g., `vista/docker/Dockerfile`) that extends claudebox.
11. **DS-F55:** Settings SHALL be validated on load: invalid `ttl_seconds` (negative or zero) SHALL be rejected, invalid image names SHALL be rejected.

### Non-Functional
1. **DS-NF10:** Image build time SHALL be under 5 minutes on a standard internet connection (first build, uncached).
2. **DS-NF11:** Image existence check SHALL complete in under 1 second.
3. **DS-NF12:** Settings defaults SHALL allow sandbox to work with zero configuration beyond having Docker installed.

## User Workflows
### Workflow: First Sandboxed Job (Image Auto-Build)
**Actor:** User via Claude/MCP
**Trigger:** First `ralph_start` with `sandbox=true` when no image exists
**Steps:**
1. RalphService calls ContainerManager.ensure_image()
2. ContainerManager checks for image via Docker SDK: `client.images.get("vista-ralph:latest")`
3. Image not found: ContainerManager triggers build from Dockerfile
4. Build progress reported to caller: "Building Docker image (first time setup, ~2-5 minutes)..."
5. Build completes, image tagged as "vista-ralph:latest"
6. ContainerManager returns success, job creation continues
**Error Cases:**
- Dockerfile not found: "Vista Dockerfile not found at {path}. Plugin may be corrupted."
- Build fails (network error): "Image build failed: {build_log_tail}. Check network and retry with POST /api/ralph/sandbox/build"
- Build fails (Dockerfile error): "Image build failed: {build_log_tail}. Please report this issue."
- Claudebox base image not pullable: "Cannot pull claudebox base image. Check Docker network access."

### Workflow: Manual Image Rebuild
**Actor:** User via dashboard or API
**Trigger:** `POST /api/ralph/sandbox/build`
**Steps:**
1. API handler calls ContainerManager.ensure_image(force_rebuild=True)
2. ContainerManager removes existing image (if any)
3. ContainerManager builds fresh image from Dockerfile
4. Returns build result with image ID and size
**Error Cases:**
- Image in use by running container: "Cannot rebuild image while sandboxed jobs are running. Stop all sandboxed jobs first."

### Workflow: Check Sandbox Readiness
**Actor:** User or dashboard
**Trigger:** `GET /api/ralph/sandbox/status`
**Steps:**
1. API handler attempts lazy import of `docker` package
2. If import fails: return `{docker_installed: false, daemon_running: false, image_exists: false, image_name: "vista-ralph:latest"}`
3. If import succeeds: attempt `docker.from_env().ping()`
4. If ping fails: return `{docker_installed: true, daemon_running: false, image_exists: false, image_name: "vista-ralph:latest"}`
5. If ping succeeds: check `client.images.get(image_name)`
6. Return full status: `{docker_installed: true, daemon_running: true, image_exists: bool, image_name: "vista-ralph:latest"}`
**Error Cases:**
- Unexpected Docker API error: return `{docker_installed: true, daemon_running: false, ...}` with error detail

### Workflow: User Customizes Sandbox Settings
**Actor:** User editing settings.json
**Trigger:** User wants to change TTL or disable network
**Steps:**
1. User opens settings.json, adds/modifies `ralph.sandbox` section
2. Sets `network_enabled: false` for offline sandbox
3. Sets `ttl_seconds: 3600` for shorter TTL
4. Next sandboxed job uses updated settings
**Error Cases:**
- Invalid TTL (negative): validation rejects on settings load, uses default

## Data Model
**Entities:**
- `SANDBOX_CONFIG`: `image` (str), `network_enabled` (bool), `ttl_seconds` (int), `credential_mounts` (dict of CredentialMountConfig)
- `CredentialMountConfig`: `enabled` (bool)

**Relationships:**
- SETTINGS contains zero or one SANDBOX_CONFIG
- SANDBOX_CONFIG contains zero or more CredentialMountConfig entries

### Settings Schema Example
```json
{
  "ralph": {
    "sandbox": {
      "image": "vista-ralph:latest",
      "network_enabled": true,
      "ttl_seconds": 7200,
      "credential_mounts": {
        "claude_auth": { "enabled": true },
        "git_ssh": { "enabled": true },
        "git_config": { "enabled": true },
        "gh_cli": { "enabled": true },
        "opencode": { "enabled": true }
      }
    }
  }
}
```

## Integration Points
**Dependencies:**
- Docker Python SDK (`docker` package, lazily imported)
- Docker daemon (for image operations)
- RchGrav/claudebox Docker image (base image pulled during build)
- Vista plugin directory (for Dockerfile location)
- settings.json loader (existing config infrastructure)

**Provides to:**
- ContainerManager: image name and sandbox configuration
- CredentialMounter: credential_mounts enable/disable flags
- ContainerManager: TTL and network settings
- RalphService: sandbox config for job creation decisions
- API routes: sandbox status and build endpoints

## Technical Considerations
### Architecture
- SANDBOX_CONFIG parsed by existing settings loader with defaults for all fields
- Dockerfile stored at `vista/docker/Dockerfile` (or `vista/docker/Dockerfile.sandbox`)
- Image management methods on ContainerManager (or separate ImageManager if complexity warrants)
- Docker client created lazily and cached for session lifetime

### Patterns
- Configuration with defaults: every field has a sensible default, sandbox works with zero config
- Lazy loading: Docker SDK import deferred until first sandbox operation
- Builder pattern potential: Dockerfile could be generated programmatically if claudebox extensions vary

### Libraries/APIs
- `docker.from_env()`: create Docker client from environment
- `client.images.get(name)`: check image existence
- `client.images.build(path, tag)`: build image from Dockerfile
- `client.images.remove(name)`: remove image for rebuild
- `client.ping()`: verify daemon connectivity

### Dockerfile Structure (conceptual)
```dockerfile
FROM ghcr.io/rchgrav/claudebox:latest

# Vista-specific additions (if needed)
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Create non-root user matching host UID/GID (set at build or runtime)
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID user && useradd -m -u $UID -g $GID user

USER user
WORKDIR /workspace
```

## Related Diagrams
- `arch/data-model.mmd` -- SETTINGS, SANDBOX_CONFIG, and CREDENTIAL_MOUNT entities
- `arch/state-container.mmd` -- ImageCheck and Building states in container lifecycle
- `arch/user-flow.mmd` -- Docker image check and auto-build decision flow
- `arch/sequence-sandboxed-job.mmd` -- ensure_image() call in job creation sequence

## Acceptance Criteria
- [ ] DS-F45: settings.json supports `ralph.sandbox` with image, network_enabled, ttl_seconds, credential_mounts
- [ ] DS-F45: Default values applied when sandbox section is absent: image="vista-ralph:latest", network_enabled=true, ttl_seconds=7200
- [ ] DS-F46: Each credential type has an `enabled` field defaulting to true
- [ ] DS-F47: `ensure_image()` returns True when image exists without triggering build
- [ ] DS-F47: `ensure_image()` triggers build when image missing and check_only=False
- [ ] DS-F47: `ensure_image(check_only=True)` returns False when image missing, does not build
- [ ] DS-F48: Built image is based on claudebox and tagged as configured image name
- [ ] DS-F49: Build progress callback invoked during image build
- [ ] DS-F50: `POST /api/ralph/sandbox/build` rebuilds image even when one exists
- [ ] DS-F51: `GET /api/ralph/sandbox/status` returns correct JSON with all four fields
- [ ] DS-F52: Docker SDK not installed produces clear error message with install instruction
- [ ] DS-F53: Docker daemon not running produces clear error message mentioning Docker Desktop
- [ ] DS-F54: Dockerfile exists at expected path within Vista plugin directory
- [ ] DS-F55: Negative ttl_seconds rejected on settings validation
- [ ] DS-NF10: Image build completes within 5 minutes on standard connection
- [ ] DS-NF11: Image existence check completes under 1 second
- [ ] DS-NF12: Sandbox works with only Docker installed and zero settings changes

## Testing Strategy
> Docker SDK connection testing (Layer 1) maps to this spec. Image management is part of ContainerManager TDD.

**TDD Required:** Partial (settings validation is testable without Docker; Docker connection is integration)

### Test Cases (from domain requirements Layer 1)
#### Happy Path
- `test_docker_sdk_import_succeeds`: `import docker` succeeds when package installed
- `test_docker_daemon_ping_succeeds`: `docker.from_env().ping()` returns True (integration, requires Docker)
- `test_image_exists_check`: `client.images.get("vista-ralph:latest")` returns image object (integration)
- `test_settings_defaults_applied`: Missing sandbox section produces correct defaults
- `test_settings_custom_values`: Custom ttl_seconds and network_enabled parsed correctly
- `test_credential_mounts_config_parsed`: All five credential types with enabled flags parsed
- `test_sandbox_status_all_available`: Returns all true when Docker and image ready
- `test_sandbox_status_no_docker`: Returns docker_installed=false

#### Edge Cases
- `test_settings_partial_sandbox_config`: Only image specified, rest default
- `test_settings_partial_credential_mounts`: Only some credential types configured, rest default to enabled
- `test_ensure_image_concurrent_calls`: Two simultaneous ensure_image calls do not duplicate builds
- `test_rebuild_when_no_existing_image`: force_rebuild with no existing image just builds fresh

#### Error Conditions
- `test_docker_sdk_not_installed`: Import fails gracefully with clear error message
- `test_docker_daemon_not_running`: Ping fails with clear error message
- `test_image_build_network_failure`: Build fails with network error, returns useful message
- `test_invalid_ttl_negative`: Negative ttl_seconds rejected at settings load
- `test_invalid_ttl_zero`: Zero ttl_seconds rejected at settings load
- `test_dockerfile_not_found`: Missing Dockerfile raises clear error with path

### Test Data Requirements
- Test settings.json with various sandbox configurations (full, partial, empty, invalid)
- Mocked Docker client for unit tests
- Real Docker daemon for integration tests (marked `@pytest.mark.docker`)

## Requirement Index
| ID | Section | Status |
|----|---------|--------|
| DS-F45 | Functional | Active |
| DS-F46 | Functional | Active |
| DS-F47 | Functional | Active |
| DS-F48 | Functional | Active |
| DS-F49 | Functional | Active |
| DS-F50 | Functional | Active |
| DS-F51 | Functional | Active |
| DS-F52 | Functional | Active |
| DS-F53 | Functional | Active |
| DS-F54 | Functional | Active |
| DS-F55 | Functional | Active |
| DS-NF10 | Non-Functional | Active |
| DS-NF11 | Non-Functional | Active |
| DS-NF12 | Non-Functional | Active |

## Open Questions
- [ ] Does claudebox ship a pre-built image on GHCR, or must it always be built from a Dockerfile locally?
- [ ] Should the Dockerfile accept build-time UID/GID args, or should the container run as the claudebox default user?
- [ ] Where should the Dockerfile live: `vista/docker/Dockerfile`, `vista/.docker/Dockerfile`, or alongside the plugin manifest?
- [ ] Should there be an image version tag beyond "latest" for reproducibility?
- [ ] Is `network_enabled: false` implemented via `--network none` or `--network host`? What about DNS resolution?
