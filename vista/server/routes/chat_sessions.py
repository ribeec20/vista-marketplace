"""Chat session API routes with SSE streaming and live diagram updates.

Uses ProviderRouter for protocol-native streaming (Claude WebSocket, OpenCode SSE).
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from server.services.project_service import ProjectService
from server.services.chat_session_service import ChatSessionService
from server.services.context_assembler import ContextAssembler
from server.services.diagram_watcher import diagram_watcher
from server.services.provider_router import provider_router
from server.services.service_lifecycle import service_lifecycle

log = logging.getLogger(__name__)
router = APIRouter(tags=["chat_sessions"])

# Per-session SSE subscriber queues
_session_subscribers: dict[str, list[asyncio.Queue]] = {}


def _subscribe(session_id: str) -> asyncio.Queue:
    if session_id not in _session_subscribers:
        _session_subscribers[session_id] = []
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _session_subscribers[session_id].append(queue)
    return queue


def _unsubscribe(session_id: str, queue: asyncio.Queue) -> None:
    if session_id in _session_subscribers:
        _session_subscribers[session_id] = [
            q for q in _session_subscribers[session_id] if q is not queue
        ]
        if not _session_subscribers[session_id]:
            del _session_subscribers[session_id]


async def _broadcast(session_id: str, message: dict) -> None:
    if session_id not in _session_subscribers:
        return
    dead = []
    for queue in _session_subscribers[session_id]:
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            dead.append(queue)
    for q in dead:
        if session_id in _session_subscribers:
            _session_subscribers[session_id].remove(q)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    feature_name: str
    provider: str
    model: str
    name: str = ""


class SendMessageRequest(BaseModel):
    message: str
    context: Optional[str] = Field(None, description="Pre-assembled diagram context")
    provider: Optional[str] = Field(
        None, description="Provider to use (overrides session default)"
    )
    model: Optional[str] = Field(
        None, description="Model to use (overrides session default)"
    )


class RenameSessionRequest(BaseModel):
    name: str


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


@router.get("/api/projects/{project_id}/chat/sessions")
async def list_sessions(project_id: str, feature: Optional[str] = None):
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ChatSessionService.list_sessions(project_id, feature)


@router.post("/api/projects/{project_id}/chat/sessions")
async def create_session(project_id: str, body: CreateSessionRequest):
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    session = ChatSessionService.create(
        project_id=project_id,
        feature_name=body.feature_name,
        provider=body.provider,
        model=body.model,
        name=body.name,
    )

    return session.to_dict()


@router.get("/api/projects/{project_id}/chat/sessions/{session_id}")
async def get_session(project_id: str, session_id: str):
    session = ChatSessionService.get(project_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.delete("/api/projects/{project_id}/chat/sessions/{session_id}")
async def delete_session(project_id: str, session_id: str):
    session = ChatSessionService.get(project_id, session_id)
    if session and session.backend_session_id:
        await provider_router.cleanup_session(session_id)
    deleted = ChatSessionService.delete(project_id, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


@router.patch("/api/projects/{project_id}/chat/sessions/{session_id}")
async def rename_session(project_id: str, session_id: str, body: RenameSessionRequest):
    session = ChatSessionService.update_name(project_id, session_id, body.name)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_summary_dict()


# ---------------------------------------------------------------------------
# Send message (triggers streaming via SSE)
# ---------------------------------------------------------------------------


def _provider_has_backend(provider_name: str) -> bool:
    """Check if a provider has a running backend service for protocol-native chat."""
    if provider_name == "claude":
        return service_lifecycle.is_available("companion")
    elif provider_name == "opencode":
        return service_lifecycle.is_available("opencode")
    return False


@router.post("/api/projects/{project_id}/chat/sessions/{session_id}/messages")
async def send_message(project_id: str, session_id: str, body: SendMessageRequest):
    """Send a user message. Streams the response via the session's SSE endpoint."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    session = ChatSessionService.get(project_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    # Use provider/model from request, fall back to session defaults
    provider_name = body.provider or session.provider
    model_name = body.model or session.model

    # Update session defaults if the user changed provider/model
    if provider_name != session.provider or model_name != session.model:
        session.provider = provider_name
        session.model = model_name
        ChatSessionService.save(session)

    # Save user message
    updated_session = ChatSessionService.add_message(
        project_id, session_id, "user", body.message
    )
    if not updated_session:
        raise HTTPException(status_code=500, detail="Failed to append message")
    session = updated_session

    arch_dir = str(
        Path(project.path) / ".vista" / "features" / session.feature_name / "arch"
    )
    specs_dir = str(
        Path(project.path) / ".vista" / "features" / session.feature_name / "specs"
    )

    # Build prompt using ContextAssembler.
    # History is NOT sent — both Claude (Companion) and OpenCode maintain
    # native conversation history within their sessions.
    system_prompt = ContextAssembler.build_system_prompt(
        arch_dir, specs_dir, project.path
    )
    prompt = ContextAssembler.build_full_prompt(
        message=body.message,
        context=body.context,
        system_prompt=system_prompt,
    )

    if not _provider_has_backend(provider_name):
        raise HTTPException(
            status_code=503, detail=f"Provider '{provider_name}' is not available"
        )

    # Protocol-native path via ProviderRouter
    if session.backend_session_id is None:
        try:
            backend_id = await provider_router.create_backend_session(
                provider=provider_name,
                model=model_name,
                session_id=session_id,
                cwd=project.path,
            )
            session.backend_session_id = backend_id
            ChatSessionService.save(session)
        except Exception as e:
            log.error("Failed to create backend session: %s", e)
            raise HTTPException(
                status_code=502, detail=f"Failed to create backend session: {e}"
            )

    asyncio.create_task(
        _stream_response_router(
            project_id,
            session_id,
            provider_name,
            model_name,
            prompt,
            project.path,
        )
    )
    return {"status": "streaming", "session_id": session_id}


