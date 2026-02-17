"""Tests for ralph_service job management."""

import json
import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class DummyProvider:
    name = "dummy"
    display_name = "Dummy Provider"

    def get_invocation(self, shell: str = "ps1") -> str:
        if shell == "sh":
            return 'echo "ITERATION $ITERATION" >> "$PROGRESS_FILE"'
        return 'Add-Content -Path $ProgressFile -Value "ITERATION $Iteration"'


def _write_job(job_dir: Path, job: dict) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")


class TestRalphServiceCreateJob:
    def test_create_job_creates_files(self, tmp_path):
        from server.services.ralph_service import RalphService

        provider = DummyProvider()
        svc = RalphService()

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "PROMPT_plan_adhoc.md").write_text(
            "Plan {{FEATURE_NAME}} in {{PROJECT_NAME}} at {{FEATURE_DIR}}",
            encoding="utf-8",
        )

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.platform.system", return_value="Windows"
            ),
            patch("server.services.ralph_service.subprocess.Popen") as popen,
        ):
            proc = MagicMock()
            proc.pid = 1234
            popen.return_value = proc

            job = svc.create_job(
                tmp_path,
                slug="alpha",
                mode="plan",
                task_description="Do the thing",
                provider=provider,
                model="sonnet",
                iterations=1,
            )

        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        ralph_dirs = list((tmp_path / ".vista" / "ralph").iterdir())
        assert len(ralph_dirs) == 1
        job_dir = ralph_dirs[0]
        assert job_dir.exists()
        assert (job_dir / "task.md").exists()
        assert (job_dir / "PROMPT_plan.md").exists()
        assert (job_dir / "loop.ps1").exists()
        assert (job_dir / "output.log").exists()
        assert job["status"] == "running"

    def test_duplicate_slug_running_creates_separate_job_dir(self, tmp_path):
        from server.services.ralph_service import RalphService

        provider = DummyProvider()
        svc = RalphService()

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "PROMPT_plan_adhoc.md").write_text(
            "Plan {{FEATURE_NAME}} in {{PROJECT_NAME}} at {{FEATURE_DIR}}",
            encoding="utf-8",
        )

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.platform.system", return_value="Windows"
            ),
            patch("server.services.ralph_service.subprocess.Popen") as popen,
        ):
            proc = MagicMock()
            proc.pid = 1234
            popen.return_value = proc
            job1 = svc.create_job(
                tmp_path,
                slug="alpha",
                mode="plan",
                task_description="Do the thing",
                provider=provider,
                model="sonnet",
                iterations=1,
            )
            svc.create_job(
                tmp_path,
                slug="alpha",
                mode="plan",
                task_description="Do the thing",
                provider=provider,
                model="sonnet",
                iterations=1,
            )

        ralph_dirs = list((tmp_path / ".vista" / "ralph").iterdir())
        assert len(ralph_dirs) == 2
        assert job1["job_id"] != svc.list_jobs(tmp_path)[0]["job_id"]

    def test_create_job_clears_stale_runtime_files(self, tmp_path):
        from server.services.ralph_service import RalphService

        provider = DummyProvider()
        svc = RalphService()

        stale_dir = tmp_path / ".vista" / "ralph" / "alpha-oldrun"
        _write_job(stale_dir, {"job_id": "old", "status": "completed"})
        (stale_dir / "progress.txt").write_text("ITERATION 99", encoding="utf-8")
        (stale_dir / "output.log").write_text("old output", encoding="utf-8")

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "PROMPT_plan_adhoc.md").write_text(
            "Plan {{FEATURE_NAME}} in {{PROJECT_NAME}} at {{FEATURE_DIR}}",
            encoding="utf-8",
        )

        with (
            patch("server.services.ralph_service.config.TEMPLATES_DIR", templates_dir),
            patch(
                "server.services.ralph_service.platform.system", return_value="Windows"
            ),
            patch("server.services.ralph_service.subprocess.Popen") as popen,
        ):
            proc = MagicMock()
            proc.pid = 1234
            popen.return_value = proc
            svc.create_job(
                tmp_path,
                slug="alpha",
                mode="plan",
                task_description="Do the thing",
                provider=provider,
                model="sonnet",
                iterations=1,
            )

        # new run uses a distinct directory, so stale files don't affect it
        all_dirs = list((tmp_path / ".vista" / "ralph").iterdir())
        assert len(all_dirs) == 2
        new_dirs = [d for d in all_dirs if d != stale_dir]
        assert len(new_dirs) == 1
        new_dir = new_dirs[0]
        assert (new_dir / "output.log").read_text(encoding="utf-8") == ""
        assert not (new_dir / "progress.txt").exists()


