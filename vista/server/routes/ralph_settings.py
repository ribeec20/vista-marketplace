"""Ralph settings API endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server import config
from server.services.provider_service import get_ralph_providers

router = APIRouter(prefix="/api/settings", tags=["settings"])

VALID_COST_TIERS = {None, "", "free", "cheap", "moderate", "expensive"}


class RalphSettingsUpdate(BaseModel):
    """Request body for updating ralph settings."""
    defaults: dict | None = None
    summarizer: dict | None = None
    providers: dict | None = None


@router.get("/ralph")
async def get_ralph_settings():
    """Get current ralph settings merged with live model discovery."""
    ralph_settings = config.get_ralph_settings()
    defaults = config.get_ralph_defaults()
    summarizer = config.get_summarizer_config()

    # Live model discovery (may be slow - run in thread)
    try:
        providers = await asyncio.wait_for(
            asyncio.to_thread(get_ralph_providers),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        providers = []

    return {
        "defaults": defaults,
        "summarizer": summarizer,
        "providers": providers,
        "raw_settings": ralph_settings,
    }


@router.put("/ralph")
async def save_ralph_settings_endpoint(req: RalphSettingsUpdate):
    """Save ralph settings back to settings.json."""
    current = config.get_ralph_settings()

    if req.defaults is not None:
        # Validate iterations
        iterations = req.defaults.get("iterations")
        if iterations is not None and (not isinstance(iterations, int) or iterations <= 0):
            raise HTTPException(status_code=400, detail="iterations must be a positive integer")
        current["defaults"] = {**current.get("defaults", {}), **req.defaults}

    if req.summarizer is not None:
        current["summarizer"] = {**current.get("summarizer", {}), **req.summarizer}

    if req.providers is not None:
        for pname, pcfg in req.providers.items():
            # Validate favorites
            favorites = pcfg.get("favorites", [])
            if not isinstance(favorites, list):
                raise HTTPException(status_code=400, detail=f"favorites must be a list for {pname}")
            if len(favorites) > 3:
                raise HTTPException(status_code=400, detail=f"Max 3 favorites per provider ({pname})")

            # Validate cost_tier values
            metadata = pcfg.get("model_metadata", {})
            for model_name, meta in metadata.items():
                tier = meta.get("cost_tier")
                if tier not in VALID_COST_TIERS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid cost_tier '{tier}' for {pname}/{model_name}. "
                               f"Valid: free, cheap, moderate, expensive",
                    )
        current["providers"] = req.providers

    config.save_ralph_settings(current)
    return {"ok": True}


@router.get("/ralph/models")
async def refresh_ralph_models():
    """Refresh-only endpoint for live model discovery."""
    try:
        providers = await asyncio.wait_for(
            asyncio.to_thread(get_ralph_providers),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        return {"providers": [], "error": "Model discovery timed out"}
    return {"providers": providers}
