"""Loop control API endpoints."""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.services.loop_service import loop_service
from server.services.project_service import ProjectService
from server.services.provider_service import get_enabled_providers, get_provider_by_name

router = APIRouter(prefix="/api/projects/{project_id}/loop", tags=["loops"])


class StartLoopRequest(BaseModel):
    feature_name: str
    mode: str                              # "plan" or "build"
    model: str = "sonnet"                  # provider-specific model id
    provider: str = "claude"               # provider name
    max_iterations: int = 0                # 0 = unlimited


@router.post("/start")
async def start_loop(project_id: str, req: StartLoopRequest):
    """Start a ralph loop for a project."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if req.mode not in ("plan", "build"):
        raise HTTPException(status_code=400, detail="Mode must be 'plan' or 'build'")

    # Resolve provider
    provider = get_provider_by_name(req.provider)
    if not provider:
        raise HTTPException(status_code=400, detail=f"Provider '{req.provider}' not found or not enabled")

    # Validate model against provider's model list (run in thread to avoid blocking)
    try:
        available_models = await asyncio.wait_for(
            asyncio.to_thread(provider.get_models),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Timed out loading models for {provider.display_name}. "
                   "The CLI may be unavailable.",
        )
    if req.model not in available_models:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{req.model}' not available for {provider.display_name}. "
                   f"Available: {available_models}",
        )

    try:
        instance = await loop_service.start_loop(
            project_id=project_id,
            project_path=project.path,
            feature_name=req.feature_name,
            mode=req.mode,
            model=req.model,
            max_iterations=req.max_iterations,
            provider=provider,
        )
        return instance.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop_loop(project_id: str):
    """Stop a running loop."""
    instance = await loop_service.stop_loop(project_id)
    if not instance:
        raise HTTPException(status_code=404, detail="No loop found for this project")
    return instance.to_dict()


@router.get("/state")
async def get_loop_state(project_id: str):
    """Get current loop state."""
    instance = loop_service.get_state(project_id)
    if not instance:
        return {"status": "idle"}
    return instance.to_dict()


@router.get("/output")
async def get_loop_output(project_id: str, last: int = 100):
    """Get recent output lines."""
    instance = loop_service.get_state(project_id)
    if not instance:
        return {"lines": []}
    lines = list(instance.output_lines)
    return {"lines": lines[-last:]}
