# Implementation Plan: share_docs (Documentation Export)

## Overview

Add a documentation export system to the Vista dashboard that produces a single self-contained HTML file with architecture diagrams (Mermaid) and domain requirements (rendered markdown) for selected features. The exported file works on any device with internet (CDN dependencies for Mermaid.js, Tailwind CSS, Marked.js), no server required.

## Architecture Summary

```
project.html ─── "Export Documentation" button (next to "Remove Project")
       │
       ▼
 Export Modal (JS) ─── GET /api/projects/{id}/export/features
       │                         │
       │                         ▼
       │              ExportService.get_exportable_features()
       │              (scans .vista/features/, reads _arch.json + domain-requirements.md)
       │
       ▼
 POST /api/projects/{id}/export
       │
       ▼
 ExportService.generate_export_html()
       │
       ├── Read _arch.json manifests (via ProgressService.read_arch_manifest)
       ├── Read .mmd diagram sources (via ProgressService.read_arch_file)
       ├── Read domain-requirements.md (via ProgressService.read_domain_requirements — new)
       └── Render export.html Jinja2 template
       │
       ▼
 Response (Content-Disposition: attachment; filename="project-docs-2026-02-13.html")
```

---

## Step 1: Add `read_domain_requirements()` to ProgressService

**File:** `vista/server/services/progress_service.py`
**Action:** MODIFY — add one new static method after `read_arch_file()` (line ~84)

```python
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
```

**Why:** The existing `ProgressService` has `read_arch_manifest` and `read_arch_file` but nothing for domain requirements. This follows the same pattern: static method, returns `Optional`, handles missing/empty/error cases.

**Existing methods on ProgressService:**
- `read_progress(project_path, feature_name)` → Optional[str]
- `read_implementation_plan(project_path, feature_name)` → Optional[str]
- `read_agents_md(project_path, feature_name)` → Optional[str]
- `read_arch_manifest(project_path, feature_name)` → Optional[dict]
- `read_arch_file(project_path, feature_name, filename)` → Optional[str]

---

## Step 2: Create ExportService

**File:** `vista/server/services/export_service.py` (NEW)

### Class design:

```python
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import jinja2

from server import config
from server.services.progress_service import ProgressService

logger = logging.getLogger(__name__)


class ExportService:
    @staticmethod
    def get_exportable_features(project_path: str) -> list[dict]:
        """Return features with their diagrams and requirements availability.

        Scans .vista/features/ for features that have at least one diagram
        OR non-empty domain-requirements.md.

        Returns:
            [
                {
                    "name": "feature_name",
                    "has_requirements": True,
                    "diagrams": [
                        {
                            "name": "System Architecture",
                            "file": "system-architecture.mmd",
                            "type": "mermaid",
                            "description": "...",
                            "category": "architecture"
                        }
                    ]
                }
            ]
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

            if not diagrams and not has_requirements:
                continue

            results.append({
                "name": d.name,
                "has_requirements": has_requirements,
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
    def generate_export_html(
        project_name: str,
        project_path: str,
        selected_features: list[dict],  # [{"name": str, "diagrams": [str]}]
    ) -> str:
        """Generate self-contained HTML export.

        For each selected feature:
        1. Read _arch.json manifest
        2. Filter diagrams to only those selected
        3. Read .mmd content for each selected diagram
        4. Read domain-requirements.md
        5. Assemble into template context and render

        Returns rendered HTML string.
        """
        features_data = []

        for selection in selected_features:
            feature_name = selection["name"]  # Pydantic model field
            selected_diagram_files = selection["diagrams"]

            # Get manifest to resolve diagram metadata
            manifest = ProgressService.read_arch_manifest(project_path, feature_name)
            all_diagrams = manifest.get("diagrams", []) if manifest else []

            # Build diagram data for selected diagrams
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

            # Get requirements
            requirements_md = ProgressService.read_domain_requirements(
                project_path, feature_name
            )

            # Only include feature if it has content
            if not diagram_data and not requirements_md:
                continue

            features_data.append({
                "name": feature_name,
                "diagrams": diagram_data,
                "requirements_md": requirements_md,
            })

        # Render Jinja2 template
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(config.VIEWS_DIR)),
            autoescape=True,
        )
        template = env.get_template("export.html")

        return template.render(
            project_name=project_name,
            export_date=datetime.now().strftime("%Y-%m-%d"),
            features=features_data,
        )
```

