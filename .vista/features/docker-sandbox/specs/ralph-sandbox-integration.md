# Spec: Ralph Sandbox Integration

## Overview
Extends RalphService to branch between native and sandboxed job execution, coordinating ContainerManager and CredentialMounter for Docker-based jobs.

## Changelog
| Date | ID | Change | Reason | Commit |
|------|-----|--------|--------|--------|
| 2026-02-12 | --- | Created | Initial spec generation | --- |

## Parent JTBD
Allow users to run Ralph agent loops inside Docker containers with a single toggle, while preserving the existing native execution path and dashboard monitoring experience.

## Scope
**In Scope:**
- `sandbox` parameter on `create_job()` and `ralph_start` MCP tool
- SandboxJobCreator class that orchestrates Docker-based job creation
- Branching logic in RalphService: native path (existing) vs sandbox path (new)
- Extended job metadata to include `sandbox`, `container_id` fields
- Extended `stop_job()` to issue `docker stop` for sandboxed jobs
- Extended API routes for sandbox status and image build endpoints
- Dashboard "Sandboxed" badge on job status display
- Docker availability check before sandboxed job creation
- Error handling: Docker unavailable, image missing, mount failures

**Out of Scope:**
- Docker container internals (see container-lifecycle spec)
- Credential path resolution (see credential-management spec)
- Loop script content generation (see bash-loop-generation spec)
- Docker image build logic (see settings-and-image spec)
- Native execution path changes (existing code untouched)

## Requirements
### Functional
1. **DS-F20:** `create_job()` SHALL accept an optional `sandbox: bool` parameter (default `False`) that determines the execution path.
2. **DS-F21:** When `sandbox=True`, RalphService SHALL call `ContainerManager.check_docker_available()` before any other sandbox operations and SHALL raise a clear error if Docker is unavailable.
3. **DS-F22:** When `sandbox=True`, RalphService SHALL call `ContainerManager.ensure_image()` to verify or build the Docker image before container creation.
4. **DS-F23:** When `sandbox=True`, RalphService SHALL generate a bash loop script (via BashLoopGenerator) regardless of the host OS.
5. **DS-F24:** When `sandbox=True`, RalphService SHALL call `CredentialMounter.get_mounts()` and combine the resulting credential mounts with the project root RW mount.
6. **DS-F25:** When `sandbox=True`, RalphService SHALL call `ContainerManager.create_container()` and `start_container()` to launch the job in a Docker container instead of a subprocess.
7. **DS-F26:** Job metadata written to `{job_dir}/job.json` SHALL include `sandbox` (bool) and `container_id` (str or null) fields.
8. **DS-F27:** `stop_job()` SHALL detect whether a job is sandboxed (from job metadata) and issue `ContainerManager.stop_container()` instead of OS process signal for sandboxed jobs.
9. **DS-F28:** When `sandbox=False` or omitted, RalphService SHALL follow the existing native execution path with zero behavioral changes.
10. **DS-F29:** The `ralph_start` MCP tool SHALL accept a `sandbox` parameter and pass it through to `create_job()`.
11. **DS-F30:** The dashboard job status response SHALL include a `sandbox` boolean field, and the dashboard UI SHALL display a "Sandboxed" badge when true.
12. **DS-F31:** The project root SHALL be mounted read-write at `/workspace` inside the container, and since `.vista/ralph/{job}/` is inside the project, `output.log` and all job artifacts are accessible on the host through this single mount.
13. **DS-F32:** The API SHALL expose `GET /api/ralph/sandbox/status` returning Docker availability, daemon status, and image existence.
14. **DS-F33:** The API SHALL expose `POST /api/ralph/sandbox/build` to trigger image build or rebuild on demand.

### Non-Functional
1. **DS-NF6:** The native execution path SHALL have zero performance impact from sandbox code (no Docker SDK import, no Docker checks when sandbox=False).
2. **DS-NF7:** Docker unavailability SHALL never cause a silent fallback to native execution; it SHALL always produce an explicit error.

## User Workflows
### Workflow: Start Sandboxed Ralph Job
**Actor:** User via Claude/MCP
**Trigger:** User calls `ralph_start` with `sandbox=true`
**Steps:**
1. MCP tool receives request with task, provider, model, iterations, sandbox=true
2. RalphService.create_job() called with sandbox=true
3. RalphService checks Docker availability via ContainerManager
4. RalphService ensures Docker image exists (builds if needed, reports progress)
5. RalphService creates job directory, writes task.md and PROMPT.md (same as native)
6. RalphService generates bash loop.sh via BashLoopGenerator (Linux variant)
7. RalphService gets credential mounts via CredentialMounter
8. RalphService creates project mount: `{project_root}` -> `/workspace` (RW)
9. RalphService calls ContainerManager.create_container() with all mounts, labels, command
10. RalphService calls ContainerManager.start_container()
11. RalphService writes job.json with sandbox=true, container_id
12. Returns job_id to user with "Job started (sandboxed)" message
**Error Cases:**
- Docker not installed: "Docker is not installed. Install from https://docs.docker.com/get-docker/"
- Docker not running: "Docker daemon is not running. Please start Docker Desktop."
- Image build fails: "Docker image build failed. See build logs: {details}. Try POST /api/ralph/sandbox/build to rebuild."
- Container creation fails: "Failed to create sandbox container: {docker_error}"

