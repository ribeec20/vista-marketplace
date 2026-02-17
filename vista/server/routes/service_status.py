"""Service health status API endpoint."""

from fastapi import APIRouter

from server.services.service_lifecycle import service_lifecycle

router = APIRouter(tags=["services"])


@router.get("/api/services/health")
async def service_health():
    """Return health status of all managed backend services."""
    return {"services": service_lifecycle.get_all_status()}
