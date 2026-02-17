"""Tests for ContainerManager — TDD from state diagram."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from server.services.sandbox.sandbox_errors import (
    ContainerCreateError,
    ContainerStartError,
    DockerDaemonNotRunningError,
    ImageBuildError,
    InvalidStateError,
)


def _make_manager(session_id="test-session"):
    """Create a ContainerManager with a mocked Docker client."""
    from server.services.sandbox.container_manager import ContainerManager
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mgr = ContainerManager.__new__(ContainerManager)
    mgr.session_id = session_id
    mgr._client = mock_client
    mgr._containers = {}
    return mgr, mock_client


class TestCheckDockerAvailable:
    def test_returns_true_when_daemon_reachable(self):
        mgr, client = _make_manager()
        client.ping.return_value = True
        ok, msg = mgr.check_docker_available()
        assert ok is True

    def test_returns_false_when_daemon_unreachable(self):
        mgr, client = _make_manager()
        client.ping.side_effect = Exception("refused")
        ok, msg = mgr.check_docker_available()
        assert ok is False
        assert "not running" in msg.lower() or "refused" in msg.lower()


class TestEnsureImage:
    def test_image_found_locally(self):
        mgr, client = _make_manager()
        mock_image = MagicMock()
        client.images.get.return_value = mock_image
        result = mgr.ensure_image("vista-ralph:latest")
        assert result is True
        client.images.get.assert_called_once_with("vista-ralph:latest")

    def test_image_not_found_check_only(self):
        mgr, client = _make_manager()
        # ImageNotFound exception
        import docker.errors
        client.images.get.side_effect = Exception("not found")
        result = mgr.ensure_image("vista-ralph:latest", check_only=True)
        assert result is False

    def test_image_not_found_triggers_build(self):
        mgr, client = _make_manager()
        client.images.get.side_effect = Exception("not found")
        mock_image = MagicMock()
        mock_image.id = "sha256:abc123"
        client.images.build.return_value = (mock_image, [])

        with patch("server.services.sandbox.container_manager.DOCKERFILE_DIR") as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.__str__ = lambda self: "/fake/docker"
            result = mgr.ensure_image("vista-ralph:latest", check_only=False)
            assert result is True
            client.images.build.assert_called_once()


class TestCreateContainer:
    def test_creates_with_correct_labels(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "vista-ralph-test1234"
        mock_container.status = "created"
        client.containers.create.return_value = mock_container

        info = mgr.create_container(
            job_id="test-job-12345678",
            provider="claude",
            image="vista-ralph:latest",
            mounts=[],
            env_vars={},
            network_enabled=True,
            ttl_seconds=7200,
        )
        call_kwargs = client.containers.create.call_args
        labels = call_kwargs.kwargs.get("labels", {})
        assert labels["managed-by"] == "vista-ralph"
        assert labels["vista-job-id"] == "test-job-12345678"
        assert labels["vista-provider"] == "claude"
        assert labels["vista-session"] == "test-session"

    def test_working_dir_is_workspace(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "vista-ralph-test1234"
        mock_container.status = "created"
        client.containers.create.return_value = mock_container

        mgr.create_container(
            job_id="test-job-12345678",
            provider="claude",
            image="vista-ralph:latest",
            mounts=[],
        )
        call_kwargs = client.containers.create.call_args
        assert call_kwargs.kwargs.get("working_dir") == "/workspace"

    def test_container_naming(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "vista-ralph-test-job"
        mock_container.status = "created"
        client.containers.create.return_value = mock_container

        info = mgr.create_container(
            job_id="test-job-12345678",
            provider="claude",
            image="vista-ralph:latest",
            mounts=[],
        )
        call_kwargs = client.containers.create.call_args
        name = call_kwargs.kwargs.get("name", "")
        assert name.startswith("vista-ralph-")

    def test_network_bridge_when_enabled(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "test"
        mock_container.status = "created"
        client.containers.create.return_value = mock_container

        mgr.create_container(
            job_id="j-12345678",
            provider="claude",
            image="vista-ralph:latest",
            mounts=[],
            network_enabled=True,
        )
        call_kwargs = client.containers.create.call_args
        assert call_kwargs.kwargs.get("network_mode") == "bridge"

    def test_network_none_when_disabled(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "test"
        mock_container.status = "created"
        client.containers.create.return_value = mock_container

        mgr.create_container(
            job_id="j-12345678",
            provider="claude",
            image="vista-ralph:latest",
            mounts=[],
            network_enabled=False,
        )
        call_kwargs = client.containers.create.call_args
        assert call_kwargs.kwargs.get("network_mode") == "none"

    def test_create_failure_raises(self):
        mgr, client = _make_manager()
        client.containers.create.side_effect = Exception("out of memory")

        with pytest.raises(ContainerCreateError):
            mgr.create_container(
                job_id="j-12345678",
                provider="claude",
                image="vista-ralph:latest",
                mounts=[],
            )

    def test_sleep_infinity_command(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "test"
        mock_container.status = "created"
        client.containers.create.return_value = mock_container

        mgr.create_container(
            job_id="j-12345678",
            provider="claude",
            image="vista-ralph:latest",
            mounts=[],
        )
        call_kwargs = client.containers.create.call_args
        assert call_kwargs.kwargs.get("command") == "sleep infinity"


class TestStartContainer:
    def test_start_success(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.status = "running"
        client.containers.get.return_value = mock_container

        mgr.start_container("abc123")
        mock_container.start.assert_called_once()

    def test_start_failure_raises(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.start.side_effect = Exception("fail")
        client.containers.get.return_value = mock_container

        with pytest.raises(ContainerStartError):
            mgr.start_container("abc123")


class TestStopContainer:
    def test_stop_running_container(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.status = "running"
        client.containers.get.return_value = mock_container

        mgr.stop_container("abc123")
        mock_container.stop.assert_called_once_with(timeout=10)

    def test_stop_already_stopped_is_idempotent(self):
        mgr, client = _make_manager()
        # Container not found (already removed)
        client.containers.get.side_effect = Exception("not found")
        # Should not raise
        mgr.stop_container("abc123")

    def test_stop_and_remove(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        mock_container.status = "running"
        client.containers.get.return_value = mock_container

        mgr.stop_container("abc123", remove=True)
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once_with(force=True)


class TestExecInContainer:
    def test_exec_returns_exit_code(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        client.containers.get.return_value = mock_container
        mock_container.exec_run.return_value = (0, b"output")

        exit_code, output = mgr.exec_in_container(
            "abc123", ["bash", "/workspace/loop.sh"]
        )
        assert exit_code == 0
        mock_container.exec_run.assert_called_once()

    def test_exec_with_workdir(self):
        mgr, client = _make_manager()
        mock_container = MagicMock()
        client.containers.get.return_value = mock_container
        mock_container.exec_run.return_value = (0, b"")

        mgr.exec_in_container(
            "abc123", ["ls"], workdir="/workspace"
        )
        call_kwargs = mock_container.exec_run.call_args
        assert call_kwargs.kwargs.get("workdir") == "/workspace"


class TestCleanupStaleContainers:
    def test_removes_vista_labeled_containers(self):
        mgr, client = _make_manager(session_id="new-session")
        old_container = MagicMock()
        old_container.name = "vista-ralph-old"
        old_container.labels = {
            "managed-by": "vista-ralph",
            "vista-session": "old-session",
        }
        old_container.status = "running"

        current_container = MagicMock()
        current_container.name = "vista-ralph-current"
        current_container.labels = {
            "managed-by": "vista-ralph",
            "vista-session": "new-session",
        }
        current_container.status = "running"

        client.containers.list.return_value = [old_container, current_container]

        removed = mgr.cleanup_orphans()
        assert "vista-ralph-old" in removed
        assert "vista-ralph-current" not in removed
        old_container.stop.assert_called_once()
        old_container.remove.assert_called_once_with(force=True)
        current_container.stop.assert_not_called()

    def test_cleanup_with_no_containers(self):
        mgr, client = _make_manager()
        client.containers.list.return_value = []
        removed = mgr.cleanup_orphans()
        assert removed == []


class TestListContainers:
    def test_lists_managed_containers(self):
        mgr, client = _make_manager()
        mock_c = MagicMock()
        mock_c.id = "abc123"
        mock_c.name = "vista-ralph-test1234"
        mock_c.status = "running"
        mock_c.labels = {
            "managed-by": "vista-ralph",
            "vista-job-id": "job-1",
            "vista-provider": "claude",
            "vista-session": "test-session",
        }
        client.containers.list.return_value = [mock_c]

        containers = mgr.list_containers()
        assert len(containers) == 1
        assert containers[0].name == "vista-ralph-test1234"
        assert containers[0].job_id == "job-1"
        assert containers[0].status == "running"
