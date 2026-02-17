"""Tests for export_service and export routes."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _setup_feature(
    project_path: Path,
    feature_name: str,
    diagrams=None,
    requirements=None,
    progress=None,
    agents_md=None,
    implementation_plan=None,
):
    """Create a feature directory with optional arch manifest, diagrams, requirements, progress, agents, and plan."""
    feature_dir = project_path / ".vista" / "features" / feature_name
    feature_dir.mkdir(parents=True, exist_ok=True)

    if diagrams is not None:
        arch_dir = feature_dir / "arch"
        arch_dir.mkdir(exist_ok=True)
        manifest = {"feature": feature_name, "diagrams": []}
        for d in diagrams:
            manifest["diagrams"].append({
                "name": d["name"],
                "file": d["file"],
                "type": d.get("type", "mermaid"),
                "description": d.get("description", ""),
                "category": d.get("category", "architecture"),
            })
            if "content" in d:
                (arch_dir / d["file"]).write_text(d["content"], encoding="utf-8")
        (arch_dir / "_arch.json").write_text(json.dumps(manifest), encoding="utf-8")

    if requirements is not None:
        (feature_dir / "domain-requirements.md").write_text(requirements, encoding="utf-8")

    if progress is not None:
        (feature_dir / "progress.txt").write_text(progress, encoding="utf-8")

    if agents_md is not None:
        (feature_dir / "AGENTS.md").write_text(agents_md, encoding="utf-8")

    if implementation_plan is not None:
        (feature_dir / "IMPLEMENTATION_PLAN.md").write_text(implementation_plan, encoding="utf-8")


class TestProgressServiceReadDomainRequirements:
    def test_returns_content_when_file_exists(self, tmp_path):
        from server.services.progress_service import ProgressService

        _setup_feature(tmp_path, "my_feature", requirements="# Requirements\n- Req 1")
        result = ProgressService.read_domain_requirements(str(tmp_path), "my_feature")
        assert result is not None
        assert "Req 1" in result

    def test_returns_none_when_file_missing(self, tmp_path):
        from server.services.progress_service import ProgressService

        feature_dir = tmp_path / ".vista" / "features" / "no_reqs"
        feature_dir.mkdir(parents=True)
        result = ProgressService.read_domain_requirements(str(tmp_path), "no_reqs")
        assert result is None

    def test_returns_none_when_file_empty(self, tmp_path):
        from server.services.progress_service import ProgressService

        _setup_feature(tmp_path, "empty_feature", requirements="   \n  ")
        result = ProgressService.read_domain_requirements(str(tmp_path), "empty_feature")
        assert result is None


class TestExportServiceGetExportableFeatures:
    def test_returns_features_with_diagrams(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "feat_a", diagrams=[
            {"name": "System Arch", "file": "system-arch.mmd", "content": "graph TD; A-->B"},
        ])
        result = ExportService.get_exportable_features(str(tmp_path))
        assert len(result) == 1
        assert result[0]["name"] == "feat_a"
        assert len(result[0]["diagrams"]) == 1
        assert result[0]["diagrams"][0]["file"] == "system-arch.mmd"

    def test_excludes_empty_features(self, tmp_path):
        from server.services.export_service import ExportService

        # Feature with no diagrams and no requirements
        feature_dir = tmp_path / ".vista" / "features" / "empty_feat"
        feature_dir.mkdir(parents=True)
        result = ExportService.get_exportable_features(str(tmp_path))
        assert len(result) == 0

    def test_includes_requirements_only_feature(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "reqs_only", requirements="# Reqs\n- Item 1")
        result = ExportService.get_exportable_features(str(tmp_path))
        assert len(result) == 1
        assert result[0]["name"] == "reqs_only"
        assert result[0]["has_requirements"] is True
        assert len(result[0]["diagrams"]) == 0

    def test_skips_underscore_prefixed_dirs(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "_planning", requirements="# Planning\n- Internal")
        result = ExportService.get_exportable_features(str(tmp_path))
        assert len(result) == 0

    def test_returns_empty_when_no_features_dir(self, tmp_path):
        from server.services.export_service import ExportService

        result = ExportService.get_exportable_features(str(tmp_path))
        assert result == []


class TestExportableFeaturesV2ContentTypes:
    """Tests for Phase 1: progress, agents_md, and implementation_plan detection."""

    def test_exportable_features_includes_progress_only(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "progress_feat", progress="Phase: build\nIteration 1")
        result = ExportService.get_exportable_features(str(tmp_path))
        assert len(result) == 1
        assert result[0]["name"] == "progress_feat"
        assert result[0]["has_progress"] is True
        assert result[0]["has_requirements"] is False

    def test_exportable_features_includes_plan_only(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "plan_feat", implementation_plan="# Plan\n## Phase 1")
        result = ExportService.get_exportable_features(str(tmp_path))
        assert len(result) == 1
        assert result[0]["name"] == "plan_feat"
        assert result[0]["has_implementation_plan"] is True
        assert result[0]["has_requirements"] is False

    def test_exportable_features_reports_new_flags(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(
            tmp_path, "full_feat",
            requirements="# Reqs",
            progress="Phase: plan",
            agents_md="# Agents\n- Agent 1",
            implementation_plan="# Plan\n## Phase 1",
        )
        result = ExportService.get_exportable_features(str(tmp_path))
        assert len(result) == 1
        feat = result[0]
        assert feat["has_requirements"] is True
        assert feat["has_progress"] is True
        assert feat["has_agents_md"] is True
        assert feat["has_implementation_plan"] is True

    def test_generate_html_includes_progress(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "feat_p", progress="Iteration 1: did stuff")
        html = ExportService.generate_export_html(
            project_name="Test",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_p", "diagrams": []}],
        )
        assert "Iteration 1: did stuff" in html
        assert "Progress Log" in html

    def test_generate_html_includes_plan(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "feat_plan", implementation_plan="# Phase 1\nDo the thing")
        html = ExportService.generate_export_html(
            project_name="Test",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_plan", "diagrams": []}],
        )
        assert "Phase 1" in html
        assert "Implementation Plan" in html

    def test_generate_html_includes_agents(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "feat_agents", agents_md="# Team\n- Researcher\n- Builder")
        html = ExportService.generate_export_html(
            project_name="Test",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_agents", "diagrams": []}],
        )
        assert "Researcher" in html
        assert "Agents" in html

    def test_generate_html_respects_content_toggles(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(
            tmp_path, "feat_toggle",
            requirements="# Reqs",
            progress="Progress text",
            agents_md="# Agents",
            implementation_plan="# Plan",
        )
        html = ExportService.generate_export_html(
            project_name="Test",
            project_path=str(tmp_path),
            selected_features=[{
                "name": "feat_toggle",
                "diagrams": [],
                "include_requirements": False,
                "include_progress": False,
                "include_agents": False,
                "include_implementation_plan": True,
            }],
        )
        # Plan should be present
        assert "Implementation Plan" in html
        # Others should NOT be present (no content sections rendered)
        assert "Domain Requirements" not in html
        assert "Progress Log" not in html
        # "Agents" heading should not appear (but "Agents" in data might)
        assert "agents-feat_toggle" not in html


class TestExportServiceGenerateHtml:
    def test_basic_export(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "my_feature", diagrams=[
            {"name": "Overview", "file": "overview.mmd", "content": "graph TD; A-->B"},
        ], requirements="# Requirements\n- Item 1")

        html = ExportService.generate_export_html(
            project_name="TestProject",
            project_path=str(tmp_path),
            selected_features=[{"name": "my_feature", "diagrams": ["overview.mmd"]}],
        )

        assert "TestProject" in html
        assert "mermaid" in html.lower()
        assert "graph TD" in html
        assert "Requirements" in html

    def test_multiple_features(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "feat_a", diagrams=[
            {"name": "Arch A", "file": "arch-a.mmd", "content": "graph LR; A-->B"},
        ])
        _setup_feature(tmp_path, "feat_b", diagrams=[
            {"name": "Arch B", "file": "arch-b.mmd", "content": "graph LR; C-->D"},
        ])

        html = ExportService.generate_export_html(
            project_name="MultiProject",
            project_path=str(tmp_path),
            selected_features=[
                {"name": "feat_a", "diagrams": ["arch-a.mmd"]},
                {"name": "feat_b", "diagrams": ["arch-b.mmd"]},
            ],
        )

        assert "feat_a" in html
        assert "feat_b" in html
        # Navigation should be present for multiple features
        assert 'href="#feature-feat_a"' in html
        assert 'href="#feature-feat_b"' in html

    def test_missing_diagram_file_skipped(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "feat_c", diagrams=[
            {"name": "Exists", "file": "exists.mmd", "content": "graph TD; X-->Y"},
            {"name": "Missing", "file": "missing.mmd"},  # no content = no file on disk
        ])

        html = ExportService.generate_export_html(
            project_name="Test",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_c", "diagrams": ["exists.mmd", "missing.mmd"]}],
        )

        # Diagram content is embedded as JSON, so check for escaped version
        assert "graph TD; X" in html
        assert "Exists" in html
        # The missing diagram should be skipped gracefully
        assert "Test" in html

    def test_missing_manifest_includes_requirements(self, tmp_path):
        from server.services.export_service import ExportService

        # Feature with requirements but no _arch.json
        _setup_feature(tmp_path, "reqs_feat", requirements="# Domain Reqs\n- Important thing")

        html = ExportService.generate_export_html(
            project_name="ReqsTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "reqs_feat", "diagrams": []}],
        )

        assert "Important thing" in html
        assert "ReqsTest" in html

    def test_empty_selection_returns_minimal_html(self, tmp_path):
        from server.services.export_service import ExportService

        html = ExportService.generate_export_html(
            project_name="Empty",
            project_path=str(tmp_path),
            selected_features=[],
        )

        assert "Empty" in html
        assert "<!DOCTYPE html>" in html


class TestExportRoutes:
    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with a registered project."""
        from unittest.mock import patch, MagicMock

        # Setup test feature
        _setup_feature(tmp_path, "test_feature", diagrams=[
            {"name": "Test Diagram", "file": "test.mmd", "content": "graph TD; A-->B"},
        ], requirements="# Test Requirements")

        mock_project = MagicMock()
        mock_project.id = "test-123"
        mock_project.name = "TestProject"
        mock_project.path = str(tmp_path)

        with patch("server.routes.export.ProjectService") as mock_ps:
            mock_ps.get_by_id.return_value = mock_project

            from fastapi.testclient import TestClient
            from fastapi import FastAPI

            app = FastAPI()
            from server.routes.export import router
            app.include_router(router)

            yield TestClient(app), mock_ps

    def test_get_export_features(self, client):
        test_client, _ = client
        resp = test_client.get("/api/projects/test-123/export/features")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "test_feature"
        assert len(data[0]["diagrams"]) == 1

    def test_post_export(self, client):
        test_client, _ = client
        resp = test_client.post("/api/projects/test-123/export", json={
            "features": [{"name": "test_feature", "diagrams": ["test.mmd"]}]
        })
        assert resp.status_code == 200
        assert "Content-Disposition" in resp.headers
        assert "TestProject" in resp.headers["Content-Disposition"]
        assert "<!DOCTYPE html>" in resp.text

    def test_post_export_invalid_project(self, tmp_path):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from fastapi import FastAPI

        app = FastAPI()
        from server.routes.export import router
        app.include_router(router)

        with patch("server.routes.export.ProjectService") as mock_ps:
            mock_ps.get_by_id.return_value = None
            test_client = TestClient(app)
            resp = test_client.post("/api/projects/nonexistent/export", json={
                "features": [{"name": "x", "diagrams": []}]
            })
            assert resp.status_code == 404


