"""Tests for sandbox configuration in config.py."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from server import config


@pytest.fixture
def settings_file(tmp_path):
    """Create a temporary settings file and patch config to use it."""
    sf = tmp_path / "settings.json"
    sf.write_text("{}", encoding="utf-8")
    with patch.object(config, "SETTINGS_FILE", sf):
        yield sf


class TestSandboxDefaults:
    def test_defaults_applied_when_no_sandbox_section(self, settings_file):
        settings_file.write_text(json.dumps({"ralph": {}}), encoding="utf-8")
        result = config.get_sandbox_settings()
        assert result["enabled"] is False
        assert result["image"] == "vista-ralph:latest"
        assert result["network_enabled"] is True
        assert result["ttl_seconds"] == 7200

    def test_defaults_applied_when_no_ralph_section(self, settings_file):
        settings_file.write_text("{}", encoding="utf-8")
        result = config.get_sandbox_settings()
        assert result["enabled"] is False
        assert result["image"] == "vista-ralph:latest"

    def test_credential_mounts_defaults(self, settings_file):
        settings_file.write_text("{}", encoding="utf-8")
        result = config.get_sandbox_settings()
        creds = result["credential_mounts"]
        assert creds["claude_auth"]["enabled"] is True
        assert creds["git_ssh"]["enabled"] is True
        assert creds["git_config"]["enabled"] is True
        assert creds["gh_cli"]["enabled"] is True
        assert creds["opencode"]["enabled"] is True

    def test_partial_sandbox_config_merged(self, settings_file):
        settings_file.write_text(json.dumps({
            "ralph": {
                "sandbox": {
                    "enabled": True,
                    "image": "custom:v2",
                }
            }
        }), encoding="utf-8")
        result = config.get_sandbox_settings()
        assert result["enabled"] is True
        assert result["image"] == "custom:v2"
        # Defaults for unset fields
        assert result["network_enabled"] is True
        assert result["ttl_seconds"] == 7200

    def test_partial_credential_mounts_merged(self, settings_file):
        settings_file.write_text(json.dumps({
            "ralph": {
                "sandbox": {
                    "credential_mounts": {
                        "git_ssh": {"enabled": False},
                    }
                }
            }
        }), encoding="utf-8")
        result = config.get_sandbox_settings()
        creds = result["credential_mounts"]
        assert creds["git_ssh"]["enabled"] is False
        assert creds["claude_auth"]["enabled"] is True  # default preserved


class TestIsSandboxEnabled:
    def test_returns_false_by_default(self, settings_file):
        settings_file.write_text("{}", encoding="utf-8")
        assert config.is_sandbox_enabled() is False

    def test_returns_true_when_enabled(self, settings_file):
        settings_file.write_text(json.dumps({
            "ralph": {"sandbox": {"enabled": True}}
        }), encoding="utf-8")
        assert config.is_sandbox_enabled() is True

    def test_returns_false_when_disabled(self, settings_file):
        settings_file.write_text(json.dumps({
            "ralph": {"sandbox": {"enabled": False}}
        }), encoding="utf-8")
        assert config.is_sandbox_enabled() is False


class TestGetSandboxCredentialMounts:
    def test_returns_credential_mounts(self, settings_file):
        settings_file.write_text("{}", encoding="utf-8")
        creds = config.get_sandbox_credential_mounts()
        assert "claude_auth" in creds
        assert "git_ssh" in creds

    def test_reflects_overrides(self, settings_file):
        settings_file.write_text(json.dumps({
            "ralph": {
                "sandbox": {
                    "credential_mounts": {
                        "gh_cli": {"enabled": False},
                    }
                }
            }
        }), encoding="utf-8")
        creds = config.get_sandbox_credential_mounts()
        assert creds["gh_cli"]["enabled"] is False


class TestSaveSandboxSettings:
    def test_save_preserves_other_ralph_sections(self, settings_file):
        settings_file.write_text(json.dumps({
            "ralph": {
                "defaults": {"provider": "claude", "model": "opus"},
                "summarizer": {"provider": "claude", "model": "haiku"},
            },
            "server": {"port": 9999},
        }), encoding="utf-8")

        config.save_sandbox_settings({"enabled": True, "image": "test:v1"})

        data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert data["ralph"]["sandbox"]["enabled"] is True
        assert data["ralph"]["sandbox"]["image"] == "test:v1"
        assert data["ralph"]["defaults"]["provider"] == "claude"
        assert data["ralph"]["summarizer"]["model"] == "haiku"
        assert data["server"]["port"] == 9999


class TestValidateSandboxSettings:
    def test_valid_config_returns_no_errors(self):
        errors = config.validate_sandbox_settings({
            "enabled": True,
            "image": "vista-ralph:latest",
            "network_enabled": True,
            "ttl_seconds": 7200,
        })
        assert errors == []

    def test_invalid_enabled_type(self):
        errors = config.validate_sandbox_settings({"enabled": "yes"})
        assert any("enabled" in e for e in errors)

    def test_invalid_image_empty(self):
        errors = config.validate_sandbox_settings({"image": ""})
        assert any("image" in e for e in errors)

    def test_invalid_image_type(self):
        errors = config.validate_sandbox_settings({"image": 123})
        assert any("image" in e for e in errors)

    def test_invalid_network_type(self):
        errors = config.validate_sandbox_settings({"network_enabled": "true"})
        assert any("network_enabled" in e for e in errors)

    def test_invalid_ttl_negative(self):
        errors = config.validate_sandbox_settings({"ttl_seconds": -1})
        assert any("ttl_seconds" in e for e in errors)

    def test_invalid_ttl_zero(self):
        errors = config.validate_sandbox_settings({"ttl_seconds": 0})
        assert any("ttl_seconds" in e for e in errors)

    def test_invalid_ttl_type(self):
        errors = config.validate_sandbox_settings({"ttl_seconds": "3600"})
        assert any("ttl_seconds" in e for e in errors)

    def test_invalid_credential_mount_entry(self):
        errors = config.validate_sandbox_settings({
            "credential_mounts": {"git_ssh": "not-a-dict"}
        })
        assert any("git_ssh" in e for e in errors)

    def test_invalid_credential_enabled_type(self):
        errors = config.validate_sandbox_settings({
            "credential_mounts": {"git_ssh": {"enabled": "yes"}}
        })
        assert any("git_ssh" in e for e in errors)

    def test_empty_config_valid(self):
        errors = config.validate_sandbox_settings({})
        assert errors == []
