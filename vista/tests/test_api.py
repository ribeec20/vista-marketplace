"""Tests for API endpoints - projects, loops, plans."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from server.models.loop_state import LoopInstance


@pytest.fixture
def api_env(tmp_path):
    """Set up isolated API test environment."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    projects_file = data_dir / "projects.json"
    projects_file.write_text("[]", encoding="utf-8")
    views_dir = Path(__file__).resolve().parent.parent / "server" / "views"
    static_dir = views_dir / "static"

    with (
        patch("server.config.DATA_DIR", data_dir),
        patch("server.config.PROJECTS_FILE", projects_file),
        patch("server.config.VIEWS_DIR", views_dir),
        patch("server.config.STATIC_DIR", static_dir),
        patch("server.services.project_service.DATA_DIR", data_dir),
        patch("server.services.project_service.PROJECTS_FILE", projects_file),
    ):
        from server.app import app

        yield TestClient(app), tmp_path


class TestProjectAPI:
    def test_list_projects_empty(self, api_env):
        """GET /api/projects should return empty list initially."""
        client, _ = api_env
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_register_project(self, api_env):
        """POST /api/projects should register a valid project."""
        client, tmp_path = api_env
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()

        resp = client.post("/api/projects", json={"path": str(project_dir)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my_project"
        assert "id" in data

    def test_register_project_invalid_path(self, api_env):
        """POST /api/projects should return 400 for invalid path."""
        client, _ = api_env
        resp = client.post("/api/projects", json={"path": "/nonexistent/path"})
        assert resp.status_code == 400

    def test_get_project(self, api_env):
        """GET /api/projects/{id} should return the project."""
        client, tmp_path = api_env
        project_dir = tmp_path / "get_proj"
        project_dir.mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.get(f"/api/projects/{reg['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "get_proj"

    def test_get_project_not_found(self, api_env):
        """GET /api/projects/{id} should return 404 for unknown ID."""
        client, _ = api_env
        resp = client.get("/api/projects/nonexistent")
        assert resp.status_code == 404

    def test_delete_project(self, api_env):
        """DELETE /api/projects/{id} should unregister the project."""
        client, tmp_path = api_env
        project_dir = tmp_path / "del_proj"
        project_dir.mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.delete(f"/api/projects/{reg['id']}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify it's gone
        resp = client.get(f"/api/projects/{reg['id']}")
        assert resp.status_code == 404

    def test_list_features(self, api_env):
        """GET /api/projects/{id}/features should scan feature directories."""
        client, tmp_path = api_env
        project_dir = tmp_path / "feat_proj"
        project_dir.mkdir()
        features_dir = project_dir / ".vista" / "features"
        features_dir.mkdir(parents=True)
        (features_dir / "alpha").mkdir()
        (features_dir / "beta").mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.get(f"/api/projects/{reg['id']}/features")
        assert resp.status_code == 200
        assert resp.json()["features"] == ["alpha", "beta"]


class TestLoopAPI:
    def test_get_loop_state_idle(self, api_env):
        """GET /api/projects/{id}/loop/state should return idle when no loop running."""
        client, tmp_path = api_env
        project_dir = tmp_path / "loop_proj"
        project_dir.mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.get(f"/api/projects/{reg['id']}/loop/state")
        assert resp.status_code == 200
        assert resp.json()["status"] == "idle"

    def test_get_loop_output_empty(self, api_env):
        """GET /api/projects/{id}/loop/output should return empty when no loop."""
        client, tmp_path = api_env
        project_dir = tmp_path / "output_proj"
        project_dir.mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.get(f"/api/projects/{reg['id']}/loop/output")
        assert resp.status_code == 200
        assert resp.json()["lines"] == []

    def test_start_loop_invalid_mode(self, api_env):
        """POST /api/projects/{id}/loop/start should reject invalid mode."""
        client, tmp_path = api_env
        project_dir = tmp_path / "invalid_mode"
        project_dir.mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.post(
            f"/api/projects/{reg['id']}/loop/start",
            json={"feature_name": "test", "mode": "invalid", "model": "sonnet"},
        )
        assert resp.status_code == 400

    def test_start_loop_invalid_model(self, api_env):
        """POST /api/projects/{id}/loop/start should reject invalid model."""
        client, tmp_path = api_env
        project_dir = tmp_path / "invalid_model"
        project_dir.mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.post(
            f"/api/projects/{reg['id']}/loop/start",
            json={"feature_name": "test", "mode": "build", "model": "gpt4"},
        )
        assert resp.status_code == 400


class TestDashboard:
    def test_dashboard_loads(self, api_env):
        """GET / should return the dashboard HTML."""
        client, _ = api_env
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Vista Dashboard" in resp.text

    def test_project_detail_page(self, api_env):
        """GET /project/{id} should return the project detail page."""
        client, tmp_path = api_env
        project_dir = tmp_path / "detail_proj"
        project_dir.mkdir()
        features_dir = project_dir / ".vista" / "features"
        features_dir.mkdir(parents=True)
        (features_dir / "mvp").mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.get(f"/project/{reg['id']}")
        assert resp.status_code == 200
        assert "detail_proj" in resp.text
        assert "mvp" in resp.text


class TestHealthAPI:
    def test_health_check(self, api_env):
        """GET /api/health should return ok status."""
        client, _ = api_env
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["running_loops"] == 0
        assert "version" in data

    def test_running_loops_summary(self, api_env):
        """GET /api/loops/running should include active loop metadata and recent actions."""
        client, tmp_path = api_env
        project_dir = tmp_path / "running_proj"
        project_dir.mkdir()
        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        state = LoopInstance(
            project_id=reg["id"],
            feature_name="mvp",
            mode="build",
            model="sonnet",
            provider="claude",
            provider_display_name="Claude Code",
            status="running",
            iteration=2,
            max_iterations=8,
            start_time="2026-02-12T09:00:00",
        )
        state.recent_actions.extend(
            [
                {"time": "2026-02-12T09:01:00", "type": "iteration", "message": "Iteration 1 started"},
                {"time": "2026-02-12T09:02:00", "type": "tool", "message": "> Tool: Read"},
            ]
        )

        with patch("server.app.loop_service.get_all_states", return_value={reg["id"]: state}):
            resp = client.get("/api/loops/running")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["count"] == 1
        loop = payload["loops"][0]
        assert loop["project_id"] == reg["id"]
        assert loop["project_name"] == "running_proj"
        assert loop["progress_percent"] == 25
        assert len(loop["recent_actions"]) == 2

    def test_running_loops_summary_includes_ralph_jobs(self, api_env):
        """GET /api/loops/running should include active Ralph jobs for global app-bar chips."""
        client, tmp_path = api_env
        project_dir = tmp_path / "ralph_running_proj"
        project_dir.mkdir()
        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        ralph_job = {
            "job_id": "job-123",
            "slug": "my-loop",
            "status": "running",
            "mode": "plan",
            "provider": "opencode",
            "model": "opencode/kimi-k2.5",
            "iterations": 2,
            "current_iteration": 1,
            "started_at": "2026-02-12T09:30:00",
            "created_at": "2026-02-12T09:30:00",
            "progress_tail": [
                "ITERATION 1 complete",
                "ITERATION 2 started",
            ],
        }

        with (
            patch("server.app.loop_service.get_all_states", return_value={}),
            patch("server.app.ralph_service.list_jobs", return_value=[ralph_job]),
            patch("server.app.ralph_service.get_job_status", return_value=ralph_job),
        ):
            resp = client.get("/api/loops/running")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["count"] == 1
        loop = payload["loops"][0]
        assert loop["kind"] == "ralph_job"
        assert loop["job_id"] == "job-123"
        assert loop["project_id"] == reg["id"]
        assert loop["project_name"] == "ralph_running_proj"

    def test_list_features_detailed(self, api_env):
        """GET /api/projects/{id}/features/detailed should return rich metadata."""
        client, tmp_path = api_env
        project_dir = tmp_path / "detail_feat_proj"
        project_dir.mkdir()
        features_dir = project_dir / ".vista" / "features"
        features_dir.mkdir(parents=True)

        # Feature with full setup
        feat1 = features_dir / "alpha"
        feat1.mkdir()
        (feat1 / "IMPLEMENTATION_PLAN.md").write_text("plan", encoding="utf-8")
        (feat1 / "AGENTS.md").write_text("agents", encoding="utf-8")
        (feat1 / "progress.txt").write_text("progress", encoding="utf-8")
        (feat1 / "PROMPT_build.md").write_text("build", encoding="utf-8")
        specs = feat1 / "specs"
        specs.mkdir()
        (specs / "spec1.md").write_text("spec", encoding="utf-8")
        (specs / "spec2.md").write_text("spec", encoding="utf-8")

        # Feature with minimal setup
        feat2 = features_dir / "beta"
        feat2.mkdir()

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.get(f"/api/projects/{reg['id']}/features/detailed")
        assert resp.status_code == 200
        features = resp.json()["features"]
        assert len(features) == 2

        alpha = features[0]
        assert alpha["name"] == "alpha"
        assert alpha["has_implementation_plan"] is True
        assert alpha["has_agents_md"] is True
        assert alpha["has_progress"] is True
        assert alpha["has_prompt_build"] is True
        assert alpha["spec_count"] == 2

        beta = features[1]
        assert beta["name"] == "beta"
        assert beta["has_implementation_plan"] is False
        assert beta["has_agents_md"] is False
        assert beta["has_progress"] is False
        assert beta["spec_count"] == 0

    def test_list_features_detailed_not_found(self, api_env):
        """GET /api/projects/{id}/features/detailed should 404 for unknown project."""
        client, _ = api_env
        resp = client.get("/api/projects/nonexistent/features/detailed")
        assert resp.status_code == 404


class TestPlanAPI:
    def test_get_plan(self, api_env):
        """GET /api/projects/{id}/features/{name}/plan should return plan data."""
        client, tmp_path = api_env
        project_dir = tmp_path / "plan_proj"
        project_dir.mkdir()
        feature_dir = project_dir / ".vista" / "features" / "feat1"
        feature_dir.mkdir(parents=True)
        (feature_dir / "IMPLEMENTATION_PLAN.md").write_text(
            "# Plan\nStep 1", encoding="utf-8"
        )

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.get(f"/api/projects/{reg['id']}/features/feat1/plan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["feature_name"] == "feat1"
        assert "# Plan" in data["implementation_plan"]

    def test_plan_preview_page(self, api_env):
        """GET /project/{id}/plan/{name} should render plan HTML."""
        client, tmp_path = api_env
        project_dir = tmp_path / "preview_proj"
        project_dir.mkdir()
        feature_dir = project_dir / ".vista" / "features" / "mvp"
        feature_dir.mkdir(parents=True)
        (feature_dir / "IMPLEMENTATION_PLAN.md").write_text(
            "# MVP Plan", encoding="utf-8"
        )

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()
        resp = client.get(f"/project/{reg['id']}/plan/mvp")
        assert resp.status_code == 200
        assert "MVP Plan" in resp.text
