"""Tests for progress service - reads progress.txt and IMPLEMENTATION_PLAN.md."""
from pathlib import Path

from server.services.progress_service import ProgressService


class TestProgressService:
    def test_read_progress_not_found(self, tmp_path):
        """Should return exists=False when progress.txt doesn't exist."""
        result = ProgressService.read_progress(str(tmp_path), "nonexistent")
        assert result["exists"] is False
        assert result["all_complete"] is False

    def test_read_progress_basic(self, tmp_path):
        """Should read and return progress.txt content."""
        feature_dir = tmp_path / ".vista" / "features" / "test_feat"
        feature_dir.mkdir(parents=True)
        progress = feature_dir / "progress.txt"
        progress.write_text("Phase: build\nSome progress info", encoding="utf-8")

        result = ProgressService.read_progress(str(tmp_path), "test_feat")
        assert result["exists"] is True
        assert result["phase"] == "build"
        assert result["all_complete"] is False

    def test_read_progress_all_complete(self, tmp_path):
        """Should detect ALL PHASES COMPLETE."""
        feature_dir = tmp_path / ".vista" / "features" / "done_feat"
        feature_dir.mkdir(parents=True)
        progress = feature_dir / "progress.txt"
        progress.write_text("ALL PHASES COMPLETE\nPhase: build", encoding="utf-8")

        result = ProgressService.read_progress(str(tmp_path), "done_feat")
        assert result["all_complete"] is True

    def test_read_implementation_plan(self, tmp_path):
        """Should read IMPLEMENTATION_PLAN.md content."""
        feature_dir = tmp_path / ".vista" / "features" / "plan_feat"
        feature_dir.mkdir(parents=True)
        plan = feature_dir / "IMPLEMENTATION_PLAN.md"
        plan.write_text("# My Plan\nSome steps", encoding="utf-8")

        result = ProgressService.read_implementation_plan(str(tmp_path), "plan_feat")
        assert result is not None
        assert "# My Plan" in result

    def test_read_implementation_plan_not_found(self, tmp_path):
        """Should return None when plan doesn't exist."""
        result = ProgressService.read_implementation_plan(str(tmp_path), "nope")
        assert result is None

    def test_read_agents_md(self, tmp_path):
        """Should read AGENTS.md content."""
        feature_dir = tmp_path / ".vista" / "features" / "agents_feat"
        feature_dir.mkdir(parents=True)
        agents = feature_dir / "AGENTS.md"
        agents.write_text("## Build & Run\nSome commands", encoding="utf-8")

        result = ProgressService.read_agents_md(str(tmp_path), "agents_feat")
        assert result is not None
        assert "Build & Run" in result

    def test_read_agents_md_not_found(self, tmp_path):
        """Should return None when AGENTS.md doesn't exist."""
        result = ProgressService.read_agents_md(str(tmp_path), "nope")
        assert result is None
