"""Tests for loop_service - the core loop lifecycle manager.

Tests the LoopService class which mirrors ralph.py's run_loop() for web.
Uses mocked subprocesses to avoid requiring the actual claude CLI.
These tests validate: state management, prompt template resolution,
script generation, subscriber management, cleanup, and error handling.
"""
import asyncio
import platform
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from server.services.loop_service import LoopService, LOOP_PS1_TEMPLATE, LOOP_SH_TEMPLATE


class TestLoopServiceState:
    """Tests for loop state management (no subprocess needed)."""

    def test_initial_state_empty(self):
        """New LoopService should have no loops."""
        svc = LoopService()
        assert svc.get_all_states() == {}
        assert svc.get_state("nonexistent") is None

    def test_get_state_returns_none_for_unknown(self):
        """get_state should return None for unknown project IDs."""
        svc = LoopService()
        assert svc.get_state("abc") is None

    def test_get_all_states_returns_dict(self):
        """get_all_states should return the internal loops dict."""
        svc = LoopService()
        assert isinstance(svc.get_all_states(), dict)


class TestLoopServiceSubscribers:
    """Tests for SSE subscriber management."""

    def test_subscribe_creates_queue(self):
        """subscribe should return an asyncio.Queue and register it."""
        svc = LoopService()
        queue = svc.subscribe("proj1")
        assert isinstance(queue, asyncio.Queue)
        assert "proj1" in svc._subscribers
        assert queue in svc._subscribers["proj1"]

    def test_multiple_subscribers(self):
        """Multiple subscribers for the same project should coexist."""
        svc = LoopService()
        q1 = svc.subscribe("proj1")
        q2 = svc.subscribe("proj1")
        assert len(svc._subscribers["proj1"]) == 2
        assert q1 is not q2

    def test_unsubscribe_removes_queue(self):
        """unsubscribe should remove the specific queue."""
        svc = LoopService()
        q1 = svc.subscribe("proj1")
        q2 = svc.subscribe("proj1")
        svc.unsubscribe("proj1", q1)
        assert q1 not in svc._subscribers["proj1"]
        assert q2 in svc._subscribers["proj1"]

    def test_unsubscribe_nonexistent_is_safe(self):
        """unsubscribe for unknown project should not raise."""
        svc = LoopService()
        queue = asyncio.Queue()
        svc.unsubscribe("nonexistent", queue)  # Should not raise

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_subscribers(self):
        """_broadcast should send message to all subscriber queues."""
        svc = LoopService()
        q1 = svc.subscribe("proj1")
        q2 = svc.subscribe("proj1")
        msg = {"event": "test", "data": {"foo": "bar"}}
        await svc._broadcast("proj1", msg)
        assert q1.get_nowait() == msg
        assert q2.get_nowait() == msg

    @pytest.mark.asyncio
    async def test_broadcast_drops_full_queues(self):
        """_broadcast should remove subscribers with full queues."""
        svc = LoopService()
        # Create a queue with maxsize=1 and fill it
        small_queue = asyncio.Queue(maxsize=1)
        small_queue.put_nowait({"existing": True})
        svc._subscribers["proj1"] = [small_queue]

        # Broadcasting should not raise, and should remove the full queue
        await svc._broadcast("proj1", {"event": "overflow"})
        assert small_queue not in svc._subscribers["proj1"]

    @pytest.mark.asyncio
    async def test_broadcast_no_subscribers_is_safe(self):
        """_broadcast with no subscribers should not raise."""
        svc = LoopService()
        await svc._broadcast("nonexistent", {"event": "test"})


