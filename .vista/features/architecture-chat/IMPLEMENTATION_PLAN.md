# Implementation Plan: Architecture Chat (v2)

## Build Status (Iteration 2 — 2026-02-12)

### DONE: Phase 1 — Service Lifecycle Manager
- `vista/server/services/service_lifecycle.py` (426 lines): implemented lifecycle manager, health checks, Windows-safe process handling, bun discovery.
- `vista/server/routes/service_status.py` (13 lines): `/api/services/health` endpoint.
- `vista/server/app.py` (346 lines): lifespan wiring for lifecycle manager + provider cleanup.
- `vista/server/config.py` (314 lines): `get_chat_settings()` added for ports.

### DONE: Phase 2 — Provider Router (Claude WebSocket + OpenCode SSE)
- `vista/server/services/claude_ws_client.py` (152 lines): Companion WS client with permission auto-approve.
- `vista/server/services/opencode_client.py` (142 lines): REST + SSE client, async prompt flow.
- `vista/server/services/provider_router.py` (169 lines): session map, backend session creation, routing.
- `vista/server/routes/chat_sessions.py` (400 lines): ProviderRouter streaming path only, 503 when backend unavailable.
- `vista/server/models/chat_session.py` (110 lines): `backend_session_id` persisted.

### DONE: Phase 3 — Diagram Watcher Upgrade
- `vista/server/services/diagram_watcher.py` (265 lines): watchdog-based observer, debounce, manifest regeneration.

### DONE: Phase 4 — Context Assembler Refactor
- `vista/server/services/context_assembler.py` (92 lines): prompt assembly extracted.
- `vista/tests/test_context_assembler.py` (129 lines): prompt assembly tests.

### DONE: Phase 5 — Model Discovery
- `vista/server/services/provider_service.py` (440 lines): OpenCode models from live server with CLI fallback.
- `vista/server/routes/providers.py`: exposes `available` based on lifecycle status.

### DONE: Phase 6 — Frontend Changes
- `vista/server/views/architecture.html` (1458 lines): service status bar, provider disabling when offline, removed keep-alive UI.

### DONE: Phase 7 — Companion Fork Verification
- No changes required in `vista/companion/` (verified in code).

### DONE: Phase 8 — Integration and Wiring
- `vista/mcp_server.py` (1088 lines): uses lifecycle-managed OpenCode serve if available.
- `requirements.txt` (11 lines): add `websockets`, `watchdog`.

### Deviations / Notes
- `vista/server/services/chat_service.py` now a deprecated placeholder (legacy CLI removed).
- `server/routes/chat.py` and `server/services/keepalive_manager.py` already removed in earlier iteration; session-based streaming is now the only path.
- `vista/tests/test_architecture.py` updated to validate ContextAssembler prompt behavior instead of legacy ChatService.

## Build Status (Iteration 3 — 2026-02-12)

### DONE: Test Stabilization and Ralph Lifecycle Fixes
- `vista/server/services/ralph_service.py`: stabilize stop/status transitions, Windows process identity checks, duplicate slug directory handling.
- `vista/server/config.py`: pytest env override behavior aligned with config tests.
- `vista/mcp_server.py`: ralph_start rejects duplicate running job slug.
- `vista/tests/integration/test_mcp_tools.py`: patched running-status checks for expected process validation.
- `vista/tests/integration/test_ralph_lifecycle.py`: patched running-status checks and null guard.
- `vista/tests/test_ralph_service.py`: stale PID stop assertion aligned with updated behavior.

### Tests
- `python -m pytest tests/ -q` (390 passed, 1 skipped)

## Overview

Replace the subprocess-based CLI chat with two protocol-native provider backends:
1. **Claude** via Companion fork's WebSocket bridge (`vista/companion/`)
2. **OpenCode** via `opencode serve` HTTP REST + SSE streaming

Vista's FastAPI server remains the single hub. The existing Jinja2/vanilla JS frontend is kept; Companion's React UI is NOT used. One active chat session at a time, provider locked per session.

### Key Corrections from v1 Plan

- Companion's browser WebSocket message type is `user_message` (not `user`) per `session-types.ts`
- Companion uses `--permission-mode` flag (not `--dangerously-skip-permissions`)
- OpenCode streaming uses `prompt_async` + SSE `/event` (not blocking `message`)
- `mcp_server.py` already has `_start_opencode_serve()` — consolidate, don't duplicate
- ChatSession model needs `backend_session_id` field for session mapping
- Windows needs `CREATE_NO_WINDOW` for all subprocess spawning

---

## Phase 1: Service Lifecycle Manager

**Goal**: Auto-start/stop/restart Companion and OpenCode as managed services.

### New File: `server/services/service_lifecycle.py`

