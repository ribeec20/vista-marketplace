"""Vista MCP Server - launches the FastAPI dashboard as a daemon thread.

Claude Code starts this process via .mcp.json (stdio transport).
The web dashboard runs as a daemon thread inside the same process,
modeled on Serena's dashboard.py:run_in_thread() pattern.

Uses fastmcp 3.x (same as claude-code-teams-mcp) for proper Context
injection, ToolError handling, and middleware support.
"""

import asyncio
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

# Ensure vista/ is on sys.path so `from server.*` imports resolve
PLUGIN_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "vendor"))

from server.config import ensure_full_path, get_server_settings  # noqa: E402

ensure_full_path()

from fastmcp import Context, FastMCP  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402
from fastmcp.server.lifespan import lifespan  # noqa: E402
from fastmcp.server.middleware import Middleware  # noqa: E402

from claude_teams import messaging, opencode_client, tasks, teams  # noqa: E402
from claude_teams.models import (  # noqa: E402
    SendMessageResult,
    ShutdownApproved,
    SpawnResult,
    TeammateMember,
)
from claude_teams.opencode_client import OpenCodeAPIError  # noqa: E402
from claude_teams.spawner import (  # noqa: E402
    discover_harness_binary,
    discover_opencode_models,
    kill_tmux_pane,
    spawn_teammate,
    use_tmux_windows,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Harness / client detection (mirrors claude-code-teams-mcp)
# ---------------------------------------------------------------------------
KNOWN_CLIENTS: dict[str, str] = {
    "claude-code": "claude",
    "claude": "claude",
    "opencode": "opencode",
}

_VALID_BACKENDS = frozenset(KNOWN_CLIENTS.values())

# NOTE: Mutated by both app_lifespan and HarnessDetectionMiddleware.
# Safe under stdio (single session).
_lifespan_state: dict[str, Any] = {}

# Reference to the spawn_teammate tool for dynamic description updates
_spawn_tool: Any = None


# ---------------------------------------------------------------------------
# Dashboard thread
# ---------------------------------------------------------------------------
def _check_existing_dashboard(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a Vista dashboard is already responding on host:port."""
    import urllib.request
    import urllib.error

    check_host = host if host != "0.0.0.0" else "localhost"
    url = f"http://{check_host}:{port}/api/services/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _find_free_port(preferred: int, host: str) -> int:
    port = preferred
    while port <= 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                return port
        except OSError:
            port += 1
    raise RuntimeError(f"No free ports found starting from {preferred}")


def _run_uvicorn_in_thread(host: str, port: int) -> threading.Thread:
    import uvicorn

    from server.app import app

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------
def _parse_backends_env(raw: str) -> list[str]:
    if not raw:
        return []
    return list(
        dict.fromkeys(
            b.strip()
            for b in raw.split(",")
            if b.strip() and b.strip() in _VALID_BACKENDS
        )
    )


def _get_lifecycle_opencode_url() -> str | None:
    """Get the OpenCode server URL from the lifecycle manager if it's running."""
    try:
        from server.services.service_lifecycle import service_lifecycle

        if service_lifecycle.is_available("opencode"):
            status = service_lifecycle.get_status("opencode")
            port = status.get("port")
            if port:
                return f"http://127.0.0.1:{port}"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Spawn tool description builder (mirrors reference)
# ---------------------------------------------------------------------------
_SPAWN_TOOL_BASE_DESCRIPTION = (
    "Spawn a new teammate in a tmux {target}. The teammate receives its initial "
    "prompt via inbox and begins working autonomously. Names must be unique "
    "within the team."
)


def _build_spawn_description(
    claude_binary: str | None,
    opencode_binary: str | None,
    opencode_models: list[str],
    opencode_server_url: str | None = None,
    opencode_agents: list[dict] | None = None,
    enabled_backends: list[str] | None = None,
) -> str:
    tmux_target = "window" if use_tmux_windows() else "pane"
    parts = [_SPAWN_TOOL_BASE_DESCRIPTION.format(target=tmux_target)]
    backends = []
    show_claude = claude_binary is not None
    show_opencode = opencode_binary is not None and opencode_server_url is not None
    if enabled_backends is not None:
        show_claude = show_claude and "claude" in enabled_backends
        show_opencode = show_opencode and "opencode" in enabled_backends
    if show_claude:
        backends.append("'claude' (default, models: sonnet, opus, haiku)")
    if show_opencode:
        model_list = (
            ", ".join(opencode_models) if opencode_models else "none discovered"
        )
        backends.append(f"'opencode' (models: {model_list})")
    if backends:
        parts.append(f"Available backends: {'; '.join(backends)}.")
    if show_opencode and opencode_agents:
        agent_lines = [f"  - {a['name']}: {a['description']}" for a in opencode_agents]
        parts.append(
            "Available opencode agents (pass as subagent_type when "
            "backend_type='opencode'):\n" + "\n".join(agent_lines)
        )
    return " ".join(parts)


def _update_spawn_tool(tool: Any, enabled: list[str], state: dict[str, Any]) -> None:
    tool.parameters["properties"]["backend_type"]["enum"] = list(enabled)
    if enabled:
        tool.parameters["properties"]["backend_type"]["default"] = enabled[0]
    tool.description = _build_spawn_description(
        state.get("claude_binary"),
        state.get("opencode_binary"),
        state.get("opencode_models", []),
        state.get("opencode_server_url"),
        state.get("opencode_agents"),
        enabled_backends=enabled,
    )


# ---------------------------------------------------------------------------
# Helpers shared by tool handlers
# ---------------------------------------------------------------------------
def _get_lifespan(ctx: Context) -> dict[str, Any]:
    return ctx.lifespan_context


def _find_teammate(team_name: str, name: str) -> TeammateMember | None:
    config = teams.read_config(team_name)
    for m in config.members:
        if isinstance(m, TeammateMember) and m.name == name:
            return m
    return None


def _push_to_opencode_session(
    server_url: str, member: TeammateMember, text: str
) -> None:
    if (
        member.backend_type != "opencode"
        or not member.opencode_session_id
        or not server_url
    ):
        return
    try:
        opencode_client.send_prompt_async(server_url, member.opencode_session_id, text)
    except OpenCodeAPIError:
        logger.warning(
            "Failed to push message to opencode session %s",
            member.opencode_session_id,
        )


def _cleanup_opencode_session(server_url: str | None, session_id: str | None) -> None:
    if not server_url or not session_id:
        return
    try:
        opencode_client.abort_session(server_url, session_id)
    except OpenCodeAPIError:
        logger.warning("Failed to abort opencode session %s", session_id)
    try:
        opencode_client.delete_session(server_url, session_id)
    except OpenCodeAPIError:
        logger.warning("Failed to delete opencode session %s", session_id)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@lifespan
async def app_lifespan(server):
    global _spawn_tool

    # -- Start dashboard thread (reuse existing if already running) -----------
    settings = get_server_settings()
    host = settings["host"]
    preferred_port = settings["port"]
    dashboard_host = host if host != "0.0.0.0" else "localhost"

    if _check_existing_dashboard(host, preferred_port):
        # Reuse the already-running dashboard — don't spawn another one
        port = preferred_port
        url = f"http://{dashboard_host}:{port}"
        print(f"Vista dashboard already running at {url}", file=sys.stderr)
    else:
        port = _find_free_port(preferred_port, host)
        _run_uvicorn_in_thread(host, port)
        url = f"http://{dashboard_host}:{port}"
        print(f"Vista dashboard started at {url}", file=sys.stderr)

        if settings.get("auto_open_browser", True):
            subprocess.Popen(
                [sys.executable, "-c", f"import webbrowser; webbrowser.open({url!r})"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    # -- Discover backends (mirrors claude-code-teams-mcp) --------------------
    from server.config import get_tools_settings

    tools_settings = get_tools_settings()
    teams_settings = tools_settings.get("teams", {})

    claude_binary = teams_settings.get("claude_binary") or discover_harness_binary(
        "claude"
    )
    opencode_binary = discover_harness_binary("opencode")
    opencode_url = teams_settings.get("opencode_url") or os.environ.get(
        "OPENCODE_SERVER_URL"
    )

    # Use OpenCode from lifecycle manager (started by dashboard lifespan)
    # instead of spawning a separate process
    if opencode_binary and not opencode_url:
        lifecycle_url = _get_lifecycle_opencode_url()
        if lifecycle_url:
            opencode_url = lifecycle_url
            logger.info(
                "Using lifecycle-managed opencode serve at %s",
                opencode_url,
            )

    opencode_models: list[str] = []
    opencode_agents: list[dict] = []
    if opencode_binary:
        try:
            opencode_models = discover_opencode_models(opencode_binary)
        except Exception:
            pass
    if opencode_url:
        try:
            opencode_agents = opencode_client.list_agents(opencode_url)
        except Exception:
            logger.warning("Failed to fetch opencode agents from %s", opencode_url)

    enabled_backends = _parse_backends_env(os.environ.get("CLAUDE_TEAMS_BACKENDS", ""))
    if "opencode" in enabled_backends and not opencode_url:
        enabled_backends.remove("opencode")

    session_id = str(uuid.uuid4())

    _lifespan_state.clear()
    _lifespan_state.update(
        {
            "dashboard_url": url,
            "dashboard_port": port,
            "claude_binary": claude_binary,
            "opencode_binary": opencode_binary,
            "opencode_server_url": opencode_url,
            "opencode_agents": opencode_agents,
            "opencode_models": opencode_models,
            "enabled_backends": enabled_backends,
            "session_id": session_id,
            "active_team": None,
            "client_name": "unknown",
            "client_version": "unknown",
        }
    )

    # -- Update spawn_teammate tool description -------------------------------
    try:
        tool = await mcp.get_tool("spawn_teammate")
        _spawn_tool = tool
        if enabled_backends:
            _update_spawn_tool(tool, enabled_backends, _lifespan_state)
    except Exception:
        pass

    # -- Detect active project from current working directory ------------------
    try:
        from server.services.project_service import ProjectService
        from server.config import set_active_project

        current_dir = Path.cwd()
        all_projects = ProjectService.get_all()
        active_project = None
        for project in all_projects:
            project_path = Path(project.path).resolve()
            if current_dir == project_path or project_path in current_dir.parents:
                active_project = project
                break

        if active_project:
            set_active_project(active_project.id)
            _lifespan_state["active_project_id"] = active_project.id
            _lifespan_state["active_project_name"] = active_project.name
            print(f"Active project detected: {active_project.name}", file=sys.stderr)
    except Exception as e:
        logger.debug("Could not detect active project: %s", e)

    yield _lifespan_state

    # -- Cleanup --------------------------------------------------------------
    # OpenCode process is managed by lifecycle manager (stopped by dashboard shutdown)
    print("Vista MCP server shutting down", file=sys.stderr)


# ---------------------------------------------------------------------------
# Middleware: auto-detect connected client and enable backends
# ---------------------------------------------------------------------------
class HarnessDetectionMiddleware(Middleware):
    async def on_initialize(self, context, call_next):
        _unknown = SimpleNamespace(name="unknown", version="unknown")
        client_info = context.message.params.clientInfo or _unknown
        client_name = client_info.name
        client_version = client_info.version

        result = await call_next(context)

        logger.info("MCP client connected: %s v%s", client_name, client_version)

        native_backend = KNOWN_CLIENTS.get(client_name)
        enabled = _lifespan_state.get("enabled_backends", [])

        if native_backend and native_backend not in enabled:
            if native_backend == "claude" or _lifespan_state.get("opencode_server_url"):
                enabled.append(native_backend)

        if not enabled:
            if _lifespan_state.get("claude_binary"):
                enabled.append("claude")
            if _lifespan_state.get("opencode_binary") and _lifespan_state.get(
                "opencode_server_url"
            ):
                enabled.append("opencode")

        _lifespan_state["enabled_backends"] = enabled
        _lifespan_state["client_name"] = client_name
        _lifespan_state["client_version"] = client_version

        if _spawn_tool:
            _update_spawn_tool(_spawn_tool, enabled, _lifespan_state)

        return result


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="vista-dashboard",
    instructions=(
        "MCP server for the Vista development dashboard. "
        "Manages team creation, teammate spawning, messaging, task tracking, "
        "and ralph planning/build loops."
    ),
    lifespan=app_lifespan,
)
mcp.add_middleware(HarnessDetectionMiddleware())


# # ===========================================================================
# # Teams tools (13 tools — mirrors claude-code-teams-mcp reference)
# # ===========================================================================

# @mcp.tool
# def team_create(
#     team_name: str,
#     ctx: Context,
#     description: str = "",
# ) -> dict:
#     """Create a new agent team. Sets up config and task directories under ~/.claude/.
#     One team per server session. Names must be filesystem-safe
#     (letters, numbers, hyphens, underscores)."""
#     ls = _get_lifespan(ctx)
#     if ls.get("active_team"):
#         raise ToolError(
#             f"Session already has active team: {ls['active_team']}. "
#             "One team per session."
#         )
#     result = teams.create_team(
#         name=team_name,
#         session_id=ls["session_id"],
#         description=description,
#     )
#     ls["active_team"] = team_name
#     return result.model_dump()


# @mcp.tool
# def team_delete(team_name: str, ctx: Context) -> dict:
#     """Delete a team and all its data. Fails if any teammates are still active.
#     Removes both team config and task directories."""
#     try:
#         result = teams.delete_team(team_name)
#     except (RuntimeError, FileNotFoundError) as e:
#         raise ToolError(str(e))
#     _get_lifespan(ctx)["active_team"] = None
#     return result.model_dump()


# @mcp.tool(name="spawn_teammate")
# def spawn_teammate_tool(
#     team_name: str,
#     name: str,
#     prompt: str,
#     ctx: Context,
#     model: str = "sonnet",
#     subagent_type: str = "general-purpose",
#     plan_mode_required: bool = False,
#     backend_type: Literal["claude", "opencode"] = "claude",
# ) -> dict:
#     """Spawn a new teammate in tmux. Description is dynamically updated
#     at startup with available backends and models."""
#     ls = _get_lifespan(ctx)
#     enabled = ls.get("enabled_backends", [])
#     if enabled and backend_type not in enabled:
#         raise ToolError(
#             f"Backend {backend_type!r} is not enabled. Enabled: {enabled}"
#         )

#     opencode_agent = None
#     if backend_type == "opencode":
#         known = {a["name"] for a in ls.get("opencode_agents", [])}
#         opencode_agent = subagent_type if subagent_type in known else "build"

#     try:
#         member = spawn_teammate(
#             team_name=team_name,
#             name=name,
#             prompt=prompt,
#             claude_binary=ls["claude_binary"],
#             lead_session_id=ls["session_id"],
#             model=model,
#             subagent_type=subagent_type,
#             plan_mode_required=plan_mode_required,
#             backend_type=backend_type,
#             opencode_binary=ls["opencode_binary"],
#             opencode_server_url=ls["opencode_server_url"],
#             opencode_agent=opencode_agent,
#         )
#     except (ValueError, OpenCodeAPIError) as e:
#         raise ToolError(str(e))

#     return SpawnResult(
#         agent_id=member.agent_id,
#         name=member.name,
#         team_name=team_name,
#     ).model_dump()


# @mcp.tool
# def send_message(
#     team_name: str,
#     type: Literal[
#         "message",
#         "broadcast",
#         "shutdown_request",
#         "shutdown_response",
#         "plan_approval_response",
#     ],
#     ctx: Context,
#     recipient: str = "",
#     content: str = "",
#     summary: str = "",
#     request_id: str = "",
#     approve: bool | None = None,
#     sender: str = "team-lead",
# ) -> dict:
#     """Send a message to a teammate or respond to a protocol request.
#     Type 'message' sends a DM (requires recipient, summary).
#     Type 'broadcast' sends to all teammates (requires summary).
#     Type 'shutdown_request' asks a teammate to shut down (requires recipient).
#     Type 'shutdown_response' responds to a shutdown request (requires sender, request_id, approve).
#     Type 'plan_approval_response' approves/rejects a plan (requires recipient, request_id, approve)."""
#     oc_url = _get_lifespan(ctx).get("opencode_server_url")

#     try:
#         teams.read_config(team_name)
#     except FileNotFoundError:
#         raise ToolError(f"Team {team_name!r} not found")

#     if type == "message":
#         if not content:
#             raise ToolError("Message content must not be empty")
#         if not summary:
#             raise ToolError("Message summary must not be empty")
#         if not recipient:
#             raise ToolError("Message recipient must not be empty")
#         config = teams.read_config(team_name)
#         member_names = {m.name for m in config.members}
#         if sender not in member_names:
#             raise ToolError(
#                 f"Sender {sender!r} is not a member of team {team_name!r}"
#             )
#         if recipient not in member_names:
#             raise ToolError(
#                 f"Recipient {recipient!r} is not a member of team {team_name!r}"
#             )
#         if sender == recipient:
#             raise ToolError("Cannot send a message to yourself")
#         if sender != "team-lead" and recipient != "team-lead":
#             raise ToolError(
#                 "Teammates can only send direct messages to team-lead"
#             )

#         target_color = None
#         target_member = None
#         for m in config.members:
#             if m.name == recipient and isinstance(m, TeammateMember):
#                 target_color = m.color
#                 target_member = m
#                 break
#         messaging.send_plain_message(
#             team_name, sender, recipient, content,
#             summary=summary, color=target_color,
#         )
#         if target_member and oc_url:
#             _push_to_opencode_session(oc_url, target_member, content)
#         return SendMessageResult(
#             success=True,
#             message=f"Message sent to {recipient}",
#             routing={
#                 "sender": sender,
#                 "target": recipient,
#                 "targetColor": target_color,
#                 "summary": summary,
#                 "content": content,
#             },
#         ).model_dump(exclude_none=True)

#     elif type == "broadcast":
#         if sender != "team-lead":
#             raise ToolError("Only team-lead can send broadcasts")
#         if not summary:
#             raise ToolError("Broadcast summary must not be empty")
#         config = teams.read_config(team_name)
#         count = 0
#         for m in config.members:
#             if isinstance(m, TeammateMember):
#                 messaging.send_plain_message(
#                     team_name, "team-lead", m.name, content,
#                     summary=summary, color=None,
#                 )
#                 if oc_url:
#                     _push_to_opencode_session(oc_url, m, content)
#                 count += 1
#         return SendMessageResult(
#             success=True,
#             message=f"Broadcast sent to {count} teammate(s)",
#         ).model_dump(exclude_none=True)

#     elif type == "shutdown_request":
#         if not recipient:
#             raise ToolError("Shutdown request recipient must not be empty")
#         if recipient == "team-lead":
#             raise ToolError("Cannot send shutdown request to team-lead")
#         config = teams.read_config(team_name)
#         member_names = {m.name for m in config.members}
#         if recipient not in member_names:
#             raise ToolError(
#                 f"Recipient {recipient!r} is not a member of team {team_name!r}"
#             )
#         req_id = messaging.send_shutdown_request(
#             team_name, recipient, reason=content
#         )
#         target_member = _find_teammate(team_name, recipient)
#         if target_member and oc_url:
#             _push_to_opencode_session(
#                 oc_url, target_member,
#                 json.dumps({
#                     "type": "shutdown_request",
#                     "requestId": req_id,
#                     "reason": content,
#                 }),
#             )
#         return SendMessageResult(
#             success=True,
#             message=f"Shutdown request sent to {recipient}",
#             request_id=req_id,
#             target=recipient,
#         ).model_dump(exclude_none=True)

#     elif type == "shutdown_response":
#         config = teams.read_config(team_name)
#         member = None
#         for m in config.members:
#             if isinstance(m, TeammateMember) and m.name == sender:
#                 member = m
#                 break
#         if member is None:
#             raise ToolError(
#                 f"Sender {sender!r} is not a teammate in team {team_name!r}"
#             )
#         if approve:
#             payload = ShutdownApproved(
#                 request_id=request_id,
#                 from_=sender,
#                 timestamp=messaging.now_iso(),
#                 pane_id=member.tmux_pane_id,
#                 backend_type=member.backend_type,
#                 session_id=member.opencode_session_id,
#             )
#             messaging.send_structured_message(
#                 team_name, sender, "team-lead", payload
#             )
#             return SendMessageResult(
#                 success=True,
#                 message=f"Shutdown approved for request {request_id}",
#             ).model_dump(exclude_none=True)
#         else:
#             messaging.send_plain_message(
#                 team_name, sender, "team-lead",
#                 content or "Shutdown rejected",
#                 summary="shutdown_rejected",
#             )
#             return SendMessageResult(
#                 success=True,
#                 message=f"Shutdown rejected for request {request_id}",
#             ).model_dump(exclude_none=True)

#     elif type == "plan_approval_response":
#         if not recipient:
#             raise ToolError("Plan approval recipient must not be empty")
#         config = teams.read_config(team_name)
#         member_names = {m.name for m in config.members}
#         if recipient not in member_names:
#             raise ToolError(
#                 f"Recipient {recipient!r} is not a member of team {team_name!r}"
#             )
#         if approve:
#             messaging.send_plain_message(
#                 team_name, sender, recipient,
#                 '{"type":"plan_approval","approved":true}',
#                 summary="plan_approved",
#             )
#         else:
#             messaging.send_plain_message(
#                 team_name, sender, recipient,
#                 content or "Plan rejected",
#                 summary="plan_rejected",
#             )
#         return SendMessageResult(
#             success=True,
#             message=f"Plan {'approved' if approve else 'rejected'} for {recipient}",
#         ).model_dump(exclude_none=True)

#     raise ToolError(f"Unknown message type: {type}")


# @mcp.tool
# def task_create(
#     team_name: str,
#     subject: str,
#     description: str,
#     active_form: str = "",
#     metadata: dict | None = None,
# ) -> dict:
#     """Create a new task for the team. Tasks get auto-incrementing IDs.
#     Optional metadata dict is stored alongside the task."""
#     try:
#         task = tasks.create_task(
#             team_name, subject, description, active_form, metadata
#         )
#     except ValueError as e:
#         raise ToolError(str(e))
#     return task.model_dump(by_alias=True, exclude_none=True)


# @mcp.tool
# def task_update(
#     team_name: str,
#     task_id: str,
#     status: Literal["pending", "in_progress", "completed", "deleted"] | None = None,
#     owner: str | None = None,
#     subject: str | None = None,
#     description: str | None = None,
#     active_form: str | None = None,
#     add_blocks: list[str] | None = None,
#     add_blocked_by: list[str] | None = None,
#     metadata: dict | None = None,
# ) -> dict:
#     """Update a task's fields. Setting owner auto-notifies the assignee.
#     Setting status to 'deleted' removes the task file.
#     Metadata keys are merged (set a key to null to delete it)."""
#     if owner is not None:
#         try:
#             config = teams.read_config(team_name)
#         except FileNotFoundError:
#             raise ToolError(f"Team {team_name!r} not found")
#         member_names = {m.name for m in config.members}
#         if owner not in member_names:
#             raise ToolError(
#                 f"Owner {owner!r} is not a member of team {team_name!r}"
#             )
#     try:
#         task = tasks.update_task(
#             team_name, task_id,
#             status=status, owner=owner, subject=subject,
#             description=description, active_form=active_form,
#             add_blocks=add_blocks, add_blocked_by=add_blocked_by,
#             metadata=metadata,
#         )
#     except FileNotFoundError:
#         raise ToolError(f"Task {task_id!r} not found in team {team_name!r}")
#     except ValueError as e:
#         raise ToolError(str(e))
#     if owner is not None and task.owner is not None and task.status != "deleted":
#         messaging.send_task_assignment(team_name, task, assigned_by="team-lead")
#     return task.model_dump(by_alias=True, exclude_none=True)


# @mcp.tool
# def task_list(team_name: str) -> list[dict]:
#     """List all tasks for a team with their current status and assignments."""
#     try:
#         result = tasks.list_tasks(team_name)
#     except ValueError as e:
#         raise ToolError(str(e))
#     return [t.model_dump(by_alias=True, exclude_none=True) for t in result]


# @mcp.tool
# def task_get(team_name: str, task_id: str) -> dict:
#     """Get full details of a specific task by ID."""
#     try:
#         task = tasks.get_task(team_name, task_id)
#     except FileNotFoundError:
#         raise ToolError(f"Task {task_id!r} not found in team {team_name!r}")
#     return task.model_dump(by_alias=True, exclude_none=True)


# @mcp.tool
# def read_inbox(
#     team_name: str,
#     agent_name: str,
#     unread_only: bool = False,
#     mark_as_read: bool = True,
# ) -> list[dict]:
#     """Read messages from an agent's inbox. Returns all messages by default.
#     Set unread_only=True to get only unprocessed messages."""
#     try:
#         config = teams.read_config(team_name)
#     except FileNotFoundError:
#         raise ToolError(f"Team {team_name!r} not found")
#     member_names = {m.name for m in config.members}
#     if agent_name not in member_names:
#         raise ToolError(
#             f"Agent {agent_name!r} is not a member of team {team_name!r}"
#         )
#     msgs = messaging.read_inbox(
#         team_name, agent_name,
#         unread_only=unread_only, mark_as_read=mark_as_read,
#     )
#     return [m.model_dump(by_alias=True, exclude_none=True) for m in msgs]


# @mcp.tool
# async def poll_inbox(
#     team_name: str,
#     agent_name: str,
#     timeout_ms: int = 30000,
# ) -> list[dict]:
#     """Poll an agent's inbox for new unread messages, waiting up to timeout_ms.
#     Returns unread messages and marks them as read."""
#     msgs = messaging.read_inbox(
#         team_name, agent_name, unread_only=True, mark_as_read=True
#     )
#     if msgs:
#         return [m.model_dump(by_alias=True, exclude_none=True) for m in msgs]
#     deadline = time.time() + timeout_ms / 1000.0
#     while time.time() < deadline:
#         await asyncio.sleep(0.5)
#         msgs = messaging.read_inbox(
#             team_name, agent_name,
#             unread_only=True, mark_as_read=True,
#         )
#         if msgs:
#             return [
#                 m.model_dump(by_alias=True, exclude_none=True) for m in msgs
#             ]
#     return []


# @mcp.tool
# def read_config(team_name: str) -> dict:
#     """Read the current team configuration including all members."""
#     try:
#         config = teams.read_config(team_name)
#     except FileNotFoundError:
#         raise ToolError(f"Team {team_name!r} not found")
#     return config.model_dump(by_alias=True)


# @mcp.tool
# def force_kill_teammate(
#     team_name: str, agent_name: str, ctx: Context
# ) -> dict:
#     """Forcibly kill a teammate's tmux pane. Use when graceful shutdown
#     is not possible. Kills the pane, removes member from config,
#     and resets their tasks."""
#     oc_url = _get_lifespan(ctx).get("opencode_server_url")
#     config = teams.read_config(team_name)
#     member = None
#     for m in config.members:
#         if isinstance(m, TeammateMember) and m.name == agent_name:
#             member = m
#             break
#     if member is None:
#         raise ToolError(
#             f"Teammate {agent_name!r} not found in team {team_name!r}"
#         )
#     if member.backend_type == "opencode" and member.opencode_session_id:
#         _cleanup_opencode_session(oc_url, member.opencode_session_id)
#     if member.tmux_pane_id:
#         kill_tmux_pane(member.tmux_pane_id)
#     teams.remove_member(team_name, agent_name)
#     tasks.reset_owner_tasks(team_name, agent_name)
#     return {"success": True, "message": f"{agent_name} has been stopped."}


# @mcp.tool
# def process_shutdown_approved(
#     team_name: str, agent_name: str, ctx: Context
# ) -> dict:
#     """Process a teammate's shutdown by removing them from config and
#     resetting their tasks. Call after confirming shutdown_approved in the lead inbox."""
#     if agent_name == "team-lead":
#         raise ToolError("Cannot process shutdown for team-lead")
#     oc_url = _get_lifespan(ctx).get("opencode_server_url")
#     member = _find_teammate(team_name, agent_name)
#     if member is None:
#         raise ToolError(
#             f"Teammate {agent_name!r} not found in team {team_name!r}"
#         )
#     if member.backend_type == "opencode" and member.opencode_session_id:
#         _cleanup_opencode_session(oc_url, member.opencode_session_id)
#     if member.tmux_pane_id:
#         kill_tmux_pane(member.tmux_pane_id)
#     teams.remove_member(team_name, agent_name)
#     tasks.reset_owner_tasks(team_name, agent_name)
#     return {"success": True, "message": f"{agent_name} removed from team."}


# ===========================================================================
# Ralph tools (5 tools — planning/build loops)
# ===========================================================================


@mcp.tool
def ralph_providers() -> dict:
    """Discover available providers and models for ralph loops.

    Returns a JSON object with:
    - providers: list of enabled providers with their available models,
      each model annotated with cost_tier, best_for_tags, and best_for_notes
      so you can choose the right model for the task
    - defaults: default provider, model, and iteration count
    - summarizer: configured summarizer provider and model

    Call this before ralph_start to know which providers and models are available.
    Models are discovered LIVE from provider CLIs (same as the standalone ralph scripts).
    Use the cost_tier and best_for metadata to select the best model for your task.
    """
    from server.config import get_ralph_defaults, get_summarizer_config
    from server.services.provider_service import get_ralph_providers

    return {
        "providers": get_ralph_providers(),
        "defaults": get_ralph_defaults(),
        "summarizer": get_summarizer_config(),
        "dashboard_url": _lifespan_state.get("dashboard_url"),
    }


@mcp.tool
def ralph_start(
    slug: str,
    mode: str,
    task_description: str,
    provider: str | None = None,
    model: str | None = None,
    iterations: int | None = None,
    sandbox: bool = False,
) -> dict:
    """Start a ralph loop as a background process.

    Creates a working directory at .vista/ralph/{slug}/ and spawns a loop subprocess.
    Returns immediately with a job ID. Use ralph_status to poll progress.

    :param slug: Short identifier for this job (lowercase, hyphens ok)
    :param mode: Loop mode - "plan" or "build"
    :param task_description: What the loop should accomplish (written to task.md)
    :param provider: Provider name (e.g. "claude", "opencode"). Uses default if omitted.
    :param model: Model name (e.g. "opus", "sonnet"). Uses default if omitted.
    :param iterations: Max loop iterations. Uses default if omitted.
    :param sandbox: Run in Docker sandbox container (default False).
    """
    from server.config import get_ralph_defaults
    from server.services.provider_service import (
        get_provider_by_name,
        get_ralph_providers,
    )
    from server.services.ralph_service import ralph_service

    defaults = get_ralph_defaults()
    provider = provider or defaults["provider"]
    model = model or defaults["model"]
    iterations = iterations or defaults["iterations"]

    if mode not in ("plan", "build"):
        raise ToolError(f"Invalid mode: {mode}. Must be 'plan' or 'build'.")

    provider_obj = get_provider_by_name(provider)
    if not provider_obj:
        raise ToolError(f"Provider not found: {provider}")

    available = {p.get("name"): p for p in get_ralph_providers()}
    provider_entry = available.get(provider)
    if not provider_entry:
        raise ToolError(f"Provider not available for ralph: {provider}")

    model_entries = provider_entry.get("models", []) or []
    available_models: list[str] = []
    for entry in model_entries:
        if isinstance(entry, dict):
            if "id" in entry and entry["id"]:
                available_models.append(entry["id"])
            elif "name" in entry and entry["name"]:
                available_models.append(entry["name"])
        elif isinstance(entry, str):
            available_models.append(entry)

    if available_models and model not in available_models:
        raise ToolError(
            f"Model not available for provider {provider}: {model}. "
            f"Available models: {', '.join(available_models)}"
        )
    if not available_models:
        raise ToolError(f"No models available for provider: {provider}")

    project_root = Path.cwd()
    existing_job_dir = project_root / ".vista" / "ralph" / slug
    if existing_job_dir.is_dir():
        existing_job = ralph_service._load_job_json(existing_job_dir)
        if existing_job and existing_job.get("status") == "running":
            raise ToolError("Active job already running for this slug")
    try:
        job = ralph_service.create_job(
            project_root,
            slug,
            mode,
            task_description,
            provider_obj,
            model,
            iterations,
            sandbox=sandbox,
        )
    except Exception as e:
        raise ToolError(str(e))
    working_dir = project_root / ".vista" / "ralph" / job.get("slug", slug)
    result = dict(job)
    result["working_dir"] = str(working_dir)
    return result


@mcp.tool
def ralph_status(job_id: str) -> dict:
    """Check the status and progress of a ralph job.

    Returns lightweight status information. For a detailed AI-generated summary,
    use ralph_summary instead.

    :param job_id: The job ID returned by ralph_start
    """
    from server.services.ralph_service import ralph_service

    project_root = Path.cwd()
    job = ralph_service.get_job_status(project_root, job_id)
    if not job:
        raise ToolError(f"Job not found: {job_id}")

    elapsed_time = None
    started_at = job.get("started_at") or job.get("created_at")
    if isinstance(started_at, str):
        try:
            started_dt = datetime.fromisoformat(started_at)
            elapsed_time = int(
                (datetime.now(timezone.utc) - started_dt).total_seconds()
            )
        except ValueError:
            elapsed_time = None

    last_progress = job.get("progress_tail") or []
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "current_iteration": job.get("current_iteration", 0),
        "total_iterations": job.get("iterations", 0),
        "last_progress_lines": last_progress,
        "elapsed_time": elapsed_time,
        "progress_tail": last_progress,
        "slug": job.get("slug"),
        "mode": job.get("mode"),
        "provider": job.get("provider"),
        "model": job.get("model"),
        "pid": job.get("pid"),
        "error": job.get("error"),
    }


@mcp.tool
def ralph_summary(job_id: str) -> dict:
    """Get an AI-generated summary of a ralph job's artifacts.

    Spawns a summarizer agent that reads the job's progress.txt,
    IMPLEMENTATION_PLAN.md, and git log, then returns a structured summary.
    Works for both running and completed jobs.

    This is more expensive than ralph_status - use it when you need
    a detailed understanding of what the loop accomplished or is working on.

    :param job_id: The job ID returned by ralph_start
    """
    from server.services.summarizer_service import summarizer_service

    project_root = Path.cwd()
    return summarizer_service.run_summarizer(project_root, job_id)


@mcp.tool
def ralph_stop(job_id: str) -> dict:
    """Stop a running ralph loop.

    Sends a termination signal to the loop subprocess and updates the job status.

    :param job_id: The job ID returned by ralph_start
    """
    from server.services.ralph_service import ralph_service

    project_root = Path.cwd()
    job = ralph_service.stop_job(project_root, job_id)
    if not job:
        raise ToolError(f"Job not found: {job_id}")
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "message": "Job stopped",
        "slug": job.get("slug"),
        "provider": job.get("provider"),
        "model": job.get("model"),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