class TestLoopServiceStartValidation:
    """Tests for start_loop validation logic (mocked subprocess)."""

    @pytest.mark.asyncio
    async def test_start_loop_missing_feature_dir(self, tmp_path):
        """start_loop should raise ValueError if feature dir doesn't exist."""
        svc = LoopService()
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        with pytest.raises(ValueError, match="Feature directory not found"):
            await svc.start_loop(
                project_id="p1",
                project_path=str(project_dir),
                feature_name="nonexistent",
                mode="build",
                model="sonnet",
            )

    @pytest.mark.asyncio
    async def test_start_loop_already_running(self, tmp_path):
        """start_loop should raise if a loop is already running for the project."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance
        svc._loops["p1"] = LoopInstance(project_id="p1", status="running")

        project_dir = tmp_path / "proj"
        feature_dir = project_dir / ".vista" / "features" / "feat"
        feature_dir.mkdir(parents=True)
        (feature_dir / "PROMPT_build.md").write_text("test", encoding="utf-8")

        with pytest.raises(ValueError, match="already running"):
            await svc.start_loop(
                project_id="p1",
                project_path=str(project_dir),
                feature_name="feat",
                mode="build",
                model="sonnet",
            )

    @pytest.mark.asyncio
    async def test_start_loop_creates_instance(self, tmp_path):
        """start_loop should create a LoopInstance and track it."""
        svc = LoopService()
        project_dir = tmp_path / "proj"
        feature_dir = project_dir / ".vista" / "features" / "feat"
        feature_dir.mkdir(parents=True)
        (feature_dir / "PROMPT_build.md").write_text("test prompt", encoding="utf-8")

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.readline = MagicMock(return_value="")
        mock_proc.wait = MagicMock(return_value=0)
        mock_proc.returncode = 0

        with patch("server.services.loop_service.subprocess.Popen", return_value=mock_proc), \
             patch("server.services.loop_service.asyncio.create_task"):
            instance = await svc.start_loop(
                project_id="p1",
                project_path=str(project_dir),
                feature_name="feat",
                mode="build",
                model="opus",
                max_iterations=5,
            )

        assert instance.project_id == "p1"
        assert instance.feature_name == "feat"
        assert instance.mode == "build"
        assert instance.model == "opus"
        assert instance.max_iterations == 5
        assert instance.status == "running"
        assert instance.pid == 12345
        assert svc.get_state("p1") is instance


class TestLoopServicePromptTemplate:
    """Tests for prompt template resolution and variable substitution."""

    def test_get_prompt_content_substitution(self, tmp_path):
        """_get_prompt_content should substitute template variables."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template = templates_dir / "PROMPT_build.md"
        template.write_text(
            "Project: {{PROJECT_NAME}}\nFeature: {{FEATURE_NAME}}\nDir: {{FEATURE_DIR}}",
            encoding="utf-8",
        )

        feature_dir = tmp_path / "features" / "my_feat"
        feature_dir.mkdir(parents=True)

        with patch("server.services.loop_service.config") as mock_config:
            mock_config.TEMPLATES_DIR = templates_dir
            result = LoopService._get_prompt_content(
                mode="build",
                feature_name="my_feat",
                feature_dir=feature_dir,
                project_path=str(tmp_path),
            )

        assert "my_feat" in result
        assert tmp_path.name in result
        assert str(feature_dir).replace("\\", "/") in result

    def test_get_prompt_content_missing_template(self, tmp_path):
        """_get_prompt_content should return None if template doesn't exist."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        with patch("server.services.loop_service.config") as mock_config:
            mock_config.TEMPLATES_DIR = templates_dir
            result = LoopService._get_prompt_content(
                mode="build",
                feature_name="feat",
                feature_dir=tmp_path,
                project_path=str(tmp_path),
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_start_loop_creates_prompt_from_template(self, tmp_path):
        """start_loop should create PROMPT file from template if it doesn't exist."""
        svc = LoopService()
        project_dir = tmp_path / "proj"
        feature_dir = project_dir / ".vista" / "features" / "feat"
        feature_dir.mkdir(parents=True)

        # Create template directory with template
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "PROMPT_build.md").write_text(
            "Build {{FEATURE_NAME}} in {{PROJECT_NAME}}",
            encoding="utf-8",
        )

        mock_proc = MagicMock()
        mock_proc.pid = 99
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.readline = MagicMock(return_value="")
        mock_proc.wait = MagicMock(return_value=0)
        mock_proc.returncode = 0

        with patch("server.services.loop_service.subprocess.Popen", return_value=mock_proc), \
             patch("server.services.loop_service.asyncio.create_task"), \
             patch("server.services.loop_service.config") as mock_config:
            mock_config.TEMPLATES_DIR = templates_dir
            instance = await svc.start_loop(
                project_id="p1",
                project_path=str(project_dir),
                feature_name="feat",
                mode="build",
                model="sonnet",
            )

        # Prompt file should have been created
        prompt_file = feature_dir / "PROMPT_build.md"
        assert prompt_file.exists()
        content = prompt_file.read_text(encoding="utf-8")
        assert "feat" in content
        assert "proj" in content

    @pytest.mark.asyncio
    async def test_start_loop_no_template_raises(self, tmp_path):
        """start_loop should raise if prompt doesn't exist and no template available."""
        svc = LoopService()
        project_dir = tmp_path / "proj"
        feature_dir = project_dir / ".vista" / "features" / "feat"
        feature_dir.mkdir(parents=True)

        templates_dir = tmp_path / "empty_templates"
        templates_dir.mkdir()

        with patch("server.services.loop_service.config") as mock_config:
            mock_config.TEMPLATES_DIR = templates_dir
            with pytest.raises(ValueError, match="No prompt template found"):
                await svc.start_loop(
                    project_id="p1",
                    project_path=str(project_dir),
                    feature_name="feat",
                    mode="build",
                    model="sonnet",
                )


