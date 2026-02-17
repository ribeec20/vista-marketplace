"""Tests for architecture diagram features and chat functionality."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def arch_project(tmp_path):
    """Create a mock project with arch/ directory and sample diagrams."""
    project_dir = tmp_path / "arch_test_project"
    project_dir.mkdir()

    # Create feature with arch directory
    feature_dir = project_dir / ".vista" / "features" / "test-feature"
    feature_dir.mkdir(parents=True)

    arch_dir = feature_dir / "arch"
    arch_dir.mkdir()

    # Create _arch.json manifest
    manifest = {
        "feature": "test-feature",
        "diagrams": [
            {
                "name": "System Architecture",
                "file": "system-arch.mmd",
                "type": "mermaid",
                "diagramType": "flowchart",
                "description": "High-level system architecture",
            },
            {
                "name": "Data Flow",
                "file": "data-flow.mmd",
                "type": "mermaid",
                "diagramType": "sequence",
                "description": "Data flow between components",
            },
            {
                "name": "Entity Model",
                "file": "entity-model.drawio",
                "type": "drawio",
                "diagramType": "er",
                "description": "Entity relationship diagram",
            },
        ],
    }
    (arch_dir / "_arch.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Create sample .mmd files
    (arch_dir / "system-arch.mmd").write_text(
        "graph TD\n    A[Client] --> B[Server]\n    B --> C[Database]", encoding="utf-8"
    )
    (arch_dir / "data-flow.mmd").write_text(
        "sequenceDiagram\n    participant C as Client\n    participant S as Server\n    C->>S: Request",
        encoding="utf-8",
    )

    # Create sample .drawio file (XML content)
    (arch_dir / "entity-model.drawio").write_text(
        '<mxfile><diagram><mxGraphModel><root><mxCell id="0" /></root></mxGraphModel></diagram></mxfile>',
        encoding="utf-8",
    )

    return project_dir, feature_dir, arch_dir


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


class TestArchitectureAPI:
    """Tests for architecture diagram API endpoints."""

    def test_get_arch_manifest_success(self, api_env, arch_project):
        """GET /api/projects/{id}/features/{name}/arch returns manifest."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        # Register project
        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/api/projects/{reg['id']}/features/test-feature/arch")
        assert resp.status_code == 200
        data = resp.json()
        assert data["feature"] == "test-feature"
        assert len(data["diagrams"]) == 3
        assert data["diagrams"][0]["name"] == "System Architecture"

    def test_get_arch_manifest_not_found(self, api_env):
        """GET /api/projects/{id}/features/{name}/arch returns 404 when no manifest."""
        client, tmp_path = api_env
        project_dir = tmp_path / "no_arch_project"
        project_dir.mkdir()
        feature_dir = project_dir / ".vista" / "features" / "no-arch-feature"
        feature_dir.mkdir(parents=True)

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/api/projects/{reg['id']}/features/no-arch-feature/arch")
        assert resp.status_code == 404

    def test_get_arch_manifest_malformed_json(self, api_env):
        """GET /api/projects/{id}/features/{name}/arch returns 404 for malformed JSON."""
        client, tmp_path = api_env
        project_dir = tmp_path / "bad_json_project"
        project_dir.mkdir()
        arch_dir = project_dir / ".vista" / "features" / "bad-feature" / "arch"
        arch_dir.mkdir(parents=True)
        (arch_dir / "_arch.json").write_text("not valid json", encoding="utf-8")

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/api/projects/{reg['id']}/features/bad-feature/arch")
        assert resp.status_code == 404

    def test_get_arch_file_mmd_success(self, api_env, arch_project):
        """GET /api/projects/{id}/features/{name}/arch/{filename} returns .mmd content."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(
            f"/api/projects/{reg['id']}/features/test-feature/arch/system-arch.mmd"
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"
        assert "graph TD" in resp.text
        assert "Client" in resp.text

    def test_get_arch_file_drawio_content_type(self, api_env, arch_project):
        """GET /api/projects/{id}/features/{name}/arch/{filename} returns correct content-type for .drawio."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(
            f"/api/projects/{reg['id']}/features/test-feature/arch/entity-model.drawio"
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        assert "<mxfile>" in resp.text

    def test_get_arch_file_path_traversal_dotdot(self, api_env, arch_project):
        """GET /api/projects/{id}/features/{name}/arch/{filename} blocks .. path traversal."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(
            f"/api/projects/{reg['id']}/features/test-feature/arch/../../../etc/passwd"
        )
        assert resp.status_code == 404

    def test_get_arch_file_path_traversal_absolute(self, api_env, arch_project):
        """GET /api/projects/{id}/features/{name}/arch/{filename} blocks absolute path traversal."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(
            f"/api/projects/{reg['id']}/features/test-feature/arch//etc/passwd"
        )
        assert resp.status_code == 404

    def test_get_arch_file_not_found(self, api_env, arch_project):
        """GET /api/projects/{id}/features/{name}/arch/{filename} returns 404 for missing file."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(
            f"/api/projects/{reg['id']}/features/test-feature/arch/nonexistent.mmd"
        )
        assert resp.status_code == 404

    def test_architecture_page_renders(self, api_env, arch_project):
        """GET /project/{id}/arch/{feature_name} renders the architecture viewer page."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/project/{reg['id']}/arch/test-feature")
        assert resp.status_code == 200
        assert "Architecture" in resp.text or "test-feature" in resp.text

    def test_architecture_page_no_manifest(self, api_env):
        """GET /project/{id}/arch/{feature_name} shows empty state when no manifest."""
        client, tmp_path = api_env
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()
        feature_dir = project_dir / ".vista" / "features" / "empty-feature"
        feature_dir.mkdir(parents=True)

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/project/{reg['id']}/arch/empty-feature")
        assert resp.status_code == 200