```python
import asyncio
import logging
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

_IS_WINDOWS = platform.system() == "Windows"
log = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    RESTARTING = "restarting"


@dataclass
class ServiceConfig:
    name: str                       # "companion" | "opencode"
    command: list[str]              # e.g. ["bun", "web/server/index.ts"]
    cwd: str                        # working directory
    preferred_port: int
    health_url_template: str        # e.g. "http://127.0.0.1:{port}/api/sessions"
    env: dict[str, str] = field(default_factory=dict)
    prerequisite_binary: str = ""   # binary name to check in PATH
    max_restarts: int = 5
    health_timeout: float = 2.0     # seconds per health check request
    startup_timeout: float = 30.0   # max seconds to wait for startup
    health_interval: float = 10.0   # seconds between periodic health checks
    consecutive_failures_threshold: int = 3


@dataclass
class ServiceInstance:
    config: ServiceConfig
    status: ServiceStatus = ServiceStatus.STOPPED
    port: int = 0
    pid: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    started_at: Optional[float] = None
    restart_count: int = 0
    consecutive_health_failures: int = 0
    last_error: str = ""


class ServiceLifecycleManager:
    """Manages Companion and OpenCode processes alongside Vista."""

    def __init__(self):
        self._services: dict[str, ServiceInstance] = {}
        self._health_task: Optional[asyncio.Task] = None

    def register(self, config: ServiceConfig) -> None:
        """Register a service configuration."""
        self._services[config.name] = ServiceInstance(config=config)

    async def start(self, name: str) -> bool:
        """Start a single service. Returns True if successfully started."""
        ...

    async def stop(self, name: str) -> None:
        """Gracefully stop a service (SIGTERM, wait 5s, force kill)."""
        ...

    async def restart(self, name: str) -> bool:
        """Stop then start with backoff."""
        ...

    async def start_all(self) -> None:
        """Start all registered services (skip if prerequisite missing)."""
        ...

    async def stop_all(self) -> None:
        """Stop all running services."""
        ...

    def get_status(self, name: str) -> dict:
        """Return status snapshot for a service."""
        ...

    def get_all_status(self) -> list[dict]:
        """Return status for all services."""
        ...

    def is_available(self, name: str) -> bool:
        """True if service is running and healthy."""
        ...
```

**State machine** (matches `state-service-lifecycle.mmd`):
- `Stopped -> Starting -> Running -> Stopping -> Stopped`
- `Running -> Error -> Restarting -> Starting`
- `Error -> Stopped` (max retries exceeded)

**Periodic health checker**: asyncio task, every 10s, 3 consecutive failures triggers restart with exponential backoff (1s, 2s, 4s, 8s, 16s cap).

**Port assignment**: Use `_find_free_port()` pattern already in `mcp_server.py`.

**Process spawning on Windows**:
```python
kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if _IS_WINDOWS else {}
```

**Process tree kill on Windows**:
```python
subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], ...)
```

### Companion Service Config

```python
COMPANION_DIR = config.PLUGIN_ROOT / "companion"

ServiceConfig(
    name="companion",
    command=["bun", "run", str(COMPANION_DIR / "web" / "server" / "index.ts")],
    cwd=str(COMPANION_DIR),
    preferred_port=3457,
    health_url_template="http://127.0.0.1:{port}/api/sessions",
    env={"PORT": "{port}", "NODE_ENV": "production"},
    prerequisite_binary="bun",
)
```

**Bun discovery on Windows**: Check standard install paths:
```python
candidates = [
    Path(os.environ.get("USERPROFILE", "")) / ".bun" / "bin" / "bun.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "bun" / "bun.exe",
]
```

### OpenCode Service Config

```python
ServiceConfig(
    name="opencode",
    command=["opencode", "serve", "--port", "{port}"],
    cwd=str(Path.cwd()),  # project root
    preferred_port=4096,
    health_url_template="http://127.0.0.1:{port}/global/health",
    prerequisite_binary="opencode",
)
```

### Changes to Existing Files

| File | Change |
|------|--------|
| `server/app.py` | Import lifecycle manager, call `start_all()`/`stop_all()` in lifespan. Remove direct import of `keepalive_manager`. |
| `server/config.py` | Add `get_chat_settings()` returning companion/opencode port config, Bun binary path. |
| `mcp_server.py` | Remove `_start_opencode_serve()` inline logic. Import and delegate to lifecycle manager via shared singleton. |

### New Route: `server/routes/service_status.py`

```python
@router.get("/api/services/health")
async def service_health():
    return {"services": service_lifecycle.get_all_status()}
```

### Tests: `tests/test_service_lifecycle.py`

TDD candidate. Test state transitions, backoff calculation, max retry cap, prerequisite check skip logic.

---

## Phase 2: Provider Router (Claude WebSocket + OpenCode SSE)

**Goal**: Replace subprocess-based `ChatService` with protocol-native provider backends.

### New File: `server/services/provider_router.py`

