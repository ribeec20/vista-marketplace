"""Tests for BashLoopGenerator — TDD from bash-loop-logic diagram."""

import re

import pytest

from server.services.sandbox.bash_loop_generator import BashLoopGenerator


def _generate(**overrides):
    """Helper to generate with sensible defaults."""
    defaults = {
        "mode": "build",
        "max_iterations": 3,
        "model": "sonnet",
        "feature_name": "my-feature",
        "feature_dir": ".vista/features/my-feature",
        "project_root": "/workspace",
        "job_dir": ".vista/ralph/my-feature-abc12345",
        "provider": "claude",
    }
    defaults.update(overrides)
    return BashLoopGenerator.generate(**defaults)


class TestValidBashSyntax:
    def test_starts_with_shebang(self):
        script = _generate()
        assert script.startswith("#!/bin/bash")

    def test_includes_set_e(self):
        script = _generate()
        assert "set -e" in script

    def test_no_powershell_syntax(self):
        script = _generate()
        # No PowerShell variable declarations like $Var or Write-Host
        assert "Write-Host" not in script
        assert "param(" not in script
        assert "Test-Path" not in script

    def test_no_unresolved_placeholders(self):
        script = _generate()
        # Python format placeholders should all be resolved
        # But bash ${VAR} is valid, so only check for Python-style {word}
        # not surrounded by $
        unresolved = re.findall(r'(?<!\$)\{[a-z_]+\}', script)
        assert unresolved == [], f"Unresolved placeholders: {unresolved}"


class TestProviderInvocationBlocks:
    def test_claude_invocation(self):
        script = _generate(provider="claude")
        assert "claude -p" in script
        assert "--dangerously-skip-permissions" in script
        assert "--output-format=stream-json" in script

    def test_opencode_invocation(self):
        script = _generate(provider="opencode")
        assert "opencode" in script

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            _generate(provider="gemini")


class TestVariableSubstitution:
    def test_model_substituted(self):
        script = _generate(model="opus")
        assert 'MODEL="opus"' in script

    def test_mode_substituted(self):
        script = _generate(mode="plan")
        assert 'MODE="plan"' in script

    def test_max_iterations_substituted(self):
        script = _generate(max_iterations=5)
        assert "MAX_ITERATIONS=5" in script

    def test_feature_name_in_banner(self):
        script = _generate(feature_name="docker-sandbox")
        assert "docker-sandbox" in script

    def test_linux_paths_used(self):
        script = _generate(
            project_root="/workspace",
            feature_dir=".vista/features/test",
            job_dir=".vista/ralph/test-abc12345",
        )
        assert "/workspace" in script
        # No Windows-style paths (C:\Users\...) — bash line continuations are fine
        assert "C:\\" not in script
        assert "D:\\" not in script


class TestIterationLoop:
    def test_limited_iterations(self):
        script = _generate(max_iterations=5)
        assert "MAX_ITERATIONS=5" in script
        assert "MAX_ITERATIONS -gt 0" in script

    def test_unlimited_iterations(self):
        script = _generate(max_iterations=0)
        assert "MAX_ITERATIONS=0" in script
        # When 0, the condition `MAX_ITERATIONS -gt 0` is false, so loop runs forever


class TestPromptFileCheck:
    def test_prompt_file_existence_check(self):
        script = _generate()
        assert "PROMPT_FILE" in script
        # Should check existence and exit 1 if missing
        assert "exit 1" in script


class TestOutputLogging:
    def test_output_appended_to_log(self):
        script = _generate()
        assert "output.log" in script


class TestStartupBanner:
    def test_banner_contains_feature_info(self):
        script = _generate(
            feature_name="my-feature",
            provider="claude",
            mode="build",
            model="sonnet",
        )
        assert "my-feature" in script
        assert "build" in script.lower()


class TestModeValidation:
    def test_valid_plan_mode(self):
        script = _generate(mode="plan")
        assert 'MODE="plan"' in script

    def test_valid_build_mode(self):
        script = _generate(mode="build")
        assert 'MODE="build"' in script

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Invalid mode"):
            _generate(mode="deploy")


class TestIterationValidation:
    def test_negative_iterations_raises(self):
        with pytest.raises(ValueError, match="max_iterations"):
            _generate(max_iterations=-1)


class TestEdgeCases:
    def test_special_chars_in_feature_name(self):
        script = _generate(feature_name="my-cool-feature_v2")
        assert "my-cool-feature_v2" in script

    def test_model_with_dots_and_dashes(self):
        script = _generate(model="claude-3.5-sonnet")
        assert "claude-3.5-sonnet" in script

    def test_empty_invocation_via_unknown_provider(self):
        with pytest.raises(ValueError):
            _generate(provider="unknown-provider")
