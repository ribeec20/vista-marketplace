"""Provider router for architecture chat.

Routes chat messages to the correct backend (Claude WebSocket or OpenCode SSE)
based on the provider type. Manages session mapping between Vista and backend
session IDs.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Optional

from server.services.service_lifecycle import service_lifecycle
from server.services.claude_ws_client import ClaudeWSClient
from server.services.opencode_client import OpenCodeClient

log = logging.getLogger(__name__)


class ProviderRouter:
    """Routes chat messages to the correct backend based on provider type."""

    def __init__(self):
        self._claude_clients: dict[str, ClaudeWSClient] = {}  # session_id -> client
        self._opencode_clients: dict[str, OpenCodeClient] = {}  # session_id -> client
        # Vista session_id -> {provider, backend_session_id, model, cwd}
        self._session_map: dict[str, dict] = {}

    async def create_backend_session(
        self, provider: str, model: str, session_id: str, cwd: str
    ) -> str:
        """Create a backend session and return the backend session ID."""
        if provider == "claude":
            return await self._create_claude_session(model, session_id, cwd)
        elif provider == "opencode":
            return await self._create_opencode_session(model, session_id, cwd)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def send_message(
        self, provider: str, model: str, prompt: str,
        session_id: str, cwd: str,
    ) -> AsyncGenerator[dict, None]:
        """Yield streaming events: {type: "token"|"done"|"error", ...}."""
        # Ensure backend session exists
        if session_id not in self._session_map:
            try:
                await self.create_backend_session(provider, model, session_id, cwd)
            except Exception as e:
                yield {"type": "error", "detail": f"Failed to create backend session: {e}"}
                return

        mapping = self._session_map[session_id]

        if mapping["provider"] == "claude":
            async for event in self._send_claude(session_id, prompt):
                yield event
        elif mapping["provider"] == "opencode":
            async for event in self._send_opencode(session_id, prompt, model):
                yield event
        else:
            yield {"type": "error", "detail": f"Unknown provider: {mapping['provider']}"}

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up backend session when Vista session is deleted."""
        mapping = self._session_map.pop(session_id, None)
        if not mapping:
            return

        backend_id = mapping["backend_session_id"]
        provider = mapping["provider"]

        if provider == "claude":
            client = self._claude_clients.pop(session_id, None)
            if client:
                await client.disconnect()
                await client.delete_session(backend_id)
        elif provider == "opencode":
            client = self._opencode_clients.pop(session_id, None)
            if client:
                await client.abort_session(backend_id)
                await client.delete_session(backend_id)

    async def cleanup_all(self) -> None:
        """Clean up all backend sessions on shutdown."""
        for session_id in list(self._session_map.keys()):
            await self.cleanup_session(session_id)

    # --- Claude WebSocket ---

    async def _create_claude_session(self, model: str, session_id: str, cwd: str) -> str:
        """Create a Claude session via Companion's HTTP API + WebSocket."""
        if not service_lifecycle.is_available("companion"):
            raise RuntimeError("Companion service is not available")

        status = service_lifecycle.get_status("companion")
        port = status.get("port", 3457)
        base_url = f"http://127.0.0.1:{port}"

        client = ClaudeWSClient(base_url)
        backend_id = await client.create_session(model, cwd)
        await client.connect(backend_id)

        self._claude_clients[session_id] = client
        self._session_map[session_id] = {
            "provider": "claude",
            "backend_session_id": backend_id,
            "model": model,
            "cwd": cwd,
        }
        return backend_id

    async def _send_claude(self, session_id: str, prompt: str) -> AsyncGenerator[dict, None]:
        """Send message via Claude WebSocket and yield events."""
        client = self._claude_clients.get(session_id)
        if not client:
            yield {"type": "error", "detail": "No Claude WebSocket client for session"}
            return

        try:
            async for event in client.send_message(prompt):
                yield event
        except Exception as e:
            log.error("Claude WebSocket error: %s", e)
            yield {"type": "error", "detail": f"Claude WebSocket error: {e}"}

    # --- OpenCode SSE ---

    async def _create_opencode_session(self, model: str, session_id: str, cwd: str) -> str:
        """Create an OpenCode session via REST API."""
        if not service_lifecycle.is_available("opencode"):
            raise RuntimeError("OpenCode service is not available")

        status = service_lifecycle.get_status("opencode")
        port = status.get("port", 4096)
        base_url = f"http://127.0.0.1:{port}"

        client = OpenCodeClient.from_env(base_url)
        backend_id = await client.create_session(f"Vista Chat {session_id}")

        self._opencode_clients[session_id] = client
        self._session_map[session_id] = {
            "provider": "opencode",
            "backend_session_id": backend_id,
            "model": model,
            "cwd": cwd,
        }
        return backend_id

    async def _send_opencode(
        self, session_id: str, prompt: str, model: Optional[str] = None
    ) -> AsyncGenerator[dict, None]:
        """Send message via OpenCode SSE and yield events."""
        client = self._opencode_clients.get(session_id)
        mapping = self._session_map.get(session_id)
        if not client or not mapping:
            yield {"type": "error", "detail": "No OpenCode client for session"}
            return

        backend_id = mapping["backend_session_id"]
        try:
            async for event in client.send_message_streaming(backend_id, prompt):
                yield event
        except Exception as e:
            log.error("OpenCode SSE error: %s", e)
            yield {"type": "error", "detail": f"OpenCode SSE error: {e}"}


# Singleton instance
provider_router = ProviderRouter()
