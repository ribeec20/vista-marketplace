"""Data models for Docker sandbox functionality."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MountSpec:
    """A single bind mount specification."""
    host_path: str
    container_path: str
    mode: str  # "rw" or "ro"
    mount_type: str = "bind"


@dataclass
class CredentialMount:
    """Configuration for a credential mount entry."""
    name: str  # "claude_auth", "git_ssh", etc.
    host_path: str
    container_path: str
    mode: str = "ro"
    is_directory: bool = True


@dataclass
class ContainerInfo:
    """Runtime information about a managed Docker container."""
    container_id: str
    name: str
    job_id: str
    provider: str
    status: str  # "creating", "running", "stopping", "removed", "failed"
    image: str = ""
    created_at: str = ""
    expires_at: str = ""
    error: str = ""