### Workflow: Start Native Ralph Job (unchanged)
**Actor:** User via Claude/MCP
**Trigger:** User calls `ralph_start` without `sandbox` or with `sandbox=false`
**Steps:**
1. MCP tool receives request without sandbox flag
2. RalphService.create_job() follows existing native path
3. Generates platform-appropriate loop script (PowerShell on Windows, bash on Linux/macOS)
4. Launches subprocess, writes job.json with sandbox=false, container_id=null
5. Returns job_id
**Error Cases:**
- Same as current implementation (no changes)

### Workflow: Stop Sandboxed Job
**Actor:** User via MCP or dashboard
**Trigger:** `ralph_stop(job_id)` called
**Steps:**
1. RalphService reads job.json to determine sandbox status
2. Job is sandboxed: retrieves container_id from job.json
3. Calls ContainerManager.stop_container(container_id)
4. Container stopped and auto-removed
5. Job status updated to "stopped"
**Error Cases:**
- Container already stopped/removed: idempotent, mark job as stopped
- Container not found: mark job as stopped (container may have exited naturally)

### Workflow: Check Sandbox Status
**Actor:** User or dashboard
**Trigger:** `GET /api/ralph/sandbox/status`
**Steps:**
1. API calls ContainerManager.check_docker_available()
2. If available, checks if image exists via ContainerManager.ensure_image(check_only=true)
3. Returns: `{docker_installed: bool, daemon_running: bool, image_exists: bool, image_name: str}`
**Error Cases:**
- Docker SDK not installed: returns `{docker_installed: false, ...}`

### Workflow: Dashboard Displays Sandboxed Job
**Actor:** Dashboard polling
**Trigger:** Dashboard requests job status
**Steps:**
1. Dashboard calls `GET /api/ralph/jobs/{id}`
2. Response includes `sandbox: true` and `container_id`
3. Dashboard reads `output.log` from host filesystem (same path as native -- volume mount makes this transparent)
4. Parser produces activity (same parsers as native)
5. Dashboard renders activity with "Sandboxed" badge overlay
**Error Cases:**
- output.log not yet created: show "Starting..." status (same as native behavior)

## Data Model
**Entities:**
- Extended `JOB` entity: add `sandbox` (bool), `container_id` (str, nullable) to existing job.json schema
- Existing fields unchanged: `job_id`, `task`, `provider`, `model`, `pid`, `status`, `created_at`

**Relationships:**
- JOB optionally has CONTAINER_INFO (via container_id FK, only when sandbox=true)

## Integration Points
**Dependencies:**
- ContainerManager (container-lifecycle spec): Docker operations
- CredentialMounter (credential-management spec): mount spec generation
- BashLoopGenerator (bash-loop-generation spec): Linux loop script generation
- SandboxConfig (settings-and-image spec): image name, TTL, network settings
- Existing RalphService infrastructure: job directory, task.md, PROMPT.md, output.log, parsers

**Provides to:**
- MCP tools: `ralph_start` extended with sandbox parameter
- Dashboard API: job metadata with sandbox flag
- Dashboard UI: "Sandboxed" badge rendering data

## Technical Considerations
### Architecture
- SandboxJobCreator is a helper class (or method group within RalphService) that encapsulates the Docker-specific creation flow
- RalphService remains the single entry point; branching on `sandbox` flag routes to native or sandbox path
- Job metadata (job.json) is the authoritative source for sandbox status; no in-memory-only tracking
- `output.log` on the host filesystem is the single source of truth for dashboard activity regardless of execution mode

### Patterns
- Strategy pattern: native vs sandbox execution strategies behind create_job()
- Guard clause: check Docker availability as first step, fail fast
- Feature flag: sandbox parameter acts as per-job feature toggle

### Libraries/APIs
- Existing RalphService methods reused for job directory setup
- FastAPI route extensions for new sandbox endpoints
- MCP tool parameter extension for sandbox flag

## Related Diagrams
- `arch/user-flow.mmd` -- Decision flow for native vs sandboxed path including Docker checks
- `arch/sequence-sandboxed-job.mmd` -- Full lifecycle from MCP call through container execution
- `arch/system-architecture.mmd` -- RalphService relationship to ContainerManager and CredentialMounter
- `arch/data-model.mmd` -- Extended JOB entity with sandbox and container_id fields

