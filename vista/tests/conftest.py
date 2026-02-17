"""Shared test fixtures for the Vista server and tool groups."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add vendor/ to sys.path so tests can import vendored packages (e.g. claude_teams)
_VENDOR_DIR = str(Path(__file__).resolve().parent.parent / "vendor")
if _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory with empty projects.json."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    projects_file = data_dir / "projects.json"
    projects_file.write_text("[]", encoding="utf-8")
    return data_dir, projects_file


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory with .vista/features/ structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create feature directories
    features_dir = project_dir / ".vista" / "features"
    features_dir.mkdir(parents=True)

    feature1 = features_dir / "feature_a"
    feature1.mkdir()
    (feature1 / "IMPLEMENTATION_PLAN.md").write_text("# Test Plan\nSome plan content", encoding="utf-8")
    (feature1 / "PROMPT_build.md").write_text("Build prompt content", encoding="utf-8")

    feature2 = features_dir / "feature_b"
    feature2.mkdir()

    return project_dir


@pytest.fixture
def patched_config(tmp_data_dir, tmp_path):
    """Patch server.config to use temporary directories."""
    data_dir, projects_file = tmp_data_dir
    views_dir = Path(__file__).resolve().parent.parent / "server" / "views"
    static_dir = views_dir / "static"

    with patch("server.config.DATA_DIR", data_dir), \
         patch("server.config.PROJECTS_FILE", projects_file), \
         patch("server.config.VIEWS_DIR", views_dir), \
         patch("server.config.STATIC_DIR", static_dir), \
         patch("server.services.project_service.DATA_DIR", data_dir), \
         patch("server.services.project_service.PROJECTS_FILE", projects_file):
        yield


@pytest.fixture
def test_client(patched_config):
    """Create a FastAPI test client with patched config."""
    from server.app import app
    return TestClient(app)