```python
class ProviderRouter:
    """Routes chat messages to the correct backend based on provider type."""

    def __init__(self, lifecycle: ServiceLifecycleManager):
        self._lifecycle = lifecycle
        self._claude_client: Optional[ClaudeWSClient] = None
        self._opencode_client: Optional[OpenCodeClient] = None
        # Vista session_id -> {provider, backend_session_id, ...}
        self._session_map: dict[str, dict] = {}

    async def create_backend_session(
        self, provider: str, model: str, session_id: str, cwd: str
    ) -> str:
        """Create a backend session and return the backend session ID."""
        ...

    async def send_message(
        self, provider: str, model: str, prompt: str,
        session_id: str, cwd: str
    ) -> AsyncGenerator[dict, None]:
        """Yield streaming events: {type: "token"|"done"|"error", ...}"""
        ...

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up backend session when Vista session is deleted."""
        ...

    async def cleanup_all(self) -> None:
        """Clean up all backend sessions on shutdown."""
        ...
```

### Claude Provider: WebSocket Bridge to Companion

**New File**: `server/services/claude_ws_client.py`

```python
import websockets

class ClaudeWSClient:
    """WebSocket client connecting to Companion's /ws/browser/{session_id} endpoint."""

    def __init__(self, companion_base_url: str):
        self.base_url = companion_base_url  # "http://127.0.0.1:3457"
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._session_id: Optional[str] = None

    async def create_session(self, model: str, cwd: str) -> str:
        """POST /api/sessions/create -> returns Companion session ID.

        Request body:
        {
            "model": model,
            "permissionMode": "dangerously-skip-permissions",
            "cwd": cwd,
            "backend": "claude"
        }

        Companion's CliLauncher.launch() spawns Claude CLI with:
        --sdk-url ws://localhost:{port}/ws/cli/{sessionId}
        --print --output-format stream-json --input-format stream-json
        --verbose --permission-mode dangerously-skip-permissions
        --model {model} -p ""
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/sessions/create",
                json={
                    "model": model,
                    "permissionMode": "dangerously-skip-permissions",
                    "cwd": cwd,
                    "backend": "claude",
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["sessionId"]

    async def connect(self, session_id: str) -> None:
        """Connect to ws://{host}:{port}/ws/browser/{session_id}"""
        ws_url = self.base_url.replace("http://", "ws://")
        self._ws = await websockets.connect(
            f"{ws_url}/ws/browser/{session_id}",
            max_size=10 * 1024 * 1024,  # 10MB for large responses
        )
        self._session_id = session_id
        # Wait for session_init message
        init_msg = json.loads(await self._ws.recv())
        if init_msg.get("type") != "session_init":
            # May receive message_history first on reconnect
            pass

    async def send_message(self, text: str) -> AsyncGenerator[dict, None]:
        """Send user message and yield streaming events.

        Send (matches BrowserOutgoingMessage from session-types.ts):
        {"type": "user_message", "content": text}

        Receive and translate (BrowserIncomingMessage types):
        - {"type": "stream_event", "event": {"type": "content_block_delta",
           "delta": {"type": "text_delta", "text": "tok"}}} -> {"type": "token", "text": "tok"}
        - {"type": "assistant", "message": {...}} -> extract text content
        - {"type": "result", "data": {...}} -> {"type": "done", "content": full_text}
        - {"type": "permission_request", ...} -> auto-approve immediately
        - {"type": "error", ...} -> {"type": "error", "detail": "..."}
        """
        await self._ws.send(json.dumps({
            "type": "user_message",
            "content": text,
        }))

        full_text = []
        async for raw in self._ws:
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "stream_event":
                event = msg.get("event", {})
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text_chunk = delta.get("text", "")
                        if text_chunk:
                            full_text.append(text_chunk)
                            yield {"type": "token", "text": text_chunk}

            elif msg_type == "assistant":
                # Complete assistant message - text already streamed above
                pass

            elif msg_type == "result":
                # Turn complete
                yield {
                    "type": "result",
                    "content": "".join(full_text),
                    "cost": msg.get("data", {}).get("total_cost_usd"),
                    "duration_ms": msg.get("data", {}).get("duration_ms"),
                }
                yield {"type": "done", "content": "".join(full_text)}
                return

            elif msg_type == "permission_request":
                # Auto-approve all tool calls
                request = msg.get("request", {})
                await self._ws.send(json.dumps({
                    "type": "permission_response",
                    "request_id": request.get("request_id", ""),
                    "behavior": "allow",
                    "updated_input": request.get("input", {}),
                }))

            elif msg_type == "error":
                yield {"type": "error", "detail": msg.get("message", "Unknown error")}
                return

            elif msg_type == "cli_disconnected":
                yield {"type": "error", "detail": "Claude CLI disconnected"}
                return

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def delete_session(self, session_id: str) -> None:
        """DELETE /api/sessions/{session_id}"""
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{self.base_url}/api/sessions/{session_id}",
                timeout=10.0,
            )
```

**Key protocol details verified from `session-types.ts`**:
- Browser sends `user_message` (not `user`)
- Browser receives `stream_event` with nested `event.delta.text`
- `permission_response` uses `behavior: "allow"` (not `approved: true`)
- `result` message wraps data in `data` field

