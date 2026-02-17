"""Tests for server data models."""

import json
from collections import deque
from server.models.project import Project
from server.models.loop_state import LoopInstance


class TestProject:
    def test_project_creation_defaults(self):
        """Project should generate ID and timestamps automatically."""
        p = Project()
        assert len(p.id) == 8
        assert p.name == ""
        assert p.path == ""
        assert p.created_at  # should be non-empty ISO datetime

    def test_project_creation_with_values(self):
        """Project should accept explicit values."""
        p = Project(id="abc123", name="my_proj", path="/some/path")
        assert p.id == "abc123"
        assert p.name == "my_proj"
        assert p.path == "/some/path"

    def test_project_to_dict(self):
        """to_dict() should return all fields as a dictionary."""
        p = Project(id="test", name="proj", path="/path")
        d = p.to_dict()
        assert d["id"] == "test"
        assert d["name"] == "proj"
        assert d["path"] == "/path"
        assert "created_at" in d
        assert "last_accessed" in d

    def test_project_from_dict(self):
        """from_dict() should reconstruct a Project from a dictionary."""
        data = {
            "id": "abc",
            "name": "test",
            "path": "/test",
            "created_at": "2025-01-01",
            "last_accessed": "2025-01-01",
        }
        p = Project.from_dict(data)
        assert p.id == "abc"
        assert p.name == "test"
        assert p.path == "/test"

    def test_project_from_dict_ignores_extra_keys(self):
        """from_dict() should ignore keys not in the dataclass."""
        data = {"id": "abc", "name": "test", "path": "/test", "extra_key": "ignore_me"}
        p = Project.from_dict(data)
        assert p.id == "abc"
        assert not hasattr(p, "extra_key")

    def test_project_roundtrip(self):
        """Project should survive to_dict() -> from_dict() roundtrip."""
        p1 = Project(name="roundtrip", path="/round/trip")
        p2 = Project.from_dict(p1.to_dict())
        assert p1.id == p2.id
        assert p1.name == p2.name
        assert p1.path == p2.path


class TestLoopInstance:
    def test_default_state(self):
        """LoopInstance should default to idle status with empty output."""
        li = LoopInstance()
        assert li.status == "idle"
        assert li.iteration == 0
        assert li.max_iterations == 0
        assert li.pid is None
        assert len(li.output_lines) == 0

    def test_to_dict(self):
        """to_dict() should return all relevant fields."""
        li = LoopInstance(
            project_id="p1",
            feature_name="feat",
            mode="build",
            model="opus",
            status="running",
            iteration=3,
        )
        d = li.to_dict()
        assert d["project_id"] == "p1"
        assert d["feature_name"] == "feat"
        assert d["mode"] == "build"
        assert d["model"] == "opus"
        assert d["status"] == "running"
        assert d["iteration"] == 3
        assert d["output_line_count"] == 0

    def test_output_lines_maxlen(self):
        """output_lines deque should cap at 2000 lines."""
        li = LoopInstance()
        for i in range(2500):
            li.output_lines.append(f"line {i}")
        assert len(li.output_lines) == 2000
        assert li.output_lines[0] == "line 500"  # First 500 dropped

    def test_to_dict_excludes_raw_output(self):
        """to_dict() should include line count, not raw lines (for API efficiency)."""
        li = LoopInstance()
        li.output_lines.append("test line")
        d = li.to_dict()
        assert "output_lines" not in d
        assert d["output_line_count"] == 1

    def test_to_dict_includes_recent_actions(self):
        """to_dict() should include serialized recent actions for UI status popups."""
        li = LoopInstance()
        li.recent_actions.append(
            {"time": "2026-02-12T10:00:00", "type": "iteration", "message": "Iteration 1 started"}
        )
        d = li.to_dict()
        assert "recent_actions" in d
        assert len(d["recent_actions"]) == 1
        assert d["recent_actions"][0]["message"] == "Iteration 1 started"


class TestRalphProviderFiltering:
    def _mock_settings(self, overrides: dict) -> dict:
        base = {
            "providers": {
                "claude": {"enabled": True, "display_name": "Claude Code"},
                "opencode": {"enabled": True, "display_name": "OpenCode"},
            },
            "ralph": {
                "defaults": {"provider": "claude", "model": "sonnet", "iterations": 3},
                "summarizer": {"provider": "claude", "model": "haiku"},
                "providers": {},
            },
        }
        base.update(overrides)
        return base

    def test_allowlist_filter(self, tmp_path):
        settings = self._mock_settings(
            {
                "ralph": {
                    "providers": {
                        "claude": {
                            "enabled": True,
                            "models_allowed": ["sonnet"],
                            "models_blocked": ["opus"],
                            "model_metadata": {"sonnet": {"cost_tier": "moderate"}},
                        }
                    }
                }
            }
        )
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps(settings), encoding="utf-8")
        from unittest.mock import patch

        with patch("server.config.SETTINGS_FILE", sf):
            from server.services.provider_service import get_ralph_providers

            providers = get_ralph_providers()
            assert len(providers) == 1
            models = providers[0]["models"]
            assert [m["id"] for m in models] == ["sonnet"]
            assert models[0]["cost_tier"] == "moderate"

    def test_blocklist_filter(self, tmp_path):
        settings = self._mock_settings(
            {
                "ralph": {
                    "providers": {
                        "claude": {
                            "enabled": True,
                            "models_allowed": [],
                            "models_blocked": ["haiku"],
                            "model_metadata": {},
                        }
                    }
                }
            }
        )
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps(settings), encoding="utf-8")
        from unittest.mock import patch

        with patch("server.config.SETTINGS_FILE", sf):
            from server.services.provider_service import get_ralph_providers

            providers = get_ralph_providers()
            model_ids = [m["id"] for m in providers[0]["models"]]
            assert "haiku" not in model_ids

    def test_missing_ralph_section(self, tmp_path):
        settings = {
            "providers": {"claude": {"enabled": True, "display_name": "Claude Code"}}
        }
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps(settings), encoding="utf-8")
        from unittest.mock import patch

        with patch("server.config.SETTINGS_FILE", sf):
            from server.services.provider_service import get_ralph_providers

            providers = get_ralph_providers()
            assert providers[0]["name"] == "claude"
            assert {m["id"] for m in providers[0]["models"]} == {
                "opus",
                "sonnet",
                "haiku",
            }

    def test_provider_disabled_in_top_level(self, tmp_path):
        settings = self._mock_settings(
            {
                "providers": {
                    "claude": {"enabled": False, "display_name": "Claude Code"}
                },
                "ralph": {"providers": {"claude": {"enabled": True}}},
            }
        )
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps(settings), encoding="utf-8")
        from unittest.mock import patch

        with patch("server.config.SETTINGS_FILE", sf):
            from server.services.provider_service import get_ralph_providers

            providers = get_ralph_providers()
            assert providers == []

    def test_model_metadata_defaults(self, tmp_path):
        settings = self._mock_settings(
            {
                "ralph": {
                    "providers": {
                        "claude": {
                            "enabled": True,
                            "models_allowed": ["opus"],
                            "models_blocked": [],
                            "model_metadata": {},
                        }
                    }
                }
            }
        )
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps(settings), encoding="utf-8")
        from unittest.mock import patch

        with patch("server.config.SETTINGS_FILE", sf):
            from server.services.provider_service import get_ralph_providers

            models = get_ralph_providers()[0]["models"]
            assert models[0]["cost_tier"] is None
            assert models[0]["best_for_tags"] == []
            assert models[0]["best_for_notes"] == ""
