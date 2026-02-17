"""Export service for generating self-contained HTML documentation."""
import json
import logging
from datetime import datetime
from pathlib import Path

import jinja2

from server import config
from server.services.progress_service import ProgressService

logger = logging.getLogger(__name__)

# Files we consider exportable from Ralph job directories
RALPH_EXPORTABLE_FILES = ("task.md", "IMPLEMENTATION_PLAN.md", "progress.txt")

# Vendor files for offline mode, stored in views/static/vendor/
VENDOR_DIR = config.STATIC_DIR / "vendor"
VENDOR_FILES = {
    "tailwind_css": "tailwind-export.css",
    "mermaid_js": "mermaid.min.js",
    "marked_js": "marked.min.js",
}


class ExportService:
    @staticmethod
    def get_exportable_features(project_path: str) -> list[dict]:
        """Return features with their diagrams and requirements availability.

        Scans .vista/features/ for features that have at least one diagram,
        non-empty domain-requirements.md, progress.txt, AGENTS.md, or
        IMPLEMENTATION_PLAN.md.
        """
        features_dir = Path(project_path) / ".vista" / "features"
        if not features_dir.exists():
            return []

        results = []
        for d in sorted(features_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue

            manifest = ProgressService.read_arch_manifest(project_path, d.name)
            diagrams = manifest.get("diagrams", []) if manifest else []
            has_requirements = ProgressService.read_domain_requirements(project_path, d.name) is not None

            progress = ProgressService.read_progress(project_path, d.name)
            has_progress = progress.get("exists", False)
            has_agents_md = ProgressService.read_agents_md(project_path, d.name) is not None
            has_implementation_plan = ProgressService.read_implementation_plan(project_path, d.name) is not None

            if not diagrams and not has_requirements and not has_progress and not has_agents_md and not has_implementation_plan:
                continue

            results.append({
                "name": d.name,
                "has_requirements": has_requirements,
                "has_progress": has_progress,
                "has_agents_md": has_agents_md,
                "has_implementation_plan": has_implementation_plan,
                "diagrams": [
                    {
                        "name": diag.get("name", diag.get("file", "")),
                        "file": diag["file"],
                        "type": diag.get("type", "mermaid"),
                        "description": diag.get("description", ""),
                        "category": diag.get("category", "architecture"),
                    }
                    for diag in diagrams
                    if "file" in diag
                ],
            })
        return results

    @staticmethod
    def get_exportable_ralph_jobs(project_path: str) -> list[dict]:
        """Return Ralph jobs with their available exportable artifacts.

        Scans .vista/ralph/ for job directories containing task.md,
        IMPLEMENTATION_PLAN.md, or progress.txt.
        """
        ralph_dir = Path(project_path) / ".vista" / "ralph"
        if not ralph_dir.exists():
            return []

        results = []
        for d in sorted(ralph_dir.iterdir()):
            if not d.is_dir():
                continue

            # Read job.json for metadata
            job_json_path = d / "job.json"
            job_meta = {}
            if job_json_path.exists():
                try:
                    job_meta = json.loads(job_json_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass

            # Check which exportable files exist
            has_task = (d / "task.md").exists()
            has_plan = (d / "IMPLEMENTATION_PLAN.md").exists()
            has_progress = (d / "progress.txt").exists()

            if not has_task and not has_plan and not has_progress:
                continue

            results.append({
                "slug": d.name,
                "mode": job_meta.get("mode", ""),
                "status": job_meta.get("status", ""),
                "has_task": has_task,
                "has_plan": has_plan,
                "has_progress": has_progress,
            })
        return results

    @staticmethod
    def read_ralph_artifact(project_path: str, job_slug: str, filename: str) -> str | None:
        """Read a single artifact file from a Ralph job directory.

        Includes path traversal prevention — only whitelisted filenames
        within .vista/ralph/{job_slug}/ are allowed.
        """
        if filename not in RALPH_EXPORTABLE_FILES:
            logger.warning("Blocked read of non-exportable Ralph file: %s", filename)
            return None

        # Prevent path traversal in job_slug
        safe_slug = Path(job_slug).name
        if safe_slug != job_slug:
            logger.warning("Blocked path traversal in Ralph job slug: %s", job_slug)
            return None

        filepath = Path(project_path) / ".vista" / "ralph" / safe_slug / filename
        if not filepath.exists():
            return None

        try:
            content = filepath.read_text(encoding="utf-8")
            return content if content.strip() else None
        except OSError:
            logger.warning("Failed to read Ralph artifact %s/%s", safe_slug, filename)
            return None

    @staticmethod
    def read_vendor_file(key: str) -> str | None:
        """Read a vendor file by key (e.g. 'tailwind_css', 'mermaid_js').

        Returns file content or None if not found.
        """
        filename = VENDOR_FILES.get(key)
        if not filename:
            return None
        filepath = VENDOR_DIR / filename
        if not filepath.exists():
            logger.warning("Vendor file not found: %s", filepath)
            return None
        try:
            return filepath.read_text(encoding="utf-8")
        except OSError:
            logger.warning("Failed to read vendor file: %s", filepath)
            return None

    @staticmethod
    def generate_export_html(
        project_name: str,
        project_path: str,
        selected_features: list[dict],
        selected_ralph_jobs: list[dict] | None = None,
        offline: bool = False,
        default_theme: str = "dark",
    ) -> str:
        """Generate self-contained HTML export.

        For each selected feature:
        1. Read _arch.json manifest
        2. Filter diagrams to only those selected
        3. Read .mmd content for each selected diagram
        4. Read domain-requirements.md
        5. Read progress.txt, AGENTS.md, IMPLEMENTATION_PLAN.md

        For each selected Ralph job:
        1. Read task.md, IMPLEMENTATION_PLAN.md, progress.txt based on toggles

        When offline=True, vendor JS/CSS is inlined into the HTML for true
        offline support. default_theme controls initial light/dark appearance.

        Returns rendered HTML string.
        """
        features_data = []

        for selection in selected_features:
            feature_name = selection["name"]
            selected_diagram_files = selection.get("diagrams", [])
            include_requirements = selection.get("include_requirements", True)
            include_progress = selection.get("include_progress", True)
            include_agents = selection.get("include_agents", True)
            include_implementation_plan = selection.get("include_implementation_plan", True)

            manifest = ProgressService.read_arch_manifest(project_path, feature_name)
            all_diagrams = manifest.get("diagrams", []) if manifest else []

            diagram_data = []
            for diag in all_diagrams:
                if diag.get("file") not in selected_diagram_files:
                    continue
                content = ProgressService.read_arch_file(
                    project_path, feature_name, diag["file"]
                )
                if content is None:
                    logger.warning(
                        "Skipping missing diagram %s/%s", feature_name, diag["file"]
                    )
                    continue
                diagram_data.append({
                    "name": diag.get("name", diag["file"]),
                    "file": diag["file"],
                    "description": diag.get("description", ""),
                    "category": diag.get("category", "architecture"),
                    "content": content,
                })

            requirements_md = None
            if include_requirements:
                requirements_md = ProgressService.read_domain_requirements(
                    project_path, feature_name
                )

            progress_md = None
            if include_progress:
                progress_data = ProgressService.read_progress(project_path, feature_name)
                if progress_data.get("exists"):
                    progress_md = progress_data["content"]

            agents_md = None
            if include_agents:
                agents_md = ProgressService.read_agents_md(project_path, feature_name)

            implementation_plan_md = None
            if include_implementation_plan:
                implementation_plan_md = ProgressService.read_implementation_plan(
                    project_path, feature_name
                )

            if not diagram_data and not requirements_md and not progress_md and not agents_md and not implementation_plan_md:
                continue

            features_data.append({
                "name": feature_name,
                "diagrams": diagram_data,
                "requirements_md": requirements_md,
                "progress_md": progress_md,
                "agents_md": agents_md,
                "implementation_plan_md": implementation_plan_md,
            })

        # Build the export_data JSON blob for client-side rendering.
        # Diagram IDs match the template pattern: "{feature_index}-{diagram_index}"
        export_diagrams = []
        export_requirements = {}
        export_progress = {}
        export_agents = {}
        export_plans = {}
        for fi, feature in enumerate(features_data):
            for di, diagram in enumerate(feature["diagrams"]):
                export_diagrams.append({
                    "id": f"{fi}-{di}",
                    "content": diagram["content"],
                    "name": diagram["name"],
                })
            if feature.get("requirements_md"):
                export_requirements[feature["name"]] = feature["requirements_md"]
            if feature.get("progress_md"):
                export_progress[feature["name"]] = feature["progress_md"]
            if feature.get("agents_md"):
                export_agents[feature["name"]] = feature["agents_md"]
            if feature.get("implementation_plan_md"):
                export_plans[feature["name"]] = feature["implementation_plan_md"]

        # --- Ralph jobs ---
        ralph_jobs_data = []
        ralph_export_plans = {}
        ralph_export_progress = {}
        ralph_export_tasks = {}

        for job_sel in (selected_ralph_jobs or []):
            slug = job_sel["slug"]
            include_task = job_sel.get("include_task", True)
            include_plan = job_sel.get("include_plan", True)
            include_progress = job_sel.get("include_progress", True)

            task_md = ExportService.read_ralph_artifact(project_path, slug, "task.md") if include_task else None
            plan_md = ExportService.read_ralph_artifact(project_path, slug, "IMPLEMENTATION_PLAN.md") if include_plan else None
            progress_txt = ExportService.read_ralph_artifact(project_path, slug, "progress.txt") if include_progress else None

            if not task_md and not plan_md and not progress_txt:
                continue

            ralph_jobs_data.append({
                "slug": slug,
                "task_md": task_md,
                "plan_md": plan_md,
                "progress_txt": progress_txt,
            })

            if task_md:
                ralph_export_tasks[slug] = task_md
            if plan_md:
                ralph_export_plans[slug] = plan_md
            if progress_txt:
                ralph_export_progress[slug] = progress_txt

        export_data = {
            "diagrams": export_diagrams,
            "requirements": export_requirements,
            "progress": export_progress,
            "agents": export_agents,
            "implementation_plans": export_plans,
            "ralph_tasks": ralph_export_tasks,
            "ralph_plans": ralph_export_plans,
            "ralph_progress": ralph_export_progress,
        }

        # --- Offline vendor deps ---
        vendor_deps = {}
        if offline:
            for key in VENDOR_FILES:
                content = ExportService.read_vendor_file(key)
                if content:
                    vendor_deps[key] = content

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(config.VIEWS_DIR)),
            autoescape=True,
        )
        template = env.get_template("export.html")

        return template.render(
            project_name=project_name,
            export_date=datetime.now().strftime("%Y-%m-%d"),
            features=features_data,
            ralph_jobs=ralph_jobs_data,
            export_data=export_data,
            offline=offline,
            default_theme=default_theme,
            vendor_deps=vendor_deps,
        )
