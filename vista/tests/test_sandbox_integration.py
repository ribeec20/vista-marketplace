"""Tests for RalphService sandbox integration — Phase 6 TDD.

Tests cover the sandbox branch in create_job(), stop_job(), get_job_status(),
sandbox API routes, and MCP tool parameter extension.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from server.models.sandbox import ContainerInfo, CredentialMount, MountSpec
from server.services.sandbox.sandbox_errors import (
    ContainerCreateError,
    ContainerStartError,
    DockerNotAvailableError,
    ImageBuildError,
)


class DummyProvider:
    name = "claude"
    display_name = "Claude Code"

    def get_invocation(self, shell: str = "ps1") -> str:
        if shell == "sh":
            return 'echo "ITERATION $ITERATION" >> "$PROGRESS_FILE"'
        return 'Add-Content -Path $ProgressFile -Value "ITERATION $Iteration"'


def _make_templates(tmp_path: Path) -> Path:
    """Create minimal prompt templates needed for create_job."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    for mode in ("plan", "build"):
        (templates_dir / f"PROMPT_{mode}_adhoc.md").write_text(
            f"{mode.upper()} {{{{FEATURE_NAME}}}} in {{{{PROJECT_NAME}}}} at {{{{FEATURE_DIR}}}}",
            encoding="utf-8",
        )
    return templates_dir


def _mock_container_manager():
    """Create a mock ContainerManager with standard responses."""
    mgr = MagicMock()
    mgr.check_docker_available.return_value = (True, "Docker is running")
    mgr.ensure_image.return_value = True
    mgr.create_container.return_value = ContainerInfo(
        container_id="abc123def456",
        name="vista-ralph-test1234",
        job_id="test-job-id",
        provider="claude",
        status="created",
        image="vista-ralph:latest",
    )
    mgr.start_container.return_value = None
    mgr.stop_container.return_value = None
    return mgr


def _mock_credential_mounter():
    """Create a mock CredentialMounter with standard mounts."""
    mounter = MagicMock()
    mounter.get_mounts.return_value = [
        CredentialMount(
            name="claude_auth",
            host_path="/home/user/.claude",
            container_path="/home/user/.claude",
            mode="ro",
            is_directory=True,
        ),
        CredentialMount(
            name="git_ssh",
            host_path="/home/user/.ssh",
            container_path="/home/user/.ssh",
            mode="ro",
            is_directory=True,
        ),
    ]
    return mounter


# =========================================================================
# DS-F20: create_job sandbox parameter
# =========================================================================


