"""Tests for Docker client lazy wrapper."""

from unittest.mock import MagicMock, patch
import pytest

from server.services.sandbox.docker_client import (
    get_docker_client,
    is_docker_available,
    reset_client,
)
from server.services.sandbox.sandbox_errors import (
    DockerDaemonNotRunningError,
    DockerNotInstalledError,
)


@pytest.fixture(autouse=True)
def clean_client_state():
    """Reset the global client before each test."""
    reset_client()
    yield
    reset_client()


class TestIsDockerAvailable:
    def test_returns_false_when_sdk_not_installed(self):
        with patch.dict("sys.modules", {"docker": None}):
            reset_client()
            available, msg = is_docker_available()
            assert available is False
            assert "not installed" in msg.lower()

    def test_returns_true_when_running(self):
        mock_docker = MagicMock()
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True

        with patch.dict("sys.modules", {"docker": mock_docker}):
            reset_client()
            available, msg = is_docker_available()
            assert available is True
            assert "running" in msg.lower()

    def test_returns_false_when_daemon_not_running(self):
        mock_docker = MagicMock()
        mock_docker.errors = MagicMock()
        mock_docker.errors.DockerException = Exception
        mock_docker.from_env.side_effect = Exception("connection refused")

        with patch.dict("sys.modules", {"docker": mock_docker}):
            reset_client()
            available, msg = is_docker_available()
            assert available is False
            assert "not running" in msg.lower() or "failed" in msg.lower()


class TestGetDockerClient:
    def test_raises_when_sdk_not_installed(self):
        with patch.dict("sys.modules", {"docker": None}):
            reset_client()
            with pytest.raises(DockerNotInstalledError):
                get_docker_client()

    def test_raises_when_daemon_not_running(self):
        mock_docker = MagicMock()
        mock_docker.errors.DockerException = Exception
        mock_docker.from_env.return_value.ping.side_effect = Exception("refused")

        with patch.dict("sys.modules", {"docker": mock_docker}):
            reset_client()
            with pytest.raises(DockerDaemonNotRunningError):
                get_docker_client()

    def test_returns_client_when_available(self):
        mock_docker = MagicMock()
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = Exception
        mock_client.ping.return_value = True

        with patch.dict("sys.modules", {"docker": mock_docker}):
            reset_client()
            client = get_docker_client()
            assert client is mock_client

    def test_caches_client(self):
        mock_docker = MagicMock()
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = Exception
        mock_client.ping.return_value = True

        with patch.dict("sys.modules", {"docker": mock_docker}):
            reset_client()
            client1 = get_docker_client()
            client2 = get_docker_client()
            assert client1 is client2
            # from_env should only be called once
            assert mock_docker.from_env.call_count == 1


class TestSandboxErrors:
    def test_error_hierarchy(self):
        from server.services.sandbox.sandbox_errors import (
            SandboxError,
            DockerNotAvailableError,
            DockerNotInstalledError,
            DockerDaemonNotRunningError,
            ImageBuildError,
            ContainerCreateError,
            ContainerStartError,
            InvalidStateError,
        )

        assert issubclass(DockerNotAvailableError, SandboxError)
        assert issubclass(DockerNotInstalledError, DockerNotAvailableError)
        assert issubclass(DockerDaemonNotRunningError, DockerNotAvailableError)
        assert issubclass(ImageBuildError, SandboxError)
        assert issubclass(ContainerCreateError, SandboxError)
        assert issubclass(ContainerStartError, SandboxError)
        assert issubclass(InvalidStateError, SandboxError)

    def test_invalid_state_error_message(self):
        from server.services.sandbox.sandbox_errors import InvalidStateError
        err = InvalidStateError("uninitialized", "stop_container")
        assert "uninitialized" in str(err)
        assert "stop_container" in str(err)

    def test_image_build_error_preserves_log(self):
        from server.services.sandbox.sandbox_errors import ImageBuildError
        err = ImageBuildError("Build failed", build_log="some log output")
        assert err.build_log == "some log output"
