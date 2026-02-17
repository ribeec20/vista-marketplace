"""WebSocket client for Companion's browser-side WebSocket bridge.

Connects to Companion's /ws/browser/{session_id} endpoint to relay
messages between Vista and the Claude CLI agent spawned by Companion.

Protocol verified from companion/web/server/session-types.ts:
- Browser sends: {type: "user_message", content: "..."}
- Browser receives: stream_event, assistant, result, permission_request, error, cli_disconnected
- Permission response: {type: "permission_response", request_id, behavior: "allow", updated_input}
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Optional

import httpx
import websockets

log = logging.getLogger(__name__)


class ClaudeWSClient:
    """WebSocket client connecting to Companion's /ws/browser/{session_id} endpoint."""

    def __init__(self, companion_base_url: str):
        self.base_url = companion_base_url  # "http://127.0.0.1:3457"
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._session_id: Optional[str] = None

    async def create_session(self, model: str, cwd: str) -> str:
        """POST /api/sessions/create -> returns Companion session ID."""
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
            session_id = data.get("sessionId") or data.get("session_id", "")
            log.info("Created Companion session: %s", session_id)
            return session_id

    async def connect(self, session_id: str) -> None:
        """Connect to ws://{host}:{port}/ws/browser/{session_id}."""
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        self._ws = await websockets.connect(
            f"{ws_url}/ws/browser/{session_id}",
            max_size=10 * 1024 * 1024,  # 10MB for large responses
        )
        self._session_id = session_id

        # Wait for initial message (session_init or message_history)
        try:
            init_raw = await self._ws.recv()
            init_msg = json.loads(init_raw)
            log.debug("Initial WS message type: %s", init_msg.get("type"))
        except Exception as e:
            log.warning("Error receiving initial WS message: %s", e)

    async def send_message(self, text: str) -> AsyncGenerator[dict, None]:
        """Send user message and yield streaming events.

        Send: {type: "user_message", content: text}
        Receive and translate:
        - stream_event with content_block_delta -> {type: "token", text: ...}
        - result -> {type: "result", ...} + {type: "done", content: ...}
        - permission_request -> auto-approve immediately
        - error -> {type: "error", detail: ...}
        - cli_disconnected -> {type: "error", detail: ...}
        """
        if not self._ws:
            yield {"type": "error", "detail": "WebSocket not connected"}
            return

        await self._ws.send(json.dumps({
            "type": "user_message",
            "content": text,
        }))

        full_text: list[str] = []
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
        """Close the WebSocket connection."""
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def delete_session(self, session_id: str) -> None:
        """DELETE /api/sessions/{session_id}."""
        try:
            async with httpx.AsyncClient() as client:
                await client.delete(
                    f"{self.base_url}/api/sessions/{session_id}",
                    timeout=10.0,
                )
        except Exception as e:
            log.warning("Failed to delete Companion session %s: %s", session_id, e)