class TestCreateSandboxedJob:
    """DS-F20, DS-F25: sandbox=True creates Docker-based job."""

    def test_create_sandboxed_job_full_flow(self, tmp_path):
        """sandbox=True, Docker available, image exists -> container created."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)
        mock_mgr = _mock_container_manager()
        mock_mounter = _mock_credential_mounter()

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.ContainerManager",
                return_value=mock_mgr,
            ),
            patch(
                "server.services.ralph_service.CredentialMounter",
                return_value=mock_mounter,
            ),
            patch(
                "server.services.ralph_service.BashLoopGenerator"
            ) as MockBashGen,
        ):
            MockBashGen.generate.return_value = "#!/bin/bash\necho hello"

            job = svc.create_job(
                tmp_path,
                slug="test-sandbox",
                mode="plan",
                task_description="Test sandbox flow",
                provider=DummyProvider(),
                model="sonnet",
                iterations=3,
                sandbox=True,
            )

        assert job["sandbox"] is True
        assert job["container_id"] == "abc123def456"
        assert job["status"] == "running"
        mock_mgr.check_docker_available.assert_called_once()
        mock_mgr.ensure_image.assert_called_once()
        mock_mgr.create_container.assert_called_once()
        mock_mgr.start_container.assert_called_once_with("abc123def456")

    def test_create_native_job_unchanged(self, tmp_path):
        """DS-F28: sandbox=False follows existing subprocess path."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.platform.system",
                return_value="Windows",
            ),
            patch("server.services.ralph_service.subprocess.Popen") as popen,
        ):
            proc = MagicMock()
            proc.pid = 1234
            popen.return_value = proc

            job = svc.create_job(
                tmp_path,
                slug="native-test",
                mode="plan",
                task_description="Native flow",
                provider=DummyProvider(),
                model="sonnet",
                iterations=1,
                sandbox=False,
            )

        assert job["sandbox"] is False
        assert job["container_id"] is None
        assert job["status"] == "running"
        assert job["pid"] == 1234

    def test_sandbox_omitted_defaults_false(self, tmp_path):
        """DS-F28: Omitting sandbox param behaves as native."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.platform.system",
                return_value="Windows",
            ),
            patch("server.services.ralph_service.subprocess.Popen") as popen,
        ):
            proc = MagicMock()
            proc.pid = 5678
            popen.return_value = proc

            # No sandbox parameter
            job = svc.create_job(
                tmp_path,
                slug="default-test",
                mode="plan",
                task_description="Default flow",
                provider=DummyProvider(),
                model="sonnet",
                iterations=1,
            )

        assert job["sandbox"] is False
        assert job["container_id"] is None


# =========================================================================
# DS-F26: Job metadata
# =========================================================================


class TestSandboxedJobMetadata:
    """DS-F26: job.json includes sandbox and container_id fields."""

    def test_sandboxed_job_metadata(self, tmp_path):
        """Sandboxed job.json has sandbox=true and valid container_id."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)
        mock_mgr = _mock_container_manager()
        mock_mounter = _mock_credential_mounter()

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.ContainerManager",
                return_value=mock_mgr,
            ),
            patch(
                "server.services.ralph_service.CredentialMounter",
                return_value=mock_mounter,
            ),
            patch("server.services.ralph_service.BashLoopGenerator") as MockBashGen,
        ):
            MockBashGen.generate.return_value = "#!/bin/bash\necho hello"
            job = svc.create_job(
                tmp_path,
                slug="meta-test",
                mode="build",
                task_description="Metadata test",
                provider=DummyProvider(),
                model="opus",
                iterations=5,
                sandbox=True,
            )

        # Read persisted job.json
        ralph_dir = tmp_path / ".vista" / "ralph"
        job_dirs = list(ralph_dir.iterdir())
        assert len(job_dirs) == 1
        job_json = json.loads(
            (job_dirs[0] / "job.json").read_text(encoding="utf-8")
        )
        assert job_json["sandbox"] is True
        assert job_json["container_id"] == "abc123def456"

    def test_native_job_metadata(self, tmp_path):
        """Native job.json has sandbox=false and container_id=null."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.platform.system",
                return_value="Windows",
            ),
            patch("server.services.ralph_service.subprocess.Popen") as popen,
        ):
            proc = MagicMock()
            proc.pid = 9999
            popen.return_value = proc

            job = svc.create_job(
                tmp_path,
                slug="native-meta",
                mode="plan",
                task_description="Native metadata",
                provider=DummyProvider(),
                model="sonnet",
                iterations=1,
                sandbox=False,
            )

        ralph_dir = tmp_path / ".vista" / "ralph"
        job_dirs = list(ralph_dir.iterdir())
        assert len(job_dirs) == 1
        job_json = json.loads(
            (job_dirs[0] / "job.json").read_text(encoding="utf-8")
        )
        assert job_json["sandbox"] is False
        assert job_json["container_id"] is None


# =========================================================================
# DS-F23: Bash loop script generation for sandbox
# =========================================================================


class TestSandboxBashScript:
    """DS-F23: sandbox=True generates bash loop.sh regardless of host OS."""

    def test_sandbox_generates_bash_loop_on_windows(self, tmp_path):
        """Even on Windows host, sandbox produces loop.sh (not loop.ps1)."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)
        mock_mgr = _mock_container_manager()
        mock_mounter = _mock_credential_mounter()

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.platform.system",
                return_value="Windows",
            ),
            patch(
                "server.services.ralph_service.ContainerManager",
                return_value=mock_mgr,
            ),
            patch(
                "server.services.ralph_service.CredentialMounter",
                return_value=mock_mounter,
            ),
            patch("server.services.ralph_service.BashLoopGenerator") as MockBashGen,
        ):
            MockBashGen.generate.return_value = "#!/bin/bash\necho hello"

            job = svc.create_job(
                tmp_path,
                slug="win-sandbox",
                mode="build",
                task_description="Windows sandbox test",
                provider=DummyProvider(),
                model="sonnet",
                iterations=2,
                sandbox=True,
            )

        ralph_dir = tmp_path / ".vista" / "ralph"
        job_dirs = list(ralph_dir.iterdir())
        job_dir = job_dirs[0]
        assert (job_dir / "loop.sh").exists()
        assert not (job_dir / "loop.ps1").exists()