### Key behaviors:

- **`get_exportable_features()`**: Reuses `ProgressService.read_arch_manifest()` and the new `read_domain_requirements()`. Filters out features with no diagrams AND no requirements. Uses the same directory iteration pattern as `ProjectService.scan_features_detailed()`.

- **`generate_export_html()`**: Collects diagram content and requirements, renders via Jinja2. Uses `jinja2.Environment` with `FileSystemLoader` pointed at `config.VIEWS_DIR` (same dir as `_base.html`, `architecture.html`, etc.).

- **Edge cases:**
  - Missing `_arch.json` → `manifest` is None → no diagrams, include requirements only
  - Empty `domain-requirements.md` → `read_domain_requirements` returns None → skip requirements
  - `.mmd` file not found → `read_arch_file` returns None → skip that diagram, log warning
  - Corrupt JSON in `_arch.json` → `read_arch_manifest` returns None → skip diagrams

### Jinja2 autoescape note:

**IMPORTANT**: The template uses `autoescape=True` for safety, but diagram Mermaid source and requirements markdown must be embedded as JavaScript string data (not raw HTML) so that:
1. Mermaid source is rendered client-side via `mermaid.render()`
2. Requirements markdown is rendered client-side via `marked.parse()`

The template will embed these as JSON data in a `<script>` block using the `|tojson` Jinja2 filter, which safely escapes for JS context.

---

## Step 3: Create Export Routes

**File:** `vista/server/routes/export.py` (NEW)

