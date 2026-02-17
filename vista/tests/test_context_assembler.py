"""Tests for ContextAssembler."""

import os
import tempfile

from server.services.context_assembler import ContextAssembler


class TestBuildSystemPrompt:
    def test_includes_all_directories(self):
        result = ContextAssembler.build_system_prompt(
            arch_dir="/project/arch",
            specs_dir="/project/specs",
            project_root="/project",
        )
        assert "/project/arch" in result
        assert "/project/specs" in result
        assert "/project" in result
        assert "architecture documentation assistant" in result

    def test_scopes_editing_to_arch_dir(self):
        result = ContextAssembler.build_system_prompt(
            arch_dir="/arch", specs_dir="/specs", project_root="/root",
        )
        assert "ONLY edit .mmd" in result
        assert "Do NOT edit source code" in result


class TestBuildFullPrompt:
    def test_basic_message(self):
        result = ContextAssembler.build_full_prompt(message="Hello")
        assert "Hello" in result
        # No role-prefix wrappers for chat API prompts
        assert "ASSISTANT:" not in result

    def test_with_system_prompt(self):
        result = ContextAssembler.build_full_prompt(
            message="Hello",
            system_prompt="You are a helpful assistant.",
        )
        assert "You are a helpful assistant." in result
        assert "Hello" in result

    def test_with_context(self):
        result = ContextAssembler.build_full_prompt(
            message="What is this?",
            context="graph TD; A-->B",
        )
        assert "--- DIAGRAM CONTEXT ---" in result
        assert "graph TD; A-->B" in result
        assert "--- END CONTEXT ---" in result

    def test_history_ignored(self):
        """History is accepted but ignored — providers maintain native history."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = ContextAssembler.build_full_prompt(
            message="How are you?",
            history=history,
        )
        # History should NOT appear in the prompt
        assert "--- CONVERSATION HISTORY ---" not in result
        assert "Hi there!" not in result
        # Current message should be present
        assert "How are you?" in result

    def test_full_assembly(self):
        result = ContextAssembler.build_full_prompt(
            message="Update the diagram",
            context="flowchart LR; A-->B",
            history=[{"role": "user", "content": "Show me the diagram"}],
            system_prompt="You are an architect.",
        )
        # System prompt first
        lines = result.split("\n")
        assert lines[0] == "You are an architect."
        # Then context
        assert "--- DIAGRAM CONTEXT ---" in result
        # History should NOT appear (providers maintain it natively)
        assert "--- CONVERSATION HISTORY ---" not in result
        # Current message present without role prefix
        assert "Update the diagram" in result
        assert "ASSISTANT:" not in result

    def test_empty_context_and_history(self):
        result = ContextAssembler.build_full_prompt(
            message="Hello",
            context=None,
            history=None,
        )
        assert "--- DIAGRAM CONTEXT ---" not in result
        assert "--- CONVERSATION HISTORY ---" not in result


class TestGetDiagramContext:
    def test_reads_attached_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mmd_path = os.path.join(tmpdir, "test.mmd")
            with open(mmd_path, "w", encoding="utf-8") as f:
                f.write("graph TD; A-->B")

            result = ContextAssembler.get_diagram_context(
                arch_dir=tmpdir,
                attached_files=["test.mmd"],
            )
            assert "## test.mmd" in result
            assert "graph TD; A-->B" in result

    def test_ignores_missing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = ContextAssembler.get_diagram_context(
                arch_dir=tmpdir,
                attached_files=["nonexistent.mmd"],
            )
            assert result == ""

    def test_includes_selected_elements(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = ContextAssembler.get_diagram_context(
                arch_dir=tmpdir,
                attached_files=[],
                selected_elements=[
                    {"id": "node1", "label": "Service A"},
                    {"id": "node2", "label": "Service B"},
                ],
            )
            assert "## Selected Elements" in result
            assert "node1: Service A" in result
            assert "node2: Service B" in result
