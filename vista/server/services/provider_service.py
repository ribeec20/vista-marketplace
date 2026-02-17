"""Provider abstraction for multi-CLI support (Claude, OpenCode, etc.).

Single source of truth for Provider classes — portable/ralph.py imports from here.
Reads configuration from PROJECT_ROOT/settings.json.
"""

import json
import platform
import re
import subprocess
from pathlib import Path
from typing import Optional

_IS_WINDOWS = platform.system() == "Windows"

import os
import shutil

from server import config


def _find_command(name: str) -> Optional[str]:
    """Find a CLI command, checking PATH and common install locations."""
    found = shutil.which(name)
    if found:
        return found
    # Check common install locations not always on PATH
    if _IS_WINDOWS:
        candidates = [
            os.path.join(os.environ.get("APPDATA", ""), "npm", f"{name}.cmd"),
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""), "Programs", name, f"{name}.exe"
            ),
        ]
    else:
        candidates = [
            os.path.expanduser(f"~/.local/bin/{name}"),
            os.path.expanduser(f"~/go/bin/{name}"),
            f"/usr/local/bin/{name}",
        ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _run_cli_with_timeout(cmd: list[str], timeout: int = 10) -> Optional[str]:
    """Run a CLI command with proper timeout + process-tree cleanup on Windows.

    Returns combined stdout+stderr on success, None on failure/timeout.
    """
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "text": True,
    }
    if _IS_WINDOWS:
        # CREATE_NO_WINDOW prevents console allocation hang in daemon/MCP context
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        # Use explicit cmd.exe /c for .cmd/.bat wrappers instead of shell=True
        if cmd[0].endswith((".cmd", ".bat")):
            cmd = ["cmd.exe", "/c"] + cmd

    proc = subprocess.Popen(cmd, **kwargs)  # type: ignore[arg-type]
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if _IS_WINDOWS:
            # Kill entire process tree; plain proc.kill() only kills cmd.exe
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=5,
            )
        else:
            proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return None
    if proc.returncode != 0:
        return None
    return (stdout or "") + (stderr or "")


# ---------------------------------------------------------------------------
# Provider base + implementations
# ---------------------------------------------------------------------------


