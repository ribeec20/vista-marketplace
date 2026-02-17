"""Shutdown endpoint for the Vista server.

Modeled on Serena's dashboard.py shutdown pattern:
PUT /api/shutdown kills the entire MCP process (and its daemon uvicorn thread).
"""
import asyncio
import os

from fastapi import APIRouter

router = APIRouter(tags=["server"])


@router.put("/api/shutdown")
async def shutdown():
    """Shut down the entire Vista MCP process.

    Returns a response, then exits after a short delay so the
    HTTP response can flush before the process dies.
    """
    async def _delayed_exit():
        await asyncio.sleep(0.5)
        os._exit(0)

    asyncio.create_task(_delayed_exit())
    return {"status": "shutting down"}
