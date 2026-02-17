"""HTTP + SSE client for OpenCode's REST API.

Uses OpenCode's `opencode serve` HTTP endpoints:
- POST /session: Create a new session
- POST /session/{id}/prompt_async: Send async prompt
- GET /event: SSE event stream
- DELETE /session/{id}: Delete session
- POST /session/{id}/abort: Abort running session
- GET /config/providers: List available providers/models

Reference: .vista/features/architecture-chat/specs/opencode-server-reference.md
"""

import json
import logging
import os
from collections.abc import AsyncGenerator
from typing import Optional

import httpx

log = logging.getLogger(__name__)


class OpenCodeClient:
    """Async client for OpenCode's REST API + SSE streaming."""

    def __init__(self, base_url: str, auth: Optional[tuple[str, str]] = None):
        self.base_url = base_url  # "http://127.0.0.1:4096"
        self._auth = auth  # (username, password) for Basic Auth if set

    @classmethod
    def from_env(cls, base_url: str) -> "OpenCodeClient":
        """Create client with auth from environment if OPENCODE_SERVER_PASSWORD is set."""
        password = os.environ.get("OPENCODE_SERVER_PASSWORD")
        auth = ("opencode", password) if password else None
        return cls(base_url, auth=auth)

    def _client_kwargs(self) -> dict:
        kwargs: dict = {"timeout": 30.0}
        if self._auth:
            kwargs["auth"] = self._auth
        return kwargs

    async def create_session(self, title: str) -> str:
        """POST /session -> returns session ID."""
        async with httpx.AsyncClient(**self._client_kwargs()) as client:
            resp = await client.post(
                f"{self.base_url}/session",
                json={
                    "title": title,
                    "permission": [
                        {"permission": "*", "pattern": "*", "action": "allow"},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def send_message_streaming(
        self, session_id: str, text: str,
        model: Optional[dict] = None,
    ) -> AsyncGenerator[dict, None]:
        """POST /session/{id}/prompt_async + subscribe to GET /event SSE.

        1. Subscribe to SSE first (so we don't miss events)
        2. Send prompt_async
        3. Yield translated events until session.idle

        Translate events:
        - message.part.updated -> {type: "token", text: delta_text}
        - session.idle -> {type: "done", content: full_text}
        - session.error -> {type: "error", detail: msg}
        """
        full_text: list[str] = []
        # Track accumulated text length to compute deltas when "delta"
        # field is absent (e.g. gpt-5.1-codex only sends full "text").
        accumulated_len = 0
        # Track message roles so we only emit assistant tokens, not user echo.
        msg_roles: dict[str, str] = {}  # messageID -> "user"|"assistant"
        # Track confirmed assistant message ID for safe filtering.
        assistant_msg_id: Optional[str] = None

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
                # OpenCode sends only `data:` lines (no `event:` lines).
                # The event type is in the JSON payload's "type" field.
                async for line in sse_response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    event_type = data.get("type", "")
                    props = data.get("properties", {})

                    # Track message roles from message.updated events.
                    # Try both nested (props.info.{id,role}) and flat
                    # (props.{id,role}) structures for robustness.
                    if event_type == "message.updated":
                        info = props.get("info", props)
                        mid = info.get("id", "")
                        role = info.get("role", "")
                        if mid and role:
                            msg_roles[mid] = role
                            if role == "assistant" and assistant_msg_id is None:
                                assistant_msg_id = mid
                                log.debug("Tracking assistant message: %s", mid)
                        continue

                    if event_type == "message.part.updated":
                        part = props.get("part", {})
                        if part.get("type") != "text":
                            continue
                        part_msg_id = part.get("messageID", "")
                        # Skip parts from confirmed user messages
                        if msg_roles.get(part_msg_id) == "user":
                            continue
                        # Skip parts from unknown messages if we haven't
                        # seen the assistant message yet (prevents user
                        # prompt echo when role tracking is delayed).
                        if msg_roles.get(part_msg_id) is None and assistant_msg_id is None:
                            continue
                        # Prefer "delta" (incremental). Some models (e.g.
                        # gpt-5.1-codex) omit it; derive delta from "text".
                        text_delta = part.get("delta", "")
                        if not text_delta:
                            full = part.get("text", "")
                            text_delta = full[accumulated_len:]
                        if text_delta:
                            full_text.append(text_delta)
                            accumulated_len += len(text_delta)
                            yield {"type": "token", "text": text_delta}

                    elif event_type == "session.idle":
                        # Filter by session ID — global SSE sends all sessions.
                        idle_id = props.get("id", props.get("sessionID", ""))
                        if idle_id and idle_id != session_id:
                            continue
                        yield {"type": "done", "content": "".join(full_text)}
                        return

                    elif event_type == "session.error":
                        err_id = props.get("id", props.get("sessionID", ""))
                        if err_id and err_id != session_id:
                            continue
                        yield {
                            "type": "error",
                            "detail": props.get("error", "Unknown error"),
                        }
                        return

    async def get_providers(self) -> list[dict]:
        """GET /config/providers -> provider/model list."""
        async with httpx.AsyncClient(**self._client_kwargs()) as client:
            resp = await client.get(f"{self.base_url}/config/providers")
            resp.raise_for_status()
            return resp.json()

    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        try:
            async with httpx.AsyncClient(**self._client_kwargs()) as client:
                await client.delete(f"{self.base_url}/session/{session_id}")
        except Exception as e:
            log.warning("Failed to delete OpenCode session %s: %s", session_id, e)

    async def abort_session(self, session_id: str) -> None:
        """Abort a running session."""
        try:
            async with httpx.AsyncClient(**self._client_kwargs()) as client:
                await client.post(f"{self.base_url}/session/{session_id}/abort")
        except Exception as e:
            log.warning("Failed to abort OpenCode session %s: %s", session_id, e)
