# Spec: Container Lifecycle

## Overview
Manages Docker container creation, state transitions, monitoring, TTL expiry, and cleanup for sandboxed Ralph jobs.

## Changelog
| Date | ID | Change | Reason | Commit |
|------|-----|--------|--------|--------|
| 2026-02-12 | --- | Created | Initial spec generation | --- |

## Parent JTBD
Provide ephemeral, isolated execution environments for Ralph agent loops so that agent actions cannot affect the host system beyond the project directory.

## Scope
**In Scope:**
- ContainerManager class responsible for all Docker container operations
- Container state machine: ImageCheck -> Building -> Creating -> Starting -> Running -> Stopping -> Removed
- Error states and transitions from any active state to Failed
- TTL-based expiry for orphan prevention
- Container labels for identification and cleanup (`managed-by=vista`, `vista-job-id=...`)
- Auto-remove containers on completion via `auto_remove=true`
- Force-remove containers on TTL expiry or cleanup
- Docker daemon connectivity checks (ping)
- Stale container scan and removal on Vista startup

**Out of Scope:**
- Docker image building (see settings-and-image spec)
- Credential mount generation (see credential-management spec)
- Loop script generation (see bash-loop-generation spec)
- Resource limits (deferred beyond v1)
- Container networking configuration beyond default/host-only toggle
- Multi-container orchestration

## Requirements
### Functional
1. **DS-F1:** ContainerManager SHALL expose a `check_docker_available()` method that pings the Docker daemon and returns a boolean indicating reachability.
2. **DS-F2:** ContainerManager SHALL expose a `create_container(image, mounts, labels, command, working_dir)` method that creates a Docker container with `auto_remove=True` and the provided configuration.
3. **DS-F3:** ContainerManager SHALL expose a `start_container(container_id)` method that starts a previously created container and transitions it to Running state.
4. **DS-F4:** ContainerManager SHALL expose a `stop_container(container_id)` method that issues `docker stop` with a configurable timeout (default 10 seconds) and transitions to Stopping/Removed.
5. **DS-F5:** Each container SHALL be labeled with `managed-by=vista` and `vista-job-id={job_id}` at creation time.
6. **DS-F6:** ContainerManager SHALL track container state internally using a state machine that enforces valid transitions and raises `InvalidStateError` for illegal transitions.
7. **DS-F7:** ContainerManager SHALL implement TTL-based expiry: if a container has been Running longer than `ttl_seconds` (from SANDBOX_CONFIG), it SHALL be force-stopped and removed.
8. **DS-F8:** ContainerManager SHALL expose a `cleanup_stale_containers()` method that lists all containers with `managed-by=vista` label and removes any that are stopped or have exceeded their TTL.
9. **DS-F9:** When a container transitions to Failed state, ContainerManager SHALL preserve the `container_id` and any error information for diagnostic purposes, and SHALL NOT auto-remove the container until `cleanup_failed_container()` is explicitly called.
10. **DS-F10:** The Docker Python SDK SHALL be imported lazily so that the plugin does not fail to load when Docker is not installed.
11. **DS-F11:** ContainerManager SHALL set the container working directory to `/workspace` (the project mount point).

### Non-Functional
1. **DS-NF1:** Container creation and startup (excluding image build) SHALL complete in under 10 seconds with a cached image.
2. **DS-NF2:** ContainerManager SHALL operate correctly on Windows (Docker Desktop), macOS (Docker Desktop), and Linux (Docker Engine), all targeting Linux containers.
3. **DS-NF3:** All Docker SDK calls SHALL include appropriate timeout values to prevent indefinite blocking.

## User Workflows
### Workflow: Container Created for Sandboxed Job
**Actor:** RalphService (internal caller)
**Trigger:** `create_job()` called with `sandbox=true`
**Steps:**
1. RalphService calls `check_docker_available()`
2. ContainerManager pings Docker daemon, returns True
3. RalphService calls `ensure_image()` (see settings-and-image spec)
4. RalphService assembles mount specs (project RW + credentials RO)
5. RalphService calls `create_container()` with image name, mounts, labels, and `bash /workspace/.vista/ralph/{job}/loop.sh` as command
6. ContainerManager creates Docker container with `auto_remove=True`
7. RalphService calls `start_container(container_id)`
8. Container begins executing loop.sh
**Error Cases:**
- Docker daemon unreachable: `check_docker_available()` returns False, RalphService raises error before attempting container creation
- Container creation fails: ContainerManager transitions to Failed, raises `ContainerCreateError` with Docker error details
- Container start fails: ContainerManager transitions to Failed, raises `ContainerStartError`

