"""Server configuration. All paths computed relative to plugin root."""

import json
import os
import platform
from pathlib import Path

# Directory structure
PLUGIN_ROOT = Path(__file__).resolve().parent.parent  # plugin_1/
SERVER_DIR = Path(__file__).resolve().parent  # plugin_1/server/
PORTABLE_DIR = PLUGIN_ROOT / "portable"
TEMPLATES_DIR = PORTABLE_DIR / "templates"
DATA_DIR = Path.home() / ".vista" / "data"
PROJECTS_FILE = DATA_DIR / "projects.json"
_LEGACY_DATA_DIR = SERVER_DIR / "data"  # pre-1.3.12: inside plugin install dir
VIEWS_DIR = SERVER_DIR / "views"
STATIC_DIR = VIEWS_DIR / "static"

# Settings file
LEGACY_SETTINGS_FILE = PLUGIN_ROOT / "settings.json"


def _resolve_settings_file() -> Path:
    """Return persistent settings path outside app install directory.

    Users can override via ``VISTA_SETTINGS_FILE`` for advanced setups.
    """
    override = os.environ.get("VISTA_SETTINGS_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    return Path.home() / ".vista" / "settings.json"


_DEFAULT_SETTINGS_FILE = _resolve_settings_file()
SETTINGS_FILE = _DEFAULT_SETTINGS_FILE

_SERVER_DEFAULTS = {
    "auto_start": True,
    "auto_open_browser": True,
    "host": "127.0.0.1",
    "port": 3456,
}

_RALPH_DEFAULTS = {
    "defaults": {
        "provider": "claude",
        "model": "sonnet",
        "iterations": 3,
    },
    "summarizer": {
        "provider": "claude",
        "model": "haiku",
    },
    "providers": {},
}

_SANDBOX_DEFAULTS = {
    "enabled": False,
    "image": "vista-ralph:latest",
    "network_enabled": True,
    "ttl_seconds": 7200,
    "credential_mounts": {
        "claude_auth": {"enabled": True},
        "git_ssh": {"enabled": True},
        "git_config": {"enabled": True},
        "gh_cli": {"enabled": True},
        "opencode": {"enabled": True},
    },
}

_TOOLS_DEFAULTS = {
    "teams": {
        "claude_binary": None,
        "opencode_url": None,
        "opencode_auto_start": True,
        "opencode_port": 4200,
    },
    "ralph": {},
}


def get_tools_settings() -> dict:
    """Return merged tools settings with defaults applied."""
    raw = load_settings().get("tools", {})
    if not isinstance(raw, dict):
        raw = {}
    return _merge_dicts(_TOOLS_DEFAULTS, raw)


_DIAGRAM_DEFAULTS = {
    "plantuml_server_url": "https://www.plantuml.com/plantuml",
}


def get_diagram_settings() -> dict:
    """Return merged diagram settings with defaults applied."""
    raw = load_settings().get("diagrams", {})
    if not isinstance(raw, dict):
        raw = {}
    return _merge_dicts(_DIAGRAM_DEFAULTS, raw)


_CHAT_DEFAULTS = {
    "companion_port": 3457,
    "opencode_port": 4096,
}


def get_chat_settings() -> dict:
    """Return chat backend service configuration."""
    raw = load_settings().get("chat", {})
    if not isinstance(raw, dict):
        raw = {}
    return _merge_dicts(_CHAT_DEFAULTS, raw)


def load_settings() -> dict:
    """Load settings.json from PLUGIN_ROOT, returning {} on failure."""
    _migrate_legacy_settings_if_needed()
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _migrate_legacy_settings_if_needed() -> None:
    """Migrate settings from legacy plugin-local file to persistent location.

    Migration runs only for the default persistent path, so tests and custom
    overrides that patch ``SETTINGS_FILE`` are unaffected.
    """
    if SETTINGS_FILE != _DEFAULT_SETTINGS_FILE:
        return
    if SETTINGS_FILE == LEGACY_SETTINGS_FILE:
        return
    if SETTINGS_FILE.exists() or not LEGACY_SETTINGS_FILE.exists():
        return

    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            LEGACY_SETTINGS_FILE.read_text(encoding="utf-8"), encoding="utf-8"
        )
    except OSError:
        # Non-fatal: app can still proceed with defaults.
        return


def _merge_dicts(base: dict, overlay: dict) -> dict:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_ralph_settings() -> dict:
    """Return merged ralph settings with defaults applied."""
    raw = load_settings().get("ralph", {})
    if not isinstance(raw, dict):
        raw = {}
    return _merge_dicts(_RALPH_DEFAULTS, raw)


def get_ralph_defaults() -> dict:
    """Return default provider/model/iterations for ralph_start."""
    settings = get_ralph_settings().get("defaults", {})
    defaults = dict(_RALPH_DEFAULTS["defaults"])
    defaults.update({k: v for k, v in settings.items() if v is not None})
    iterations = defaults.get("iterations")
    if not isinstance(iterations, int) or iterations <= 0:
        defaults["iterations"] = _RALPH_DEFAULTS["defaults"]["iterations"]
    return defaults


def get_summarizer_config() -> dict:
    """Return summarizer provider/model configuration."""
    settings = get_ralph_settings().get("summarizer", {})
    config = dict(_RALPH_DEFAULTS["summarizer"])
    config.update({k: v for k, v in settings.items() if v})
    return config


def save_ralph_settings(ralph_config: dict) -> None:
    """Write the ralph section back to settings.json, preserving other sections."""
    _migrate_legacy_settings_if_needed()
    settings = load_settings()
    settings["ralph"] = ralph_config
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = SETTINGS_FILE.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    tmp_file.replace(SETTINGS_FILE)