class TestLoopServiceScriptGeneration:
    """Tests for loop script generation (PS1/SH templates)."""

    @pytest.mark.asyncio
    async def test_script_generated_in_feature_dir(self, tmp_path):
        """start_loop should generate a loop script in the feature directory."""
        svc = LoopService()
        project_dir = tmp_path / "proj"
        feature_dir = project_dir / ".vista" / "features" / "feat"
        feature_dir.mkdir(parents=True)
        (feature_dir / "PROMPT_build.md").write_text("test", encoding="utf-8")

        mock_proc = MagicMock()
        mock_proc.pid = 42
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.readline = MagicMock(return_value="")
        mock_proc.wait = MagicMock(return_value=0)
        mock_proc.returncode = 0

        with patch("server.services.loop_service.subprocess.Popen", return_value=mock_proc), \
             patch("server.services.loop_service.asyncio.create_task"):
            await svc.start_loop(
                project_id="p1",
                project_path=str(project_dir),
                feature_name="feat",
                mode="build",
                model="opus",
                max_iterations=3,
            )

        if platform.system() == "Windows":
            script = feature_dir / "loop.ps1"
        else:
            script = feature_dir / "loop.sh"
        assert script.exists()
        content = script.read_text(encoding="utf-8")
        assert "opus" in content
        assert "feat" in content

    def test_ps1_template_format(self):
        """LOOP_PS1_TEMPLATE should format correctly with all variables."""
        result = LOOP_PS1_TEMPLATE.format(
            mode="build",
            max_iterations=5,
            model="opus",
            feature_name="my_feat",
            feature_dir="C:/path/to/feature",
            project_root="C:/path/to/project",
            provider_name="Claude Code",
            invocation_block="$PromptContent | claude -p --model $Model",
        )
        assert '"build"' in result
        assert "5" in result
        assert '"opus"' in result
        assert "my_feat" in result
        assert "C:/path/to/feature" in result
        assert "C:/path/to/project" in result

    def test_sh_template_format(self):
        """LOOP_SH_TEMPLATE should format correctly with all variables."""
        result = LOOP_SH_TEMPLATE.format(
            mode="plan",
            max_iterations=0,
            model="sonnet",
            feature_name="alpha",
            feature_dir="/home/user/project/features/alpha",
            project_root="/home/user/project",
            provider_name="Claude Code",
            invocation_block='cat "$PROMPT_FILE" | claude -p --model "$MODEL"',
        )
        assert 'MODE="plan"' in result
        assert "MAX_ITERATIONS=0" in result
        assert 'MODEL="sonnet"' in result
        assert "alpha" in result