class TestProgressServiceArch:
    """Tests for ProgressService architecture methods."""

    def test_read_arch_manifest_valid(self, tmp_path):
        """read_arch_manifest returns parsed JSON for valid manifest."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)

        manifest = {"feature": "test", "diagrams": []}
        (arch_dir / "_arch.json").write_text(json.dumps(manifest), encoding="utf-8")

        result = ProgressService.read_arch_manifest(str(tmp_path), "test")
        assert result == manifest

    def test_read_arch_manifest_missing_file(self, tmp_path):
        """read_arch_manifest returns None for missing manifest."""
        from server.services.progress_service import ProgressService

        result = ProgressService.read_arch_manifest(str(tmp_path), "nonexistent")
        assert result is None

    def test_read_arch_manifest_invalid_json(self, tmp_path):
        """read_arch_manifest returns None for invalid JSON."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)
        (arch_dir / "_arch.json").write_text("not json", encoding="utf-8")

        result = ProgressService.read_arch_manifest(str(tmp_path), "test")
        assert result is None

    def test_read_arch_file_valid_mmd(self, tmp_path):
        """read_arch_file returns content for valid .mmd file."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)
        (arch_dir / "diagram.mmd").write_text("graph TD\n    A-->B", encoding="utf-8")

        result = ProgressService.read_arch_file(str(tmp_path), "test", "diagram.mmd")
        assert result == "graph TD\n    A-->B"

    def test_read_arch_file_valid_drawio(self, tmp_path):
        """read_arch_file returns content for valid .drawio file."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)
        (arch_dir / "diagram.drawio").write_text("<xml></xml>", encoding="utf-8")

        result = ProgressService.read_arch_file(str(tmp_path), "test", "diagram.drawio")
        assert result == "<xml></xml>"

    def test_read_arch_file_path_traversal_dotdot(self, tmp_path):
        """read_arch_file blocks .. path traversal attempts."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)
        (arch_dir / "secret.txt").write_text("secret", encoding="utf-8")

        # Create file outside arch directory
        (tmp_path / "outside.txt").write_text("outside content", encoding="utf-8")

        result = ProgressService.read_arch_file(str(tmp_path), "test", "../outside.txt")
        assert result is None

    def test_read_arch_file_path_traversal_absolute(self, tmp_path):
        """read_arch_file blocks absolute path traversal attempts."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)

        result = ProgressService.read_arch_file(str(tmp_path), "test", "/etc/passwd")
        assert result is None

    def test_read_arch_file_not_found(self, tmp_path):
        """read_arch_file returns None for non-existent file."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)

        result = ProgressService.read_arch_file(str(tmp_path), "test", "missing.mmd")
        assert result is None


class TestSchemaValidation:
    """Tests for JSON schema validation."""

    def _get_template_path(self, filename: str) -> Path:
        """Get path to a template file relative to test location."""
        # Tests are in vista/tests/, templates are in vista/templates/
        return Path(__file__).parent.parent / "templates" / filename

    def test_plan_schema_valid_minimal(self):
        """plan-schema.json validates plan with only implementationPhases."""
        import jsonschema

        schema = json.loads(self._get_template_path("plan-schema.json").read_text())

        plan = {
            "meta": {
                "feature": "test",
                "version": 1,
                "created": "2025-01-01T00:00:00Z",
                "lastModified": "2025-01-01T00:00:00Z",
                "status": "draft",
                "description": "Test feature",
            },
            "sections": {"implementationPhases": {"phases": []}},
        }

        # Should not raise
        jsonschema.validate(plan, schema)

    def test_plan_schema_valid_with_architecture(self):
        """plan-schema.json validates plan with architecture.ref."""
        import jsonschema

        schema = json.loads(self._get_template_path("plan-schema.json").read_text())

        plan = {
            "meta": {
                "feature": "test",
                "version": 1,
                "created": "2025-01-01T00:00:00Z",
                "lastModified": "2025-01-01T00:00:00Z",
                "status": "draft",
                "description": "Test feature",
            },
            "sections": {
                "architecture": {"ref": "./arch/_arch.json"},
                "implementationPhases": {"phases": []},
            },
        }

        # Should not raise
        jsonschema.validate(plan, schema)

    def test_plan_schema_rejects_missing_phases(self):
        """plan-schema.json rejects plan missing implementationPhases."""
        import jsonschema

        schema = json.loads(self._get_template_path("plan-schema.json").read_text())

        plan = {
            "meta": {
                "feature": "test",
                "version": 1,
                "created": "2025-01-01T00:00:00Z",
                "lastModified": "2025-01-01T00:00:00Z",
                "status": "draft",
                "description": "Test feature",
            },
            "sections": {},
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(plan, schema)

    def test_arch_schema_valid_manifest(self):
        """arch-schema.json validates a valid manifest."""
        import jsonschema

        schema = json.loads(self._get_template_path("arch-schema.json").read_text())

        manifest = {
            "feature": "test",
            "diagrams": [
                {
                    "name": "Test Diagram",
                    "file": "test.mmd",
                    "type": "mermaid",
                    "diagramType": "flowchart",
                    "description": "A test diagram",
                }
            ],
        }

        # Should not raise
        jsonschema.validate(manifest, schema)

    def test_arch_schema_rejects_invalid_type(self):
        """arch-schema.json rejects invalid diagram type."""
        import jsonschema

        schema = json.loads(self._get_template_path("arch-schema.json").read_text())

        manifest = {
            "feature": "test",
            "diagrams": [
                {
                    "name": "Test Diagram",
                    "file": "test.mmd",
                    "type": "invalid_type",
                    "diagramType": "flowchart",
                    "description": "A test diagram",
                }
            ],
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(manifest, schema)

    def test_arch_schema_rejects_missing_fields(self):
        """arch-schema.json rejects manifest with missing required fields."""
        import jsonschema

        schema = json.loads(self._get_template_path("arch-schema.json").read_text())

        manifest = {
            "feature": "test",
            "diagrams": [
                {
                    "name": "Test Diagram"
                    # Missing file, type, diagramType
                }
            ],
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(manifest, schema)


class TestProjectServiceArch:
    """Tests for ProjectService architecture-related methods."""

    def test_scan_features_detailed_has_arch_manifest(self, tmp_path):
        """scan_features_detailed includes has_arch_manifest field."""
        from server.services.project_service import ProjectService

        # Create feature with arch manifest
        arch_dir = tmp_path / ".vista" / "features" / "with-arch" / "arch"
        arch_dir.mkdir(parents=True)
        manifest = {
            "feature": "with-arch",
            "diagrams": [
                {
                    "name": "D",
                    "file": "d.mmd",
                    "type": "mermaid",
                    "diagramType": "flowchart",
                    "description": "",
                }
            ],
        }
        (arch_dir / "_arch.json").write_text(json.dumps(manifest), encoding="utf-8")
        (arch_dir / "d.mmd").write_text("graph TD", encoding="utf-8")

        # Create feature without arch
        no_arch_dir = tmp_path / ".vista" / "features" / "no-arch"
        no_arch_dir.mkdir(parents=True)

        features = ProjectService.scan_features_detailed(str(tmp_path))

        # Find features by name
        with_arch = next(f for f in features if f["name"] == "with-arch")
        without_arch = next(f for f in features if f["name"] == "no-arch")

        assert with_arch["has_arch_manifest"] is True
        assert without_arch["has_arch_manifest"] is False

    def test_scan_features_detailed_arch_diagram_count(self, tmp_path):
        """scan_features_detailed includes arch_diagram_count field."""
        from server.services.project_service import ProjectService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)

        # Create actual diagram files (count is based on files, not manifest)
        (arch_dir / "d1.mmd").write_text("graph TD\n    A-->B", encoding="utf-8")
        (arch_dir / "d2.mmd").write_text(
            "sequenceDiagram\n    A->>B: msg", encoding="utf-8"
        )
        (arch_dir / "d3.drawio").write_text("<mxfile></mxfile>", encoding="utf-8")

        features = ProjectService.scan_features_detailed(str(tmp_path))

        assert features[0]["arch_diagram_count"] == 3

    def test_scan_features_detailed_no_arch(self, tmp_path):
        """scan_features_detailed returns 0 count for feature without arch directory."""
        from server.services.project_service import ProjectService

        feature_dir = tmp_path / ".vista" / "features" / "test"
        feature_dir.mkdir(parents=True)

        features = ProjectService.scan_features_detailed(str(tmp_path))

        assert features[0]["has_arch_manifest"] is False
        assert features[0]["arch_diagram_count"] == 0


class TestContextAssembler:
    """Tests for ContextAssembler prompt helpers."""

    def test_build_prompt_includes_context(self):
        """build_full_prompt includes diagram context before message."""
        from server.services.context_assembler import ContextAssembler

        prompt = ContextAssembler.build_full_prompt(
            message="What do you think?", context="graph TD\n    A-->B", history=None
        )

        assert "DIAGRAM CONTEXT" in prompt
        assert "graph TD" in prompt
        assert "What do you think?" in prompt

    def test_build_prompt_ignores_history(self):
        """build_full_prompt ignores history — providers maintain it natively."""
        from server.services.context_assembler import ContextAssembler

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        prompt = ContextAssembler.build_full_prompt(
            message="What's next?", context=None, history=history
        )

        # History should NOT be re-sent
        assert "CONVERSATION HISTORY" not in prompt
        assert "Hi there" not in prompt
        # Current message should be present
        assert "What's next?" in prompt

    def test_build_prompt_works_with_empty_context_and_history(self):
        """build_full_prompt works with no context or history."""
        from server.services.context_assembler import ContextAssembler

        prompt = ContextAssembler.build_full_prompt(
            message="Hello", context=None, history=None
        )

        assert "Hello" in prompt


class TestProgressServiceWrite:
    """Tests for ProgressService.write_arch_file()."""

    def test_write_arch_file_md_success(self, tmp_path):
        """write_arch_file() writes .md content to arch/."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)

        result = ProgressService.write_arch_file(str(tmp_path), "test", "notes.md", "# Hello")
        assert result is True
        assert (arch_dir / "notes.md").read_text(encoding="utf-8") == "# Hello"

    def test_write_arch_file_mmd_rejected(self, tmp_path):
        """write_arch_file() rejects .mmd files."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)

        result = ProgressService.write_arch_file(str(tmp_path), "test", "diagram.mmd", "graph TD")
        assert result is False

    def test_write_arch_file_puml_rejected(self, tmp_path):
        """write_arch_file() rejects .puml files."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)

        result = ProgressService.write_arch_file(str(tmp_path), "test", "diagram.puml", "@startuml")
        assert result is False

    def test_write_arch_file_path_traversal(self, tmp_path):
        """write_arch_file() blocks ../evil path."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)

        result = ProgressService.write_arch_file(str(tmp_path), "test", "../evil.md", "pwned")
        assert result is False

    def test_write_arch_file_no_arch_dir(self, tmp_path):
        """write_arch_file() returns False when arch/ doesn't exist."""
        from server.services.progress_service import ProgressService

        result = ProgressService.write_arch_file(str(tmp_path), "test", "notes.md", "# Hello")
        assert result is False

    def test_write_arch_file_overwrites_existing(self, tmp_path):
        """write_arch_file() overwrites an existing .md file."""
        from server.services.progress_service import ProgressService

        arch_dir = tmp_path / ".vista" / "features" / "test" / "arch"
        arch_dir.mkdir(parents=True)
        (arch_dir / "notes.md").write_text("old content", encoding="utf-8")

        result = ProgressService.write_arch_file(str(tmp_path), "test", "notes.md", "new content")
        assert result is True
        assert (arch_dir / "notes.md").read_text(encoding="utf-8") == "new content"