### OpenCode Provider: HTTP REST + SSE

**New File**: `server/services/opencode_client.py`

```python
import httpx

class OpenCodeClient:
    """Async client for OpenCode's REST API + SSE streaming."""

    def __init__(self, base_url: str, auth: tuple[str, str] | None = None):
        self.base_url = base_url  # "http://127.0.0.1:4096"
        self._auth = auth  # (username, password) for Basic Auth if set

    def _client_kwargs(self) -> dict:
        kwargs = {"timeout": 30.0}
        if self._auth:
            kwargs["auth"] = self._auth
        return kwargs

    async def create_session(self, title: str) -> str:
        """POST /session -> returns session ID"""
        async with httpx.AsyncClient(**self._client_kwargs()) as client:
            resp = await client.post(
                f"{self.base_url}/session",
                json={"title": title, "permission": ["read", "write"]},
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def send_message_streaming(
        self, session_id: str, text: str,
        model: dict | None = None,
    ) -> AsyncGenerator[dict, None]:
        """POST /session/{id}/prompt_async + subscribe to GET /event SSE.

        1. Subscribe to SSE first (so we don't miss events)
        2. Send prompt_async
        3. Yield translated events until session.idle

        Translate events:
        - message.part.updated -> {"type": "token", "text": delta_text}
        - session.idle -> {"type": "done", "content": full_text}
        - session.error -> {"type": "error", "detail": msg}
        """
        full_text = []
        event_type = ""

        async with httpx.AsyncClient(**self._client_kwargs()) as client:
            # Start SSE subscription
            async with client.stream(
                "GET", f"{self.base_url}/event",
                headers={"Accept": "text/event-stream"},
                timeout=httpx.Timeout(connect=5.0, read=300.0, write=5.0, pool=5.0),
            ) as sse_response:
                # Send the async prompt
                await client.post(
                    f"{self.base_url}/session/{session_id}/prompt_async",
                    json={
                        "parts": [{"type": "text", "text": text}],
                        **({"model": model} if model else {}),
                    },
                )

                # Process SSE events
                async for line in sse_response.aiter_lines():
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                    elif line.startswith("data: ") and event_type:
                        data = json.loads(line[6:])
                        props = data.get("properties", {})

                        if event_type == "message.part.updated":
                            text_delta = props.get("text", "")
                            if text_delta:
                                full_text.append(text_delta)
                                yield {"type": "token", "text": text_delta}

                        elif event_type == "session.idle":
                            yield {"type": "done", "content": "".join(full_text)}
                            return

                        elif event_type == "session.error":
                            yield {
                                "type": "error",
                                "detail": props.get("error", "Unknown error"),
                            }
                            return

                        event_type = ""

    async def get_providers(self) -> list[dict]:
        """GET /config/providers -> provider/model list"""
        async with httpx.AsyncClient(**self._client_kwargs()) as client:
            resp = await client.get(f"{self.base_url}/config/providers")
            resp.raise_for_status()
            return resp.json()

    async def delete_session(self, session_id: str) -> None:
        async with httpx.AsyncClient(**self._client_kwargs()) as client:
            await client.delete(f"{self.base_url}/session/{session_id}")

    async def abort_session(self, session_id: str) -> None:
        async with httpx.AsyncClient(**self._client_kwargs()) as client:
            await client.post(f"{self.base_url}/session/{session_id}/abort")
```

**Auth**: If `OPENCODE_SERVER_PASSWORD` env var is set, construct Basic Auth tuple:
```python
auth = ("opencode", os.environ["OPENCODE_SERVER_PASSWORD"]) if os.environ.get("OPENCODE_SERVER_PASSWORD") else None
```

### Session Mapping

The `ProviderRouter` maintains:
```python
_session_map: dict[str, dict] = {}
# Key: Vista session_id
# Value: {
#     "provider": "claude" | "opencode",
#     "backend_session_id": "companion-uuid" | "opencode-session-id",
#     "model": str,
#     "cwd": str,
# }
```

The `ChatSession` model is also extended with a `backend_session_id` field for persistence across server restarts.

### Changes to Existing Files

| File | Change |
|------|--------|
| `server/services/chat_service.py` | **Rewrite**: Remove all subprocess logic. Keep `build_prompt()` as static (backward compat). Delegate streaming to `ProviderRouter`. |
| `server/routes/chat_sessions.py` | Replace `_stream_response()` to use `ProviderRouter`. Remove `keepalive_manager` imports and all persistent-mode tmux logic. Replace `_stream_response_keepalive()` entirely. |
| `server/routes/chat.py` | **Remove**: Blocking `/api/projects/{project_id}/chat` endpoint is superseded by session-based streaming. |
| `server/services/keepalive_manager.py` | **Remove**: tmux-based approach fully replaced by WebSocket/SSE. |
| `server/models/chat_session.py` | Add `backend_session_id: Optional[str] = None` field. Update `to_dict()`/`from_dict()`. |

