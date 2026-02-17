"""Read progress.txt, IMPLEMENTATION_PLAN.md, and architecture manifests from feature directories."""
import json
from pathlib import Path
from typing import Optional


class ProgressService:

    @staticmethod
    def read_progress(project_path: str, feature_name: str) -> dict:
        """Read and parse progress.txt for a feature."""
        import re
        feature_dir = Path(project_path) / ".vista" / "features" / feature_name
        progress_file = feature_dir / "progress.txt"

        if not progress_file.exists():
            return {"exists": False, "content": "", "all_complete": False}

        content = progress_file.read_text(encoding="utf-8")

        # Extract phase info
        phase_match = re.search(r"Phase:\s*(\w+)", content)
        current_phase_match = re.search(r"CurrentPhase:\s*(\d+)", content)

        return {
            "exists": True,
            "content": content,
            "phase": phase_match.group(1) if phase_match else None,
            "current_phase": int(current_phase_match.group(1)) if current_phase_match else None,
            "all_complete": content.strip().startswith("ALL PHASES COMPLETE")
                           or "ALL PHASES COMPLETE" in content,
        }

    @staticmethod
    def read_implementation_plan(project_path: str, feature_name: str) -> Optional[str]:
        """Read IMPLEMENTATION_PLAN.md if it exists."""
        plan_file = Path(project_path) / ".vista" / "features" / feature_name / "IMPLEMENTATION_PLAN.md"
        if plan_file.exists():
            return plan_file.read_text(encoding="utf-8")
        return None

    @staticmethod
    def read_agents_md(project_path: str, feature_name: str) -> Optional[str]:
        """Read AGENTS.md if it exists."""
        agents_file = Path(project_path) / ".vista" / "features" / feature_name / "AGENTS.md"
        if agents_file.exists():
            return agents_file.read_text(encoding="utf-8")
        return None

    @staticmethod
    def read_arch_manifest(project_path: str, feature_name: str) -> Optional[dict]:
        """Read arch/_arch.json manifest for a feature."""
        arch_file = Path(project_path) / ".vista" / "features" / feature_name / "arch" / "_arch.json"
        if not arch_file.exists():
            return None
        try:
            data = json.loads(arch_file.read_text(encoding="utf-8"))
            # Normalize legacy format: bare list -> dict with "diagrams" key
            if isinstance(data, list):
                data = {"feature": feature_name, "diagrams": data}
            return data
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def read_domain_requirements(project_path: str, feature_name: str) -> Optional[str]:
        """Read domain-requirements.md for a feature, returning raw markdown or None."""
        req_file = Path(project_path) / ".vista" / "features" / feature_name / "domain-requirements.md"
        if not req_file.exists():
            return None
        try:
            content = req_file.read_text(encoding="utf-8")
            return content if content.strip() else None
        except OSError:
            return None

    @staticmethod
    def read_arch_file(project_path: str, feature_name: str, filename: str) -> Optional[str]:
        """Read a specific diagram file from arch/ with path traversal prevention."""
        # Prevent path traversal
        safe_name = Path(filename).name
        if safe_name != filename or ".." in filename:
            return None

        arch_dir = Path(project_path) / ".vista" / "features" / feature_name / "arch"
        target = arch_dir / safe_name

        # Ensure resolved path is within arch_dir
        try:
            target.resolve().relative_to(arch_dir.resolve())
        except ValueError:
            return None

        if not target.exists():
            return None

        return target.read_text(encoding="utf-8")

    @staticmethod
    def write_arch_file(project_path: str, feature_name: str, filename: str, content: str) -> bool:
        """Write content to a diagram file in arch/ with path traversal prevention.

        Only allows writing to files with extensions: .md
        Returns True on success, False on validation failure.
        """
        WRITABLE_EXTENSIONS = {".md"}

        safe_name = Path(filename).name
        if safe_name != filename or ".." in filename:
            return False

        if Path(safe_name).suffix not in WRITABLE_EXTENSIONS:
            return False

        arch_dir = Path(project_path) / ".vista" / "features" / feature_name / "arch"
        target = arch_dir / safe_name

        try:
            target.resolve().relative_to(arch_dir.resolve())
        except ValueError:
            return False

        if not arch_dir.exists():
            return False

        target.write_text(content, encoding="utf-8")
        return True
