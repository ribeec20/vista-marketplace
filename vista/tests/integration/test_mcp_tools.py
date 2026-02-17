"""Integration tests for Ralph MCP tools.

Tests the 5 ralph tools defined inline in mcp_server.py:
- ralph_providers: Discovery flow
- ralph_start: Job creation flow
- ralph_status: Status and PID check flow
- ralph_summary: AI-generated summary flow
- ralph_stop: Job termination flow

These tests import the tool functions directly from mcp_server and call
them to verify end-to-end behavior.

With the fastmcp 3.x conversion:
- Tools return dicts (not JSON strings)
- Errors raise ToolError (not return {"error": ...})
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastmcp.exceptions import ToolError


class DummyProvider:
    """Mock provider for testing."""

    name = "dummy"
    display_name = "Dummy Provider"

    def get_invocation(self, shell: str = "ps1") -> str:
        if shell == "sh":
            return 'echo "ITERATION $ITERATION" >> "$PROGRESS_FILE"'
        return 'Add-Content -Path $ProgressFile -Value "ITERATION $Iteration"'

    def get_summarizer_command(self, model: str) -> list[str]:
        return ["echo", '{"status_summary": "Test summary"}']


def _write_job(job_dir: Path, job: dict) -> None:
    """Write a job.json file to a job directory."""
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")


def _get_ralph_fn(name: str):
    """Import a ralph tool function by name from mcp_server."""
    from mcp_server import (
        ralph_providers,
        ralph_start,
        ralph_status,
        ralph_summary,
        ralph_stop,
    )

    fns = {
        "ralph_providers": ralph_providers,
        "ralph_start": ralph_start,
        "ralph_status": ralph_status,
        "ralph_summary": ralph_summary,
        "ralph_stop": ralph_stop,
    }
    return fns[name]


class TestRalphProviders:
    """Tests for ralph_providers MCP tool."""

    def test_returns_providers_structure(self):
        """Test that ralph_providers returns dict with expected structure."""
        fn = _get_ralph_fn("ralph_providers")

        with (
            patch(
                "server.services.provider_service.get_ralph_providers"
            ) as mock_get_providers,
            patch("server.config.get_ralph_defaults") as mock_get_defaults,
            patch("server.config.get_summarizer_config") as mock_get_summarizer,
        ):
            mock_get_providers.return_value = [
                {
                    "name": "claude",
                    "display_name": "Claude",
                    "models": [
                        {
                            "name": "opus",
                            "display_name": "Claude Opus 4.6",
                            "cost_tier": "high",
                            "best_for_tags": ["complex", "reasoning"],
                            "best_for_notes": "Best for complex reasoning tasks",
                        }
                    ],
                }
            ]
            mock_get_defaults.return_value = {
                "provider": "claude",
                "model": "sonnet",
                "iterations": 3,
            }
            mock_get_summarizer.return_value = {
                "provider": "claude",
                "model": "haiku",
            }

            result = fn()

            assert "providers" in result
            assert "defaults" in result
            assert "summarizer" in result
            assert result["defaults"]["provider"] == "claude"
            assert result["defaults"]["model"] == "sonnet"
            assert result["defaults"]["iterations"] == 3
            assert result["summarizer"]["provider"] == "claude"
            assert result["summarizer"]["model"] == "haiku"
            assert len(result["providers"]) == 1
            assert result["providers"][0]["name"] == "claude"


class TestRalphStart:
    """Tests for ralph_start MCP tool."""

    def test_creates_job_successfully(self, tmp_path):
        """Test that ralph_start creates a job and returns job metadata."""
        fn = _get_ralph_fn("ralph_start")

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "PROMPT_plan_adhoc.md").write_text(
            "Plan {{FEATURE_NAME}} in {{PROJECT_NAME}} at {{FEATURE_DIR}}",
            encoding="utf-8",
        )

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch("server.config.get_ralph_defaults") as mock_get_defaults,
            patch(
                "server.services.provider_service.get_provider_by_name"
            ) as mock_get_provider,
            patch(
                "server.services.provider_service.get_ralph_providers"
            ) as mock_get_providers,
            patch(
                "server.services.ralph_service.platform.system", return_value="Windows"
            ),
            patch("server.services.ralph_service.subprocess.Popen") as mock_popen,
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            mock_get_defaults.return_value = {
                "provider": "dummy",
                "model": "test",
                "iterations": 3,
            }
            mock_get_provider.return_value = DummyProvider()
            mock_get_providers.return_value = [
                {"name": "dummy", "display_name": "Dummy", "models": [{"id": "test"}]}
            ]
            mock_proc = MagicMock()
            mock_proc.pid = 1234
            mock_popen.return_value = mock_proc

            result = fn(
                slug="test-job",
                mode="plan",
                task_description="Test task",
            )

            assert result["slug"] == "test-job"
            assert result["mode"] == "plan"
            assert result["status"] == "running"
            assert result["pid"] == 1234
            assert "job_id" in result
            assert "working_dir" in result

    def test_validates_mode(self, tmp_path):
        """Test that invalid mode raises ToolError."""
        fn = _get_ralph_fn("ralph_start")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with pytest.raises(ToolError, match="Invalid mode"):
                fn(
                    slug="test-job",
                    mode="invalid",
                    task_description="Test task",
                )

    def test_validates_provider(self, tmp_path):
        """Test that invalid provider raises ToolError."""
        fn = _get_ralph_fn("ralph_start")

        with (
            patch("server.config.get_ralph_defaults") as mock_get_defaults,
            patch(
                "server.services.provider_service.get_provider_by_name"
            ) as mock_get_provider,
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            mock_get_defaults.return_value = {
                "provider": "invalid",
                "model": "test",
                "iterations": 3,
            }
            mock_get_provider.return_value = None

            with pytest.raises(ToolError, match="Provider not found"):
                fn(
                    slug="test-job",
                    mode="plan",
                    task_description="Test task",
                )

    def test_uses_defaults_when_params_omitted(self, tmp_path):
        """Test that ralph_start uses defaults when optional params are None."""
        fn = _get_ralph_fn("ralph_start")

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "PROMPT_plan_adhoc.md").write_text(
            "Plan {{FEATURE_NAME}} in {{PROJECT_NAME}} at {{FEATURE_DIR}}",
            encoding="utf-8",
        )

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch("server.config.get_ralph_defaults") as mock_get_defaults,
            patch(
                "server.services.provider_service.get_provider_by_name"
            ) as mock_get_provider,
            patch(
                "server.services.provider_service.get_ralph_providers"
            ) as mock_get_providers,
            patch(
                "server.services.ralph_service.platform.system", return_value="Windows"
            ),
            patch("server.services.ralph_service.subprocess.Popen") as mock_popen,
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            mock_get_defaults.return_value = {
                "provider": "dummy",
                "model": "default-model",
                "iterations": 5,
            }
            mock_get_provider.return_value = DummyProvider()
            mock_get_providers.return_value = [
                {
                    "name": "dummy",
                    "display_name": "Dummy",
                    "models": [{"id": "default-model"}],
                }
            ]
            mock_proc = MagicMock()
            mock_proc.pid = 1234
            mock_popen.return_value = mock_proc

            result = fn(
                slug="test-job",
                mode="plan",
                task_description="Test task",
            )

            assert result["iterations"] == 5

    def test_handles_duplicate_running_job(self, tmp_path):
        """Test that duplicate slug with running job raises ToolError."""
        fn = _get_ralph_fn("ralph_start")

        job_dir = tmp_path / ".vista" / "ralph" / "duplicate-job"
        _write_job(job_dir, {"job_id": "existing-123", "status": "running"})

        with (
            patch("server.config.get_ralph_defaults") as mock_get_defaults,
            patch(
                "server.services.provider_service.get_provider_by_name"
            ) as mock_get_provider,
            patch(
                "server.services.provider_service.get_ralph_providers"
            ) as mock_get_providers,
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            mock_get_defaults.return_value = {
                "provider": "dummy",
                "model": "test",
                "iterations": 3,
            }
            mock_get_provider.return_value = DummyProvider()
            mock_get_providers.return_value = [
                {"name": "dummy", "display_name": "Dummy", "models": [{"id": "test"}]}
            ]

            with pytest.raises((ToolError, Exception), match="(?i)active job"):
                fn(
                    slug="duplicate-job",
                    mode="plan",
                    task_description="Test task",
                )


class TestRalphStatus:
    """Tests for ralph_status MCP tool."""

    def test_returns_job_status(self, tmp_path):
        """Test that ralph_status returns job metadata."""
        fn = _get_ralph_fn("ralph_status")

        job_dir = tmp_path / ".vista" / "ralph" / "test-job"
        _write_job(
            job_dir,
            {
                "job_id": "test-123",
                "slug": "test-job",
                "status": "running",
                "pid": 999,
                "iterations": 3,
                "current_iteration": 1,
            },
        )

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch(
                "server.services.ralph_service.RalphService._is_process_running",
                return_value=True,
            ),
            patch(
                "server.services.ralph_service.RalphService._is_expected_job_process",
                return_value=True,
            ),
        ):
            result = fn("test-123")

            assert result["job_id"] == "test-123"
            assert result["slug"] == "test-job"
            assert result["status"] == "running"
            assert result["pid"] == 999
            assert result["current_iteration"] == 1

    def test_marks_failed_when_pid_dead(self, tmp_path):
        """Test that ralph_status marks job as failed when PID is dead."""
        fn = _get_ralph_fn("ralph_status")

        job_dir = tmp_path / ".vista" / "ralph" / "test-job"
        _write_job(
            job_dir,
            {
                "job_id": "test-123",
                "slug": "test-job",
                "status": "running",
                "pid": 999,
                "iterations": 3,
                "current_iteration": 1,
            },
        )

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch(
                "server.services.ralph_service.RalphService._is_process_running",
                return_value=False,
            ),
        ):
            result = fn("test-123")

            assert result["status"] == "failed"
            assert result["error"] is not None
            assert "pid" in result["error"].lower()

    def test_returns_error_for_invalid_job_id(self, tmp_path):
        """Test that ralph_status raises ToolError for nonexistent job."""
        fn = _get_ralph_fn("ralph_status")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with pytest.raises(ToolError, match="not found"):
                fn("nonexistent-job")

    def test_reads_progress_tail(self, tmp_path):
        """Test that ralph_status includes progress tail from progress.txt."""
        fn = _get_ralph_fn("ralph_status")

        job_dir = tmp_path / ".vista" / "ralph" / "test-job"
        _write_job(
            job_dir,
            {
                "job_id": "test-123",
                "slug": "test-job",
                "status": "running",
                "pid": 999,
                "iterations": 3,
                "current_iteration": 0,
            },
        )

        progress_lines = [f"Progress line {i}" for i in range(10)]
        (job_dir / "progress.txt").write_text(
            "\n".join(progress_lines), encoding="utf-8"
        )

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch(
                "server.services.ralph_service.RalphService._is_process_running",
                return_value=True,
            ),
        ):
            result = fn("test-123")

            assert "progress_tail" in result
            assert len(result["progress_tail"]) <= 5


class TestRalphStop:
    """Tests for ralph_stop MCP tool."""

    def test_stops_job_successfully(self, tmp_path):
        """Test that ralph_stop terminates job and updates status."""
        fn = _get_ralph_fn("ralph_stop")

        job_dir = tmp_path / ".vista" / "ralph" / "test-job"
        _write_job(
            job_dir,
            {
                "job_id": "test-123",
                "slug": "test-job",
                "status": "running",
                "pid": 555,
            },
        )

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch(
                "server.services.ralph_service.platform.system",
                return_value="Windows",
            ),
            patch("server.services.ralph_service.subprocess.run") as mock_run,
        ):
            result = fn("test-123")

            assert result["status"] == "stopped"
            mock_run.assert_called_once()

    def test_returns_error_for_invalid_job_id(self, tmp_path):
        """Test that ralph_stop raises ToolError for nonexistent job."""
        fn = _get_ralph_fn("ralph_stop")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with pytest.raises(ToolError, match="not found"):
                fn("nonexistent-job")


class TestRalphSummary:
    """Tests for ralph_summary MCP tool."""

    def test_returns_structured_summary(self, tmp_path):
        """Test that ralph_summary returns AI-generated summary dict."""
        fn = _get_ralph_fn("ralph_summary")

        job_dir = tmp_path / ".vista" / "ralph" / "test-job"
        _write_job(
            job_dir,
            {
                "job_id": "test-123",
                "slug": "test-job",
                "mode": "build",
                "status": "running",
            },
        )
        (job_dir / "task.md").write_text("Test task description", encoding="utf-8")

        summary_output = {
            "status_summary": "Job is running",
            "completed_work": ["Implemented feature X"],
            "in_progress": ["Testing feature X"],
            "issues": [],
            "recommendations": ["Deploy to staging"],
            "key_files_changed": ["api.py"],
        }

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch(
                "server.services.summarizer_service.get_summarizer_config"
            ) as mock_config,
            patch(
                "server.services.summarizer_service.get_provider_by_name"
            ) as mock_provider,
            patch("server.services.summarizer_service.subprocess.run") as mock_run,
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_config.return_value = {"provider": "dummy", "model": "test"}
            mock_provider.return_value = DummyProvider()
            mock_run.return_value = Mock(returncode=0, stdout="")

            mock_proc = Mock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (json.dumps(summary_output), "")
            mock_popen.return_value = mock_proc

            result = fn("test-123")

            assert result["status_summary"] == "Job is running"
            assert result["completed_work"] == ["Implemented feature X"]
            assert result["in_progress"] == ["Testing feature X"]
            assert result["recommendations"] == ["Deploy to staging"]