class Provider:
    """Base class for CLI agent providers."""

    name: str = ""
    display_name: str = ""

    def get_models(self) -> list[str]:
        raise NotImplementedError

    def get_invocation(self, shell: str = "ps1") -> str:
        """Return shell snippet for invoking the CLI.

        shell: "ps1" for PowerShell, "sh" for Bash.
        PowerShell has $PromptContent and $Model available.
        Bash has $PROMPT_CONTENT and $MODEL available.
        """
        raise NotImplementedError

    def get_summarizer_command(self, model: str) -> list[str]:
        """Return CLI command list for summarizer invocation."""
        raise NotImplementedError

    # --- Chat streaming interface ---

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming output."""
        return False

    @property
    def stdin_pipe(self) -> bool:
        """Whether the prompt should be piped via stdin (True) or passed as CLI arg (False)."""
        return True

    def get_chat_cmd(
        self, model: str, *, streaming: bool = False, permissions: bool = False
    ) -> Optional[list[str]]:
        """Return CLI command list for chat invocation.

        Returns None if the CLI command cannot be found.
        """
        return None

    def get_persistent_cmd(
        self, model: str, *, permissions: bool = False
    ) -> Optional[list[str]]:
        """Return CLI command for a persistent interactive chat process.

        Returns None if the provider doesn't support interactive mode.
        The process stays alive reading messages from stdin (one per line),
        responding via stdout, then waiting for the next message.
        """
        return None

    def parse_stream_event(self, line: str) -> Optional[dict]:
        """Parse one line of streaming output into an event dict.

        Returns {"type": "token", "text": "..."} for content tokens,
                {"type": "result", ...} for completion,
                None for lines to skip.
        """
        return None

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Full dict including models (calls get_models() which may run CLI)."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "models": self.get_models(),
        }

    def to_summary_dict(self) -> dict:
        """Lightweight dict without models — safe for page-load use."""
        return {
            "name": self.name,
            "display_name": self.display_name,
        }


class ClaudeProvider(Provider):
    name = "claude"
    display_name = "Claude Code"

    def get_models(self) -> list[str]:
        return ["opus", "sonnet", "haiku"]

    def get_invocation(self, shell: str = "ps1") -> str:
        if shell == "sh":
            return (
                'printf "%s" "$PROMPT_CONTENT" | claude -p \\\n'
                "        --dangerously-skip-permissions \\\n"
                "        --output-format=stream-json \\\n"
                '        --model "$MODEL" \\\n'
                "        --verbose"
            )
        return (
            "$PromptContent | claude -p `\n"
            "        --dangerously-skip-permissions `\n"
            "        --output-format=stream-json `\n"
            "        --model $Model `\n"
            "        --verbose"
        )

    def get_summarizer_command(self, model: str) -> list[str]:
        cmd_path = _find_command("claude")
        if cmd_path is None:
            return []
        return [cmd_path, "-p", "--model", model, "--output-format", "text"]

    def get_chat_cmd(
        self, model: str, *, streaming: bool = False, permissions: bool = False
    ) -> Optional[list[str]]:
        cmd_path = _find_command("claude")
        if cmd_path is None:
            return None
        cmd = [cmd_path, "-p", "--model", model]
        if permissions:
            cmd.append("--dangerously-skip-permissions")
        if streaming:
            cmd.extend(["--output-format", "stream-json", "--verbose"])
        return cmd

    def get_persistent_cmd(
        self, model: str, *, permissions: bool = False
    ) -> Optional[list[str]]:
        cmd_path = _find_command("claude")
        if cmd_path is None:
            return None
        # Interactive mode (no -p): stays alive, reads messages from stdin
        cmd = [cmd_path, "--output-format", "stream-json", "--verbose", "--model", model]
        if permissions:
            cmd.append("--dangerously-skip-permissions")
        return cmd

    def parse_stream_event(self, line: str) -> Optional[dict]:
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return None
        msg_type = data.get("type")
        if msg_type == "assistant":
            text = data.get("text", "")
            if text:
                return {"type": "token", "text": text}
        elif msg_type == "result":
            return {
                "type": "result",
                "session_id": data.get("session_id", ""),
                "cost": data.get("cost_usd"),
                "duration_ms": data.get("duration_ms"),
            }
        return None


class OpenCodeProvider(Provider):
    name = "opencode"
    display_name = "OpenCode"

    def get_models(self) -> list[str]:
        """Discover models. Try running OpenCode server first, fall back to CLI."""
        # 1. Try HTTP: GET http://localhost:{port}/config/providers
        try:
            from server.services.service_lifecycle import service_lifecycle
            if service_lifecycle.is_available("opencode"):
                status = service_lifecycle.get_status("opencode")
                port = status.get("port")
                if port:
                    import httpx
                    resp = httpx.get(
                        f"http://127.0.0.1:{port}/config/providers",
                        timeout=5.0,
                    )
                    if resp.status_code == 200:
                        providers_data = resp.json()
                        models = []
                        for p in providers_data:
                            for m in p.get("models", []):
                                model_id = m if isinstance(m, str) else m.get("id", "")
                                if model_id:
                                    models.append(f"{p['id']}/{model_id}")
                        if models:
                            return models
        except Exception:
            pass

        # 2. Fall back to CLI discovery
        return self._get_models_from_cli()

    def _get_models_from_cli(self) -> list[str]:
        """Discover models via `opencode models` CLI."""
        try:
            cmd = _find_command("opencode")
            if cmd is None:
                return []
            output = _run_cli_with_timeout([cmd, "models"], timeout=10)
            if output is None:
                return []
            models = []
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Only skip log noise lines
                if re.match(
                    r"^(INFO|DEBUG|WARN|ERROR|FATAL|CRITICAL)\b",
                    line,
                ):
                    continue
                models.append(line)
            if models:
                return models
        except (FileNotFoundError, OSError):
            pass
        return []

    def get_invocation(self, shell: str = "ps1") -> str:
        if shell == "sh":
            return 'opencode run --model "$MODEL" "$PROMPT_CONTENT"'
        return "opencode run --model $Model $PromptContent"

    def get_chat_cmd(
        self, model: str, *, streaming: bool = False, permissions: bool = False
    ) -> Optional[list[str]]:
        cmd_path = _find_command("opencode")
        if cmd_path is None:
            return None
        return [cmd_path, "run", "--model", model]

    def get_summarizer_command(self, model: str) -> list[str]:
        cmd_path = _find_command("opencode")
        if cmd_path is None:
            return []
        return [cmd_path, "run", "--model", model]


# ---------------------------------------------------------------------------
# Registry & settings
# ---------------------------------------------------------------------------

_PROVIDER_REGISTRY: dict[str, type[Provider]] = {
    "claude": ClaudeProvider,
    "opencode": OpenCodeProvider,
}

_DEFAULT_SETTINGS = {
    "providers": {
        "claude": {"enabled": True, "display_name": "Claude Code"},
    }
}


def get_enabled_providers(settings: Optional[dict] = None) -> list[Provider]:
    """Instantiate enabled providers from settings."""
    if settings is None:
        raw = config.load_settings()
        settings = {**_DEFAULT_SETTINGS, **raw}
    providers_cfg = settings.get("providers", {})
    enabled: list[Provider] = []
    for key, cfg in providers_cfg.items():
        if not cfg.get("enabled", False):
            continue
        cls = _PROVIDER_REGISTRY.get(key)
        if cls is None:
            continue
        provider = cls()
        if "display_name" in cfg:
            provider.display_name = cfg["display_name"]
        enabled.append(provider)
    return enabled


def get_provider_by_name(name: str) -> Optional[Provider]:
    """Get a specific enabled provider by name, or None."""
    for p in get_enabled_providers():
        if p.name == name:
            return p
    return None


def _apply_model_filters(
    models: list[str], allowlist: list[str], blocklist: list[str]
) -> list[str]:
    if allowlist:
        allowed = set(allowlist)
        return [m for m in models if m in allowed]
    if blocklist:
        blocked = set(blocklist)
        return [m for m in models if m not in blocked]
    return list(models)


def get_ralph_providers() -> list[dict]:
    """Return enabled providers with filtered model lists and metadata for ralph MCP tools."""
    settings = config.load_settings()
    ralph_cfg = config.get_ralph_settings()
    ralph_providers = ralph_cfg.get("providers", {})

    enabled = []
    top_level_enabled = {p.name: p for p in get_enabled_providers(settings)}
    if ralph_providers:
        provider_names = [
            name for name, cfg in ralph_providers.items() if cfg.get("enabled")
        ]
    else:
        provider_names = list(top_level_enabled.keys())

    for name in provider_names:
        provider = top_level_enabled.get(name)
        if provider is None:
            continue
        cfg = ralph_providers.get(name, {})
        live_models = provider.get_models()
        allowlist = cfg.get("models_allowed", []) or []
        blocklist = cfg.get("models_blocked", []) or []
        filtered = _apply_model_filters(live_models, allowlist, blocklist)
        metadata = cfg.get("model_metadata", {}) or {}
        models = []
        for model in filtered:
            entry = metadata.get(model, {}) or {}
            models.append(
                {
                    "id": model,
                    "cost_tier": entry.get("cost_tier"),
                    "best_for_tags": entry.get("best_for_tags", []) or [],
                    "best_for_notes": entry.get("best_for_notes", "") or "",
                }
            )
        enabled.append(
            {
                "name": provider.name,
                "display_name": provider.display_name,
                "models": models,
                "favorites": (cfg.get("favorites") or [])[:3],
            }
        )
    return enabled


def get_ralph_defaults() -> dict:
    """Return default provider/model/iterations for ralph_start."""
    return config.get_ralph_defaults()


def get_summarizer_config() -> dict:
    """Return summarizer provider/model configuration."""
    return config.get_summarizer_config()