# =========================================================================
# DS-F24: Mount configuration
# =========================================================================


class TestSandboxMounts:
    """DS-F24: Container created with project RW mount + credential RO mounts."""

    def test_container_created_with_combined_mounts(self, tmp_path):
        """create_container called with project mount + credential mounts."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)
        mock_mgr = _mock_container_manager()
        mock_mounter = _mock_credential_mounter()

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.ContainerManager",
                return_value=mock_mgr,
            ),
            patch(
                "server.services.ralph_service.CredentialMounter",
                return_value=mock_mounter,
            ),
            patch("server.services.ralph_service.BashLoopGenerator") as MockBashGen,
        ):
            MockBashGen.generate.return_value = "#!/bin/bash\necho hello"
            job = svc.create_job(
                tmp_path,
                slug="mount-test",
                mode="plan",
                task_description="Mount test",
                provider=DummyProvider(),
                model="sonnet",
                iterations=1,
                sandbox=True,
            )

        # Verify create_container was called with mounts
        call_kwargs = mock_mgr.create_container.call_args
        mounts = call_kwargs.kwargs.get("mounts") or call_kwargs[1].get("mounts")
        assert mounts is not None
        assert len(mounts) >= 3  # project RW + 2 credential RO


# =========================================================================
# DS-F21, DS-NF7: Docker availability checks
# =========================================================================


class TestSandboxDockerErrors:
    """DS-F21, DS-NF7: sandbox=True with Docker unavailable raises error."""

    def test_sandbox_docker_not_available(self, tmp_path):
        """Docker not available raises DockerNotAvailableError."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)
        mock_mgr = MagicMock()
        mock_mgr.check_docker_available.return_value = (False, "Docker not running")

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.ContainerManager",
                return_value=mock_mgr,
            ),
            pytest.raises(DockerNotAvailableError),
        ):
            svc.create_job(
                tmp_path,
                slug="docker-fail",
                mode="plan",
                task_description="Docker fail test",
                provider=DummyProvider(),
                model="sonnet",
                iterations=1,
                sandbox=True,
            )

    def test_sandbox_never_silent_fallback(self, tmp_path):
        """DS-NF7: Docker unavailable + sandbox=True -> error, never native."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)
        mock_mgr = MagicMock()
        mock_mgr.check_docker_available.return_value = (False, "No Docker")

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.ContainerManager",
                return_value=mock_mgr,
            ),
        ):
            with pytest.raises(DockerNotAvailableError):
                svc.create_job(
                    tmp_path,
                    slug="no-fallback",
                    mode="plan",
                    task_description="No fallback test",
                    provider=DummyProvider(),
                    model="sonnet",
                    iterations=1,
                    sandbox=True,
                )

        # Verify no job directory was created
        ralph_dir = tmp_path / ".vista" / "ralph"
        if ralph_dir.exists():
            assert len(list(ralph_dir.iterdir())) == 0


# =========================================================================
# DS-F22: Image build
# =========================================================================


class TestSandboxImageErrors:
    """DS-F22: Image build failure raises ImageBuildError."""

    def test_image_build_failure(self, tmp_path):
        """ensure_image failure raises ImageBuildError."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)
        mock_mgr = MagicMock()
        mock_mgr.check_docker_available.return_value = (True, "Docker running")
        mock_mgr.ensure_image.return_value = False

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.ContainerManager",
                return_value=mock_mgr,
            ),
            pytest.raises(ImageBuildError),
        ):
            svc.create_job(
                tmp_path,
                slug="image-fail",
                mode="plan",
                task_description="Image fail test",
                provider=DummyProvider(),
                model="sonnet",
                iterations=1,
                sandbox=True,
            )


