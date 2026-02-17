"""Integration tests for Docker sandbox (requires Docker running).

Run with: python -m pytest tests/integration/test_docker_sandbox.py -v -m docker
"""

import pytest
from unittest.mock import MagicMock

# Mark all tests in this module as requiring Docker
pytestmark = pytest.mark.docker


def _docker_available() -> bool:
    """Check if Docker is available for integration tests."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


skip_no_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker not available for integration tests"
)


@skip_no_docker
class TestDockerSandboxIntegration:
    """Integration tests requiring a running Docker daemon."""

    def test_docker_client_connection(self):
        """Test that Docker SDK can connect to the daemon."""
        from server.services.sandbox.docker_client import is_docker_available, reset_client
        reset_client()
        available, msg = is_docker_available()
        assert available is True

    def test_container_manager_check_docker(self):
        """Test ContainerManager can ping Docker."""
        import docker
        from server.services.sandbox.container_manager import ContainerManager
        client = docker.from_env()
        mgr = ContainerManager(session_id="integration-test", client=client)
        ok, msg = mgr.check_docker_available()
        assert ok is True

    def test_ensure_image_check_only(self):
        """Test that ensure_image(check_only=True) does not fail."""
        import docker
        from server.services.sandbox.container_manager import ContainerManager
        client = docker.from_env()
        mgr = ContainerManager(session_id="integration-test", client=client)
        # Just checks — may return True or False depending on image state
        result = mgr.ensure_image("vista-ralph:latest", check_only=True)
        assert isinstance(result, bool)

    def test_sandbox_status_endpoint_format(self):
        """Test that sandbox status returns correct format fields."""
        from server.services.sandbox.docker_client import is_docker_available, reset_client
        reset_client()
        available, msg = is_docker_available()
        # Should be a tuple of (bool, str)
        assert isinstance(available, bool)
        assert isinstance(msg, str)


@skip_no_docker
class TestDockerContainerLifecycle:
    """Test full container create-start-exec-stop cycle."""

    def test_full_lifecycle(self):
        """Create, start, exec, stop, remove a container."""
        import docker
        from server.services.sandbox.container_manager import ContainerManager

        client = docker.from_env()

        # Ensure we have a test image (pull if needed)
        test_image = "alpine:latest"
        try:
            client.images.get(test_image)
        except Exception:
            try:
                client.images.pull(test_image)
            except Exception:
                pytest.skip(f"Cannot pull {test_image} for integration test")

        mgr = ContainerManager(session_id="lifecycle-test", client=client)

        info = mgr.create_container(
            job_id="integration-test-lifecycle",
            provider="claude",
            image=test_image,
            mounts=[],
            network_enabled=True,
            ttl_seconds=60,
        )
        assert info.container_id
        assert info.name.startswith("vista-ralph-")

        try:
            mgr.start_container(info.container_id)

            # Exec a simple command
            exit_code, output = mgr.exec_in_container(
                info.container_id,
                ["echo", "hello from sandbox"],
            )
            assert exit_code == 0
            assert b"hello from sandbox" in output
        finally:
            mgr.stop_container(info.container_id, remove=True)
