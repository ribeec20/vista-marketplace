"""Lazy Docker SDK wrapper with graceful degradation."""

from __future__ import annotations

import logging
from typing import Any, Optional

from server.services.sandbox.sandbox_errors import (
    DockerDaemonNotRunningError,
    DockerNotInstalledError,
)

logger = logging.getLogger(__name__)

_client: Optional[Any] = None
_sdk_available: Optional[bool] = None


def _check_sdk() -> bool:
    """Check if docker SDK is importable."""
    global _sdk_available
    if _sdk_available is not None:
        return _sdk_available
    try:
        import docker  # noqa: F401
        _sdk_available = True
    except ImportError:
        _sdk_available = False
    return _sdk_available


def get_docker_client() -> Any:
    """Return a cached Docker client, creating it lazily.

    Raises DockerNotInstalledError if the SDK is missing.
    Raises DockerDaemonNotRunningError if the daemon is unreachable.
    """
    global _client
    if _client is not None:
        return _client

    if not _check_sdk():
        raise DockerNotInstalledError()

    import docker
    try:
        client = docker.from_env()
        client.ping()
        _client = client
        return _client
    except docker.errors.DockerException:
        raise DockerDaemonNotRunningError()


def is_docker_available() -> tuple[bool, str]:
    """Check Docker availability without raising.

    Returns (available: bool, message: str).
    """
    if not _check_sdk():
        return False, "Docker SDK not installed. Run: pip install docker"
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True, "Docker is running"
    except docker.errors.DockerException as e:
        return False, f"Docker daemon is not running: {e}"
    except Exception as e:
        return False, f"Docker check failed: {e}"


def reset_client() -> None:
    """Reset cached client (useful for testing)."""
    global _client, _sdk_available
    _client = None
    _sdk_available = None
