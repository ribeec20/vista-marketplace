"""Ralph job API endpoints for the dashboard."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from server.services.output_parser import parse_plaintext_activity, parse_stream_json_activity
from server.services.project_service import ProjectService
from server.services.ralph_service import ralph_service

router = APIRouter(prefix="/api/ralph", tags=["ralph"])


def _find_job_context(job_id: str):
    """Find a ralph job across all registered projects.

    Returns (project, project_root, job_dir) or raises HTTPException(404).
    """
    for project in ProjectService.get_all():
        project_root = Path(project.path)
        ralph_dir = project_root / ".vista" / "ralph"
        if not ralph_dir.exists():
            continue
        for slug_dir in ralph_dir.iterdir():
            if not slug_dir.is_dir():
                continue
            job_file = slug_dir / "job.json"
            if not job_file.exists():
                continue
            try:
                data = json.loads(job_file.read_text(encoding="utf-8"))
                if data.get("job_id") == job_id:
                    return project, project_root, slug_dir
            except (json.JSONDecodeError, OSError):
                continue
    raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


@router.get("/jobs")
async def list_ralph_jobs():
    """List all ralph jobs across all registered projects."""
    all_jobs = []
    for project in ProjectService.get_all():
        project_root = Path(project.path)
        jobs = ralph_service.list_jobs(project_root)
        for job in jobs:
            job["project_name"] = project.name
            job["project_id"] = project.id
        all_jobs.extend(jobs)
    all_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return {"jobs": all_jobs}


@router.get("/jobs/{job_id}")
async def get_ralph_job(job_id: str):
    """Get a single ralph job with current status."""
    project, project_root, _job_dir = _find_job_context(job_id)
    job = ralph_service.get_job_status(project_root, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    job["project_name"] = project.name
    job["project_id"] = project.id
    return job


@router.get("/jobs/{job_id}/progress")
async def get_ralph_progress(job_id: str, last: int = 50):
    """Get parsed agent activity from output.log."""
    _project, _project_root, job_dir = _find_job_context(job_id)
    # Always parse output.log for dashboard display (progress.txt is inter-loop context only)
    output_file = job_dir / "output.log"
    if not output_file.exists():
        return {"lines": []}
    try:
        raw = output_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {"lines": []}
    # Read provider from job.json to choose the right parser
    provider = ""
    job_file = job_dir / "job.json"
    if job_file.exists():
        try:
            provider = json.loads(job_file.read_text(encoding="utf-8")).get("provider", "")
        except (json.JSONDecodeError, OSError):
            pass
    if provider == "claude":
        activity, _iteration = parse_stream_json_activity(raw[-500:])
    else:
        activity, _iteration = parse_plaintext_activity(raw[-500:])
    return {"lines": activity[-last:]}


@router.get("/jobs/{job_id}/output")
async def get_ralph_output(job_id: str, last: int = 200):
    """Get last N lines of output.log."""
    _project, _project_root, job_dir = _find_job_context(job_id)
    output_file = job_dir / "output.log"
    if not output_file.exists():
        return {"lines": []}
    lines = output_file.read_text(encoding="utf-8").splitlines()
    return {"lines": lines[-last:]}


@router.get("/jobs/{job_id}/artifacts")
async def list_ralph_artifacts(job_id: str):
    """List artifact files in job directory."""
    _project, _project_root, job_dir = _find_job_context(job_id)
    # Exclude internal files, show everything else
    exclude = {"job.json", "output.log"}
    artifacts = []
    for f in sorted(job_dir.iterdir()):
        if f.is_file() and f.name not in exclude:
            artifacts.append({
                "name": f.name,
                "size": f.stat().st_size,
            })
    # Also include archived job.json files
    for f in sorted(job_dir.glob("job.*.json")):
        artifacts.append({
            "name": f.name,
            "size": f.stat().st_size,
        })
    return {"artifacts": artifacts}


@router.get("/jobs/{job_id}/artifacts/{filename:path}")
async def get_ralph_artifact(job_id: str, filename: str):
    """Read contents of a specific artifact file."""
    _project, _project_root, job_dir = _find_job_context(job_id)
    artifact = job_dir / filename
    # Security: ensure the resolved path is within the job directory
    try:
        artifact.resolve().relative_to(job_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact path")
    if not artifact.exists() or not artifact.is_file():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {filename}")
    content = artifact.read_text(encoding="utf-8", errors="replace")
    return PlainTextResponse(content)


@router.post("/jobs/{job_id}/stop")
async def stop_ralph_job(job_id: str):
    """Stop a running ralph job."""
    try:
        project, project_root, _job_dir = _find_job_context(job_id)
        job = ralph_service.stop_job(project_root, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        job["project_name"] = project.name
        job["project_id"] = project.id
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop job: {e}")
