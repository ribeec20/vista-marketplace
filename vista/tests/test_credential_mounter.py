"""Tests for CredentialMounter — TDD from decision tree diagram.

Tests cover 3 OS x 5 credentials = 15 path resolution cases,
plus enable/disable, missing paths, and edge cases.
"""

from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import patch, MagicMock

import pytest

from server.services.sandbox.credential_mounter import CredentialMounter


def _make_mounter(
    host_os: str = "Linux",
    home_dir: str = "/home/testuser",
    appdata: str = "",
    credential_config: dict = None,
    existing_paths: set = None,
):
    """Create a CredentialMounter with mocked OS/filesystem."""
    if credential_config is None:
        credential_config = {}
    if existing_paths is None:
        existing_paths = set()

    mounter = CredentialMounter(
        host_os=host_os,
        home_dir=home_dir,
        appdata=appdata,
        credential_config=credential_config,
        _path_exists_fn=lambda p: p in existing_paths,
        _is_dir_fn=lambda p: not p.endswith(".gitconfig"),
    )
    return mounter


# =========================================================================
# 15 path resolution tests: 3 OS x 5 credentials
# =========================================================================


class TestWindowsPathResolution:
    def test_claude_auth(self):
        m = _make_mounter(
            host_os="Windows",
            home_dir="C:\\Users\\Grove",
            existing_paths={"C:\\Users\\Grove\\.claude"},
        )
        mounts = m.get_mounts()
        claude_mount = next((x for x in mounts if x.name == "claude_auth"), None)
        assert claude_mount is not None
        assert claude_mount.host_path == "C:\\Users\\Grove\\.claude"
        assert claude_mount.container_path == "/home/user/.claude"
        assert claude_mount.mode == "ro"

    def test_git_ssh(self):
        m = _make_mounter(
            host_os="Windows",
            home_dir="C:\\Users\\Grove",
            existing_paths={"C:\\Users\\Grove\\.ssh"},
        )
        mounts = m.get_mounts()
        ssh_mount = next((x for x in mounts if x.name == "git_ssh"), None)
        assert ssh_mount is not None
        assert ssh_mount.host_path == "C:\\Users\\Grove\\.ssh"
        assert ssh_mount.container_path == "/home/user/.ssh"

    def test_gitconfig(self):
        m = _make_mounter(
            host_os="Windows",
            home_dir="C:\\Users\\Grove",
            existing_paths={"C:\\Users\\Grove\\.gitconfig"},
        )
        mounts = m.get_mounts()
        gc_mount = next((x for x in mounts if x.name == "git_config"), None)
        assert gc_mount is not None
        assert gc_mount.host_path == "C:\\Users\\Grove\\.gitconfig"
        assert gc_mount.container_path == "/home/user/.gitconfig"
        assert gc_mount.is_directory is False

    def test_github_cli(self):
        m = _make_mounter(
            host_os="Windows",
            home_dir="C:\\Users\\Grove",
            appdata="C:\\Users\\Grove\\AppData\\Roaming",
            existing_paths={"C:\\Users\\Grove\\AppData\\Roaming\\GitHub CLI"},
        )
        mounts = m.get_mounts()
        gh_mount = next((x for x in mounts if x.name == "gh_cli"), None)
        assert gh_mount is not None
        assert gh_mount.host_path == "C:\\Users\\Grove\\AppData\\Roaming\\GitHub CLI"
        assert gh_mount.container_path == "/home/user/.config/gh"

    def test_opencode(self):
        m = _make_mounter(
            host_os="Windows",
            home_dir="C:\\Users\\Grove",
            appdata="C:\\Users\\Grove\\AppData\\Roaming",
            existing_paths={"C:\\Users\\Grove\\AppData\\Roaming\\opencode"},
        )
        mounts = m.get_mounts()
        oc_mount = next((x for x in mounts if x.name == "opencode"), None)
        assert oc_mount is not None
        assert oc_mount.host_path == "C:\\Users\\Grove\\AppData\\Roaming\\opencode"
        assert oc_mount.container_path == "/home/user/.config/opencode"