```python
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from server.services.export_service import ExportService
from server.services.project_service import ProjectService

logger = logging.getLogger(__name__)
router = APIRouter()


class ExportFeatureSelection(BaseModel):
    name: str
    diagrams: list[str]  # list of filenames, e.g. ["system-architecture.mmd"]


class ExportRequest(BaseModel):
    features: list[ExportFeatureSelection]


@router.get("/api/projects/{project_id}/export/features")
async def get_export_features(project_id: str):
    """Return the feature tree for the export modal checklist."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ExportService.get_exportable_features(project.path)


@router.post("/api/projects/{project_id}/export")
async def export_documentation(project_id: str, body: ExportRequest):
    """Generate and return the exported HTML documentation file."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    html = ExportService.generate_export_html(
        project_name=project.name,
        project_path=project.path,
        selected_features=[f.model_dump() for f in body.features],
    )

    filename = f"{project.name}-docs-{datetime.now().strftime('%Y-%m-%d')}.html"

    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

### Route registration in `app.py`:

Add at line ~83 (after existing `include_router` calls):

```python
from server.routes import export
app.include_router(export.router)
```

**Response shapes:**

GET `/api/projects/{id}/export/features`:
```json
[
  {
    "name": "diagram_representations",
    "has_requirements": true,
    "diagrams": [
      {"name": "System Architecture", "file": "system-architecture.mmd",
       "type": "mermaid", "description": "...", "category": "architecture"}
    ]
  }
]
```

POST `/api/projects/{id}/export`:
- Returns HTML file as attachment with `Content-Disposition` header

---

## Step 4: Create Export HTML Template

**File:** `vista/server/views/export.html` (NEW)

A **standalone** HTML file (NOT extending `_base.html`) that is self-contained when rendered. The resulting HTML works without any server.

### Template structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_name }} - Documentation Export</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked@15/marked.min.js"></script>
    <style>
        /* Vista dark theme styles extracted from architecture.html */
        /* .diagram-card, .diagram-header, .diagram-body, .diagram-viewport */
        /* .diagram-zoom-controls, .badge, .badge-arch, .badge-tdd */
        /* Modal overlay styles */
        /* Requirements section styles */
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <!-- Header -->
    <header class="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
            <div class="flex items-center gap-3">
                <span class="text-green-400 font-semibold text-lg">Vista Dashboard</span>
                <span class="text-gray-600">·</span>
                <span class="text-xl font-bold">{{ project_name }}</span>
            </div>
            <span class="text-gray-400 text-sm">Exported {{ export_date }}</span>
        </div>
    </header>

    <!-- Feature Navigation (if multiple features) -->
    {% if features|length > 1 %}
    <nav class="bg-gray-800/50 border-b border-gray-700 px-6 py-2">
        <div class="max-w-7xl mx-auto flex gap-4">
            {% for feature in features %}
            <a href="#feature-{{ feature.name }}"
               class="text-sm text-gray-400 hover:text-gray-200 transition-colors">
                {{ feature.name }}
            </a>
            {% endfor %}
        </div>
    </nav>
    {% endif %}

    <main class="max-w-7xl mx-auto px-6 py-8">
        {% for feature in features %}
        <section id="feature-{{ feature.name }}" class="mb-12">
            <h2 class="text-2xl font-bold mb-6 capitalize">
                {{ feature.name | replace('_', ' ') }}
            </h2>

            <!-- Diagram Card Gallery -->
            {% if feature.diagrams %}
            <div class="space-y-6 mb-8">
                {% for diagram in feature.diagrams %}
                <div class="diagram-card" data-idx="{{ loop.index0 }}">
                    <div class="diagram-header">
                        <div class="flex items-center gap-2 flex-1 min-w-0">
                            <span class="font-semibold text-sm">{{ diagram.name }}</span>
                            <span class="badge {{ 'badge-tdd' if diagram.category == 'tdd' else 'badge-arch' }}">
                                {{ diagram.category or 'architecture' }}
                            </span>
                            {% if diagram.description %}
                            <span class="text-gray-500 text-xs truncate hidden sm:inline">
                                {{ diagram.description }}
                            </span>
                            {% endif %}
                        </div>
                        <button onclick="expandDiagram({{ loop.index0 }})"
                                class="diagram-expand-btn" title="Expand">&#x26F6;</button>
                    </div>
                    <div class="diagram-body">
                        <div class="diagram-viewport" id="viewport-{{ loop.index0 }}">
                            <div class="mermaid-placeholder" id="mermaid-{{ loop.index0 }}">
                                Loading...
                            </div>
                        </div>
                        <div class="diagram-zoom-controls">
                            <button onclick="zoomDiagram({{ loop.index0 }}, -0.2)">&minus;</button>
                            <button onclick="resetZoom({{ loop.index0 }})">1:1</button>
                            <button onclick="zoomDiagram({{ loop.index0 }}, 0.2)">+</button>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <!-- Domain Requirements (rendered client-side via marked.js) -->
            {% if feature.requirements_md %}
            <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
                <h3 class="text-lg font-semibold mb-4">Domain Requirements</h3>
                <div class="requirements-content prose prose-invert max-w-none"
                     id="requirements-{{ feature.name }}">
                </div>
            </div>
            {% endif %}
        </section>
        {% endfor %}
    </main>

    <!-- Modal Overlay (for expanded diagram view) -->
    <div id="diagram-modal" class="fixed inset-0 bg-black/80 z-50 hidden flex items-center justify-center"
         onclick="closeModal(event)">
        <div class="bg-gray-900 rounded-lg border border-gray-700 w-[95vw] h-[90vh] flex flex-col"
             onclick="event.stopPropagation()">
            <div class="flex items-center justify-between px-4 py-3 border-b border-gray-700">
                <span id="modal-title" class="font-semibold"></span>
                <button onclick="closeModal()" class="text-gray-400 hover:text-white text-xl">&times;</button>
            </div>
            <div class="flex-1 overflow-auto p-4" id="modal-content"></div>
        </div>
    </div>

    <!-- Data: embed diagram sources and requirements as JSON for client-side rendering -->
    <script id="export-data" type="application/json">
        {{ {
            "features": features | map(attribute='name') | list,
            "diagrams": features | sum(attribute='diagrams', start=[]) | map(attribute='content') | list,
            "diagram_names": features | sum(attribute='diagrams', start=[]) | map(attribute='name') | list,
            "requirements": dict(features | map(attribute='name') | zip(features | map(attribute='requirements_md')))
        } | tojson }}
    </script>

    <script>
        // Parse embedded data
        const EXPORT_DATA = JSON.parse(
            document.getElementById('export-data').textContent
        );

        // --- Mermaid Init ---
        mermaid.initialize({
            startOnLoad: false,
            theme: 'dark',
            themeVariables: {
                darkMode: true,
                background: '#0f172a',
                primaryColor: '#1e3a5f',
                primaryTextColor: '#e2e8f0',
                primaryBorderColor: '#475569',
                lineColor: '#94a3b8',
                secondaryColor: '#1a2332',
                tertiaryColor: '#0f172a',
                fontSize: '14px',
            }
        });

        // --- Marked config ---
        marked.setOptions({ breaks: true, gfm: true });

        // --- Render all diagrams ---
        // ... (render each mermaid-N placeholder using EXPORT_DATA.diagrams[N])

        // --- Render all requirements ---
        // ... (for each feature with requirements, use marked.parse())

        // --- Pan/zoom (same as architecture.html) ---
        // ... (initViewport, zoomDiagram, resetZoom, applyTransform)

        // --- Modal expand/close ---
        // ... (expandDiagram, closeModal)

        // --- Feature nav smooth scroll ---
        // ... (anchor click handlers)
    </script>
</body>
</html>
```