### Workflow: Container Stopped by User
**Actor:** User via MCP tool or dashboard
**Trigger:** `ralph_stop(job_id)` called for a sandboxed job
**Steps:**
1. RalphService retrieves `container_id` from job metadata
2. RalphService calls `stop_container(container_id)`
3. ContainerManager issues `docker stop` with graceful timeout
4. Docker sends SIGTERM to container process
5. Container exits and is auto-removed
6. ContainerManager transitions state to Removed
**Error Cases:**
- Container already stopped: ContainerManager checks state, returns success (idempotent)
- Container not responding to SIGTERM: Docker kills after timeout, container still auto-removed

### Workflow: TTL Expiry
**Actor:** System (background check)
**Trigger:** Container Running duration exceeds `ttl_seconds`
**Steps:**
1. Periodic check (or checked on next status query) compares container `created_at` + `ttl_seconds` against current time
2. TTL exceeded: ContainerManager transitions to Expired
3. ContainerManager force-stops and removes container
4. Job status updated to reflect TTL expiry
**Error Cases:**
- Container already exited naturally before TTL check: no-op, already Removed

### Workflow: Stale Container Cleanup on Startup
**Actor:** Vista plugin startup
**Trigger:** Plugin initialization
**Steps:**
1. ContainerManager calls `cleanup_stale_containers()`
2. Lists all Docker containers with `managed-by=vista` label
3. For each: if stopped, remove; if running and TTL exceeded, force-stop and remove
4. Log count of cleaned-up containers
**Error Cases:**
- Docker not available: skip cleanup silently (user may not have Docker)

## Data Model
**Entities:**
- `ContainerInfo`: `container_id` (str PK), `job_id` (str FK), `image` (str), `status` (enum: ImageChecking, Building, Creating, Starting, Running, Stopping, Expired, Failed, Removed), `created_at` (datetime), `expires_at` (datetime), `labels` (dict)
- `Mount`: `host_path` (str), `container_path` (str), `mode` ("rw" or "ro"), `type` ("project" or "credential")

**Relationships:**
- A Job has zero or one ContainerInfo (present only if sandboxed)
- A ContainerInfo has one or more Mounts

## Integration Points
**Dependencies:**
- Docker Python SDK (`docker` package, lazily imported)
- Docker daemon running on host
- SandboxConfig from settings (for TTL, image name)
- CredentialMounter (provides mount specs)

**Provides to:**
- RalphService: container lifecycle operations (create, start, stop, cleanup)
- Dashboard API: container status and metadata for sandbox badge

## Technical Considerations
### Architecture
- ContainerManager is a standalone service class in `server/services/container_manager.py`
- Lazy import pattern: `docker` SDK imported inside methods, wrapped in try/except ImportError
- State machine can be implemented as a simple dict of valid transitions with current state tracking per container
- ContainerManager holds a dict of `{container_id: ContainerInfo}` for active containers

### Patterns
- State machine pattern for container lifecycle enforcement
- Lazy initialization for Docker client connection
- Context manager or explicit cleanup for failed containers

### Libraries/APIs
- `docker` Python SDK: `docker.from_env()`, `client.containers.create()`, `container.start()`, `container.stop()`, `container.remove()`, `client.containers.list(filters={"label": ...})`
- `docker.errors.DockerException`, `docker.errors.NotFound`, `docker.errors.APIError`

## Related Diagrams
- `arch/state-container.mmd` -- Container state machine showing all transitions including error and TTL paths
- `arch/sequence-sandboxed-job.mmd` -- Full lifecycle sequence from creation through execution to cleanup
- `arch/system-architecture.mmd` -- ContainerManager placement within host services
- `arch/tdd-container-manager-states.mmd` -- TDD state diagram with testable assertions per transition

