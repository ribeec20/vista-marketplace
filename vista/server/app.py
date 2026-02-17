"""FastAPI web server entry point - Vista Dashboard."""

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server import config
from server.services.project_service import ProjectService
from server.services.loop_service import loop_service
from server.services.diagram_watcher import diagram_watcher
from server.services.provider_service import get_enabled_providers
from server.services.output_parser import parse_stream_json_activity
from server.services.ralph_service import ralph_service
from server.services.service_lifecycle import (
    service_lifecycle,
    companion_config,
    opencode_config,
)
from server.services.provider_router import provider_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    config.ensure_full_path()
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / "sessions").mkdir(exist_ok=True)

    # Register and start backend services
    service_lifecycle.register(companion_config())
    service_lifecycle.register(opencode_config())
    await service_lifecycle.start_all()

    yield

    # Shutdown
    await provider_router.cleanup_all()
    await service_lifecycle.stop_all()
    await loop_service.stop_all()
    await diagram_watcher.stop()


app = FastAPI(title="Ralph Loop Dashboard", version="1.4.1", lifespan=lifespan)

# Mount static files
config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(config.VIEWS_DIR))

# Include routers
from server.routes import (
    projects,
    loops,
    stream,
    plans,
    providers,
    shutdown,
    architecture,
    chat_sessions,
    ralph,
    ralph_settings,
    sandbox,
    service_status,
    export,
)

app.include_router(projects.router)
app.include_router(loops.router)
app.include_router(stream.router)
app.include_router(plans.router)
app.include_router(providers.router)
app.include_router(shutdown.router)
app.include_router(architecture.router)
app.include_router(chat_sessions.router)
app.include_router(ralph.router)
app.include_router(ralph_settings.router)
app.include_router(sandbox.router)
app.include_router(service_status.router)
app.include_router(export.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring and hooks."""
    running_loops = {
        pid: state.to_dict()
        for pid, state in loop_service.get_all_states().items()
        if state.status in ("running", "starting")
    }
    return {
        "status": "ok",
        "version": app.version,
        "running_loops": len(running_loops),
    }


@app.get("/api/loops/running")
async def running_loops_summary():
    """Return compact summary of active loops for global app-bar status UI."""
    project_map = {p.id: p for p in ProjectService.get_all()}
    summaries = []
    for project_id, state in loop_service.get_all_states().items():
        if state.status not in ("running", "starting"):
            continue

        max_iters = state.max_iterations or 0
        progress = None
        if max_iters > 0:
            progress = min(100, int((state.iteration / max_iters) * 100))

        project = project_map.get(project_id)
        recent_actions = list(state.recent_actions)[-3:]
        summaries.append(
            {
                "kind": "project_loop",
                "project_id": project_id,
                "project_name": project.name if project else project_id,
                "status": state.status,
                "feature_name": state.feature_name,
                "mode": state.mode,
                "provider": state.provider,
                "provider_display_name": state.provider_display_name,
                "model": state.model,
                "iteration": state.iteration,
                "max_iterations": max_iters,
                "progress_percent": progress,
                "start_time": state.start_time,
                "recent_actions": recent_actions,
            }
        )

    # Also include running Ralph jobs started via ralph_start
    for project in project_map.values():
        project_root = Path(project.path)
        for job in ralph_service.list_jobs(project_root):
            if job.get("status") != "running":
                continue

            # Refresh status to avoid stale "running" jobs with dead PID
            refreshed = ralph_service.get_job_status(project_root, job.get("job_id", ""))
            if not refreshed or refreshed.get("status") != "running":
                continue

            progress_tail = refreshed.get("progress_tail") or []
            recent_actions = [
                {
                    "time": refreshed.get("completed_at")
                    or refreshed.get("started_at")
                    or refreshed.get("created_at"),
                    "type": "progress",
                    "message": line,
                }
                for line in progress_tail[-3:]
            ]

            max_iters = refreshed.get("iterations") or 0
            current_iter = refreshed.get("current_iteration") or 0
            progress = None
            if max_iters > 0:
                progress = min(100, int((current_iter / max_iters) * 100))

            summaries.append(
                {
                    "kind": "ralph_job",
                    "job_id": refreshed.get("job_id"),
                    "project_id": project.id,
                    "project_name": project.name,
                    "status": refreshed.get("status"),
                    "feature_name": refreshed.get("slug") or refreshed.get("job_id"),
                    "mode": refreshed.get("mode"),
                    "provider": refreshed.get("provider"),
                    "provider_display_name": refreshed.get("provider"),
                    "model": refreshed.get("model"),
                    "iteration": current_iter,
                    "max_iterations": max_iters,
                    "progress_percent": progress,
                    "start_time": refreshed.get("started_at") or refreshed.get("created_at"),
                    "recent_actions": recent_actions,
                }
            )

    summaries.sort(key=lambda item: item.get("start_time") or "", reverse=True)
    return {"count": len(summaries), "loops": summaries}


@app.get("/")
async def dashboard(request: Request):
    """Main dashboard showing all registered projects."""
    all_projects = ProjectService.get_all()
    states = loop_service.get_all_states()

    # Enrich projects with loop state
    project_data = []
    for p in all_projects:
        state = states.get(p.id)
        project_data.append(
            {
                **p.to_dict(),
                "loop_status": state.status if state else "idle",
                "loop_iteration": state.iteration if state else 0,
                "loop_feature": state.feature_name if state else None,
                "loop_mode": state.mode if state else None,
            }
        )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "projects": project_data,
        },
    )


@app.get("/project/{project_id}")
async def project_detail(request: Request, project_id: str):
    """Single project detail page with loop controls."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "projects": [],
                "error": "Project not found",
            },
        )

    features = ProjectService.scan_features_detailed(project.path)
    state = loop_service.get_state(project_id)
    providers = [p.to_summary_dict() for p in get_enabled_providers()]

    return templates.TemplateResponse(
        request,
        "project.html",
        {
            "project": project.to_dict(),
            "features": features,
            "loop_state": state.to_dict() if state else {"status": "idle"},
            "providers": providers,
        },
    )