### CRITICAL: Data embedding strategy

The Jinja2 template **MUST NOT** embed raw Mermaid source or raw markdown directly in HTML elements. Instead:

1. **All diagram content and requirements markdown** are embedded as a JSON blob inside a `<script type="application/json">` tag using Jinja2's `|tojson` filter (which properly escapes `<`, `>`, `&`, quotes, etc.)
2. JavaScript parses this JSON on page load
3. Mermaid diagrams are rendered client-side via `mermaid.render(id, source)`
4. Requirements markdown is rendered client-side via `marked.parse(markdown)`

This avoids HTML injection issues and ensures Mermaid source (which contains `-->`, `<`, etc.) doesn't break the HTML.

**Alternative approach (simpler):** Since the Jinja2 Environment uses `autoescape=True`, we could pass each diagram's content as a Jinja2 variable and embed it in a per-diagram `<script type="text/plain">` tag. The JS then reads `.textContent` from each. Either approach works; the JSON blob approach is cleaner for multiple data items.

### CSS to extract from architecture.html:

Copy these exact styles from `architecture.html` (lines 10-112):
- `.diagram-card` (background, border, border-radius, overflow, transitions, cursor)
- `.diagram-header` (padding, border-bottom, flex layout)
- `.diagram-body` (position relative, overflow hidden, background, min/max height)
- `.diagram-viewport` (width, height, cursor grab, transform-origin, padding)
- `.diagram-viewport .mermaid svg` overrides (stroke-width, font-size)
- `.diagram-zoom-controls` (position absolute, bottom/right, flex, z-index)
- `.diagram-zoom-controls button` (sizing, styling)
- `.badge`, `.badge-arch`, `.badge-tdd` (category badge styles)
- `.diagram-expand-btn` (expand button style)

**Do not copy**: Chat panel styles (`.chat-*`), attach indicator styles (`.attach-*`), node selection styles (`.node-selected`), session popup styles — these are not needed for the static export.

### JS to include (simplified versions from architecture.html):

1. **Mermaid init** — copy exact theme variables from architecture.html lines 1224-1238
2. **marked config** — `marked.setOptions({ breaks: true, gfm: true })`
3. **Diagram rendering loop** — iterate over EXPORT_DATA, call `mermaid.render()` for each
4. **Requirements rendering** — iterate over features, call `marked.parse()` for each
5. **Pan/zoom** — copy `initViewport`, `applyTransform`, `zoomDiagram`, `resetZoom` from architecture.html lines 1323-1375
6. **Modal expand/close** — simplified version: copy diagram SVG into modal, add close handler
7. **Feature nav** — smooth scroll on anchor click

---

## Step 5: Add Export Modal to Project Page

**File:** `vista/server/views/project.html` (MODIFY)

### Changes:

#### 5a. Add "Export Documentation" button

Location: In the project header, next to the "Remove Project" button (line ~11-14).

```html
<!-- Before the Remove Project button, add: -->
<button onclick="openExportModal()"
        class="px-3 py-1.5 rounded border border-blue-600 text-blue-300 hover:bg-blue-900/30 text-sm transition-colors">
    Export Docs
</button>
```

#### 5b. Add Export Modal HTML

Location: At the bottom of `{% block content %}`, before `{% endblock %}` (after the loops section).

