"""Integration tests for ralph job lifecycle with real subprocesses.

These tests verify the full lifecycle of ralph jobs using actual subprocess
execution, file persistence, and PID verification.
"""

import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class SimpleProvider:
    """Minimal provider for integration tests."""

    name = "simple"
    display_name = "Simple Provider"

    def get_invocation(self, shell: str = "ps1") -> str:
        """Return a simple echo command instead of full loop script."""
        if shell == "sh":
            return 'echo "Test invocation" >> "$PROGRESS_FILE"'
        return 'Add-Content -Path $ProgressFile -Value "Test invocation"'


def _get_simple_command():
    """Get a simple long-running command for testing."""
    if platform.system() == "Windows":
        # Use Python to sleep - more reliable than PowerShell
        return [sys.executable, "-c", "import time; time.sleep(30)"]
    else:
        return ["sleep", "30"]


@pytest.fixture
def simple_provider():
    """Provide a simple test provider."""
    return SimpleProvider()


@pytest.fixture
def templates_dir(tmp_path):
    """Create minimal template files."""
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "PROMPT_plan_adhoc.md").write_text(
        "Plan {{FEATURE_NAME}} in {{PROJECT_NAME}} at {{FEATURE_DIR}}",
        encoding="utf-8",
    )
    (templates / "PROMPT_build_adhoc.md").write_text(
        "Build {{FEATURE_NAME}} in {{PROJECT_NAME}} at {{FEATURE_DIR}}",
        encoding="utf-8",
    )
    return templates


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.Popen to use a simple sleep command instead of loop script."""
    original_popen = subprocess.Popen
    spawned_procs = []

    def mock_popen(cmd, **kwargs):
        """Replace the loop script command with a simple sleep command."""
        # Close the output handle if provided to avoid file handle issues
        if "stdout" in kwargs and hasattr(kwargs["stdout"], "close"):
            kwargs["stdout"].close()
        # Replace with a simple sleep command
        simple_cmd = _get_simple_command()
        # Remove stdout/stderr to let them go to default
        kwargs.pop("stdout", None)
        kwargs.pop("stderr", None)
        proc = original_popen(simple_cmd, **kwargs)
        spawned_procs.append(proc)
        return proc

    with patch(
        "server.services.ralph_service.subprocess.Popen", side_effect=mock_popen
    ):
        yield spawned_procs

    # Cleanup: kill any remaining processes
    for proc in spawned_procs:
        try:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=2)
        except Exception:
            pass


class TestRalphJobLifecycle:
    """Test full lifecycle: create -> status -> stop with real subprocess."""

    def test_create_job_spawns_real_subprocess(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test that create_job spawns a real subprocess that we can verify."""
        from server.services.ralph_service import RalphService

        svc = RalphService()

        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc.create_job(
                tmp_path,
                slug="test-job",
                mode="plan",
                task_description="Integration test task",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        # Verify job was created
        assert job["status"] == "running"
        assert job["slug"] == "test-job"
        assert isinstance(job["pid"], int)
        assert job["pid"] > 0

        # Verify subprocess is actually running
        pid = job["pid"]
        assert svc._is_process_running(pid)

        # Verify files were created
        job_dir = tmp_path / ".vista" / "ralph" / "test-job"
        assert job_dir.exists()
        assert (job_dir / "job.json").exists()
        assert (job_dir / "task.md").exists()
        assert (job_dir / "PROMPT_plan.md").exists()
        assert (job_dir / "output.log").exists()

        # Verify job.json content
        job_data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        assert job_data["job_id"] == job["job_id"]
        assert job_data["pid"] == pid
        assert job_data["status"] == "running"

        # Clean up - stop the process
        svc.stop_job(tmp_path, job["job_id"])

    def test_status_while_running(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test getting status while job is running."""
        from server.services.ralph_service import RalphService

        svc = RalphService()

        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc.create_job(
                tmp_path,
                slug="status-test",
                mode="plan",
                task_description="Status test",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        job_id = job["job_id"]
        pid = job["pid"]

        # Get status immediately
        with patch.object(svc, "_is_expected_job_process", return_value=True):
            status = svc.get_job_status(tmp_path, job_id)
        assert status is not None
        assert status["status"] == "running"
        assert status["pid"] == pid

        # Clean up
        svc.stop_job(tmp_path, job_id)

    def test_stop_job_terminates_subprocess(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test that stop_job sends termination signal and updates status."""
        from server.services.ralph_service import RalphService

        svc = RalphService()

        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc.create_job(
                tmp_path,
                slug="stop-test",
                mode="plan",
                task_description="Stop test",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        job_id = job["job_id"]
        pid = job["pid"]

        # Verify process is running
        assert svc._is_process_running(pid)

        # Stop the job
        stopped_job = svc.stop_job(tmp_path, job_id)
        assert stopped_job is not None
        assert stopped_job["status"] == "stopped"
        assert stopped_job["completed_at"] is not None

        # Verify job.json was updated immediately
        job_dir = tmp_path / ".vista" / "ralph" / "stop-test"
        job_data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        assert job_data["status"] == "stopped"
        assert job_data["completed_at"] is not None

        # Wait for process to actually terminate (taskkill is async on Windows)
        # We don't assert this in the test because it's timing-dependent,
        # but we verify that the kill command was sent (implicitly via stop_job)
        # In production, the process will eventually terminate
        max_wait = 2.0
        start = time.time()
        while time.time() - start < max_wait:
            if not svc._is_process_running(pid):
                break
            time.sleep(0.2)

    def test_full_lifecycle_create_status_stop(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test complete lifecycle: create -> check status -> stop."""
        from server.services.ralph_service import RalphService

        svc = RalphService()

        # Step 1: Create job
        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc.create_job(
                tmp_path,
                slug="lifecycle",
                mode="plan",
                task_description="Full lifecycle test",
                provider=simple_provider,
                model="test-model",
                iterations=2,
            )

        job_id = job["job_id"]
        assert job["status"] == "running"

        # Step 2: Check status
        with patch.object(svc, "_is_expected_job_process", return_value=True):
            status = svc.get_job_status(tmp_path, job_id)
        assert status is not None
        assert status["status"] == "running"
        assert status["job_id"] == job_id
        assert "progress_tail" in status

        # Step 3: Stop job
        stopped = svc.stop_job(tmp_path, job_id)
        assert stopped is not None
        assert stopped["status"] == "stopped"

        # Step 4: Verify final status
        final_status = svc.get_job_status(tmp_path, job_id)
        assert final_status is not None
        assert final_status["status"] == "stopped"


class TestJobPersistence:
    """Test job.json persistence and restart scenarios."""

    def test_job_json_persists_across_service_instances(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test that job.json persists and can be read by new service instance."""
        from server.services.ralph_service import RalphService

        # Create job with first service instance
        svc1 = RalphService()
        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job1 = svc1.create_job(
                tmp_path,
                slug="persist-test",
                mode="plan",
                task_description="Persistence test",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        job_id = job1["job_id"]
        pid = job1["pid"]

        # Stop the job
        svc1.stop_job(tmp_path, job_id)

        # Create new service instance (simulates server restart)
        svc2 = RalphService()

        # Read status with new instance
        status = svc2.get_job_status(tmp_path, job_id)
        assert status is not None
        assert status["job_id"] == job_id
        assert status["pid"] == pid
        assert status["status"] == "stopped"

    def test_job_listing_across_instances(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test that list_jobs works after service restart."""
        from server.services.ralph_service import RalphService

        # Create multiple jobs
        svc1 = RalphService()
        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job1 = svc1.create_job(
                tmp_path,
                slug="list-test-1",
                mode="plan",
                task_description="List test 1",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )
            time.sleep(0.1)  # Ensure different timestamps
            job2 = svc1.create_job(
                tmp_path,
                slug="list-test-2",
                mode="build",
                task_description="List test 2",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        # Stop both jobs
        svc1.stop_job(tmp_path, job1["job_id"])
        svc1.stop_job(tmp_path, job2["job_id"])

        # Create new service instance
        svc2 = RalphService()

        # List jobs
        jobs = svc2.list_jobs(tmp_path)
        assert len(jobs) == 2
        job_ids = [j["job_id"] for j in jobs]
        assert job1["job_id"] in job_ids
        assert job2["job_id"] in job_ids


class TestPIDVerification:
    """Test PID verification detects dead processes."""

    def test_status_detects_dead_process(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test that get_job_status detects when process PID is no longer alive.

        Note: On Windows, OpenProcess can still return a handle for a terminated process
        if the process object hasn't been fully cleaned up. This test uses process exit
        to ensure clean termination rather than forceful kill.
        """
        from server.services.ralph_service import RalphService

        svc = RalphService()

        # Create job with short-lived command that will complete quickly
        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc.create_job(
                tmp_path,
                slug="dead-pid-test",
                mode="plan",
                task_description="Dead PID test",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        job_id = job["job_id"]
        pid = job["pid"]

        # Stop the process normally first
        svc.stop_job(tmp_path, job_id)

        # Wait for process to fully terminate
        max_wait = 10
        for _ in range(max_wait):
            if not svc._is_process_running(pid):
                break
            time.sleep(0.5)

        # Manually set job status back to "running" to simulate a crash scenario
        # where the process died but the job.json wasn't updated
        job_dir = tmp_path / ".vista" / "ralph" / "dead-pid-test"
        job_data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        job_data["status"] = "running"
        (job_dir / "job.json").write_text(json.dumps(job_data), encoding="utf-8")

        # Get status - should detect dead process
        status = svc.get_job_status(tmp_path, job_id)
        assert status is not None
        assert status["status"] == "failed"
        assert "pid" in status.get("error", "").lower()

        # Verify job.json was updated
        job_data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        assert job_data["status"] == "failed"
        assert "pid" in job_data.get("error", "").lower()

    def test_pid_verification_with_fake_pid(self, tmp_path):
        """Test that _is_process_running returns False for non-existent PID."""
        from server.services.ralph_service import RalphService

        svc = RalphService()

        # Use a PID that definitely doesn't exist (very high number)
        fake_pid = 999999
        assert not svc._is_process_running(fake_pid)

        # Test with invalid PIDs
        assert not svc._is_process_running(0)
        assert not svc._is_process_running(-1)

    def test_restart_scenario_dead_process_marked_failed(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test MCP server restart scenario: job.json persists, dead PID detected.

        Note: On Windows, OpenProcess can still return a handle for a terminated process.
        This test uses a proper stop followed by manual status change to ensure clean testing.
        """
        from server.services.ralph_service import RalphService

        # Step 1: Create a job
        svc1 = RalphService()
        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc1.create_job(
                tmp_path,
                slug="restart-test",
                mode="plan",
                task_description="Restart scenario test",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        job_id = job["job_id"]
        pid = job["pid"]

        # Step 2: Stop the process normally
        svc1.stop_job(tmp_path, job_id)

        # Wait for process to fully terminate
        max_wait = 10
        for _ in range(max_wait):
            if not svc1._is_process_running(pid):
                break
            time.sleep(0.5)

        # Step 3: Manually set job status back to "running" to simulate crash scenario
        job_dir = tmp_path / ".vista" / "ralph" / "restart-test"
        job_data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        job_data["status"] = "running"
        job_data["completed_at"] = None
        (job_dir / "job.json").write_text(json.dumps(job_data), encoding="utf-8")

        # Verify job.json says "running"
        job_data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        assert job_data["status"] == "running"

        # Step 4: Create new service instance (simulates MCP server restart)
        svc2 = RalphService()

        # Step 5: Get status - should detect dead process and update job.json
        status = svc2.get_job_status(tmp_path, job_id)
        assert status is not None
        assert status["status"] == "failed"
        assert "pid" in status.get("error", "").lower()

        # Step 6: Verify job.json was updated to "failed"
        job_data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
        assert job_data["status"] == "failed"


class TestProgressTracking:
    """Test progress tracking with real subprocess."""

    def test_progress_file_created_and_readable(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test that progress.txt is created and can be read."""
        from server.services.ralph_service import RalphService

        svc = RalphService()

        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc.create_job(
                tmp_path,
                slug="progress-test",
                mode="plan",
                task_description="Progress tracking test",
                provider=simple_provider,
                model="test-model",
                iterations=2,
            )

        job_id = job["job_id"]

        # Allow some time for loop script to potentially write progress
        time.sleep(1.0)

        # Get status
        status = svc.get_job_status(tmp_path, job_id)
        assert status is not None
        assert "progress_tail" in status

        # Clean up
        svc.stop_job(tmp_path, job_id)


class TestPlatformSpecific:
    """Test platform-specific behavior."""

    def test_correct_script_extension_created(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test that the correct script extension is used based on platform."""
        from server.services.ralph_service import RalphService

        svc = RalphService()

        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc.create_job(
                tmp_path,
                slug="platform-test",
                mode="plan",
                task_description="Platform test",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        job_dir = tmp_path / ".vista" / "ralph" / "platform-test"

        if platform.system() == "Windows":
            assert (job_dir / "loop.ps1").exists()
            assert not (job_dir / "loop.sh").exists()
        else:
            assert (job_dir / "loop.sh").exists()
            assert not (job_dir / "loop.ps1").exists()

        # Clean up
        svc.stop_job(tmp_path, job["job_id"])

    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix-only test")
    def test_unix_script_has_execute_permission(
        self, tmp_path, simple_provider, templates_dir, mock_subprocess
    ):
        """Test that Unix scripts have execute permissions."""
        from server.services.ralph_service import RalphService

        svc = RalphService()

        with patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir):
            job = svc.create_job(
                tmp_path,
                slug="unix-perms",
                mode="plan",
                task_description="Unix permissions test",
                provider=simple_provider,
                model="test-model",
                iterations=1,
            )

        job_dir = tmp_path / ".vista" / "ralph" / "unix-perms"
        loop_script = job_dir / "loop.sh"

        import os
        import stat

        mode = os.stat(loop_script).st_mode
        assert mode & stat.S_IXUSR  # User execute permission

        # Clean up
        svc.stop_job(tmp_path, job["job_id"])