### Tests: `tests/test_provider_router.py`

TDD candidate. Test:
- Routing to correct backend based on provider name
- Event translation for Claude WebSocket messages
- Event translation for OpenCode SSE events
- Auto-approve flow for permission_request
- Session map lifecycle (create, send, cleanup)
- Error handling (backend down, connection drop)

---

## Phase 3: Diagram Watcher Upgrade (Polling -> watchdog)

**Goal**: Replace 2s polling with instant filesystem event detection.

### Changes to: `server/services/diagram_watcher.py`

Replace internal polling with `watchdog.observers.Observer`:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

class _DiagramEventHandler(FileSystemEventHandler):
    """Handles filesystem events for .mmd/.drawio files."""

    def __init__(self, key: str, watcher: 'DiagramWatcher'):
        self.key = key
        self.watcher = watcher
        self._debounce_timers: dict[str, asyncio.TimerHandle] = {}

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_diagram(event.src_path):
            self._debounced_notify(event.src_path, "diagram_added")

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_diagram(event.src_path):
            self._debounced_notify(event.src_path, "diagram_changed")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_diagram(event.src_path):
            self._debounced_notify(event.src_path, "diagram_removed")

    def _is_diagram(self, path: str) -> bool:
        return Path(path).suffix in {".mmd", ".drawio"}

    def _debounced_notify(self, path: str, event_type: str, delay: float = 0.1):
        """Debounce rapid events (100ms) to coalesce file saves."""
        ...
```

**Key changes from existing code**:
- Replace `_poll_loop()` with `Observer` per watched directory
- `subscribe()` creates an Observer if one doesn't exist for that key
- `unsubscribe()` stops the Observer when all subscribers leave
- Add 100ms debounce to coalesce rapid file changes
- `_update_manifest()` scans arch dir and regenerates `_arch.json`

### Manifest Auto-Updater

On `diagram_added` or `diagram_removed` events:
```python
def _update_manifest(self, key: str, arch_dir: Path) -> None:
    """Scan arch dir for .mmd files and regenerate _arch.json."""
    entries = []
    for f in sorted(arch_dir.iterdir()):
        if f.is_file() and f.suffix in self.WATCH_EXTENSIONS:
            name = f.stem.replace("-", " ").replace("_", " ").title()
            diagram_type = self._detect_diagram_type(f)
            entries.append({
                "name": name,
                "file": f.name,
                "type": "mermaid" if f.suffix == ".mmd" else "drawio",
                "diagramType": diagram_type,
            })
    manifest_path = arch_dir / "_arch.json"
    manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
```

### Dependencies

Add `watchdog` to requirements. Note: watchdog has a polling fallback on platforms without native support, but Windows `ReadDirectoryChangesW` is well-supported.

### Tests: `tests/test_diagram_watcher.py`

TDD candidate. Test:
- Create/edit/delete events fire correctly
- Manifest auto-update on add/remove
- Debounce behavior (rapid saves coalesced)
- Observer lifecycle (start/stop per directory)

---

## Phase 4: Context Assembler Refactor

**Goal**: Extract prompt assembly from `ChatService.build_prompt()` into a clean, testable module.

### New File: `server/services/context_assembler.py`

```python
class ContextAssembler:
    """Assembles the full prompt from diagram context, history, and user message."""

    @staticmethod
    def build_system_prompt(
        arch_dir: str,
        specs_dir: str,
        project_root: str,
    ) -> str:
        """Build system prompt scoping AI to arch/ and specs/ directories.

        Existing logic from ChatService.build_prompt() preserved:
        - Architecture documentation assistant role
        - Read access to project root for context
        - Write access scoped to arch/ directory (.mmd files only)
        - Read access to specs/ directory
        """
        return (
            "You are an architecture documentation assistant.\n"
            f"You can read files anywhere in the project for context: {project_root}\n"
            f"You can read specification files in: {specs_dir}\n"
            f"You ONLY edit .mmd diagram files in the arch directory: {arch_dir}\n"
            "Do NOT edit source code or any files outside the arch directory.\n"
            "When asked to modify diagrams, edit the .mmd files directly.\n"
            "Provide clear, concise feedback on the provided diagrams.\n"
            "When discussing diagrams, be specific and reference node names and connections."
        )

    @staticmethod
    def build_full_prompt(
        message: str,
        context: str | None = None,
        history: list[dict] | None = None,
        system_prompt: str = "",
    ) -> str:
        """Assemble the complete prompt.

        Structure:
        1. System prompt (role + file access instructions)
        2. Diagram context (attached files + selected elements)
        3. Conversation history
        4. Current user message
        """
        parts = []
        if system_prompt:
            parts.append(system_prompt)
            parts.append("")

        if context:
            parts.append("--- DIAGRAM CONTEXT ---")
            parts.append(context)
            parts.append("--- END CONTEXT ---")
            parts.append("")

        if history:
            parts.append("--- CONVERSATION HISTORY ---")
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role.upper()}: {content}")
            parts.append("--- END HISTORY ---")
            parts.append("")

        parts.append(f"USER: {message}")
        parts.append("")
        parts.append("ASSISTANT:")

        return "\n".join(parts)

    @staticmethod
    def get_diagram_context(
        arch_dir: str,
        attached_files: list[str],
        selected_elements: list[dict] | None = None,
    ) -> str:
        """Read attached diagram files and format as context block."""
        parts = []
        for filename in attached_files:
            filepath = Path(arch_dir) / filename
            if filepath.is_file():
                content = filepath.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n```mermaid\n{content}\n```")

        if selected_elements:
            parts.append("\n## Selected Elements")
            for elem in selected_elements:
                parts.append(f"- {elem.get('id', 'unknown')}: {elem.get('label', '')}")

        return "\n\n".join(parts)