```html
<!-- Export Modal -->
<div id="export-modal" class="fixed inset-0 bg-black/60 z-50 hidden flex items-center justify-center">
    <div class="bg-gray-800 rounded-lg border border-gray-700 w-full max-w-lg max-h-[80vh] flex flex-col">
        <!-- Header -->
        <div class="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
            <h3 class="font-semibold">Export Documentation</h3>
            <button onclick="closeExportModal()" class="text-gray-400 hover:text-white">&times;</button>
        </div>

        <!-- Tree Content -->
        <div class="flex-1 overflow-y-auto p-4" id="export-tree">
            <div class="text-gray-500 text-center py-8">Click "Export Docs" to load features</div>
        </div>

        <!-- Footer -->
        <div class="px-4 py-3 border-t border-gray-700 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <button onclick="selectAllExport(true)" class="text-xs text-blue-400 hover:text-blue-300">Select All</button>
                <button onclick="selectAllExport(false)" class="text-xs text-gray-400 hover:text-gray-300">Deselect All</button>
            </div>
            <button id="export-download-btn" onclick="startExport()" disabled
                    class="px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                Download
            </button>
        </div>
    </div>
</div>
```

#### 5c. Add JavaScript

Location: Inside `{% block scripts %}` at the bottom of project.html.

```javascript
// =========================================================================
// Export Modal
// =========================================================================

let exportFeatures = [];

async function openExportModal() {
    const modal = document.getElementById('export-modal');
    const tree = document.getElementById('export-tree');
    modal.classList.remove('hidden');
    tree.innerHTML = '<div class="text-gray-500 text-center py-8">Loading features...</div>';

    try {
        const resp = await fetch(`/api/projects/${PROJECT_ID}/export/features`);
        if (!resp.ok) throw new Error('Failed to load features');
        exportFeatures = await resp.json();

        if (exportFeatures.length === 0) {
            tree.innerHTML = '<div class="text-gray-500 text-center py-8">No exportable features found</div>';
            return;
        }
        renderExportTree();
    } catch (err) {
        tree.innerHTML = `<div class="text-red-400 text-center py-8">${err.message}</div>`;
    }
}

function closeExportModal() {
    document.getElementById('export-modal').classList.add('hidden');
}

function renderExportTree() {
    const tree = document.getElementById('export-tree');
    tree.innerHTML = exportFeatures.map((feature, fi) => {
        const diagrams = feature.diagrams || [];
        return `
            <div class="mb-3">
                <div class="flex items-center gap-2 mb-1">
                    <button onclick="toggleFeatureExpand(${fi})"
                            class="text-gray-400 hover:text-gray-200 text-xs w-5 text-center"
                            id="expand-btn-${fi}">▶</button>
                    <label class="flex items-center gap-2 cursor-pointer flex-1">
                        <input type="checkbox" class="feature-cb" data-fi="${fi}"
                               onchange="onFeatureToggle(${fi})" checked>
                        <span class="text-sm font-medium">${escapeHtml(feature.name)}</span>
                        <span class="text-xs text-gray-500">${diagrams.length} diagram${diagrams.length !== 1 ? 's' : ''}</span>
                        ${feature.has_requirements ? '<span class="text-xs text-green-600">+ requirements</span>' : ''}
                    </label>
                </div>
                <div id="diagrams-${fi}" class="ml-7 hidden space-y-1">
                    ${diagrams.map((d, di) => `
                        <label class="flex items-center gap-2 cursor-pointer py-0.5">
                            <input type="checkbox" class="diagram-cb" data-fi="${fi}" data-di="${di}" checked
                                   onchange="onDiagramToggle(${fi})">
                            <span class="text-xs text-gray-300">${escapeHtml(d.name)}</span>
                            <span class="text-xs text-gray-600 truncate">${escapeHtml(d.description || '')}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `;
    }).join('');
    updateDownloadButton();
}

function toggleFeatureExpand(fi) {
    const el = document.getElementById(`diagrams-${fi}`);
    const btn = document.getElementById(`expand-btn-${fi}`);
    if (el.classList.contains('hidden')) {
        el.classList.remove('hidden');
        btn.textContent = '▼';
    } else {
        el.classList.add('hidden');
        btn.textContent = '▶';
    }
}

