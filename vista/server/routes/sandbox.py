"""Sandbox API endpoints for Docker status and image management."""

import logging

from fastapi import APIRouter, HTTPException

from server.config import get_sandbox_settings
from server.services.sandbox.container_manager import ContainerManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ralph/sandbox", tags=["sandbox"])


@router.get("/status")
async def sandbox_status():
    """DS-F32: Return Docker availability and image existence status."""
    mgr = ContainerManager(session_id="sandbox-status")
    docker_available, docker_message = mgr.check_docker_available()

    image_exists = False
    image_name = get_sandbox_settings().get("image", "vista-ralph:latest")

    if docker_available:
        try:
            image_exists = mgr.ensure_image(image_name, check_only=True)
        except Exception as e:
            logger.debug("Image check failed: %s", e)

    return {
        "docker_available": docker_available,
        "docker_message": docker_message,
        "image_exists": image_exists,
        "image_name": image_name,
    }


@router.post("/build")
async def sandbox_build():
    """DS-F33: Trigger image build or rebuild on demand."""
    mgr = ContainerManager(session_id="sandbox-build")
    docker_available, docker_message = mgr.check_docker_available()

    if not docker_available:
        raise HTTPException(
            status_code=503,
            detail=f"Docker is not available: {docker_message}",
        )

    image_name = get_sandbox_settings().get("image", "vista-ralph:latest")

    try:
        result = mgr.ensure_image(image_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image build failed: {e}",
        )

    return {
        "success": result,
        "image_name": image_name,
        "message": "Image ready" if result else "Image build failed",
    }
