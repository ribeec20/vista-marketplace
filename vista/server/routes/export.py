"""Export routes for generating self-contained HTML documentation."""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from server.services.export_service import ExportService
from server.services.project_service import ProjectService

logger = logging.getLogger(__name__)
router = APIRouter()


class ExportFeatureSelection(BaseModel):
    name: str
    diagrams: list[str] = []
    include_requirements: bool = True
    include_progress: bool = True
    include_agents: bool = True
    include_implementation_plan: bool = True


class ExportRalphJobSelection(BaseModel):
    slug: str
    include_task: bool = True
    include_plan: bool = True
    include_progress: bool = True


class ExportRequest(BaseModel):
    features: list[ExportFeatureSelection] = []
    ralph_jobs: list[ExportRalphJobSelection] = []
    offline: bool = False
    default_theme: str = "dark"


@router.get("/api/projects/{project_id}/export/features")
async def get_export_features(project_id: str):
    """Return the feature tree for the export modal checklist."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ExportService.get_exportable_features(project.path)


@router.get("/api/projects/{project_id}/export/ralph-jobs")
async def get_export_ralph_jobs(project_id: str):
    """Return Ralph jobs available for export."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ExportService.get_exportable_ralph_jobs(project.path)


@router.post("/api/projects/{project_id}/export")
async def export_documentation(project_id: str, body: ExportRequest):
    """Generate and return the exported HTML documentation file."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    html = ExportService.generate_export_html(
        project_name=project.name,
        project_path=project.path,
        selected_features=[f.model_dump() for f in body.features],
        selected_ralph_jobs=[j.model_dump() for j in body.ralph_jobs],
        offline=body.offline,
        default_theme=body.default_theme,
    )

    filename = f"{project.name}-docs-{datetime.now().strftime('%Y-%m-%d')}.html"

    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
