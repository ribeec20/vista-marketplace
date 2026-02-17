"""Architecture diagram viewing and chat."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from server import config
from server.services.project_service import ProjectService
from server.services.progress_service import ProgressService
from server.services.provider_service import get_enabled_providers

router = APIRouter(tags=["architecture"])
templates = Jinja2Templates(directory=str(config.VIEWS_DIR))


@router.get("/api/projects/{project_id}/features/{feature_name}/arch")
async def get_arch_manifest(project_id: str, feature_name: str):
    """Return the _arch.json manifest for a feature."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    manifest = ProgressService.read_arch_manifest(project.path, feature_name)
    if manifest is None:
        raise HTTPException(status_code=404, detail="No architecture manifest found")

    return manifest


@router.get("/api/projects/{project_id}/features/{feature_name}/arch/{filename}")
async def get_arch_file(project_id: str, feature_name: str, filename: str):
    """Return raw content of a diagram file from arch/."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = ProgressService.read_arch_file(project.path, feature_name, filename)
    if content is None:
        raise HTTPException(status_code=404, detail="Diagram file not found")

    # Determine content type
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    CONTENT_TYPES = {
        "mmd": "text/plain",
        "drawio": "application/xml",
        "puml": "text/plain",
        "d2": "text/plain",
        "dot": "text/plain",
        "md": "text/markdown",
    }
    media_type = CONTENT_TYPES.get(ext, "text/plain")

    return PlainTextResponse(content=content, media_type=media_type)


class FileContent(BaseModel):
    content: str


@router.put("/api/projects/{project_id}/features/{feature_name}/arch/{filename}")
async def put_arch_file(project_id: str, feature_name: str, filename: str, body: FileContent):
    """Write content to a markdown file in arch/."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    success = ProgressService.write_arch_file(project.path, feature_name, filename, body.content)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot write to this file")

    return {"status": "ok", "filename": filename}


@router.get("/project/{project_id}/arch/{feature_name}")
async def architecture_viewer_page(request: Request, project_id: str, feature_name: str):
    """Render architecture diagram viewer page."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    manifest = ProgressService.read_arch_manifest(project.path, feature_name)
    providers = [p.to_summary_dict() for p in get_enabled_providers()]
    diagram_settings = config.get_diagram_settings()
    plantuml_url = diagram_settings.get("plantuml_server_url", "https://www.plantuml.com/plantuml")

    return templates.TemplateResponse(request, "architecture.html", {
        "project": project.to_dict(),
        "feature_name": feature_name,
        "manifest": manifest,
        "providers": providers,
        "plantuml_url": plantuml_url,
    })


@router.get("/project/{project_id}/arch/{feature_name}/diagram/{filename}")
async def diagram_expand_page(
    request: Request, project_id: str, feature_name: str, filename: str
):
    """Render a single diagram in a full-page view."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = ProgressService.read_arch_file(project.path, feature_name, filename)
    if content is None:
        raise HTTPException(status_code=404, detail="Diagram file not found")

    diagram_name = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
    providers = [p.to_summary_dict() for p in get_enabled_providers()]
    diagram_settings = config.get_diagram_settings()
    plantuml_url = diagram_settings.get("plantuml_server_url", "https://www.plantuml.com/plantuml")

    return templates.TemplateResponse(request, "diagram_expand.html", {
        "project": project.to_dict(),
        "feature_name": feature_name,
        "filename": filename,
        "diagram_name": diagram_name,
        "providers": providers,
        "plantuml_url": plantuml_url,
    })
