"""Tests for project service - JSON-based project CRUD."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from server.services.project_service import ProjectService


@pytest.fixture
def project_env(tmp_path):
    """Set up isolated project service with temp directories."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    projects_file = data_dir / "projects.json"
    projects_file.write_text("[]", encoding="utf-8")

    with patch("server.services.project_service.DATA_DIR", data_dir), \
         patch("server.services.project_service.PROJECTS_FILE", projects_file):
        yield tmp_path, projects_file


class TestProjectService:
    def test_get_all_empty(self, project_env):
        """Should return empty list when no projects registered."""
        assert ProjectService.get_all() == []

    def test_register_project(self, project_env):
        """Should register a valid project directory."""
        tmp_path, _ = project_env
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()

        project = ProjectService.register(str(project_dir))
        assert project.name == "my_project"
        assert project.path == str(project_dir.resolve())
        assert len(project.id) == 8

    def test_register_nonexistent_path_raises(self, project_env):
        """Should raise ValueError for paths that don't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            ProjectService.register("/nonexistent/path/xyz")

    def test_register_duplicate_raises(self, project_env):
        """Should raise ValueError when registering the same path twice."""
        tmp_path, _ = project_env
        project_dir = tmp_path / "dup_project"
        project_dir.mkdir()

        ProjectService.register(str(project_dir))
        with pytest.raises(ValueError, match="already registered"):
            ProjectService.register(str(project_dir))

    def test_get_by_id(self, project_env):
        """Should retrieve a project by its ID."""
        tmp_path, _ = project_env
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        registered = ProjectService.register(str(project_dir))
        found = ProjectService.get_by_id(registered.id)
        assert found is not None
        assert found.id == registered.id
        assert found.name == registered.name

    def test_get_by_id_not_found(self, project_env):
        """Should return None for unknown ID."""
        assert ProjectService.get_by_id("nonexistent") is None

    def test_unregister(self, project_env):
        """Should remove a project from the registry."""
        tmp_path, _ = project_env
        project_dir = tmp_path / "to_remove"
        project_dir.mkdir()

        project = ProjectService.register(str(project_dir))
        assert ProjectService.unregister(project.id) is True
        assert ProjectService.get_by_id(project.id) is None

    def test_unregister_not_found(self, project_env):
        """Should return False for unknown project ID."""
        assert ProjectService.unregister("nonexistent") is False

    def test_scan_features(self, project_env):
        """Should scan .vista/features/ directory for feature names."""
        tmp_path, _ = project_env
        project_dir = tmp_path / "scan_proj"
        project_dir.mkdir()

        features_dir = project_dir / ".vista" / "features"
        features_dir.mkdir(parents=True)
        (features_dir / "alpha").mkdir()
        (features_dir / "beta").mkdir()
        (features_dir / "_hidden").mkdir()  # Should be excluded

        features = ProjectService.scan_features(str(project_dir))
        assert features == ["alpha", "beta"]

    def test_scan_features_no_features_dir(self, project_env):
        """Should return empty list when .vista/features/ doesn't exist."""
        tmp_path, _ = project_env
        project_dir = tmp_path / "no_features"
        project_dir.mkdir()

        features = ProjectService.scan_features(str(project_dir))
        assert features == []

    def test_persistence(self, project_env):
        """Registered projects should persist across service calls."""
        tmp_path, projects_file = project_env
        project_dir = tmp_path / "persist"
        project_dir.mkdir()

        ProjectService.register(str(project_dir))

        # Read directly from JSON file
        data = json.loads(projects_file.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["name"] == "persist"