```

### Changes to Existing Files

| File | Change |
|------|--------|
| `server/services/chat_service.py` | Replace `build_prompt()` body with calls to `ContextAssembler` methods |
| `server/routes/chat_sessions.py` | Import from `context_assembler` instead of `chat_service` for prompt building |

### Tests: `tests/test_context_assembler.py`

TDD candidate. Test prompt assembly with various combinations of:
- System prompt with/without arch_dir and specs_dir
- Context with attached files and selected elements
- History with multiple messages
- Edge cases (empty context, no history, unicode content)

---

## Phase 5: Model Discovery

**Goal**: Dynamic model lists from both providers using running backend services.

### Changes to: `server/services/provider_service.py`

Extend `OpenCodeProvider.get_models()`:

```python
class OpenCodeProvider(Provider):
    def get_models(self) -> list[str]:
        """Try running OpenCode server first, fall back to CLI."""
        # 1. Try HTTP: GET http://localhost:{port}/config/providers
        lifecycle = _get_lifecycle_manager()
        if lifecycle and lifecycle.is_available("opencode"):
            status = lifecycle.get_status("opencode")
            port = status.get("port")
            if port:
                try:
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

        # 2. Fall back to CLI discovery (existing logic)
        return self._get_models_from_cli()
```

Claude provider keeps static list: `["opus", "sonnet", "haiku"]`.

### Changes to: `server/routes/providers.py`

Ensure existing `/api/providers` endpoint also exposes `available` status based on lifecycle health.

---

## Phase 6: Frontend Changes

**Goal**: Update `architecture.html` chat panel for new streaming backend.

### Changes to: `server/views/architecture.html`

The frontend SSE pattern is **preserved unchanged** -- Vista's SSE endpoint (`/api/projects/{id}/chat/sessions/{sid}/stream`) bridges to the backend WebSocket/SSE. Frontend doesn't know about Companion or OpenCode directly.

**Specific changes needed**:

1. **Service status indicators**: Add status bar below provider dropdown:
   ```html
   <div id="service-status" class="flex gap-2 px-3 py-1 text-xs">
     <span class="service-dot" data-service="companion">
       <span class="dot"></span> Claude Bridge
     </span>
     <span class="service-dot" data-service="opencode">
       <span class="dot"></span> OpenCode
     </span>
   </div>
   ```
   Poll `GET /api/services/health` every 10s. Color dots green/red.

2. **Provider availability**: Disable providers whose backend service is down:
   ```javascript
   function updateProviderAvailability(healthData) {
       const select = document.getElementById('provider-select');
       for (const opt of select.options) {
           const svcName = opt.value === 'claude' ? 'companion' : opt.value;
           const svc = healthData.services.find(s => s.name === svcName);
           opt.disabled = svc && svc.status !== 'running';
       }
   }
   ```

3. **Toast notifications**: Show toast when service goes down/recovers.

4. **Remove persistent mode UI**: The `chatMode` toggle between "oneshot" and "persistent" is removed. All chat goes through the ProviderRouter. The frontend always sends `mode: "oneshot"` (the backend handles the persistent WebSocket/SSE connections transparently).

5. **Dynamic model fetch**: Already exists via `fetchModels()`. No change needed.

6. **Diagram live updates**: **No changes needed** -- the existing SSE handlers for `diagram_changed`/`diagram_added`/`diagram_removed` work unchanged. Only the backend watcher implementation changes.

---

## Phase 7: Companion Fork Modifications

**Goal**: Verify Companion works as-is for Vista's backend-only use case.

### Analysis: Zero Changes Needed

After reading the Companion source code (`index.ts`, `cli-launcher.ts`, `routes.ts`, `session-types.ts`, `ws-bridge.ts`):

**No changes to Companion fork required.** Vista interacts through:
1. `POST /api/sessions/create` -- Create session + spawn Claude CLI
   - Body: `{model, permissionMode, cwd, backend: "claude"}`
   - Companion's `CliLauncher.launch()` handles everything
2. `ws://localhost:{port}/ws/browser/{sessionId}` -- WebSocket for bidirectional message exchange
   - Send: `{type: "user_message", content: "..."}`
   - Receive: `stream_event`, `assistant`, `result`, `permission_request`, etc.