# =========================================================================
# DS-F27: stop_job for sandboxed jobs
# =========================================================================


class TestStopSandboxedJob:
    """DS-F27: stop_job detects sandbox and calls ContainerManager.stop_container."""

    def test_stop_sandboxed_job(self, tmp_path):
        """Stopping sandboxed job calls docker stop, not OS signal."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        # Create a job directory with sandbox metadata
        job_dir = tmp_path / ".vista" / "ralph" / "stop-test-abcd1234"
        job_dir.mkdir(parents=True)
        job_data = {
            "job_id": "abcd1234-5678-9012-3456-abcdef012345",
            "slug": "stop-test",
            "mode": "plan",
            "status": "running",
            "provider": "claude",
            "model": "sonnet",
            "iterations": 3,
            "pid": None,
            "sandbox": True,
            "container_id": "container-xyz-789",
            "created_at": "2026-02-12T00:00:00+00:00",
            "started_at": "2026-02-12T00:00:00+00:00",
            "completed_at": None,
            "error": None,
        }
        (job_dir / "job.json").write_text(json.dumps(job_data), encoding="utf-8")

        mock_mgr = MagicMock()
        with patch(
            "server.services.ralph_service.ContainerManager",
            return_value=mock_mgr,
        ):
            result = svc.stop_job(tmp_path, "abcd1234-5678-9012-3456-abcdef012345")

        assert result is not None
        assert result["status"] == "stopped"
        mock_mgr.stop_container.assert_called_once_with(
            "container-xyz-789", remove=True
        )

    def test_stop_native_job_uses_os_signal(self, tmp_path):
        """Stopping native job uses OS signal (existing behavior)."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "native-stop-1234abcd"
        job_dir.mkdir(parents=True)
        job_data = {
            "job_id": "1234abcd-5678-9012-3456-abcdef012345",
            "slug": "native-stop",
            "mode": "plan",
            "status": "running",
            "provider": "claude",
            "model": "sonnet",
            "iterations": 3,
            "pid": 99999,
            "sandbox": False,
            "container_id": None,
            "created_at": "2026-02-12T00:00:00+00:00",
            "started_at": "2026-02-12T00:00:00+00:00",
            "completed_at": None,
            "error": None,
        }
        (job_dir / "job.json").write_text(json.dumps(job_data), encoding="utf-8")

        # Mock process as not running so stop_job skips os.kill
        with patch.object(svc, "_is_process_running", return_value=False):
            result = svc.stop_job(tmp_path, "1234abcd-5678-9012-3456-abcdef012345")

        assert result is not None
        assert result["status"] == "stopped"

    def test_stop_already_exited_container(self, tmp_path):
        """Container already stopped -> stop is idempotent."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "exited-test-11112222"
        job_dir.mkdir(parents=True)
        job_data = {
            "job_id": "11112222-3333-4444-5555-666677778888",
            "slug": "exited-test",
            "mode": "plan",
            "status": "running",
            "provider": "claude",
            "model": "sonnet",
            "iterations": 1,
            "pid": None,
            "sandbox": True,
            "container_id": "dead-container-123",
            "created_at": "2026-02-12T00:00:00+00:00",
            "started_at": "2026-02-12T00:00:00+00:00",
            "completed_at": None,
            "error": None,
        }
        (job_dir / "job.json").write_text(json.dumps(job_data), encoding="utf-8")

        mock_mgr = MagicMock()
        # stop_container may raise if container already gone, should be handled
        mock_mgr.stop_container.side_effect = Exception("container not found")
        with patch(
            "server.services.ralph_service.ContainerManager",
            return_value=mock_mgr,
        ):
            result = svc.stop_job(tmp_path, "11112222-3333-4444-5555-666677778888")

        assert result is not None
        assert result["status"] == "stopped"


# =========================================================================
# DS-F30: Sandbox badge in job response
# =========================================================================


class TestSandboxBadgeInJobResponse:
    """DS-F30: GET job endpoint includes sandbox field."""

    def test_sandbox_field_in_get_job_status(self, tmp_path):
        """get_job_status returns sandbox field."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "badge-test-aabb1122"
        job_dir.mkdir(parents=True)
        job_data = {
            "job_id": "aabb1122-3344-5566-7788-99aabbccddee",
            "slug": "badge-test",
            "mode": "build",
            "status": "completed",
            "provider": "claude",
            "model": "opus",
            "iterations": 5,
            "pid": None,
            "sandbox": True,
            "container_id": "container-badge-test",
            "created_at": "2026-02-12T00:00:00+00:00",
            "started_at": "2026-02-12T00:00:00+00:00",
            "completed_at": "2026-02-12T01:00:00+00:00",
            "error": None,
        }
        (job_dir / "job.json").write_text(json.dumps(job_data), encoding="utf-8")

        result = svc.get_job_status(
            tmp_path, "aabb1122-3344-5566-7788-99aabbccddee"
        )
        assert result is not None
        assert result["sandbox"] is True
        assert result["container_id"] == "container-badge-test"