## Acceptance Criteria
- [ ] DS-F20: `create_job(sandbox=True)` creates a sandboxed job; `create_job(sandbox=False)` creates a native job
- [ ] DS-F21: `create_job(sandbox=True)` with Docker unavailable raises error with clear message
- [ ] DS-F22: `create_job(sandbox=True)` with missing image triggers auto-build before container creation
- [ ] DS-F23: Sandboxed job generates bash loop.sh even on Windows host
- [ ] DS-F24: Container created with project RW mount and credential RO mounts combined
- [ ] DS-F25: Sandboxed job launches via ContainerManager, not subprocess
- [ ] DS-F26: job.json contains `sandbox: true` and `container_id` for sandboxed jobs
- [ ] DS-F26: job.json contains `sandbox: false` and `container_id: null` for native jobs
- [ ] DS-F27: Stopping sandboxed job calls `docker stop`, not OS signal
- [ ] DS-F28: Native jobs execute identically to pre-sandbox implementation
- [ ] DS-F29: `ralph_start` MCP tool accepts sandbox parameter
- [ ] DS-F30: Dashboard shows "Sandboxed" badge for sandboxed jobs
- [ ] DS-F31: output.log written inside container is visible on host via project mount
- [ ] DS-F32: `GET /api/ralph/sandbox/status` returns correct Docker/image status
- [ ] DS-F33: `POST /api/ralph/sandbox/build` triggers image build
- [ ] DS-NF6: Native job creation does not import Docker SDK or check Docker
- [ ] DS-NF7: Docker unavailable + sandbox=true produces error, never silent fallback

## Testing Strategy
> SandboxJobCreator is a TDD-flagged component

**TDD Required:** Yes
**TDD Diagrams:** N/A (integration orchestration, tested via mock collaborators)

### Test Cases (from domain requirements Layer 6)
#### Happy Path
- `test_create_sandboxed_job_full_flow`: sandbox=true, Docker available, image exists -> container created and started
- `test_create_native_job_unchanged`: sandbox=false -> existing subprocess path, no Docker interaction
- `test_sandboxed_job_metadata`: job.json contains sandbox=true and valid container_id
- `test_native_job_metadata`: job.json contains sandbox=false and container_id=null
- `test_stop_sandboxed_job`: stop_job calls ContainerManager.stop_container
- `test_stop_native_job`: stop_job sends OS signal (existing behavior)
- `test_output_log_accessible_via_mount`: output.log path on host matches expected job_dir location
- `test_sandbox_status_endpoint`: returns correct docker_installed, daemon_running, image_exists

#### Edge Cases
- `test_sandbox_omitted_defaults_false`: create_job without sandbox param behaves as native
- `test_stop_already_exited_container`: container naturally completed, stop is idempotent
- `test_image_auto_built_on_first_use`: image missing triggers build, then container creation proceeds
- `test_sandbox_badge_in_job_response`: GET job endpoint includes sandbox field

#### Error Conditions
- `test_sandbox_docker_not_installed`: clear error message with install link
- `test_sandbox_docker_not_running`: clear error message mentioning Docker Desktop
- `test_sandbox_image_build_failure`: error with build logs and rebuild suggestion
- `test_sandbox_container_create_failure`: error with Docker details
- `test_sandbox_never_silent_fallback`: Docker unavailable + sandbox=true -> error, never native execution

### Test Data Requirements
- Mocked ContainerManager with configurable responses
- Mocked CredentialMounter returning test mount specs
- Mocked BashLoopGenerator returning test script content
- Real job directory structure (via tmp_path fixture)
- Test task descriptions and provider configurations

## Requirement Index
| ID | Section | Status |
|----|---------|--------|
| DS-F20 | Functional | Active |
| DS-F21 | Functional | Active |
| DS-F22 | Functional | Active |
| DS-F23 | Functional | Active |
| DS-F24 | Functional | Active |
| DS-F25 | Functional | Active |
| DS-F26 | Functional | Active |
| DS-F27 | Functional | Active |
| DS-F28 | Functional | Active |
| DS-F29 | Functional | Active |
| DS-F30 | Functional | Active |
| DS-F31 | Functional | Active |
| DS-F32 | Functional | Active |
| DS-F33 | Functional | Active |
| DS-NF6 | Non-Functional | Active |
| DS-NF7 | Non-Functional | Active |

## Open Questions
- [ ] Should `sandbox=true` be persisted as a user preference per slug, or always explicit per job?
- [ ] Should the MCP tool expose a `ralph_sandbox_status` tool, or only the REST API endpoint?
- [ ] How should the dashboard "Sandboxed" badge be styled (color, position, icon)?
- [ ] Should image build progress be streamed to the MCP tool caller, or only logged?
