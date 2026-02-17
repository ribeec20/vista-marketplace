"""View implementation plans and progress."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from server import config
from server.services.project_service import ProjectService
from server.services.progress_service import ProgressService

router = APIRouter(tags=["plans"])
templates = Jinja2Templates(directory=str(config.VIEWS_DIR))


@router.get("/api/projects/{project_id}/features/{feature_name}/plan")
async def get_plan(project_id: str, feature_name: str):
    """Get implementation plan as JSON."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    plan = ProgressService.read_implementation_plan(project.path, feature_name)
    progress = ProgressService.read_progress(project.path, feature_name)
    agents = ProgressService.read_agents_md(project.path, feature_name)

    return {
        "feature_name": feature_name,
        "implementation_plan": plan,
        "progress": progress,
        "agents": agents,
    }


@router.get("/project/{project_id}/plan/{feature_name}")
async def plan_preview_page(request: Request, project_id: str, feature_name: str):
    """Render implementation plan as HTML page."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    plan = ProgressService.read_implementation_plan(project.path, feature_name)
    progress = ProgressService.read_progress(project.path, feature_name)

    return templates.TemplateResponse(request, "plan_preview.html", {
        "project": project.to_dict(),
        "feature_name": feature_name,
        "plan_content": plan or "No implementation plan found.",
        "progress": progress,
    })