@app.get("/ralph/jobs")
async def ralph_jobs_page(request: Request):
    """Ralph jobs list page."""
    all_jobs = []
    for project in ProjectService.get_all():
        project_root = Path(project.path)
        jobs = ralph_service.list_jobs(project_root)
        for job in jobs:
            job["project_name"] = project.name
            job["project_id"] = project.id
        all_jobs.extend(jobs)
    all_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    has_running = any(j.get("status") == "running" for j in all_jobs)

    return templates.TemplateResponse(
        request,
        "ralph_jobs.html",
        {"jobs": all_jobs, "has_running": has_running},
    )


@app.get("/ralph/jobs/{job_id}")
async def ralph_job_detail_page(request: Request, job_id: str):
    """Ralph job detail page."""
    job = None
    job_dir = None
    for project in ProjectService.get_all():
        project_root = Path(project.path)
        result = ralph_service.get_job_status(project_root, job_id)
        if result:
            job = result
            job["project_name"] = project.name
            job["project_id"] = project.id
            # Find job dir for artifacts
            ralph_dir = project_root / ".vista" / "ralph"
            if ralph_dir.exists():
                for slug_dir in ralph_dir.iterdir():
                    if slug_dir.is_dir():
                        jf = slug_dir / "job.json"
                        if jf.exists():
                            try:
                                data = json.loads(jf.read_text(encoding="utf-8"))
                                if data.get("job_id") == job_id:
                                    job_dir = slug_dir
                                    break
                            except (json.JSONDecodeError, OSError):
                                continue
            break

    if not job:
        return templates.TemplateResponse(
            request,
            "ralph_jobs.html",
            {"jobs": [], "has_running": False, "error": "Job not found"},
        )

    # Read progress lines — prefer progress.txt, fall back to output.log parsing
    progress_lines = []
    if job_dir:
        progress_file = job_dir / "progress.txt"
        if progress_file.exists():
            lines = progress_file.read_text(encoding="utf-8").splitlines()
            progress_lines = lines[-50:]
        else:
            output_file = job_dir / "output.log"
            if output_file.exists():
                try:
                    raw = output_file.read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                    progress_lines, _iter = parse_stream_json_activity(raw[-500:])
                    progress_lines = progress_lines[-50:]
                except OSError:
                    pass

    # List artifacts
    artifacts = []
    if job_dir:
        exclude = {"job.json", "output.log"}
        for f in sorted(job_dir.iterdir()):
            if f.is_file() and f.name not in exclude:
                artifacts.append({"name": f.name, "size": f.stat().st_size})

    return templates.TemplateResponse(
        request,
        "ralph_job_detail.html",
        {
            "job": job,
            "progress_lines": progress_lines,
            "artifacts": artifacts,
        },
    )


@app.get("/ralph/settings")
async def ralph_settings_page(request: Request):
    """Ralph settings page."""
    return templates.TemplateResponse(request, "ralph_settings.html", {})