# =========================================================================
# DS-F32, DS-F33: Sandbox API routes
# =========================================================================


class TestSandboxAPIRoutes:
    """DS-F32, DS-F33: Sandbox status and build endpoints."""

    def test_sandbox_status_endpoint(self, patched_config):
        """GET /api/ralph/sandbox/status returns Docker/image status."""
        from server.app import app
        from fastapi.testclient import TestClient

        mock_mgr = MagicMock()
        mock_mgr.check_docker_available.return_value = (True, "Docker running")
        mock_mgr.ensure_image.return_value = True

        with patch(
            "server.routes.sandbox.ContainerManager",
            return_value=mock_mgr,
        ):
            client = TestClient(app)
            resp = client.get("/api/ralph/sandbox/status")

        assert resp.status_code == 200
        data = resp.json()
        assert "docker_available" in data
        assert "image_exists" in data

    def test_sandbox_build_endpoint(self, patched_config):
        """POST /api/ralph/sandbox/build triggers image build."""
        from server.app import app
        from fastapi.testclient import TestClient

        mock_mgr = MagicMock()
        mock_mgr.check_docker_available.return_value = (True, "Docker running")
        mock_mgr.ensure_image.return_value = True

        with patch(
            "server.routes.sandbox.ContainerManager",
            return_value=mock_mgr,
        ):
            client = TestClient(app)
            resp = client.post("/api/ralph/sandbox/build")

        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data


# =========================================================================
# DS-NF6: No Docker import when sandbox=False
# =========================================================================


class TestNativePathNoDockerImport:
    """DS-NF6: Native execution path does not import Docker SDK."""

    def test_native_job_does_not_instantiate_container_manager(self, tmp_path):
        """Native path never creates ContainerManager."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        templates_dir = _make_templates(tmp_path)

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.platform.system",
                return_value="Windows",
            ),
            patch("server.services.ralph_service.subprocess.Popen") as popen,
            patch(
                "server.services.ralph_service.ContainerManager"
            ) as MockCM,
        ):
            proc = MagicMock()
            proc.pid = 1234
            popen.return_value = proc

            svc.create_job(
                tmp_path,
                slug="no-docker",
                mode="plan",
                task_description="No Docker test",
                provider=DummyProvider(),
                model="sonnet",
                iterations=1,
                sandbox=False,
            )

        # ContainerManager should never be instantiated for native jobs
        MockCM.assert_not_called()
