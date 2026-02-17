"""Credential mount resolution for Docker sandbox containers.

Pure logic class — no Docker SDK dependency. Resolves host credential
paths and generates mount specs for container creation.
"""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Callable, Optional

from server.models.sandbox import CredentialMount

logger = logging.getLogger(__name__)

# Default credential definitions: name, relative_path (from home), container_path, is_directory
# Windows overrides use APPDATA for gh_cli and opencode
_CREDENTIAL_REGISTRY = [
    {
        "name": "claude_auth",
        "rel_path": ".claude",
        "container_path": "/home/user/.claude",
        "is_directory": True,
        "win_appdata": False,
    },
    {
        "name": "git_ssh",
        "rel_path": ".ssh",
        "container_path": "/home/user/.ssh",
        "is_directory": True,
        "win_appdata": False,
    },
    {
        "name": "git_config",
        "rel_path": ".gitconfig",
        "container_path": "/home/user/.gitconfig",
        "is_directory": False,
        "win_appdata": False,
    },
    {
        "name": "gh_cli",
        "rel_path": ".config/gh",
        "container_path": "/home/user/.config/gh",
        "is_directory": True,
        "win_appdata": True,
        "win_appdata_path": "GitHub CLI",
    },
    {
        "name": "opencode",
        "rel_path": ".config/opencode",
        "container_path": "/home/user/.config/opencode",
        "is_directory": True,
        "win_appdata": True,
        "win_appdata_path": "opencode",
    },
]


class CredentialMounter:
    """Resolves host credentials and generates Docker mount specs."""

    def __init__(
        self,
        host_os: Optional[str] = None,
        home_dir: Optional[str] = None,
        appdata: Optional[str] = None,
        credential_config: Optional[dict] = None,
        _path_exists_fn: Optional[Callable] = None,
        _is_dir_fn: Optional[Callable] = None,
    ):
        self.host_os = host_os or platform.system()
        self.home_dir = home_dir or str(Path.home())
        self.appdata = appdata or os.environ.get("APPDATA", "")
        self.credential_config = credential_config or {}
        self._path_exists = _path_exists_fn or (lambda p: Path(p).exists())
        self._is_dir = _is_dir_fn or (lambda p: Path(p).is_dir())

    def _join_path(self, base: str, *parts: str) -> str:
        """Join paths using the separator appropriate to the host OS being emulated."""
        if self.host_os == "Windows":
            sep = "\\"
        else:
            sep = "/"
        result = base.rstrip("/\\")
        for part in parts:
            part = part.strip("/\\")
            result = result + sep + part
        return result

    def _resolve_host_path(self, cred_def: dict) -> str:
        """Resolve the host path for a credential entry."""
        if self.host_os == "Windows" and cred_def.get("win_appdata"):
            win_path = cred_def.get("win_appdata_path", "")
            if self.appdata:
                return self._join_path(self.appdata, win_path)
        # Default: home_dir + relative_path
        return self._join_path(self.home_dir, cred_def["rel_path"])

    def _is_enabled(self, cred_name: str) -> bool:
        """Check if a credential is enabled in config. Default: True."""
        entry = self.credential_config.get(cred_name, {})
        if isinstance(entry, dict):
            return entry.get("enabled", True)
        return True

    def get_mounts(self) -> list[CredentialMount]:
        """Generate mount specs for all enabled, existing credentials."""
        mounts = []

        for cred_def in _CREDENTIAL_REGISTRY:
            name = cred_def["name"]

            if not self._is_enabled(name):
                logger.debug(f"Skipping {name}: disabled in config")
                continue

            host_path = self._resolve_host_path(cred_def)

            if not self._path_exists(host_path):
                logger.debug(f"{name} path not found: {host_path} — skipping mount")
                continue

            is_dir = cred_def["is_directory"]

            mount = CredentialMount(
                name=name,
                host_path=host_path,
                container_path=cred_def["container_path"],
                mode="ro",
                is_directory=is_dir,
            )
            mounts.append(mount)

        return mounts