class TestMacOSPathResolution:
    def test_claude_auth(self):
        m = _make_mounter(
            host_os="Darwin",
            home_dir="/Users/testuser",
            existing_paths={"/Users/testuser/.claude"},
        )
        mounts = m.get_mounts()
        claude_mount = next((x for x in mounts if x.name == "claude_auth"), None)
        assert claude_mount is not None
        assert claude_mount.host_path == "/Users/testuser/.claude"
        assert claude_mount.container_path == "/home/user/.claude"

    def test_git_ssh(self):
        m = _make_mounter(
            host_os="Darwin",
            home_dir="/Users/testuser",
            existing_paths={"/Users/testuser/.ssh"},
        )
        mounts = m.get_mounts()
        ssh_mount = next((x for x in mounts if x.name == "git_ssh"), None)
        assert ssh_mount is not None
        assert ssh_mount.host_path == "/Users/testuser/.ssh"

    def test_gitconfig(self):
        m = _make_mounter(
            host_os="Darwin",
            home_dir="/Users/testuser",
            existing_paths={"/Users/testuser/.gitconfig"},
        )
        mounts = m.get_mounts()
        gc_mount = next((x for x in mounts if x.name == "git_config"), None)
        assert gc_mount is not None
        assert gc_mount.is_directory is False

    def test_github_cli(self):
        m = _make_mounter(
            host_os="Darwin",
            home_dir="/Users/testuser",
            existing_paths={"/Users/testuser/.config/gh"},
        )
        mounts = m.get_mounts()
        gh_mount = next((x for x in mounts if x.name == "gh_cli"), None)
        assert gh_mount is not None
        assert gh_mount.host_path == "/Users/testuser/.config/gh"

    def test_opencode(self):
        m = _make_mounter(
            host_os="Darwin",
            home_dir="/Users/testuser",
            existing_paths={"/Users/testuser/.config/opencode"},
        )
        mounts = m.get_mounts()
        oc_mount = next((x for x in mounts if x.name == "opencode"), None)
        assert oc_mount is not None
        assert oc_mount.host_path == "/Users/testuser/.config/opencode"


class TestLinuxPathResolution:
    def test_claude_auth(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.claude"},
        )
        mounts = m.get_mounts()
        claude_mount = next((x for x in mounts if x.name == "claude_auth"), None)
        assert claude_mount is not None
        assert claude_mount.host_path == "/home/testuser/.claude"
        assert claude_mount.container_path == "/home/user/.claude"

    def test_git_ssh(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.ssh"},
        )
        mounts = m.get_mounts()
        ssh_mount = next((x for x in mounts if x.name == "git_ssh"), None)
        assert ssh_mount is not None

    def test_gitconfig(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.gitconfig"},
        )
        mounts = m.get_mounts()
        gc_mount = next((x for x in mounts if x.name == "git_config"), None)
        assert gc_mount is not None
        assert gc_mount.is_directory is False

    def test_github_cli(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.config/gh"},
        )
        mounts = m.get_mounts()
        gh_mount = next((x for x in mounts if x.name == "gh_cli"), None)
        assert gh_mount is not None

    def test_opencode(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.config/opencode"},
        )
        mounts = m.get_mounts()
        oc_mount = next((x for x in mounts if x.name == "opencode"), None)
        assert oc_mount is not None


# =========================================================================
# Mode enforcement
# =========================================================================


class TestMountModes:
    def test_all_mounts_are_readonly(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={
                "/home/testuser/.claude",
                "/home/testuser/.ssh",
                "/home/testuser/.gitconfig",
                "/home/testuser/.config/gh",
                "/home/testuser/.config/opencode",
            },
        )
        mounts = m.get_mounts()
        assert len(mounts) == 5
        assert all(mount.mode == "ro" for mount in mounts)

    def test_container_paths_use_home_user_prefix(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={
                "/home/testuser/.claude",
                "/home/testuser/.ssh",
            },
        )
        mounts = m.get_mounts()
        for mount in mounts:
            assert mount.container_path.startswith("/home/user/")


# =========================================================================
# Enable/disable behavior
# =========================================================================


class TestCredentialEnableDisable:
    def test_disabled_credential_skipped(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.ssh"},
            credential_config={"git_ssh": {"enabled": False}},
        )
        mounts = m.get_mounts()
        assert not any(x.name == "git_ssh" for x in mounts)

    def test_all_disabled_returns_empty(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.claude", "/home/testuser/.ssh"},
            credential_config={
                "claude_auth": {"enabled": False},
                "git_ssh": {"enabled": False},
                "git_config": {"enabled": False},
                "gh_cli": {"enabled": False},
                "opencode": {"enabled": False},
            },
        )
        mounts = m.get_mounts()
        assert mounts == []


# =========================================================================
# Missing paths
# =========================================================================


class TestMissingPaths:
    def test_missing_path_skipped_silently(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths=set(),  # nothing exists
        )
        mounts = m.get_mounts()
        assert mounts == []

    def test_partial_credentials(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={
                "/home/testuser/.claude",
                "/home/testuser/.ssh",
            },
        )
        mounts = m.get_mounts()
        assert len(mounts) == 2
        names = {x.name for x in mounts}
        assert names == {"claude_auth", "git_ssh"}


# =========================================================================
# File vs directory
# =========================================================================


class TestFileVsDirectory:
    def test_gitconfig_is_file_mount(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.gitconfig"},
        )
        mounts = m.get_mounts()
        gc_mount = next((x for x in mounts if x.name == "git_config"), None)
        assert gc_mount is not None
        assert gc_mount.is_directory is False

    def test_ssh_is_directory_mount(self):
        m = _make_mounter(
            host_os="Linux",
            home_dir="/home/testuser",
            existing_paths={"/home/testuser/.ssh"},
        )
        mounts = m.get_mounts()
        ssh_mount = next((x for x in mounts if x.name == "git_ssh"), None)
        assert ssh_mount is not None
        assert ssh_mount.is_directory is True
