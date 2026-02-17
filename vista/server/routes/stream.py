"""SSE streaming endpoint for live loop output."""
import asyncio
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from server.services.loop_service import loop_service

router = APIRouter(tags=["stream"])


@router.get("/api/projects/{project_id}/loop/stream")
async def stream_loop_output(project_id: str, request: Request):
    """Stream loop output and parsed events via SSE."""
    queue = loop_service.subscribe(project_id)

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": message.get("event", "message"),
                        "data": json.dumps(message.get("data", {})),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "ping", "data": ""}
        finally:
            loop_service.unsubscribe(project_id, queue)

    return EventSourceResponse(event_generator())
