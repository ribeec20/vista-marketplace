# Spec: Credential Management

## Overview
Detects host credential directories, translates paths across operating systems, and generates read-only Docker bind mount specifications for container access.

## Changelog
| Date | ID | Change | Reason | Commit |
|------|-----|--------|--------|--------|
| 2026-02-12 | --- | Created | Initial spec generation | --- |

## Parent JTBD
Enable sandboxed agent loops to authenticate with external services (GitHub, Claude API, SSH remotes) by securely mounting host credentials into containers without write access.

## Scope
**In Scope:**
- CredentialMounter class responsible for mount spec generation
- Detection of host credential directories on Windows, macOS, and Linux
- Path translation from host OS paths to Linux container paths
- Read-only mount mode enforcement for all credential mounts
- Graceful handling of missing credential directories (skip, do not fail)
- Configurable credential mount list via SANDBOX_CONFIG
- Support for individual credential mount enable/disable

**Out of Scope:**
- Creating or managing credentials themselves
- Credential rotation or refresh inside containers
- Docker volume creation (uses bind mounts only)
- Network-based credential forwarding (e.g., SSH agent forwarding)
- Encrypting credentials at rest within containers

## Requirements
### Functional
1. **DS-F12:** CredentialMounter SHALL detect and generate mount specs for these credential directories: `~/.claude/`, `~/.ssh/`, `~/.gitconfig`, `~/.config/gh/`, `~/.config/opencode/`.
2. **DS-F13:** All credential mounts SHALL use read-only mode (`ro`).
3. **DS-F14:** CredentialMounter SHALL resolve host credential paths using the correct home directory for the current OS: `%USERPROFILE%` on Windows, `$HOME` on macOS/Linux.
4. **DS-F15:** CredentialMounter SHALL translate host paths to Linux container paths using a fixed mapping: host `~/.claude/` -> container `/home/user/.claude/`, host `~/.ssh/` -> container `/home/user/.ssh/`, etc.
5. **DS-F16:** When a credential directory does not exist on the host, CredentialMounter SHALL skip that mount silently and continue with remaining mounts.
6. **DS-F17:** CredentialMounter SHALL accept a `credential_mounts` configuration (from SANDBOX_CONFIG) that allows enabling/disabling individual credential types.
7. **DS-F18:** CredentialMounter SHALL handle single-file credentials (e.g., `~/.gitconfig`) differently from directory credentials, using the correct Docker bind mount type.
8. **DS-F19:** CredentialMounter SHALL return mount specs as a list of `Mount` objects with `host_path`, `container_path`, `mode`, and `type` fields.

### Non-Functional
1. **DS-NF4:** CredentialMounter SHALL be a pure logic class with no Docker SDK dependency, operating only on path resolution and mount spec generation.
2. **DS-NF5:** Path resolution SHALL work correctly regardless of whether the host uses forward slashes or backslashes.

## User Workflows
### Workflow: Mount Specs Generated for Sandboxed Job
**Actor:** RalphService (internal caller)
**Trigger:** Sandboxed job creation needs credential mounts
**Steps:**
1. RalphService calls `CredentialMounter.get_mounts(host_os)` passing current platform
2. CredentialMounter reads SANDBOX_CONFIG for enabled credential types
3. For each enabled credential type, resolves host path using OS-appropriate home directory
4. Checks if host path exists on filesystem
5. If exists: generates Mount spec with host path, container target path, and `ro` mode
6. If missing: logs debug message, skips this mount
7. Returns list of Mount specs to RalphService
8. RalphService passes mount specs to ContainerManager for container creation
**Error Cases:**
- Home directory not resolvable: raise configuration error (should never happen in practice)
- All credential directories missing: return empty list (container runs without credentials)

### Workflow: User Disables Specific Credential Mount
**Actor:** User editing settings.json
**Trigger:** User wants to exclude SSH keys from container
**Steps:**
1. User sets `credential_mounts.git_ssh.enabled = false` in settings.json
2. Next sandboxed job creation: CredentialMounter reads config, skips `~/.ssh/` mount
3. Container created without SSH key access
**Error Cases:**
- Invalid credential mount name in config: ignored, does not affect other mounts

## Data Model
**Entities:**
- `CredentialMount` (config): `name` (str: "claude_auth", "git_ssh", "git_config", "gh_cli", "opencode"), `host_path` (str, OS-specific), `container_path` (str, Linux), `mode` ("ro"), `enabled` (bool)
- `Mount` (runtime): `host_path` (str, resolved absolute), `container_path` (str), `mode` ("ro"), `type` ("credential")

**Relationships:**
- SANDBOX_CONFIG has one or more CredentialMount definitions
- CredentialMounter produces zero or more Mount specs per invocation

## Integration Points
**Dependencies:**
- Host filesystem (to check credential directory existence)
- SANDBOX_CONFIG from settings (for credential mount definitions and enable/disable)
- `platform` module (for OS detection)
- `pathlib.Path` (for cross-platform path resolution)

**Provides to:**
- ContainerManager: mount specs included in `create_container()` call
- RalphService: intermediary caller

## Technical Considerations
### Architecture
- CredentialMounter is a standalone class in `server/services/credential_mounter.py`
- No Docker SDK dependency -- pure path logic and filesystem checks
- Default credential mount definitions hardcoded with config overrides