class TestLoopServiceCleanup:
    """Tests for file cleanup after loop completion."""

    def test_cleanup_removes_created_files(self, tmp_path):
        """_cleanup_files should remove files that were created by the service."""
        svc = LoopService()
        f1 = tmp_path / "file1.md"
        f2 = tmp_path / "file2.ps1"
        f1.write_text("temp", encoding="utf-8")
        f2.write_text("temp", encoding="utf-8")

        svc._created_files["proj1"] = [f1, f2]
        svc._cleanup_files("proj1")

        assert not f1.exists()
        assert not f2.exists()
        assert "proj1" not in svc._created_files

    def test_cleanup_ignores_already_deleted(self, tmp_path):
        """_cleanup_files should not raise if files are already gone."""
        svc = LoopService()
        missing = tmp_path / "already_gone.md"
        svc._created_files["proj1"] = [missing]
        svc._cleanup_files("proj1")  # Should not raise

    def test_cleanup_empty_list(self):
        """_cleanup_files with no tracked files should be safe."""
        svc = LoopService()
        svc._cleanup_files("unknown")  # Should not raise

    def test_cleanup_does_not_delete_preexisting(self, tmp_path):
        """Only files tracked in _created_files should be cleaned up."""
        svc = LoopService()
        preexisting = tmp_path / "keep_me.md"
        preexisting.write_text("important", encoding="utf-8")

        # Only track a different file for cleanup
        tracked = tmp_path / "delete_me.md"
        tracked.write_text("temp", encoding="utf-8")
        svc._created_files["proj1"] = [tracked]
        svc._cleanup_files("proj1")

        assert preexisting.exists()
        assert not tracked.exists()