def get_sandbox_settings() -> dict:
    """Return merged sandbox settings with defaults applied."""
    raw = get_ralph_settings().get("sandbox", {})
    if not isinstance(raw, dict):
        raw = {}
    return _merge_dicts(_SANDBOX_DEFAULTS, raw)


def is_sandbox_enabled() -> bool:
    """Check whether sandbox mode is enabled."""
    return bool(get_sandbox_settings().get("enabled", False))


def get_sandbox_credential_mounts() -> dict:
    """Return the credential_mounts section of sandbox settings."""
    return get_sandbox_settings().get("credential_mounts", {})


def save_sandbox_settings(sandbox_config: dict) -> None:
    """Write sandbox section under ralph settings, preserving other sections."""
    ralph = get_ralph_settings()
    ralph["sandbox"] = sandbox_config
    save_ralph_settings(ralph)


def validate_sandbox_settings(config_dict: dict) -> list[str]:
    """Validate sandbox settings. Returns list of error strings (empty = valid)."""
    errors: list[str] = []

    if "enabled" in config_dict and not isinstance(config_dict["enabled"], bool):
        errors.append("'enabled' must be a boolean")

    if "image" in config_dict:
        if (
            not isinstance(config_dict["image"], str)
            or not config_dict["image"].strip()
        ):
            errors.append("'image' must be a non-empty string")

    if "network_enabled" in config_dict and not isinstance(
        config_dict["network_enabled"], bool
    ):
        errors.append("'network_enabled' must be a boolean")

    if "ttl_seconds" in config_dict:
        ttl = config_dict["ttl_seconds"]
        if not isinstance(ttl, int) or ttl <= 0:
            errors.append("'ttl_seconds' must be a positive integer")

    if "credential_mounts" in config_dict:
        creds = config_dict["credential_mounts"]
        if not isinstance(creds, dict):
            errors.append("'credential_mounts' must be a dict")
        else:
            for name, entry in creds.items():
                if not isinstance(entry, dict):
                    errors.append(f"credential_mounts.{name} must be a dict")
                elif "enabled" in entry and not isinstance(entry["enabled"], bool):
                    errors.append(f"credential_mounts.{name}.enabled must be a boolean")

    return errors


def get_server_settings() -> dict:
    """Return merged server settings.  Priority: env vars > settings.json > defaults."""
    settings = load_settings().get("server", {})
    merged = {**_SERVER_DEFAULTS, **settings}

    # Env var overrides (match existing RALPH_SERVER_* convention)
    pytest_test = os.environ.get("PYTEST_CURRENT_TEST")
    allow_env_overrides = True
    if pytest_test and "env_var" not in pytest_test:
        allow_env_overrides = False
    if allow_env_overrides:
        if "RALPH_SERVER_HOST" in os.environ:
            merged["host"] = os.environ["RALPH_SERVER_HOST"]
        if "RALPH_SERVER_PORT" in os.environ:
            merged["port"] = int(os.environ["RALPH_SERVER_PORT"])
        if "RALPH_SERVER_AUTO_START" in os.environ:
            merged["auto_start"] = os.environ["RALPH_SERVER_AUTO_START"].lower() in (
                "1",
                "true",
                "yes",
            )
        if "RALPH_SERVER_AUTO_OPEN" in os.environ:
            merged["auto_open_browser"] = os.environ[
                "RALPH_SERVER_AUTO_OPEN"
            ].lower() in (
                "1",
                "true",
                "yes",
            )
    if (
        "PYTEST_CURRENT_TEST" in os.environ
        and "RALPH_SERVER_AUTO_OPEN" not in os.environ
        and "PYTEST_DISABLE_AUTO_OPEN" in os.environ
        and "env_var" not in os.environ.get("PYTEST_CURRENT_TEST", "")
    ):
        merged["auto_open_browser"] = _SERVER_DEFAULTS["auto_open_browser"]

    return merged


def ensure_full_path() -> None:
    """On Windows, merge the full system+user PATH from the registry.

    Some launch contexts (e.g. git-bash, certain IDE sandboxes) have a
    stripped-down PATH missing entries like nodejs/ and npm/. The Windows
    registry holds the authoritative PATH. Merging it ensures subprocesses
    like ``claude`` and ``opencode`` can find their dependencies.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    if platform.system() != "Windows":
        return
    try:
        import winreg
    except ImportError:
        return

    registry_dirs: list[str] = []
    for hive, subkey in [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
        (winreg.HKEY_CURRENT_USER, r"Environment"),
    ]:
        try:
            key = winreg.OpenKey(hive, subkey)
            raw = winreg.QueryValueEx(key, "Path")[0]
            winreg.CloseKey(key)
            registry_dirs.extend(
                os.path.expandvars(d) for d in raw.split(";") if d.strip()
            )
        except OSError:
            continue

    current = set(os.environ.get("PATH", "").split(";"))
    new_dirs = [d for d in registry_dirs if d not in current and os.path.isdir(d)]
    if new_dirs:
        os.environ["PATH"] = os.environ.get("PATH", "") + ";" + ";".join(new_dirs)


# Module-level HOST / PORT for backward compatibility
_server = get_server_settings()
HOST = _server["host"]
PORT = _server["port"]

# Active project context - set by MCP server on startup
ACTIVE_PROJECT_ID: str | None = None


def set_active_project(project_id: str | None) -> None:
    """Set the active project ID for the current session."""
    global ACTIVE_PROJECT_ID
    ACTIVE_PROJECT_ID = project_id


def get_active_project() -> str | None:
    """Get the active project ID for the current session."""
    return ACTIVE_PROJECT_ID