class TestArchWriteAPI:
    """Tests for PUT /api/projects/{id}/features/{name}/arch/{filename}."""

    def test_put_markdown_file_success(self, api_env, arch_project):
        """PUT .md file writes content and returns 200."""
        client, tmp_path = api_env
        project_dir, _, arch_dir = arch_project

        # Create a .md file in arch/
        (arch_dir / "notes.md").write_text("# Old", encoding="utf-8")

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.put(
            f"/api/projects/{reg['id']}/features/test-feature/arch/notes.md",
            json={"content": "# New Content"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert (arch_dir / "notes.md").read_text(encoding="utf-8") == "# New Content"

    def test_put_non_markdown_file_rejected(self, api_env, arch_project):
        """PUT .mmd file returns 400."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.put(
            f"/api/projects/{reg['id']}/features/test-feature/arch/system-arch.mmd",
            json={"content": "graph TD"},
        )
        assert resp.status_code == 400

    def test_put_path_traversal_blocked(self, api_env, arch_project):
        """PUT with path traversal is blocked (returns 4xx)."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        # URL-encoded slashes may be decoded by the framework, resulting in
        # either a 400 (path validation) or 404 (route mismatch). Both are
        # correct security outcomes — the traversal is blocked.
        resp = client.put(
            f"/api/projects/{reg['id']}/features/test-feature/arch/..%2F..%2Fevil.md",
            json={"content": "pwned"},
        )
        assert resp.status_code in (400, 404)

    def test_put_dotdot_in_filename(self, api_env, arch_project):
        """PUT with '..' anywhere in filename is blocked (returns 4xx)."""
        client, tmp_path = api_env
        project_dir, _, _ = arch_project

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.put(
            f"/api/projects/{reg['id']}/features/test-feature/arch/..%2Fevil.md",
            json={"content": "pwned"},
        )
        assert resp.status_code in (400, 404)

    def test_put_project_not_found(self, api_env):
        """PUT to nonexistent project returns 404."""
        client, tmp_path = api_env

        resp = client.put(
            "/api/projects/nonexistent-id/features/test/arch/notes.md",
            json={"content": "test"},
        )
        assert resp.status_code == 404

    def test_put_no_arch_directory(self, api_env):
        """PUT to feature without arch/ returns 400."""
        client, tmp_path = api_env
        project_dir = tmp_path / "no_arch"
        project_dir.mkdir()
        feature_dir = project_dir / ".vista" / "features" / "no-arch-feature"
        feature_dir.mkdir(parents=True)

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.put(
            f"/api/projects/{reg['id']}/features/no-arch-feature/arch/notes.md",
            json={"content": "test"},
        )
        assert resp.status_code == 400

    def test_put_verify_file_written(self, api_env, arch_project):
        """After successful PUT, GET returns the new content."""
        client, tmp_path = api_env
        project_dir, _, arch_dir = arch_project

        (arch_dir / "readme.md").write_text("old", encoding="utf-8")

        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        # Write
        client.put(
            f"/api/projects/{reg['id']}/features/test-feature/arch/readme.md",
            json={"content": "# Updated"},
        )

        # Read back
        resp = client.get(
            f"/api/projects/{reg['id']}/features/test-feature/arch/readme.md"
        )
        assert resp.status_code == 200
        assert resp.text == "# Updated"


class TestExtendedSchemaValidation:
    """Tests for extended arch-schema.json type enum."""

    def _get_template_path(self, filename: str) -> Path:
        return Path(__file__).parent.parent / "templates" / filename

    def _make_manifest(self, diagram_type: str) -> dict:
        return {
            "feature": "test",
            "diagrams": [
                {
                    "name": "Test",
                    "file": "test.mmd",
                    "type": diagram_type,
                    "diagramType": "custom",
                    "description": "A test",
                }
            ],
        }

    def test_arch_schema_accepts_plantuml_type(self):
        """arch-schema.json accepts plantuml type."""
        import jsonschema

        schema = json.loads(self._get_template_path("arch-schema.json").read_text())
        jsonschema.validate(self._make_manifest("plantuml"), schema)

    def test_arch_schema_accepts_d2_type(self):
        """arch-schema.json accepts d2 type."""
        import jsonschema

        schema = json.loads(self._get_template_path("arch-schema.json").read_text())
        jsonschema.validate(self._make_manifest("d2"), schema)

    def test_arch_schema_accepts_graphviz_type(self):
        """arch-schema.json accepts graphviz type."""
        import jsonschema

        schema = json.loads(self._get_template_path("arch-schema.json").read_text())
        jsonschema.validate(self._make_manifest("graphviz"), schema)

    def test_arch_schema_accepts_markdown_type(self):
        """arch-schema.json accepts markdown type."""
        import jsonschema

        schema = json.loads(self._get_template_path("arch-schema.json").read_text())
        jsonschema.validate(self._make_manifest("markdown"), schema)


class TestContentTypes:
    """Tests for content-type headers on GET arch file endpoint."""

    def test_get_puml_returns_text_plain(self, api_env, arch_project):
        """GET .puml file returns text/plain content-type."""
        client, tmp_path = api_env
        project_dir, _, arch_dir = arch_project

        (arch_dir / "class.puml").write_text("@startuml\nclass Foo\n@enduml", encoding="utf-8")
        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/api/projects/{reg['id']}/features/test-feature/arch/class.puml")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"

    def test_get_d2_returns_text_plain(self, api_env, arch_project):
        """GET .d2 file returns text/plain content-type."""
        client, tmp_path = api_env
        project_dir, _, arch_dir = arch_project

        (arch_dir / "arch.d2").write_text("a -> b", encoding="utf-8")
        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/api/projects/{reg['id']}/features/test-feature/arch/arch.d2")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"

    def test_get_dot_returns_text_plain(self, api_env, arch_project):
        """GET .dot file returns text/plain content-type."""
        client, tmp_path = api_env
        project_dir, _, arch_dir = arch_project

        (arch_dir / "graph.dot").write_text("digraph G { a -> b; }", encoding="utf-8")
        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/api/projects/{reg['id']}/features/test-feature/arch/graph.dot")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"

    def test_get_md_returns_text_markdown(self, api_env, arch_project):
        """GET .md file returns text/markdown content-type."""
        client, tmp_path = api_env
        project_dir, _, arch_dir = arch_project

        (arch_dir / "notes.md").write_text("# Hello", encoding="utf-8")
        reg = client.post("/api/projects", json={"path": str(project_dir)}).json()

        resp = client.get(f"/api/projects/{reg['id']}/features/test-feature/arch/notes.md")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/markdown; charset=utf-8"


class TestDiagramSettings:
    """Tests for diagram settings in config."""

    def test_get_diagram_settings_default(self, tmp_path):
        """Default plantuml_server_url is plantuml.com."""
        from server.config import get_diagram_settings, _DIAGRAM_DEFAULTS

        with patch("server.config.SETTINGS_FILE", tmp_path / "settings.json"):
            settings = get_diagram_settings()
            assert settings["plantuml_server_url"] == "https://www.plantuml.com/plantuml"

    def test_get_diagram_settings_override(self, tmp_path):
        """Custom plantuml_server_url from settings.json is returned."""
        from server.config import get_diagram_settings

        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps({"diagrams": {"plantuml_server_url": "http://localhost:8080/plantuml"}}),
            encoding="utf-8",
        )

        with patch("server.config.SETTINGS_FILE", settings_file):
            settings = get_diagram_settings()
            assert settings["plantuml_server_url"] == "http://localhost:8080/plantuml"