class TestRalphServiceStatus:
    def test_status_marks_failed_when_pid_dead(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 1,
                "current_iteration": 0,
            },
        )

        with patch.object(svc, "_is_process_running", return_value=False):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["status"] == "failed"
        assert "pid" in job.get("error", "").lower()

    def test_status_includes_output_tail_when_pid_dead(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 1,
                "current_iteration": 0,
            },
        )
        (job_dir / "output.log").write_text(
            "line 1\nline 2\nerror detail", encoding="utf-8"
        )

        with patch.object(svc, "_is_process_running", return_value=False):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["status"] == "failed"
        assert "Last output:" in job.get("error", "")
        assert "error detail" in job.get("error", "")

    def test_status_marks_completed_when_pid_dead_after_max_iterations(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 2,
                "current_iteration": 0,
                "provider": "claude",
            },
        )
        (job_dir / "progress.txt").write_text(
            "ITERATION 1\nITERATION 2\nReached max iterations: 2",
            encoding="utf-8",
        )
        # output.log must contain both completion markers and model activity
        (job_dir / "output.log").write_text(
            '{"type":"assistant","message":{"content":[{"type":"text","text":"Hello"}]}}\n'
            "Reached max iterations: 2\n",
            encoding="utf-8",
        )

        with patch.object(svc, "_is_process_running", return_value=False):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["status"] == "completed"
        assert job.get("error") is None

    def test_status_not_completed_from_iteration_count_without_marker(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 1,
                "current_iteration": 1,
            },
        )
        (job_dir / "progress.txt").write_text(
            "ITERATION 1\nAgent invocation failed with exit code 127",
            encoding="utf-8",
        )

        with patch.object(svc, "_is_process_running", return_value=False):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["status"] == "failed"

    def test_status_reads_activity_from_output_log(self, tmp_path):
        """progress_tail comes from output.log parsing, not progress.txt."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 3,
                "current_iteration": 0,
                "provider": "opencode",
            },
        )
        # progress.txt has iteration markers (used for inter-loop context only)
        (job_dir / "progress.txt").write_text(
            "ITERATION 1\nITERATION 2\nITERATION 3", encoding="utf-8"
        )
        # output.log has the real agent activity
        (job_dir / "output.log").write_text(
            "======== ITERATION 1 ========\n"
            "Working on task...\n"
            "======== ITERATION 2 ========\n"
            "More work\n"
            "======== ITERATION 3 ========\n"
            "Final step\n",
            encoding="utf-8",
        )

        with patch.object(svc, "_is_process_running", return_value=True):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["current_iteration"] == 3
        # progress_tail comes from output.log, not progress.txt
        assert "Working on task..." in job["progress_tail"]
        assert "Final step" in job["progress_tail"]


class TestRalphServiceStop:
    def test_stop_job_updates_status(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 555,
            },
        )

        with (
            patch.object(svc, "_is_process_running", return_value=True),
            patch.object(svc, "_is_expected_job_process", return_value=True),
            patch("server.services.ralph_service.os.kill") as kill_mock,
        ):
            job = svc.stop_job(tmp_path, "abc")

        assert job["status"] == "stopped"
        kill_mock.assert_called_once_with(555, signal.SIGTERM)

    def test_stop_job_persists_status_before_kill(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 555,
            },
        )

        save_calls = []
        original_save = svc._save_job_json

        def tracking_save(jd, j):
            save_calls.append(j.get("status"))
            return original_save(jd, j)

        kill_calls = []

        def tracking_kill(pid, sig):
            # At the time kill is called, check what was last saved
            kill_calls.append(save_calls.copy())

        with (
            patch.object(svc, "_is_process_running", return_value=True),
            patch.object(svc, "_is_expected_job_process", return_value=True),
            patch.object(svc, "_save_job_json", side_effect=tracking_save),
            patch("server.services.ralph_service.os.kill", side_effect=tracking_kill),
        ):
            svc.stop_job(tmp_path, "abc")

        # _save_job_json was called with "stopped" before os.kill
        assert len(kill_calls) == 1
        assert kill_calls[0] == ["stopped"]

    def test_stop_job_uses_os_kill(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 555,
            },
        )

        with (
            patch.object(svc, "_is_process_running", return_value=True),
            patch.object(svc, "_is_expected_job_process", return_value=True),
            patch("server.services.ralph_service.os.kill") as kill_mock,
        ):
            svc.stop_job(tmp_path, "abc")

        kill_mock.assert_called_once_with(555, signal.SIGTERM)

    def test_stop_job_refuses_stale_pid_process(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 555,
            },
        )

        with (
            patch.object(svc, "_is_process_running", return_value=True),
            patch.object(svc, "_is_expected_job_process", return_value=False),
            patch("server.services.ralph_service.os.kill") as kill_mock,
        ):
            job = svc.stop_job(tmp_path, "abc")

        assert job["status"] == "stopped"
        assert "stale pid" in job.get("error", "").lower()
        kill_mock.assert_not_called()


class TestRalphServiceList:
    def test_list_jobs_sorted(self, tmp_path):
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_a = tmp_path / ".vista" / "ralph" / "a"
        job_b = tmp_path / ".vista" / "ralph" / "b"
        _write_job(job_a, {"job_id": "1", "created_at": "2026-01-01T00:00:00Z"})
        _write_job(job_b, {"job_id": "2", "created_at": "2026-02-01T00:00:00Z"})

        jobs = svc.list_jobs(tmp_path)
        assert [j["job_id"] for j in jobs] == ["2", "1"]


class TestProviderInvocation:
    """Verify that provider invocations use correct patterns."""

    def test_opencode_invocation_passes_prompt_as_arg_ps1(self):
        from server.services.provider_service import OpenCodeProvider

        inv = OpenCodeProvider().get_invocation("ps1")
        assert "opencode run" in inv
        assert "--model $Model" in inv
        assert "$PromptContent" in inv

    def test_opencode_invocation_passes_prompt_as_arg_sh(self):
        from server.services.provider_service import OpenCodeProvider

        inv = OpenCodeProvider().get_invocation("sh")
        assert "opencode run" in inv
        assert '"$MODEL"' in inv
        assert '"$PROMPT_CONTENT"' in inv

    def test_claude_invocation_pipes_stdin_ps1(self):
        from server.services.provider_service import ClaudeProvider

        inv = ClaudeProvider().get_invocation("ps1")
        assert "$PromptContent |" in inv
        assert "claude -p" in inv

    def test_claude_invocation_pipes_stdin_sh(self):
        from server.services.provider_service import ClaudeProvider

        inv = ClaudeProvider().get_invocation("sh")
        assert 'printf "%s" "$PROMPT_CONTENT"' in inv
        assert "| claude -p" in inv


class TestCompletionInference:
    """Verify that completion requires both markers AND model activity."""

    def test_status_requires_activity_for_completion_claude(self, tmp_path):
        """Completion markers in output.log but no model content → failed."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 2,
                "current_iteration": 0,
                "provider": "claude",
            },
        )
        # Completion markers in output.log but no model activity
        (job_dir / "output.log").write_text(
            "======== ITERATION 1 ========\n"
            "======== ITERATION 2 ========\n"
            "Reached max iterations: 2\n",
            encoding="utf-8",
        )

        with patch.object(svc, "_is_process_running", return_value=False):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["status"] == "failed"
        assert "no model output" in job.get("error", "").lower()

    def test_status_completed_when_activity_present_claude(self, tmp_path):
        """Completion markers + assistant JSON in output.log → completed."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 2,
                "current_iteration": 0,
                "provider": "claude",
            },
        )
        (job_dir / "output.log").write_text(
            '{"type":"assistant","message":{"content":[{"type":"text","text":"I will implement..."}]}}\n'
            "Reached max iterations: 2\n",
            encoding="utf-8",
        )

        with patch.object(svc, "_is_process_running", return_value=False):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["status"] == "completed"
        assert job.get("error") is None

    def test_status_requires_activity_for_completion_opencode(self, tmp_path):
        """Completion markers + only boilerplate in output.log → failed."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 2,
                "current_iteration": 0,
                "provider": "opencode",
            },
        )
        # Completion markers present, but only boilerplate — no real model output
        (job_dir / "output.log").write_text(
            "Feature: alpha\nProvider: OpenCode\nModel: gpt-4\n"
            "Mode: plan\nIteration 1 started:\n"
            "========================\n"
            "Reached max iterations: 2\n",
            encoding="utf-8",
        )

        with patch.object(svc, "_is_process_running", return_value=False):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["status"] == "failed"
        assert "no model output" in job.get("error", "").lower()

    def test_status_completed_when_activity_present_opencode(self, tmp_path):
        """Completion markers + real model text in output.log → completed."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        _write_job(
            job_dir,
            {
                "job_id": "abc",
                "slug": "alpha",
                "status": "running",
                "pid": 999,
                "iterations": 2,
                "current_iteration": 0,
                "provider": "opencode",
            },
        )
        (job_dir / "output.log").write_text(
            "Feature: alpha\nProvider: OpenCode\n"
            "Here is my implementation plan for the feature...\n"
            "Reached max iterations: 2\n",
            encoding="utf-8",
        )

        with patch.object(svc, "_is_process_running", return_value=False):
            job = svc.get_job_status(tmp_path, "abc")

        assert job["status"] == "completed"
        assert job.get("error") is None


class TestPlaintextActivityParsing:
    """Tests for parse_plaintext_activity (OpenCode output)."""

    def test_strips_ansi_and_extracts_tool_read(self):
        from server.services.output_parser import parse_plaintext_activity

        lines = [
            "\x1b[36m→ Read src/main.py\x1b[0m",
        ]
        activity, iteration = parse_plaintext_activity(lines)
        assert activity == ["> Read src/main.py"]
        assert iteration is None

    def test_extracts_tool_write_and_edit(self):
        from server.services.output_parser import parse_plaintext_activity

        lines = [
            "← Write src/output.py",
            "← Edit src/config.py",
        ]
        activity, _it = parse_plaintext_activity(lines)
        assert "> Wrote src/output.py" in activity
        assert "> Edit src/config.py" in activity

    def test_extracts_shell_commands(self):
        from server.services.output_parser import parse_plaintext_activity

        lines = [
            "$ ls -la",
            "$ git status --short",
        ]
        activity, _it = parse_plaintext_activity(lines)
        assert "> $ ls -la" in activity
        assert "> $ git status --short" in activity

    def test_preserves_assistant_text(self):
        from server.services.output_parser import parse_plaintext_activity

        lines = [
            "I will now implement the feature by modifying two files.",
            "",
            "Let me start with the config.",
        ]
        activity, _it = parse_plaintext_activity(lines)
        assert "I will now implement the feature by modifying two files." in activity
        assert "Let me start with the config." in activity
        assert len(activity) == 2  # empty line skipped

    def test_skips_powershell_boilerplate(self):
        from server.services.output_parser import parse_plaintext_activity

        lines = [
            "Write-Host 'Starting...'",
            "if ($true) {",
            "  $result = Get-Something",
            "}",
            "Real assistant output here",
        ]
        activity, _it = parse_plaintext_activity(lines)
        assert activity == ["Real assistant output here"]

    def test_tracks_iteration_markers(self):
        from server.services.output_parser import parse_plaintext_activity

        lines = [
            "======== ITERATION 1 ========",
            "→ Read src/main.py",
            "[2026-02-10 14:30] ITERATION 1 complete",
            "======== ITERATION 2 ========",
            "Working on changes...",
        ]
        activity, iteration = parse_plaintext_activity(lines)
        assert iteration == 2
        assert len(activity) == 5

    def test_truncates_long_lines(self):
        from server.services.output_parser import parse_plaintext_activity

        long_line = "x" * 300
        lines = [long_line]
        activity, _it = parse_plaintext_activity(lines)
        assert len(activity) == 1
        assert len(activity[0]) == 203  # 200 + "..."
        assert activity[0].endswith("...")

    def test_truncates_long_commands(self):
        from server.services.output_parser import parse_plaintext_activity

        long_cmd = "$ " + "a" * 250
        lines = [long_cmd]
        activity, _it = parse_plaintext_activity(lines)
        assert len(activity) == 1
        assert activity[0].startswith("> $ ")
        assert activity[0].endswith("...")

    def test_mixed_opencode_output(self):
        from server.services.output_parser import parse_plaintext_activity

        lines = [
            "======== ITERATION 1 ========",
            "Started: 2026-02-10 14:30",
            "\x1b[36m→ Read src/app.py\x1b[0m",
            "I see the issue in the config loading.",
            "\x1b[33m← Edit src/app.py\x1b[0m",
            "\x1b[32m$ python -m pytest tests/ -q\x1b[0m",
            "All 5 tests passed.",
            "[2026-02-10 14:31] ITERATION 1 complete",
            "Loop finished after 1 iteration(s)",
        ]
        activity, iteration = parse_plaintext_activity(lines)
        assert iteration == 1
        assert "> Read src/app.py" in activity
        assert "I see the issue in the config loading." in activity
        assert "> Edit src/app.py" in activity
        assert "> $ python -m pytest tests/ -q" in activity
        assert "All 5 tests passed." in activity
        assert any("Loop finished" in a for a in activity)

    def test_read_activity_dispatches_by_provider(self, tmp_path):
        """_read_activity uses plaintext parser for non-claude providers."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        job_dir.mkdir(parents=True)
        (job_dir / "output.log").write_text(
            "\x1b[36m→ Read src/main.py\x1b[0m\n"
            "I will fix the bug.\n"
            "\x1b[33m← Edit src/main.py\x1b[0m\n",
            encoding="utf-8",
        )

        activity, _it = svc._read_activity(job_dir, provider="opencode")
        assert "> Read src/main.py" in activity
        assert "I will fix the bug." in activity
        assert "> Edit src/main.py" in activity

    def test_read_activity_uses_stream_json_for_claude(self, tmp_path):
        """_read_activity uses stream-json parser for claude provider."""
        from server.services.ralph_service import RalphService

        svc = RalphService()
        job_dir = tmp_path / ".vista" / "ralph" / "alpha"
        job_dir.mkdir(parents=True)
        (job_dir / "output.log").write_text(
            '{"type":"assistant","message":{"content":[{"type":"text","text":"Hello"}]}}\n',
            encoding="utf-8",
        )

        activity, _it = svc._read_activity(job_dir, provider="claude")
        assert "Hello" in activity
