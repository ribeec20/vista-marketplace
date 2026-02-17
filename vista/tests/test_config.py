"""Tests for server.config settings loading."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestLoadSettings:
    """Tests for load_settings()."""

    def test_returns_empty_when_no_file(self, tmp_path):
        missing = tmp_path / "settings.json"
        with patch("server.config.SETTINGS_FILE", missing):
            from server.config import load_settings

            assert load_settings() == {}

    def test_reads_settings_file(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps({"server": {"port": 9999}}), encoding="utf-8")
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import load_settings

            result = load_settings()
            assert result["server"]["port"] == 9999

    def test_malformed_json_returns_empty(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text("{bad json", encoding="utf-8")
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import load_settings

            assert load_settings() == {}

    def test_partial_settings_preserved(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(
            json.dumps({"providers": {"claude": {"enabled": True}}}), encoding="utf-8"
        )
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import load_settings

            result = load_settings()
            assert "providers" in result
            assert "server" not in result


class TestGetServerSettings:
    """Tests for get_server_settings()."""

    def test_defaults_when_no_file(self, tmp_path):
        missing = tmp_path / "settings.json"
        with patch("server.config.SETTINGS_FILE", missing):
            from server.config import get_server_settings

            cfg = get_server_settings()
            assert cfg["host"] == "127.0.0.1"
            assert cfg["port"] == 3456
            assert cfg["auto_start"] is True
            assert cfg["auto_open_browser"] is True

    def test_settings_file_overrides_defaults(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(
            json.dumps({"server": {"port": 4000, "host": "0.0.0.0"}}), encoding="utf-8"
        )
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import get_server_settings

            cfg = get_server_settings()
            assert cfg["port"] == 4000
            assert cfg["host"] == "0.0.0.0"
            # Defaults still present for unset keys
            assert cfg["auto_start"] is True

    def test_env_vars_override_all(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(
            json.dumps({"server": {"port": 4000, "host": "0.0.0.0"}}), encoding="utf-8"
        )
        env = {
            "RALPH_SERVER_HOST": "10.0.0.1",
            "RALPH_SERVER_PORT": "5555",
            "RALPH_SERVER_AUTO_START": "false",
            "RALPH_SERVER_AUTO_OPEN": "0",
        }
        with (
            patch("server.config.SETTINGS_FILE", sf),
            patch.dict(os.environ, env, clear=False),
        ):
            from server.config import get_server_settings

            cfg = get_server_settings()
            assert cfg["host"] == "10.0.0.1"
            assert cfg["port"] == 5555
            assert cfg["auto_start"] is False
            assert cfg["auto_open_browser"] is False

    def test_env_var_true_values(self, tmp_path):
        missing = tmp_path / "settings.json"
        env = {
            "RALPH_SERVER_AUTO_START": "yes",
            "RALPH_SERVER_AUTO_OPEN": "1",
        }
        with (
            patch("server.config.SETTINGS_FILE", missing),
            patch.dict(os.environ, env, clear=False),
        ):
            from server.config import get_server_settings

            cfg = get_server_settings()
            assert cfg["auto_start"] is True
            assert cfg["auto_open_browser"] is True

    def test_missing_server_section_uses_defaults(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps({"providers": {}}), encoding="utf-8")
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import get_server_settings

            cfg = get_server_settings()
            assert cfg["host"] == "127.0.0.1"
            assert cfg["port"] == 3456

    def test_partial_server_section_merges(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps({"server": {"auto_start": False}}), encoding="utf-8")
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import get_server_settings

            cfg = get_server_settings()
            assert cfg["auto_start"] is False
            assert cfg["host"] == "127.0.0.1"
            assert cfg["port"] == 3456
            assert cfg["auto_open_browser"] is True


class TestRalphSettings:
    def test_get_ralph_defaults_fallback(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(
            json.dumps({"ralph": {"defaults": {"iterations": -1}}}),
            encoding="utf-8",
        )
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import get_ralph_defaults

            defaults = get_ralph_defaults()
            assert defaults["provider"] == "claude"
            assert defaults["model"] == "sonnet"
            assert defaults["iterations"] == 3

    def test_get_summarizer_config_defaults(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps({"ralph": {"summarizer": {}}}), encoding="utf-8")
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import get_summarizer_config

            cfg = get_summarizer_config()
            assert cfg["provider"] == "claude"
            assert cfg["model"] == "haiku"

    def test_save_ralph_settings_preserves_other_sections(self, tmp_path):
        settings = {
            "server": {"host": "127.0.0.1", "port": 3456},
            "providers": {"claude": {"enabled": True, "display_name": "Claude Code"}},
        }
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps(settings), encoding="utf-8")
        with patch("server.config.SETTINGS_FILE", sf):
            from server.config import save_ralph_settings

            save_ralph_settings({"defaults": {"provider": "claude"}})
            updated = json.loads(sf.read_text(encoding="utf-8"))
            assert "server" in updated
            assert "providers" in updated
            assert updated["ralph"]["defaults"]["provider"] == "claude"


class TestSettingsMigration:
    def test_load_settings_migrates_legacy_file_to_persistent_location(self, tmp_path):
        legacy = tmp_path / "legacy_settings.json"
        persistent = tmp_path / "persistent" / "settings.json"
        legacy.write_text(json.dumps({"server": {"port": 4567}}), encoding="utf-8")

        with (
            patch("server.config.LEGACY_SETTINGS_FILE", legacy),
            patch("server.config._DEFAULT_SETTINGS_FILE", persistent),
            patch("server.config.SETTINGS_FILE", persistent),
        ):
            from server.config import load_settings

            loaded = load_settings()
            assert loaded["server"]["port"] == 4567
            assert persistent.exists()
            migrated = json.loads(persistent.read_text(encoding="utf-8"))
            assert migrated["server"]["port"] == 4567

    def test_custom_settings_path_does_not_auto_migrate_legacy(self, tmp_path):
        legacy = tmp_path / "legacy_settings.json"
        custom = tmp_path / "custom" / "settings.json"
        legacy.write_text(json.dumps({"server": {"port": 7890}}), encoding="utf-8")

        with (
            patch("server.config.LEGACY_SETTINGS_FILE", legacy),
            patch("server.config._DEFAULT_SETTINGS_FILE", tmp_path / "default" / "settings.json"),
            patch("server.config.SETTINGS_FILE", custom),
        ):
            from server.config import load_settings

            loaded = load_settings()
            assert loaded == {}
            assert not custom.exists()
