"""Unit tests for summarizer service."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from server.services.summarizer_service import (
    SummarizerService,
    build_summarizer_prompt,
    summarizer_service,
)


@pytest.fixture
def mock_job_dir(tmp_path):
    """Create a mock job directory with artifacts."""
    job_dir = tmp_path / ".vista" / "ralph" / "test-job"
    job_dir.mkdir(parents=True)

    # Create task.md
    (job_dir / "task.md").write_text("Refactor the API handlers\n", encoding="utf-8")

    # Create progress.txt with 150 lines
    progress_lines = [f"Progress line {i}" for i in range(150)]
    (job_dir / "progress.txt").write_text("\n".join(progress_lines), encoding="utf-8")

    # Create IMPLEMENTATION_PLAN.md with 600 lines
    plan_lines = [f"Plan line {i}" for i in range(600)]
    (job_dir / "IMPLEMENTATION_PLAN.md").write_text("\n".join(plan_lines), encoding="utf-8")

    # Create job.json
    job_meta = {
        "job_id": "test-job-id",
        "slug": "test-job",
        "mode": "build",
        "status": "running",
        "provider": "claude",
        "model": "sonnet",
        "current_iteration": 2,
        "iterations": 3,
    }
    (job_dir / "job.json").write_text(json.dumps(job_meta), encoding="utf-8")

    return job_dir


class TestBuildSummarizerPrompt:
    """Tests for build_summarizer_prompt function."""

    def test_builds_prompt_with_all_artifacts(self, mock_job_dir):
        """Test that prompt includes all available artifacts."""
        job_meta = json.loads((mock_job_dir / "job.json").read_text())

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="abc123 Latest commit\n")

            prompt = build_summarizer_prompt(mock_job_dir, job_meta)

            assert "test-job" in prompt
            assert "build" in prompt
            assert "running" in prompt
            assert "2/3" in prompt
            assert "Refactor the API handlers" in prompt
            assert "Progress line 149" in prompt  # Last line
            assert "Progress line 50" in prompt  # Within last 100
            assert "Plan line 0" in prompt  # First line
            assert "Plan line 499" in prompt  # Last of first 500
            assert "abc123 Latest commit" in prompt

    def test_handles_missing_artifacts(self, tmp_path):
        """Test prompt generation when artifacts are missing."""
        empty_job_dir = tmp_path / ".vista" / "ralph" / "empty-job"
        empty_job_dir.mkdir(parents=True)

        job_meta = {
            "job_id": "empty-job-id",
            "slug": "empty-job",
            "mode": "plan",
            "status": "queued",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            prompt = build_summarizer_prompt(empty_job_dir, job_meta)

            assert "empty-job" in prompt
            assert "No task description available" in prompt
            assert "No progress yet" in prompt
            assert "No implementation plan yet" in prompt
            assert "Git log unavailable" in prompt

    def test_truncates_progress_to_last_100_lines(self, mock_job_dir):
        """Test that progress is truncated to last 100 lines."""
        job_meta = json.loads((mock_job_dir / "job.json").read_text())

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")

            prompt = build_summarizer_prompt(mock_job_dir, job_meta)

            # Should have line 50 (within last 100)
            assert "Progress line 50" in prompt
            # Should NOT have line 40 (outside last 100)
            assert "Progress line 40" not in prompt

    def test_truncates_plan_to_first_500_lines(self, mock_job_dir):
        """Test that implementation plan is truncated to first 500 lines."""
        job_meta = json.loads((mock_job_dir / "job.json").read_text())

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")

            prompt = build_summarizer_prompt(mock_job_dir, job_meta)

            # Should have line 499 (within first 500)
            assert "Plan line 499" in prompt
            # Should NOT have line 500 (outside first 500)
            assert "Plan line 500" not in prompt

    def test_handles_git_timeout(self, mock_job_dir):
        """Test handling of git command timeout."""
        job_meta = json.loads((mock_job_dir / "job.json").read_text())

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

            prompt = build_summarizer_prompt(mock_job_dir, job_meta)

            assert "Git log unavailable" in prompt


class TestSummarizerService:
    """Tests for SummarizerService class."""

    def test_run_summarizer_returns_structured_summary(self, tmp_path):
        """Test that summarizer returns properly structured JSON."""
        # Setup mock job directory
        project_root = tmp_path
        job_dir = project_root / ".vista" / "ralph" / "test-job"
        job_dir.mkdir(parents=True)

        job_meta = {
            "job_id": "test-123",
            "slug": "test-job",
            "mode": "build",
            "status": "running",
        }
        (job_dir / "job.json").write_text(json.dumps(job_meta), encoding="utf-8")
        (job_dir / "task.md").write_text("Test task", encoding="utf-8")

        # Mock provider and subprocess
        with patch("server.services.summarizer_service.get_summarizer_config") as mock_config, \
             patch("server.services.summarizer_service.get_provider_by_name") as mock_provider, \
             patch("server.services.summarizer_service.subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen:

            mock_config.return_value = {"provider": "claude", "model": "haiku"}

            mock_provider_inst = Mock()
            mock_provider_inst.get_summarizer_command.return_value = ["claude", "-p"]
            mock_provider.return_value = mock_provider_inst

            # Mock git log
            mock_run.return_value = Mock(returncode=0, stdout="abc123 Latest commit\n")

            mock_proc = Mock()
            mock_proc.returncode = 0
            summary_json = {
                "status_summary": "Job is running",
                "completed_work": ["Implemented feature X"],
                "in_progress": ["Testing feature X"],
                "issues": [],
                "recommendations": ["Deploy to staging"],
                "key_files_changed": ["api.py"],
            }
            mock_proc.communicate.return_value = (json.dumps(summary_json), "")
            mock_popen.return_value = mock_proc

            service = SummarizerService()
            result = service.run_summarizer(project_root, "test-123")

            assert result["status_summary"] == "Job is running"
            assert result["completed_work"] == ["Implemented feature X"]
            assert result["in_progress"] == ["Testing feature X"]
            assert result["issues"] == []
            assert result["recommendations"] == ["Deploy to staging"]
            assert result["key_files_changed"] == ["api.py"]

    def test_run_summarizer_raises_on_job_not_found(self, tmp_path):
        """Test that missing job raises ValueError."""
        service = SummarizerService()

        with pytest.raises(ValueError, match="Job not found"):
            service.run_summarizer(tmp_path, "nonexistent-job")

    def test_run_summarizer_raises_on_provider_not_found(self, tmp_path):
        """Test that invalid provider raises ValueError."""
        # Setup mock job directory
        project_root = tmp_path
        job_dir = project_root / ".vista" / "ralph" / "test-job"
        job_dir.mkdir(parents=True)

        job_meta = {"job_id": "test-123", "slug": "test-job"}
        (job_dir / "job.json").write_text(json.dumps(job_meta), encoding="utf-8")

        with patch("server.services.summarizer_service.get_summarizer_config") as mock_config, \
             patch("server.services.summarizer_service.get_provider_by_name") as mock_provider:

            mock_config.return_value = {"provider": "invalid", "model": "haiku"}
            mock_provider.return_value = None

            service = SummarizerService()

            with pytest.raises(ValueError, match="Summarizer provider not found"):
                service.run_summarizer(project_root, "test-123")

    def test_run_summarizer_raises_on_cli_unavailable(self, tmp_path):
        """Test that missing CLI raises ValueError."""
        # Setup mock job directory
        project_root = tmp_path
        job_dir = project_root / ".vista" / "ralph" / "test-job"
        job_dir.mkdir(parents=True)

        job_meta = {"job_id": "test-123", "slug": "test-job"}
        (job_dir / "job.json").write_text(json.dumps(job_meta), encoding="utf-8")

        with patch("server.services.summarizer_service.get_summarizer_config") as mock_config, \
             patch("server.services.summarizer_service.get_provider_by_name") as mock_provider:

            mock_config.return_value = {"provider": "claude", "model": "haiku"}

            mock_provider_inst = Mock()
            mock_provider_inst.get_summarizer_command.return_value = []
            mock_provider.return_value = mock_provider_inst

            service = SummarizerService()

            with pytest.raises(ValueError, match="Summarizer CLI not available"):
                service.run_summarizer(project_root, "test-123")

    def test_run_summarizer_handles_timeout(self, tmp_path):
        """Test that subprocess timeout is handled."""
        # Setup mock job directory
        project_root = tmp_path
        job_dir = project_root / ".vista" / "ralph" / "test-job"
        job_dir.mkdir(parents=True)

        job_meta = {"job_id": "test-123", "slug": "test-job"}
        (job_dir / "job.json").write_text(json.dumps(job_meta), encoding="utf-8")
        (job_dir / "task.md").write_text("Test task", encoding="utf-8")

        with patch("server.services.summarizer_service.get_summarizer_config") as mock_config, \
             patch("server.services.summarizer_service.get_provider_by_name") as mock_provider, \
             patch("server.services.summarizer_service.subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen:

            mock_config.return_value = {"provider": "claude", "model": "haiku"}

            mock_provider_inst = Mock()
            mock_provider_inst.get_summarizer_command.return_value = ["claude", "-p"]
            mock_provider.return_value = mock_provider_inst

            # Mock git log
            mock_run.return_value = Mock(returncode=0, stdout="")

            mock_proc = Mock()
            mock_proc.communicate.side_effect = subprocess.TimeoutExpired("claude", 55)
            mock_popen.return_value = mock_proc

            service = SummarizerService()

            with pytest.raises(ValueError, match="timed out after 55 seconds"):
                service.run_summarizer(project_root, "test-123")

            mock_proc.kill.assert_called_once()

    def test_run_summarizer_handles_non_json_output(self, tmp_path):
        """Test fallback when subprocess returns non-JSON."""
        # Setup mock job directory
        project_root = tmp_path
        job_dir = project_root / ".vista" / "ralph" / "test-job"
        job_dir.mkdir(parents=True)

        job_meta = {"job_id": "test-123", "slug": "test-job"}
        (job_dir / "job.json").write_text(json.dumps(job_meta), encoding="utf-8")
        (job_dir / "task.md").write_text("Test task", encoding="utf-8")

        with patch("server.services.summarizer_service.get_summarizer_config") as mock_config, \
             patch("server.services.summarizer_service.get_provider_by_name") as mock_provider, \
             patch("server.services.summarizer_service.subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen:

            mock_config.return_value = {"provider": "claude", "model": "haiku"}

            mock_provider_inst = Mock()
            mock_provider_inst.get_summarizer_command.return_value = ["claude", "-p"]
            mock_provider.return_value = mock_provider_inst

            # Mock git log
            mock_run.return_value = Mock(returncode=0, stdout="")

            mock_proc = Mock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = ("This is not JSON", "")
            mock_popen.return_value = mock_proc

            service = SummarizerService()
            result = service.run_summarizer(project_root, "test-123")

            assert "Summary generated but not in expected JSON format" in result["status_summary"]
            assert len(result["issues"]) > 0
            assert "Failed to parse JSON output from summarizer" in result["issues"]
            assert "raw_output" in result

    def test_singleton_instance_exists(self):
        """Test that singleton instance is exported."""
        from server.services.summarizer_service import summarizer_service

        assert summarizer_service is not None
        assert isinstance(summarizer_service, SummarizerService)
