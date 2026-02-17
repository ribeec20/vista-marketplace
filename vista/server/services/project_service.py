"""CRUD operations on server/data/projects.json. No database - just JSON file read/write."""
import json
from pathlib import Path
from typing import Optional
import shutil
from server.config import PROJECTS_FILE, DATA_DIR, _LEGACY_DATA_DIR
from server.models.project import Project


def _has_arch_manifest(feature_dir: Path) -> bool:
    """Check if feature has an arch/_arch.json manifest."""
    arch_file = feature_dir / "arch" / "_arch.json"
    if not arch_file.exists():
        return False
    try:
        data = json.loads(arch_file.read_text(encoding="utf-8"))
        if not data:
            return False
        # Support both formats: list of diagrams or dict with "diagrams" key
        if isinstance(data, list):
            return len(data) > 0
        return bool(data.get("diagrams"))
    except (json.JSONDecodeError, OSError):
        return False


def _count_arch_diagrams(feature_dir: Path) -> int:
    """Count .mmd and .drawio files in the arch/ directory."""
    arch_dir = feature_dir / "arch"
    if not arch_dir.exists():
        return 0
    count = len(list(arch_dir.glob("*.mmd")))
    count += len(list(arch_dir.glob("*.drawio")))
    return count


class ProjectService:
    """Manages the project registry stored in projects.json."""

    _migrated = False

    @staticmethod
    def _migrate_legacy_data():
        """One-time migration from plugin-internal data dir to ~/.vista/data/."""
        if ProjectService._migrated:
            return
        ProjectService._migrated = True

        legacy_projects = _LEGACY_DATA_DIR / "projects.json"
        if legacy_projects.exists() and not PROJECTS_FILE.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_projects, PROJECTS_FILE)

        # Also migrate sessions/ if present
        legacy_sessions = _LEGACY_DATA_DIR / "sessions"
        new_sessions = DATA_DIR / "sessions"
        if legacy_sessions.is_dir() and not new_sessions.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copytree(legacy_sessions, new_sessions)

    @staticmethod
    def _ensure_file():
        """Create data directory and projects.json if they don't exist."""
        ProjectService._migrate_legacy_data()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROJECTS_FILE.exists():
            PROJECTS_FILE.write_text("[]", encoding="utf-8")

    @staticmethod
    def _load() -> list[dict]:
        ProjectService._ensure_file()
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))

    @staticmethod
    def _save(projects: list[dict]):
        ProjectService._ensure_file()
        PROJECTS_FILE.write_text(json.dumps(projects, indent=2), encoding="utf-8")

    @staticmethod
    def get_all() -> list[Project]:
        """Return all registered projects."""
        return [Project.from_dict(p) for p in ProjectService._load()]

    @staticmethod
    def get_by_id(project_id: str) -> Optional[Project]:
        """Get a single project by ID."""
        for p in ProjectService._load():
            if p["id"] == project_id:
                return Project.from_dict(p)
        return None

    @staticmethod
    def register(path: str) -> Project:
        """Register a new project. Validates path exists."""
        abs_path = Path(path).resolve()
        if not abs_path.is_dir():
            raise ValueError(f"Path does not exist or is not a directory: {path}")

        projects = ProjectService._load()

        # Check for duplicate path
        for p in projects:
            if Path(p["path"]).resolve() == abs_path:
                raise ValueError(f"Project already registered: {abs_path}")

        project = Project(
            name=abs_path.name,
            path=str(abs_path),
        )
        projects.append(project.to_dict())
        ProjectService._save(projects)
        return project

    @staticmethod
    def unregister(project_id: str) -> bool:
        """Remove a project from the registry."""
        projects = ProjectService._load()
        filtered = [p for p in projects if p["id"] != project_id]
        if len(filtered) == len(projects):
            return False
        ProjectService._save(filtered)
        return True

    @staticmethod
    def scan_features(project_path: str) -> list[str]:
        """Scan a project's .vista/features/ directory for feature names."""
        features_dir = Path(project_path) / ".vista" / "features"
        if not features_dir.exists():
            return []
        features = []
        for d in sorted(features_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("_"):
                features.append(d.name)
        return features

    @staticmethod
    def scan_features_detailed(project_path: str) -> list[dict]:
        """Scan features with rich metadata about each feature's files.

        Returns list of dicts with feature name and which key files exist,
        enabling the dashboard to show feature readiness at a glance.
        """
        features_dir = Path(project_path) / ".vista" / "features"
        if not features_dir.exists():
            return []
        results = []
        for d in sorted(features_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            specs_dir = d / "specs"
            spec_count = len(list(specs_dir.glob("*.md"))) if specs_dir.exists() else 0
            results.append({
                "name": d.name,
                "has_implementation_plan": (d / "IMPLEMENTATION_PLAN.md").exists(),
                "has_agents_md": (d / "AGENTS.md").exists(),
                "has_progress": (d / "progress.txt").exists(),
                "has_prompt_build": (d / "PROMPT_build.md").exists(),
                "has_prompt_plan": (d / "PROMPT_plan.md").exists(),
                "spec_count": spec_count,
                "has_arch_manifest": _has_arch_manifest(d),
                "arch_diagram_count": _count_arch_diagrams(d),
            })
        return results