3. `DELETE /api/sessions/{sessionId}` -- Clean up session + kill CLI process

**Key observations from source code**:
- Companion reads `PORT` env var (`index.ts:26`)
- CORS middleware on `/api/*` routes (`index.ts:87`)
- `permissionMode` passed to CLI as `--permission-mode` flag (`cli-launcher.ts:259-261`)
- Health check: `GET /api/sessions` returns 200 when server is up
- Session persistence to disk via `SessionStore` survives restarts
- Auto-relaunch: Companion auto-relaunches CLI if browser connects to session with no CLI

**On `--dangerously-skip-permissions`**: Pass `permissionMode: "dangerously-skip-permissions"` in create session body. Companion translates to `--permission-mode dangerously-skip-permissions`.

### Bun Installation Check

```python
bun_path = shutil.which("bun")
if not bun_path and _IS_WINDOWS:
    for candidate in [
        Path.home() / ".bun" / "bin" / "bun.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "bun" / "bun.exe",
    ]:
        if candidate.exists():
            bun_path = str(candidate)
            break
```

If Bun not found, skip Companion startup, disable Claude provider in UI.

---

## Phase 8: Integration and Wiring

### Updated `server/app.py` Lifespan

```python
from server.services.service_lifecycle import service_lifecycle
from server.services.provider_router import provider_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_full_path()
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / "sessions").mkdir(exist_ok=True)

    # Register and start backend services
    service_lifecycle.register(companion_config())
    service_lifecycle.register(opencode_config())
    await service_lifecycle.start_all()

    yield

    # Shutdown
    await provider_router.cleanup_all()
    await service_lifecycle.stop_all()
    await diagram_watcher.stop()
```

### Updated `server/routes/chat_sessions.py`

The `send_message` endpoint simplifies dramatically:

```python
@router.post("/api/projects/{project_id}/chat/sessions/{session_id}/messages")
async def send_message(project_id: str, session_id: str, body: SendMessageRequest):
    # ... validation (unchanged) ...

    # Build prompt using ContextAssembler
    arch_dir = str(Path(project.path) / ".vista" / "features" / session.feature_name / "arch")
    specs_dir = str(Path(project.path) / ".vista" / "features" / session.feature_name / "specs")
    system_prompt = ContextAssembler.build_system_prompt(arch_dir, specs_dir, project.path)
    all_msgs = [{"role": m.role, "content": m.content} for m in session.messages]
    history = all_msgs[:-1] if len(all_msgs) > 1 else None
    prompt = ContextAssembler.build_full_prompt(
        message=body.message, context=body.context,
        history=history, system_prompt=system_prompt,
    )

    # Ensure backend session exists
    if not session.backend_session_id:
        backend_id = await provider_router.create_backend_session(
            provider=provider_name, model=model_name,
            session_id=session_id, cwd=project.path,
        )
        session.backend_session_id = backend_id
        ChatSessionService.save(session)

    # Stream response via ProviderRouter
    asyncio.create_task(
        _stream_response(project_id, session_id, provider_name, model_name, prompt, project.path)
    )
    return {"status": "streaming", "session_id": session_id}
```

### Updated `mcp_server.py`

Remove `_start_opencode_serve()` function and related logic from `app_lifespan`. The lifecycle manager handles this now. Keep teams-related code (commented out) and ralph tools unchanged.

### Updated SSE Endpoint

Remove keepalive-related cleanup from `stream_session`:
- Remove `keepalive_manager.cancel_disconnect_cleanup()`
- Remove `keepalive_manager.schedule_disconnect_cleanup()` in finally block

---

## Dependency Summary

### New Python Packages

| Package | Purpose | Required? |
|---------|---------|-----------|
| `watchdog` | Filesystem event monitoring (replaces polling) | Yes |
| `websockets` | Async WebSocket client for Companion bridge | Yes (for Claude provider) |
| `httpx` | Async HTTP client for OpenCode REST + Companion REST | Yes |

**Not needed**: `httpx-sse` (manual line parsing is simpler), `opencode-ai` SDK (raw httpx suffices).

### System Dependencies

| Dependency | Purpose | Required? |
|------------|---------|-----------|
| `bun` | Companion server runtime | For Claude provider only |
| `claude` CLI | Claude Code | For Claude provider only |
| `opencode` binary | OpenCode server | For OpenCode provider only |

All optional -- graceful degradation when not installed.

---

## Implementation Order

