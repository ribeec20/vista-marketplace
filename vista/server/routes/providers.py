"""Provider API endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException

from server.services.provider_service import get_enabled_providers, get_provider_by_name
from server.services.service_lifecycle import service_lifecycle

router = APIRouter(prefix="/api", tags=["providers"])


@router.get("/providers")
async def list_providers():
    """Return enabled providers (without models — use /models endpoint for those)."""
    providers = get_enabled_providers()
    availability = {
        "claude": service_lifecycle.is_available("companion"),
        "opencode": service_lifecycle.is_available("opencode"),
    }
    return {
        "providers": [
            {
                **p.to_summary_dict(),
                "available": availability.get(p.name, False),
            }
            for p in providers
        ],
    }


@router.get("/providers/{name}/models")
async def get_provider_models(name: str):
    """Discover models for a provider on-demand.

    For OpenCode this runs `opencode models` CLI live.
    For Claude this returns the hardcoded list instantly.
    Runs in a thread to avoid blocking the event loop.
    """
    provider = get_provider_by_name(name)
    if not provider:
        raise HTTPException(
            status_code=404, detail=f"Provider '{name}' not found or not enabled"
        )
    try:
        models = await asyncio.wait_for(
            asyncio.to_thread(provider.get_models),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        return {"provider": name, "models": [], "error": "Model loading timed out"}
    return {
        "provider": name,
        "models": models,
    }