function onFeatureToggle(fi) {
    const featureCb = document.querySelector(`.feature-cb[data-fi="${fi}"]`);
    const diagramCbs = document.querySelectorAll(`.diagram-cb[data-fi="${fi}"]`);
    diagramCbs.forEach(cb => cb.checked = featureCb.checked);
    updateDownloadButton();
}

function onDiagramToggle(fi) {
    const featureCb = document.querySelector(`.feature-cb[data-fi="${fi}"]`);
    const diagramCbs = document.querySelectorAll(`.diagram-cb[data-fi="${fi}"]`);
    const checked = [...diagramCbs].filter(cb => cb.checked).length;
    featureCb.checked = checked > 0;
    featureCb.indeterminate = checked > 0 && checked < diagramCbs.length;
    updateDownloadButton();
}

function selectAllExport(select) {
    document.querySelectorAll('.feature-cb, .diagram-cb').forEach(cb => {
        cb.checked = select;
        cb.indeterminate = false;
    });
    updateDownloadButton();
}

function updateDownloadButton() {
    const anySelected = document.querySelectorAll('.feature-cb:checked').length > 0;
    document.getElementById('export-download-btn').disabled = !anySelected;
}

function collectSelectedFeatures() {
    return exportFeatures.map((feature, fi) => {
        const featureCb = document.querySelector(`.feature-cb[data-fi="${fi}"]`);
        if (!featureCb.checked && !featureCb.indeterminate) return null;

        const diagramCbs = document.querySelectorAll(`.diagram-cb[data-fi="${fi}"]:checked`);
        const selectedDiagrams = [...diagramCbs].map(cb => {
            const di = parseInt(cb.dataset.di);
            return feature.diagrams[di].file;
        });

        return { name: feature.name, diagrams: selectedDiagrams };
    }).filter(Boolean);
}