### Patterns
- Registry pattern: default credential types registered internally, overridable via config
- Null object pattern: missing credentials produce empty mount list, not errors

### Libraries/APIs
- `pathlib.Path.home()` for cross-platform home directory resolution
- `pathlib.Path.exists()` for credential directory detection
- `platform.system()` for OS identification
- `os.environ.get("USERPROFILE")` as Windows fallback

### Credential Path Mapping Table

| Credential | Host Path (Windows) | Host Path (macOS/Linux) | Container Path |
|------------|-------------------|------------------------|----------------|
| Claude auth | `%USERPROFILE%\.claude\` | `~/.claude/` | `/home/user/.claude/` |
| SSH keys | `%USERPROFILE%\.ssh\` | `~/.ssh/` | `/home/user/.ssh/` |
| Git config | `%USERPROFILE%\.gitconfig` | `~/.gitconfig` | `/home/user/.gitconfig` |
| GitHub CLI | `%USERPROFILE%\.config\gh\` | `~/.config/gh/` | `/home/user/.config/gh/` |
| OpenCode | `%USERPROFILE%\.config\opencode\` | `~/.config/opencode/` | `/home/user/.config/opencode/` |

## Related Diagrams
- `arch/data-model.mmd` -- CREDENTIAL_MOUNT entity and relationship to SANDBOX_CONFIG
- `arch/system-architecture.mmd` -- CredentialMounter component within host services
- `arch/sequence-sandboxed-job.mmd` -- CredentialMounter called during job creation sequence

## Acceptance Criteria
- [ ] DS-F12: Mount specs generated for all five credential directories when all exist on host
- [ ] DS-F13: Every mount spec in the returned list has `mode="ro"`
- [ ] DS-F14: On Windows, host paths resolve using `%USERPROFILE%`; on macOS/Linux, using `$HOME`
- [ ] DS-F15: Container paths follow `/home/user/` prefix convention for all credential types
- [ ] DS-F16: Missing `~/.ssh/` on host produces mount list without SSH entry, no error raised
- [ ] DS-F16: All credential directories missing produces empty mount list, no error raised
- [ ] DS-F17: Setting `git_ssh.enabled=false` in config excludes SSH mount from results
- [ ] DS-F18: `~/.gitconfig` (file) and `~/.ssh/` (directory) produce correct bind mount types
- [ ] DS-F19: Each mount spec has all four fields: host_path, container_path, mode, type

## Testing Strategy
> CredentialMounter is a TDD-flagged component

**TDD Required:** Yes
**TDD Diagrams:** N/A (pure logic, state diagram not applicable)

### Test Cases (from domain requirements Layer 3)
#### Happy Path
- `test_all_credentials_exist_all_mounted`: All 5 credential dirs exist, 5 mount specs returned
- `test_mount_mode_always_ro`: Every returned mount has mode="ro"
- `test_mount_type_always_credential`: Every returned mount has type="credential"
- `test_windows_paths_resolved_correctly`: On Windows (mocked), host paths use USERPROFILE
- `test_linux_paths_resolved_correctly`: On Linux (mocked), host paths use HOME
- `test_macos_paths_resolved_correctly`: On macOS (mocked), host paths use HOME
- `test_container_paths_use_home_user_prefix`: All container paths start with `/home/user/`
- `test_gitconfig_file_mount`: `~/.gitconfig` produces file bind mount, not directory mount
- `test_ssh_directory_mount`: `~/.ssh/` produces directory bind mount

#### Edge Cases
- `test_no_credentials_exist`: All 5 missing, returns empty list, no error
- `test_partial_credentials`: Only `~/.claude/` and `~/.ssh/` exist, returns 2 mount specs
- `test_disabled_credential_skipped`: `git_ssh.enabled=false` excludes SSH even if dir exists
- `test_all_credentials_disabled`: All disabled in config, returns empty list
- `test_windows_backslash_paths`: Windows paths with backslashes handled correctly
- `test_symlinked_credential_dir`: Symlinked `~/.ssh` resolves and mounts correctly

#### Error Conditions
- `test_home_dir_not_resolvable`: Raises clear configuration error (mocked scenario)
- `test_invalid_credential_name_in_config`: Unknown names in config ignored, valid ones processed

### Test Data Requirements
- Mocked `platform.system()` returning "Windows", "Darwin", "Linux"
- Mocked `Path.home()` returning OS-appropriate paths
- Mocked `Path.exists()` returning True/False per credential directory
- Test SANDBOX_CONFIG with various credential enable/disable combinations

## Requirement Index
| ID | Section | Status |
|----|---------|--------|
| DS-F12 | Functional | Active |
| DS-F13 | Functional | Active |
| DS-F14 | Functional | Active |
| DS-F15 | Functional | Active |
| DS-F16 | Functional | Active |
| DS-F17 | Functional | Active |
| DS-F18 | Functional | Active |
| DS-F19 | Functional | Active |
| DS-NF4 | Non-Functional | Active |
| DS-NF5 | Non-Functional | Active |

## Open Questions
- [ ] Should the container user be `user` (matching claudebox base image) or configurable?
- [ ] Should UID/GID mapping be handled here or in ContainerManager? Domain requirements specify "UID/GID matching host user."
- [ ] Is SSH agent forwarding needed in v1, or is key file mounting sufficient?
- [ ] Should `~/.config/opencode/` path vary by OS (e.g., `%APPDATA%\opencode\` on Windows)?