# ---------------------------------------------------------------------------
# Streaming response handlers
# ---------------------------------------------------------------------------


async def _stream_response_router(
    project_id: str,
    session_id: str,
    provider_name: str,
    model: str,
    prompt: str,
    project_path: str,
) -> None:
    """Background task: stream via ProviderRouter (protocol-native)."""
    full_text: list[str] = []

    try:
        async for event in provider_router.send_message(
            provider=provider_name,
            model=model,
            prompt=prompt,
            session_id=session_id,
            cwd=project_path,
        ):
            if event["type"] == "token":
                full_text.append(event["text"])
                await _broadcast(
                    session_id,
                    {
                        "event": "token",
                        "data": {"text": event["text"]},
                    },
                )
            elif event["type"] == "done":
                content = event.get("content", "".join(full_text))
                ChatSessionService.add_message(
                    project_id, session_id, "assistant", content
                )
                await _broadcast(
                    session_id,
                    {
                        "event": "message_done",
                        "data": {"role": "assistant", "content": content},
                    },
                )
            elif event["type"] == "result":
                await _broadcast(
                    session_id,
                    {
                        "event": "result",
                        "data": event,
                    },
                )
            elif event["type"] == "error":
                await _broadcast(
                    session_id,
                    {
                        "event": "chat_error",
                        "data": {"detail": event["detail"]},
                    },
                )
    except Exception as e:
        await _broadcast(
            session_id,
            {
                "event": "chat_error",
                "data": {"detail": str(e)},
            },
        )


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


@router.post("/api/projects/{project_id}/chat/sessions/{session_id}/cancel")
async def cancel_session_chat(project_id: str, session_id: str):
    session = ChatSessionService.get(project_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.backend_session_id:
        await provider_router.cleanup_session(session_id)
        session.backend_session_id = None
        ChatSessionService.save(session)
        return {"cancelled": True}

    return {"cancelled": False}


# ---------------------------------------------------------------------------
# SSE streaming endpoint
# ---------------------------------------------------------------------------


async def _forward_queue(source: asyncio.Queue, dest: asyncio.Queue) -> None:
    """Forward items from source queue to dest queue until cancelled."""
    try:
        while True:
            item = await source.get()
            await dest.put(item)
    except asyncio.CancelledError:
        pass


@router.get("/api/projects/{project_id}/chat/sessions/{session_id}/stream")
async def stream_session(project_id: str, session_id: str, request: Request):
    """SSE endpoint delivering chat tokens and diagram change events."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    session = ChatSessionService.get(project_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Subscribe to chat events
    chat_queue = _subscribe(session_id)

    # Subscribe to diagram watcher
    arch_dir = (
        Path(project.path) / ".vista" / "features" / session.feature_name / "arch"
    )
    diagram_queue = diagram_watcher.subscribe(
        project_id, session.feature_name, arch_dir
    )

    # Merge both queues into one so the generator reads from a single source
    merged: asyncio.Queue = asyncio.Queue(maxsize=500)

    async def event_generator():
        fwd_chat = asyncio.create_task(_forward_queue(chat_queue, merged))
        fwd_diagram = asyncio.create_task(_forward_queue(diagram_queue, merged))
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(merged.get(), timeout=30.0)
                    yield {
                        "event": event.get("event", "message"),
                        "data": json.dumps(event.get("data", {})),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass
        finally:
            fwd_chat.cancel()
            fwd_diagram.cancel()
            _unsubscribe(session_id, chat_queue)
            diagram_watcher.unsubscribe(project_id, session.feature_name, diagram_queue)

    return EventSourceResponse(event_generator())
