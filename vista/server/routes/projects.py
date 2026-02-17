"""Project CRUD API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


class RegisterRequest(BaseModel):
    path: str


@router.get("")
async def list_projects():
    """List all registered projects."""
    projects = ProjectService.get_all()
    return [p.to_dict() for p in projects]


@router.post("")
async def register_project(req: RegisterRequest):
    """Register a new project by path."""
    try:
        project = ProjectService.register(req.path)
        return project.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get a single project."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.to_dict()


@router.delete("/{project_id}")
async def unregister_project(project_id: str):
    """Unregister a project."""
    if not ProjectService.unregister(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.get("/{project_id}/features")
async def list_features(project_id: str):
    """Scan and return features for a project."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    features = ProjectService.scan_features(project.path)
    return {"features": features}


@router.get("/{project_id}/features/detailed")
async def list_features_detailed(project_id: str):
    """Scan features with rich metadata (key files present, spec count).

    Returns per-feature info about which key files exist so the dashboard
    can show feature readiness at a glance.
    """
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    features = ProjectService.scan_features_detailed(project.path)
    return {"features": features}