## Acceptance Criteria
- [ ] DS-F1: `check_docker_available()` returns True when daemon is running and False when unreachable
- [ ] DS-F2: `create_container()` produces a container with correct image, mounts, labels, and auto_remove=True
- [ ] DS-F3: `start_container()` starts a created container and state transitions to Running
- [ ] DS-F4: `stop_container()` sends stop signal and container transitions to Stopping then Removed
- [ ] DS-F5: Every created container has `managed-by=vista` and `vista-job-id={job_id}` labels
- [ ] DS-F6: Calling `stop_container()` from Uninitialized state raises InvalidStateError
- [ ] DS-F6: Calling `create_container()` from Running state raises InvalidStateError
- [ ] DS-F7: Container running beyond TTL is automatically force-stopped and removed
- [ ] DS-F8: `cleanup_stale_containers()` removes all stopped vista-labeled containers
- [ ] DS-F9: Failed container preserves container_id and error info until explicit cleanup
- [ ] DS-F10: Plugin loads without error when `docker` package is not installed
- [ ] DS-F11: Container working directory is set to `/workspace`
- [ ] DS-NF1: Container create+start completes in under 10 seconds with cached image
- [ ] DS-NF2: Operations work on Windows, macOS, and Linux hosts

## Testing Strategy
> ContainerManager is a TDD-flagged component

**TDD Required:** Yes
**TDD Diagrams:** `arch/tdd-container-manager-states.mmd`

### Test Cases (from TDD diagrams)
#### Happy Path
- `test_ensure_image_found_locally`: ImageChecking -> Creating transition when image exists
- `test_ensure_image_triggers_build`: ImageChecking -> Building -> Creating when image missing
- `test_create_container_returns_id`: Creating -> Starting with valid container_id
- `test_start_container_transitions_to_running`: Starting -> Running on success
- `test_stop_container_transitions_to_removed`: Running -> Stopping -> Removed with auto_remove
- `test_container_labels_present`: Created container has `managed-by=vista` and `vista-job-id` labels
- `test_working_dir_is_workspace`: Container working_dir is `/workspace`
- `test_auto_remove_enabled`: Container created with `auto_remove=True`

#### Edge Cases
- `test_stop_already_stopped_container`: Idempotent, no error
- `test_cleanup_stale_with_no_vista_containers`: Returns 0, no errors
- `test_cleanup_stale_with_mixed_containers`: Only removes vista-labeled containers
- `test_ttl_not_expired_yet`: Container not stopped when TTL not reached
- `test_docker_sdk_not_installed`: Lazy import returns clear error message

#### Error Conditions
- `test_reject_stop_from_uninitialized`: Raises InvalidStateError
- `test_reject_start_from_uninitialized`: Raises InvalidStateError
- `test_reject_create_from_running`: Raises InvalidStateError
- `test_reject_ensure_image_from_running`: Raises InvalidStateError
- `test_docker_daemon_unreachable`: check_docker_available returns False
- `test_create_container_docker_error`: Creating -> Failed with ContainerCreateError
- `test_start_container_docker_error`: Starting -> Failed with ContainerStartError
- `test_container_crash_during_run`: Running -> Failed with ContainerCrashedError
- `test_image_build_failure`: Building -> Failed with ImageBuildError
- `test_failed_preserves_container_id`: Failed state retains container_id for cleanup
- `test_failed_preserves_error_type`: Failed state retains specific error type
- `test_cleanup_failed_container`: Failed -> Removed via cleanup_failed_container()

### Test Data Requirements
- Mocked `docker.DockerClient` with configurable responses for `.ping()`, `.containers.create()`, `.containers.list()`, `.images.get()`
- Mocked container objects with `.start()`, `.stop()`, `.remove()`, `.status` attributes
- Test mount specs (project mount RW, credential mount RO)
- Test labels dict

## Requirement Index
| ID | Section | Status |
|----|---------|--------|
| DS-F1 | Functional | Active |
| DS-F2 | Functional | Active |
| DS-F3 | Functional | Active |
| DS-F4 | Functional | Active |
| DS-F5 | Functional | Active |
| DS-F6 | Functional | Active |
| DS-F7 | Functional | Active |
| DS-F8 | Functional | Active |
| DS-F9 | Functional | Active |
| DS-F10 | Functional | Active |
| DS-F11 | Functional | Active |
| DS-NF1 | Non-Functional | Active |
| DS-NF2 | Non-Functional | Active |
| DS-NF3 | Non-Functional | Active |

## Open Questions
- [ ] Should TTL checks be periodic (background task) or lazy (checked on next status query)?
- [ ] What is the appropriate default TTL value? Domain requirements suggest 7200 seconds (2 hours) -- confirm.
- [ ] Should `cleanup_stale_containers()` run automatically on plugin startup, or only on explicit call?
- [ ] What graceful stop timeout should be used before Docker force-kills (default 10s)?