def _setup_ralph_job(
    project_path: Path,
    slug: str,
    job_meta: dict | None = None,
    task: str | None = None,
    plan: str | None = None,
    progress: str | None = None,
):
    """Create a Ralph job directory with optional artifacts."""
    job_dir = project_path / ".vista" / "ralph" / slug
    job_dir.mkdir(parents=True, exist_ok=True)

    if job_meta is not None:
        (job_dir / "job.json").write_text(json.dumps(job_meta), encoding="utf-8")

    if task is not None:
        (job_dir / "task.md").write_text(task, encoding="utf-8")

    if plan is not None:
        (job_dir / "IMPLEMENTATION_PLAN.md").write_text(plan, encoding="utf-8")

    if progress is not None:
        (job_dir / "progress.txt").write_text(progress, encoding="utf-8")


class TestExportableRalphJobs:
    """Tests for Phase 2: Ralph job artifact discovery and export."""

    def test_returns_empty_when_no_ralph_dir(self, tmp_path):
        from server.services.export_service import ExportService

        result = ExportService.get_exportable_ralph_jobs(str(tmp_path))
        assert result == []

    def test_discovers_ralph_jobs_with_task(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_ralph_job(tmp_path, "my-build-job", task="Build the widget")
        result = ExportService.get_exportable_ralph_jobs(str(tmp_path))
        assert len(result) == 1
        assert result[0]["slug"] == "my-build-job"
        assert result[0]["has_task"] is True
        assert result[0]["has_plan"] is False
        assert result[0]["has_progress"] is False

    def test_discovers_ralph_jobs_with_all_artifacts(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_ralph_job(
            tmp_path, "full-job",
            job_meta={"mode": "build", "status": "completed"},
            task="Do the thing",
            plan="# Phase 1\nBuild it",
            progress="Iteration 1: done",
        )
        result = ExportService.get_exportable_ralph_jobs(str(tmp_path))
        assert len(result) == 1
        job = result[0]
        assert job["slug"] == "full-job"
        assert job["mode"] == "build"
        assert job["status"] == "completed"
        assert job["has_task"] is True
        assert job["has_plan"] is True
        assert job["has_progress"] is True

    def test_skips_empty_ralph_dirs(self, tmp_path):
        from server.services.export_service import ExportService

        # Create a ralph dir with no exportable files
        empty_dir = tmp_path / ".vista" / "ralph" / "empty-job"
        empty_dir.mkdir(parents=True)
        (empty_dir / "output.log").write_text("log data", encoding="utf-8")
        result = ExportService.get_exportable_ralph_jobs(str(tmp_path))
        assert len(result) == 0

    def test_read_ralph_artifact_returns_content(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_ralph_job(tmp_path, "read-job", task="My task content")
        result = ExportService.read_ralph_artifact(str(tmp_path), "read-job", "task.md")
        assert result == "My task content"

    def test_read_ralph_artifact_blocks_non_exportable(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_ralph_job(tmp_path, "block-job", task="task")
        # output.log is not in the whitelist
        result = ExportService.read_ralph_artifact(str(tmp_path), "block-job", "output.log")
        assert result is None

    def test_read_ralph_artifact_blocks_path_traversal(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_ralph_job(tmp_path, "safe-job", task="task")
        result = ExportService.read_ralph_artifact(str(tmp_path), "../../../etc", "task.md")
        assert result is None

    def test_generate_html_includes_ralph_jobs(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_ralph_job(
            tmp_path, "html-job",
            task="# Build Widget\nMake the widget work",
            plan="# Phase 1\nStep 1: Do it",
            progress="Iteration 1: completed step 1",
        )
        html = ExportService.generate_export_html(
            project_name="RalphTest",
            project_path=str(tmp_path),
            selected_features=[],
            selected_ralph_jobs=[{"slug": "html-job"}],
        )
        assert "Build Widget" in html
        assert "Phase 1" in html
        assert "Iteration 1" in html
        assert "Ralph Job" in html

    def test_generate_html_respects_ralph_content_toggles(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_ralph_job(
            tmp_path, "toggle-job",
            task="Task content here",
            plan="Plan content here",
            progress="Progress content here",
        )
        html = ExportService.generate_export_html(
            project_name="ToggleTest",
            project_path=str(tmp_path),
            selected_features=[],
            selected_ralph_jobs=[{
                "slug": "toggle-job",
                "include_task": True,
                "include_plan": False,
                "include_progress": False,
            }],
        )
        assert "Task content here" in html
        assert "ralph-plan-toggle-job" not in html
        assert "ralph-progress-toggle-job" not in html

    def test_generate_html_mixed_features_and_ralph(self, tmp_path):
        from server.services.export_service import ExportService

        _setup_feature(tmp_path, "my_feature", requirements="# Reqs\n- Item 1")
        _setup_ralph_job(tmp_path, "my-ralph", task="Ralph task")

        html = ExportService.generate_export_html(
            project_name="MixedTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "my_feature", "diagrams": []}],
            selected_ralph_jobs=[{"slug": "my-ralph"}],
        )
        assert "my_feature" in html
        assert "Ralph task" in html
        assert "Ralph Job" in html


class TestExportRalphRoutes:
    @pytest.fixture
    def ralph_client(self, tmp_path):
        """Create a test client with Ralph jobs."""
        _setup_ralph_job(
            tmp_path, "test-build",
            job_meta={"mode": "build", "status": "completed"},
            task="Build the feature",
            plan="# Plan\n## Phase 1",
            progress="Iteration 1: done",
        )

        mock_project = MagicMock()
        mock_project.id = "test-456"
        mock_project.name = "RalphProject"
        mock_project.path = str(tmp_path)

        with patch("server.routes.export.ProjectService") as mock_ps:
            mock_ps.get_by_id.return_value = mock_project

            from fastapi.testclient import TestClient
            from fastapi import FastAPI

            app = FastAPI()
            from server.routes.export import router
            app.include_router(router)

            yield TestClient(app), mock_ps

    def test_get_ralph_jobs_endpoint(self, ralph_client):
        test_client, _ = ralph_client
        resp = test_client.get("/api/projects/test-456/export/ralph-jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["slug"] == "test-build"
        assert data[0]["has_task"] is True
        assert data[0]["has_plan"] is True

    def test_export_with_ralph_jobs(self, ralph_client):
        test_client, _ = ralph_client
        resp = test_client.post("/api/projects/test-456/export", json={
            "features": [],
            "ralph_jobs": [{"slug": "test-build"}],
        })
        assert resp.status_code == 200
        assert "<!DOCTYPE html>" in resp.text
        assert "Build the feature" in resp.text


class TestOfflineMode:
    """Tests for Phase 3: Offline-First inline CDN dependencies."""

    def test_read_vendor_file_returns_content(self):
        from server.services.export_service import ExportService
        content = ExportService.read_vendor_file("marked_js")
        assert content is not None
        assert len(content) > 100

    def test_read_vendor_file_returns_none_for_unknown_key(self):
        from server.services.export_service import ExportService
        content = ExportService.read_vendor_file("nonexistent")
        assert content is None

    def test_online_mode_uses_cdn(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_feature(tmp_path, "feat_a", requirements="# Reqs")
        html = ExportService.generate_export_html(
            project_name="OnlineTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_a", "diagrams": []}],
            offline=False,
        )
        assert "cdn.tailwindcss.com" in html
        assert "cdn.jsdelivr.net/npm/mermaid" in html
        assert "cdn.jsdelivr.net/npm/marked" in html

    def test_offline_mode_inlines_vendor_deps(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_feature(tmp_path, "feat_offline", requirements="# Reqs")
        html = ExportService.generate_export_html(
            project_name="OfflineTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_offline", "diagrams": []}],
            offline=True,
        )
        # Should NOT have CDN links
        assert "cdn.tailwindcss.com" not in html
        assert "cdn.jsdelivr.net" not in html
        # Should have inline content (tailwind CSS has a recognizable comment)
        assert "tailwind-inline" in html
        # Should have mermaid inlined (contains mermaid's code)
        assert "mermaid" in html.lower()

    def test_offline_mode_via_route(self, tmp_path):
        from unittest.mock import patch, MagicMock

        _setup_feature(tmp_path, "route_feat", requirements="# Reqs")

        mock_project = MagicMock()
        mock_project.id = "off-123"
        mock_project.name = "OfflineRouteTest"
        mock_project.path = str(tmp_path)

        with patch("server.routes.export.ProjectService") as mock_ps:
            mock_ps.get_by_id.return_value = mock_project

            from fastapi.testclient import TestClient
            from fastapi import FastAPI
            from server.routes.export import router

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            resp = client.post("/api/projects/off-123/export", json={
                "features": [{"name": "route_feat", "diagrams": []}],
                "offline": True,
            })
            assert resp.status_code == 200
            assert "cdn.tailwindcss.com" not in resp.text
            assert "tailwind-inline" in resp.text


class TestThemeAndToc:
    """Tests for Phase 4: Theme toggle and Table of Contents."""

    def test_default_theme_is_dark(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_feature(tmp_path, "feat_theme", requirements="# Reqs")
        html = ExportService.generate_export_html(
            project_name="ThemeTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_theme", "diagrams": []}],
        )
        assert 'data-theme="dark"' in html

    def test_light_theme_default(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_feature(tmp_path, "feat_light", requirements="# Reqs")
        html = ExportService.generate_export_html(
            project_name="LightTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_light", "diagrams": []}],
            default_theme="light",
        )
        assert 'data-theme="light"' in html

    def test_theme_toggle_button_present(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_feature(tmp_path, "feat_btn", requirements="# Reqs")
        html = ExportService.generate_export_html(
            project_name="ToggleTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_btn", "diagrams": []}],
        )
        assert "theme-toggle" in html
        assert "toggleTheme()" in html

    def test_toc_sidebar_present(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_feature(tmp_path, "feat_toc", requirements="# Reqs")
        html = ExportService.generate_export_html(
            project_name="TocTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "feat_toc", "diagrams": []}],
        )
        assert "toc-sidebar" in html
        assert "Table of Contents" in html
        assert "toggleToc()" in html

    def test_toc_contains_feature_links(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_feature(tmp_path, "alpha_feat", requirements="# Alpha Reqs")
        _setup_feature(tmp_path, "beta_feat", requirements="# Beta Reqs")
        html = ExportService.generate_export_html(
            project_name="TocLinksTest",
            project_path=str(tmp_path),
            selected_features=[
                {"name": "alpha_feat", "diagrams": []},
                {"name": "beta_feat", "diagrams": []},
            ],
        )
        assert 'href="#feature-alpha_feat"' in html
        assert 'href="#feature-beta_feat"' in html

    def test_toc_contains_ralph_links(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_ralph_job(tmp_path, "toc-ralph", task="A task")
        html = ExportService.generate_export_html(
            project_name="TocRalphTest",
            project_path=str(tmp_path),
            selected_features=[],
            selected_ralph_jobs=[{"slug": "toc-ralph"}],
        )
        assert 'href="#ralph-toc-ralph"' in html

    def test_theme_via_route(self, tmp_path):
        from unittest.mock import patch, MagicMock

        _setup_feature(tmp_path, "theme_feat", requirements="# Reqs")

        mock_project = MagicMock()
        mock_project.id = "theme-123"
        mock_project.name = "ThemeRouteTest"
        mock_project.path = str(tmp_path)

        with patch("server.routes.export.ProjectService") as mock_ps:
            mock_ps.get_by_id.return_value = mock_project

            from fastapi.testclient import TestClient
            from fastapi import FastAPI
            from server.routes.export import router

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            resp = client.post("/api/projects/theme-123/export", json={
                "features": [{"name": "theme_feat", "diagrams": []}],
                "default_theme": "light",
            })
            assert resp.status_code == 200
            assert 'data-theme="light"' in resp.text

    def test_css_custom_properties_present(self, tmp_path):
        from server.services.export_service import ExportService
        _setup_feature(tmp_path, "vars_feat", requirements="# Reqs")
        html = ExportService.generate_export_html(
            project_name="VarsTest",
            project_path=str(tmp_path),
            selected_features=[{"name": "vars_feat", "diagrams": []}],
        )
        assert "--bg-primary" in html
        assert "--text-primary" in html
        assert '[data-theme="light"]' in html
        assert '[data-theme="dark"]' in html