| Step | Phase | Files | Dependencies | Effort |
|------|-------|-------|-------------|--------|
| 1 | Phase 1 | `service_lifecycle.py` | None | Medium |
| 2 | Phase 1 | `routes/service_status.py`, `config.py` changes | Step 1 | Small |
| 3 | Phase 1 | `app.py` lifespan changes | Steps 1-2 | Small |
| 4 | Phase 3 | `diagram_watcher.py` rewrite | `watchdog` package | Medium |
| 5 | Phase 4 | `context_assembler.py` | None | Small |
| 6 | Phase 2 | `claude_ws_client.py` | `websockets`, `httpx`, Step 1 | Large |
| 7 | Phase 2 | `opencode_client.py` | `httpx`, Step 1 | Medium |
| 8 | Phase 2 | `provider_router.py` | Steps 6+7 | Medium |
| 9 | Phase 2 | `chat_service.py` rewrite, `chat_sessions.py` update | Steps 5+8 | Medium |
| 10 | Phase 5 | `provider_service.py` model discovery | Steps 1+7 | Small |
| 11 | Phase 6 | `architecture.html` frontend changes | Steps 1+9 | Medium |
| 12 | Phase 7 | Companion fork verification + Bun check | Step 1 | Small |
| 13 | Phase 8 | Final integration, `mcp_server.py` cleanup | All above | Medium |

---

## Files Summary

### New Files (8)

| File | Purpose |
|------|---------|
| `server/services/service_lifecycle.py` | Multi-service lifecycle management |
| `server/services/provider_router.py` | Route messages to Claude/OpenCode backends |
| `server/services/claude_ws_client.py` | WebSocket client for Companion bridge |
| `server/services/opencode_client.py` | HTTP+SSE client for OpenCode server |
| `server/services/context_assembler.py` | Prompt assembly (extracted from chat_service) |
| `server/routes/service_status.py` | Health status API endpoint |
| `tests/test_service_lifecycle.py` | Lifecycle manager tests (TDD) |
| `tests/test_provider_router.py` | Provider routing + event translation tests (TDD) |

### Modified Files (9)

| File | Change Summary |
|------|---------------|
| `server/app.py` | Lifecycle integration, remove keepalive_manager |
| `server/config.py` | Add `get_chat_settings()` for service config |
| `server/services/chat_service.py` | Remove subprocess logic, delegate to ProviderRouter |
| `server/services/diagram_watcher.py` | Rewrite from polling to watchdog |
| `server/services/provider_service.py` | Add live model discovery from running services |
| `server/routes/chat_sessions.py` | Use ProviderRouter, remove keepalive/tmux logic |
| `server/models/chat_session.py` | Add `backend_session_id` field |
| `server/views/architecture.html` | Service status bar, provider availability |
| `mcp_server.py` | Remove inline `_start_opencode_serve()` |

### Removed Files (2)

| File | Reason |
|------|--------|
| `server/services/keepalive_manager.py` | Replaced by WebSocket/SSE via ProviderRouter |
| `server/routes/chat.py` | Blocking endpoint superseded by streaming sessions |

### Unchanged Companion Files

`vista/companion/` requires **zero changes**. Vista interacts via:
- HTTP: `POST /api/sessions/create`, `GET /api/sessions`, `DELETE /api/sessions/{id}`
- WebSocket: `ws://localhost:{port}/ws/browser/{sessionId}`

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Bun not installed on Windows | Medium | Detect at startup, disable Claude provider, show in UI |
| OpenCode binary not installed | Medium | Detect at startup, disable OpenCode provider |
| WebSocket connection drops mid-chat | High | Auto-reconnect with backoff; Companion buffers 1000 messages for replay |
| OpenCode SSE stream disconnects | Medium | Re-subscribe on disconnect, accumulate partial text |
| Port conflicts with other services | Low | Use `_find_free_port()` pattern |
| Companion CLI crash mid-chat | Medium | Lifecycle manager auto-restarts; ProviderRouter surfaces error |
| watchdog platform issues | Low | Has PollingObserver fallback; Windows well-supported |
| Process tree not killed on Windows | Medium | Use `taskkill /T /F /PID` |
| Concurrent async issues | Medium | Single-session enforcement prevents race conditions |
| `permissionMode` flag mismatch | Low | Verified: Companion uses `--permission-mode` flag |

---

## Testing Strategy

### Unit Tests (TDD)

1. **`test_service_lifecycle.py`**: State machine transitions, backoff calculation, max retry cap, prerequisite check
2. **`test_provider_router.py`**: Routing logic, Claude WS event translation, OpenCode SSE event translation, session map CRUD
3. **`test_context_assembler.py`**: Prompt assembly with all combinations, edge cases
4. **`test_diagram_watcher.py`**: Create/edit/delete events, manifest updates, debounce

### Integration Tests

- Start Companion + create session + send message + verify streaming tokens
- Start OpenCode serve + create session + prompt_async + verify SSE events
- Diagram edit during chat -> watcher fires -> SSE delivers to frontend
- Service crash -> lifecycle manager restarts -> health check passes

### Manual Verification

- Full chat flow with both providers on Windows 11
- Diagram editing by AI with live re-render in browser
- Service status indicators reflecting real health
- Graceful degradation when one provider is unavailable