async function startExport() {
    const btn = document.getElementById('export-download-btn');
    const origText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Generating...';

    const selected = collectSelectedFeatures();

    try {
        const resp = await fetch(`/api/projects/${PROJECT_ID}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ features: selected }),
        });

        if (!resp.ok) throw new Error('Export failed');

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = resp.headers.get('Content-Disposition')
            ?.match(/filename="(.+?)"/)?.[1] || 'export.html';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        closeExportModal();
    } catch (err) {
        alert('Export failed: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = origText;
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
```

### Tree checklist UX:

- Each feature row: expand/collapse chevron, checkbox, feature name, diagram count badge, requirements indicator
- Expanded: individual diagram checkboxes with name and description
- Feature checkbox toggles all children; individual toggles update parent (checked/indeterminate/unchecked)
- Requirements are implicitly included when any content from a feature is selected (no separate checkbox)
- All features start checked by default
- Download button disabled when nothing is selected

### PROJECT_ID availability:

The `project.html` template already has `{{ project.id }}` available in its context. The export JS uses `PROJECT_ID` which must be defined. Check if project.html already defines it (it doesn't — the loops section uses inline `{{ project.id }}`). We need to add:

```javascript
const PROJECT_ID = '{{ project.id }}';
```

at the top of the scripts block if not already present.

---

## Step 6: Tests

**File:** `vista/tests/test_export_service.py` (NEW)

### Test cases for ExportService:

| # | Test | Description |
|---|------|-------------|
| 1 | `test_get_exportable_features_returns_features_with_diagrams` | Project with features that have `_arch.json` manifests returns them |
| 2 | `test_get_exportable_features_excludes_empty_features` | Feature with no diagrams and no requirements is excluded |
| 3 | `test_get_exportable_features_includes_requirements_only` | Feature with no diagrams but valid `domain-requirements.md` is included |
| 4 | `test_generate_export_html_basic` | Generates valid HTML with one feature, one diagram |
| 5 | `test_generate_export_html_multiple_features` | HTML contains navigation when >1 feature |
| 6 | `test_generate_export_html_missing_diagram_file` | Gracefully skips missing .mmd files |
| 7 | `test_generate_export_html_missing_manifest` | Includes requirements when manifest is missing |
| 8 | `test_generate_export_html_empty_selection` | Returns minimal HTML when no content matches |

### Test cases for routes:

| # | Test | Description |
|---|------|-------------|
| 9 | `test_get_export_features_endpoint` | Returns correct JSON shape |
| 10 | `test_post_export_endpoint` | Returns HTML with correct Content-Disposition header |
| 11 | `test_post_export_invalid_project` | Returns 404 for unknown project |

### Test approach:

Use `tmp_path` fixture to create mock `.vista/features/` directories with test manifests and `.mmd` files. Follow existing test patterns from `vista/tests/test_ralph_service.py`. For route tests, use `httpx.AsyncClient` with the FastAPI `TestClient`.

---

## File Summary

| Action | File | Description |
|--------|------|-------------|
| MODIFY | `vista/server/services/progress_service.py` | Add `read_domain_requirements()` static method |
| CREATE | `vista/server/services/export_service.py` | `ExportService` with `get_exportable_features()` and `generate_export_html()` |
| CREATE | `vista/server/routes/export.py` | Two API endpoints: GET features tree, POST generate export |
| MODIFY | `vista/server/app.py` | Register export router (`app.include_router(export.router)`) |
| CREATE | `vista/server/views/export.html` | Self-contained export HTML template (standalone, not extending _base.html) |
| MODIFY | `vista/server/views/project.html` | Add "Export Docs" button + export modal + JS |
| CREATE | `vista/tests/test_export_service.py` | Unit tests for export service and routes |

---

## Dependencies

- **No new Python packages** — uses existing `jinja2` (already a FastAPI dependency), `pathlib`, `json`, `datetime`
- **No new CDN links in dashboard** — the CDN links (Mermaid, Tailwind, Marked) are only in the **exported** HTML file, not the dashboard itself
- **Reuses existing services**: `ProjectService.get_by_id()`, `ProgressService.read_arch_manifest()`, `ProgressService.read_arch_file()`

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| HTML injection from diagram source | Embed all content as JSON via `\|tojson` filter; render client-side via Mermaid/Marked APIs |
| Large export files (many diagrams) | Mermaid source ~2-5KB per diagram; 20 diagrams ≈ 100KB. Template overhead ≈ 50KB. Well within 500KB target |
| Mermaid rendering failures in export | Same behavior as dashboard — Mermaid shows inline error for bad syntax |
| Path traversal in diagram filenames | Reuse `ProgressService.read_arch_file()` which has path traversal prevention |
| CDN availability | Pin to major versions (@11, @15) for stability; accepted trade-off per requirements |
| `project.html` already has `escapeHtml()` | The loops tab section defines its own JS. The export JS is in the same script block, so check for name collisions. If project.html's script block already has `escapeHtml`, reuse it; otherwise define it. |

## Implementation Order

1. **Step 1** (ProgressService `read_domain_requirements`) — prerequisite for step 2
2. **Step 2** (ExportService) — core business logic
3. **Step 3** (Routes + app.py registration) — thin API layer, enables testing via curl
4. **Step 4** (export.html template) — the most effort; HTML/CSS/JS template
5. **Step 5** (project.html modal) — UI integration
6. **Step 6** (Tests) — can start alongside step 2

Steps 1-3 can be built and API-tested before the templates (steps 4-5) are complete.

## Verified Codebase References

| Reference | Location | Confirmed |
|-----------|----------|-----------|
| `ProgressService.read_arch_manifest()` | `progress_service.py:49-62` | Static, returns Optional[dict], handles legacy list format |
| `ProgressService.read_arch_file()` | `progress_service.py:64-84` | Static, path traversal prevention, returns Optional[str] |
| `ProjectService.get_by_id()` | `project_service.py:83-89` | Returns Optional[Project] with `.name`, `.path`, `.id` |
| `ProjectService.scan_features_detailed()` | `project_service.py:135-162` | Pattern for scanning `.vista/features/` |
| Router registration | `app.py:72-83` | `app.include_router(module.router)` pattern |
| `config.VIEWS_DIR` | `config.py:16` | `SERVER_DIR / "views"` |
| Mermaid theme variables | `architecture.html:1224-1261` | Dark + light theme configs |
| Diagram card CSS | `architecture.html:10-112` | Complete card gallery styling |
| Project header button area | `project.html:7-14` | "Remove Project" button location |
| `PROJECT_ID` JS variable | Not yet in project.html | Must add `const PROJECT_ID = '{{ project.id }}'` |