class TestLoopServiceStop:
    """Tests for stop_loop and stop_all."""

    @pytest.mark.asyncio
    async def test_stop_loop_not_running(self):
        """stop_loop should return None if no loop exists for the project."""
        svc = LoopService()
        result = await svc.stop_loop("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_stop_loop_already_stopped(self):
        """stop_loop should return instance without changes if already stopped."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance
        instance = LoopInstance(project_id="p1", status="completed")
        svc._loops["p1"] = instance
        result = await svc.stop_loop("p1")
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_stop_loop_terminates_process(self):
        """stop_loop should terminate the subprocess and set status to stopped."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance
        instance = LoopInstance(project_id="p1", status="running")
        svc._loops["p1"] = instance

        mock_proc = MagicMock()
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock(return_value=0)
        svc._processes["p1"] = mock_proc

        result = await svc.stop_loop("p1")
        assert result.status == "stopped"
        assert result.end_time is not None
        mock_proc.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_loop_cancels_reader_task(self):
        """stop_loop should cancel the output reader task."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance
        instance = LoopInstance(project_id="p1", status="running")
        svc._loops["p1"] = instance

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()
        svc._tasks["p1"] = mock_task

        mock_proc = MagicMock()
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock(return_value=0)
        svc._processes["p1"] = mock_proc

        await svc.stop_loop("p1")
        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_loop_broadcasts_event(self):
        """stop_loop should broadcast loop_stopped event to subscribers."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance
        instance = LoopInstance(project_id="p1", status="running")
        svc._loops["p1"] = instance

        queue = svc.subscribe("p1")

        mock_proc = MagicMock()
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock(return_value=0)
        svc._processes["p1"] = mock_proc

        await svc.stop_loop("p1")
        msg = queue.get_nowait()
        assert msg["event"] == "loop_stopped"

    @pytest.mark.asyncio
    async def test_stop_all_stops_running_loops(self):
        """stop_all should stop all running loops."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance

        svc._loops["p1"] = LoopInstance(project_id="p1", status="running")
        svc._loops["p2"] = LoopInstance(project_id="p2", status="running")

        mock_proc1 = MagicMock()
        mock_proc1.terminate = MagicMock()
        mock_proc1.wait = MagicMock(return_value=0)
        mock_proc2 = MagicMock()
        mock_proc2.terminate = MagicMock()
        mock_proc2.wait = MagicMock(return_value=0)

        svc._processes["p1"] = mock_proc1
        svc._processes["p2"] = mock_proc2

        await svc.stop_all()
        assert svc._loops["p1"].status == "stopped"
        assert svc._loops["p2"].status == "stopped"


class TestLoopServiceReadOutput:
    """Tests for the async output reader."""

    @pytest.mark.asyncio
    async def test_read_output_parses_iteration(self):
        """_read_output should parse iteration markers and update state."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance

        instance = LoopInstance(project_id="p1", status="running")
        svc._loops["p1"] = instance

        # Create a mock process that outputs iteration markers then closes
        lines = [
            "======================== ITERATION 1 ========================\n",
            "Started: 2026-01-01 12:00\n",
            "Building...\n",
            "[2026-01-01 12:05] ITERATION 1 complete\n",
            "======================== ITERATION 2 ========================\n",
            "Loop finished after 2 iteration(s)\n",
            "",  # EOF
        ]
        line_iter = iter(lines)

        mock_proc = MagicMock()
        mock_proc.stdout.readline = lambda: next(line_iter, "")
        mock_proc.wait = MagicMock(return_value=0)
        mock_proc.returncode = 0

        svc._processes["p1"] = mock_proc

        await svc._read_output("p1", mock_proc)

        assert instance.iteration == 2
        assert instance.status == "completed"
        assert instance.end_time is not None
        assert len(instance.output_lines) > 0

    @pytest.mark.asyncio
    async def test_read_output_parses_ralph_control(self):
        """_read_output should parse RALPH_CONTROL blocks."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance

        instance = LoopInstance(project_id="p1", status="running")
        svc._loops["p1"] = instance

        lines = [
            "# RALPH_CONTROL\n",
            "status: done\n",
            "files_changed: 5\n",
            "\n",
            "",  # EOF
        ]
        line_iter = iter(lines)

        mock_proc = MagicMock()
        mock_proc.stdout.readline = lambda: next(line_iter, "")
        mock_proc.wait = MagicMock(return_value=0)
        mock_proc.returncode = 0

        svc._processes["p1"] = mock_proc

        await svc._read_output("p1", mock_proc)

        assert instance.last_ralph_control == {"status": "done", "files_changed": "5"}

    @pytest.mark.asyncio
    async def test_read_output_failed_process(self):
        """_read_output should set status to failed for non-zero exit code."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance

        instance = LoopInstance(project_id="p1", status="running")
        svc._loops["p1"] = instance

        mock_proc = MagicMock()
        mock_proc.stdout.readline = MagicMock(return_value="")
        mock_proc.wait = MagicMock(return_value=1)
        mock_proc.returncode = 1

        svc._processes["p1"] = mock_proc

        await svc._read_output("p1", mock_proc)

        assert instance.status == "failed"
        assert "exit" in instance.error.lower()

    @pytest.mark.asyncio
    async def test_read_output_all_phases_complete(self):
        """_read_output should set completed on 'All phases complete'."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance

        instance = LoopInstance(project_id="p1", status="running")
        svc._loops["p1"] = instance

        lines = [
            "All phases complete! Stopping loop.\n",
            "",  # EOF
        ]
        line_iter = iter(lines)

        mock_proc = MagicMock()
        mock_proc.stdout.readline = lambda: next(line_iter, "")
        mock_proc.wait = MagicMock(return_value=0)
        mock_proc.returncode = 0

        svc._processes["p1"] = mock_proc

        await svc._read_output("p1", mock_proc)

        assert instance.status == "completed"

    @pytest.mark.asyncio
    async def test_read_output_broadcasts_lines(self):
        """_read_output should broadcast each line to subscribers."""
        svc = LoopService()
        from server.models.loop_state import LoopInstance

        instance = LoopInstance(project_id="p1", status="running")
        svc._loops["p1"] = instance

        queue = svc.subscribe("p1")

        lines = [
            "Hello world\n",
            "",  # EOF
        ]
        line_iter = iter(lines)

        mock_proc = MagicMock()
        mock_proc.stdout.readline = lambda: next(line_iter, "")
        mock_proc.wait = MagicMock(return_value=0)
        mock_proc.returncode = 0

        svc._processes["p1"] = mock_proc

        await svc._read_output("p1", mock_proc)

        # Should have received output event + loop_ended event
        messages = []
        while not queue.empty():
            messages.append(queue.get_nowait())

        output_events = [m for m in messages if m["event"] == "output"]
        assert len(output_events) == 1
        assert output_events[0]["data"]["line"] == "Hello world"

        ended_events = [m for m in messages if m["event"] == "loop_ended"]
        assert len(ended_events) == 1
