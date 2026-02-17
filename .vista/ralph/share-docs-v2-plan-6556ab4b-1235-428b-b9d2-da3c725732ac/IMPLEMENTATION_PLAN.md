# Implementation Plan: Share Docs V2 (Documentation Export Enhancements)

## Overview

Enhance the existing documentation export feature with five improvements: (1) export progress/planning artifacts from feature directories, (2) export specs/plans from `.vista/ralph/` jobs, (3) inline CDN dependencies for offline support, (4) add light/dark theme toggle and table of contents, and (5) track export history with metadata.

## Current State (Codebase-Verified)

| File | Role | Key Details |
|------|------|-------------|
| `vista/server/services/export_service.py` | `ExportService` — `get_exportable_features()` + `generate_export_html()` | Returns features with `{name, has_requirements, diagrams}`. HTML uses `jinja2.Environment` with `config.VIEWS_DIR` loader. Export data blob: `{diagrams, requirements}` |
| `vista/server/routes/export.py` | `ExportFeatureSelection(name, diagrams)` + `ExportRequest(features)` | Two Pydantic models, GET features tree + POST generate. Response uses `Content-Disposition` attachment header |
| `vista/server/views/export.html` | Standalone HTML template (465 lines) | CDN: Tailwind, Mermaid@11, Marked@15. All colors hardcoded (dark theme only). Client-side `EXPORT_DATA` JSON blob with `renderAllDiagrams()` + `renderAllRequirements()` |
| `vista/server/views/project.html` | Export modal JS (lines 410-571) | `openExportModal()`, `renderExportTree()`, `collectSelectedFeatures()`, `startExport()`. Feature badges show `has_requirements` |
| `vista/server/services/progress_service.py` | Reads feature artifacts | `read_progress()` → `dict{exists, content, phase, current_phase, all_complete}`, `read_implementation_plan()` → `Optional[str]`, `read_agents_md()` → `Optional[str]`, `read_domain_requirements()` → `Optional[str]`, `read_arch_file()` → `Optional[str]` with path traversal prevention |
| `vista/server/services/ralph_service.py` | `RalphService.list_jobs()` | Scans `.vista/ralph/` dirs, loads `job.json` with `{job_id, slug, mode, status, created_at, ...}`. `_resolve_plan_dir()` puts plans in `.vista/features/{slug}/` when feature dir exists |
| `vista/tests/test_export_service.py` | 16 tests across 4 classes | `_setup_feature()` helper, `TestClient` fixture with mocked `ProjectService` |
| `vista/server/config.py` | Paths | `VIEWS_DIR = SERVER_DIR / "views"`, `STATIC_DIR = VIEWS_DIR / "static"`, `DATA_DIR = ~/.vista/data` |
| `vista/server/views/static/` | Existing static assets | `app.js`, `style.css`, `arch-chat.js`, `arch-chat.css` — no `vendor/` subdirectory yet |

### Ralph Job Directory Layout (verified)

```
.vista/ralph/{slug}/           # First job for slug (no UUID suffix)
.vista/ralph/{slug}-{uuid}/    # Subsequent jobs for same slug
  ├── job.json                 # {job_id, slug, mode, status, created_at, ...}
  ├── task.md                  # Task description
  ├── IMPLEMENTATION_PLAN.md   # Generated plan (plan mode) or consumed plan (build mode)
  ├── progress.txt             # Iteration progress log
  ├── PROMPT_{mode}.md         # Generated prompt template
  ├── loop.ps1                 # Loop runner script
  └── output.log               # Claude output log
```

---

## Phase 1: Progress File & Planning Artifacts Export

**Priority: HIGH** — Low effort, high value. Users already have progress.txt, AGENTS.md, and IMPLEMENTATION_PLAN.md in feature directories; they just aren't exported.

### 1a. Extend `get_exportable_features()` to detect new content types

**File:** `vista/server/services/export_service.py` — line 16
**Action:** MODIFY

Add detection for three new content types using existing `ProgressService` methods:

```python
# After line 33 (has_requirements):
progress = ProgressService.read_progress(project_path, d.name)
has_progress = progress.get("exists", False)
agents_md = ProgressService.read_agents_md(project_path, d.name)
has_agents = agents_md is not None
plan_md = ProgressService.read_implementation_plan(project_path, d.name)
has_plan = plan_md is not None
```

Update exportability guard (line 35):
```python
if not diagrams and not has_requirements and not has_progress and not has_agents and not has_plan:
    continue
```

Add new boolean fields to result dict (after line 40):
```python
results.append({
    "name": d.name,
    "has_requirements": has_requirements,
    "has_progress": has_progress,        # NEW
    "has_agents": has_agents,            # NEW
    "has_implementation_plan": has_plan,  # NEW
    "diagrams": [...],
})
```

### 1b. Extend `generate_export_html()` to collect new content

**File:** `vista/server/services/export_service.py` — line 56
**Action:** MODIFY

For each selected feature, additionally read:
```python
# After requirements_md (line 101-103):
progress_data = ProgressService.read_progress(project_path, feature_name)
progress_content = progress_data.get("content") if progress_data.get("exists") else None
agents_content = ProgressService.read_agents_md(project_path, feature_name)
plan_content = ProgressService.read_implementation_plan(project_path, feature_name)
```

**Critical:** `read_progress()` returns a `dict`, not a `str`. Must extract `progress_data["content"]`.

Update the skip guard (line 105):
```python
if not diagram_data and not requirements_md and not progress_content and not agents_content and not plan_content:
    continue
```

Add to features_data (after line 111):
```python
features_data.append({
    "name": feature_name,
    "diagrams": diagram_data,
    "requirements_md": requirements_md,
    "progress_md": progress_content,            # NEW
    "agents_md": agents_content,                # NEW
    "implementation_plan_md": plan_content,     # NEW
})
```

Extend `export_data` blob (after line 131):
```python
export_progress = {}
export_agents = {}
export_plans = {}
for feature in features_data:
    if feature.get("progress_md"):
        export_progress[feature["name"]] = feature["progress_md"]
    if feature.get("agents_md"):
        export_agents[feature["name"]] = feature["agents_md"]
    if feature.get("implementation_plan_md"):
        export_plans[feature["name"]] = feature["implementation_plan_md"]

export_data = {
    "diagrams": export_diagrams,
    "requirements": export_requirements,
    "progress": export_progress,              # NEW
    "agents": export_agents,                  # NEW
    "implementation_plans": export_plans,     # NEW
}
```

### 1c. Add content-type toggles to `ExportFeatureSelection`

**File:** `vista/server/routes/export.py` — line 16
**Action:** MODIFY

```python
class ExportFeatureSelection(BaseModel):
    name: str
    diagrams: list[str]
    include_requirements: bool = True          # NEW (default True = backward compatible)
    include_progress: bool = True              # NEW
    include_agents: bool = True                # NEW
    include_implementation_plan: bool = True   # NEW
```

**Backward compatibility:** All new fields default to `True`, so existing callers sending `{"name": "x", "diagrams": ["y"]}` still work.

Pass toggle flags to `generate_export_html()` — add a new parameter `content_flags: dict[str, dict[str, bool]]` keyed by feature name, or pass the full selection objects. The simpler approach: pass `selected_features` as the full model_dump list and let `generate_export_html()` check the flags per feature.

### 1d. Extend export.html template

**File:** `vista/server/views/export.html`
**Action:** MODIFY — after the requirements section (line 285)

Add three new collapsible content sections per feature:

```html
{% if feature.implementation_plan_md %}
<div class="bg-gray-800 rounded-lg border border-gray-700 p-6 mt-4">
    <h3 class="text-lg font-semibold mb-4">Implementation Plan</h3>
    <div class="requirements-content" id="plan-{{ feature.name }}"></div>
</div>
{% endif %}

{% if feature.agents_md %}
<div class="bg-gray-800 rounded-lg border border-gray-700 p-6 mt-4">
    <h3 class="text-lg font-semibold mb-4">Agents</h3>
    <div class="requirements-content" id="agents-{{ feature.name }}"></div>
</div>
{% endif %}

{% if feature.progress_md %}
<div class="bg-gray-800 rounded-lg border border-gray-700 p-6 mt-4">
    <h3 class="text-lg font-semibold mb-4">Progress Log</h3>
    <pre class="text-sm text-gray-300 whitespace-pre-wrap bg-gray-900 rounded p-4 overflow-x-auto"
         id="progress-{{ feature.name }}"></pre>
</div>
{% endif %}
```

Rename `renderAllRequirements()` → `renderAllMarkdown()` and add rendering for new sections:

```javascript
function renderAllMarkdown() {
    // Requirements (existing)
    for (const [name, md] of Object.entries(EXPORT_DATA.requirements || {})) {
        const el = document.getElementById(`requirements-${name}`);
        if (el && md) el.innerHTML = marked.parse(md);
    }
    // Implementation plans (markdown)
    for (const [name, md] of Object.entries(EXPORT_DATA.implementation_plans || {})) {
        const el = document.getElementById(`plan-${name}`);
        if (el && md) el.innerHTML = marked.parse(md);
    }
    // Agents (markdown)
    for (const [name, md] of Object.entries(EXPORT_DATA.agents || {})) {
        const el = document.getElementById(`agents-${name}`);
        if (el && md) el.innerHTML = marked.parse(md);
    }
    // Progress (plain text — NOT markdown)
    for (const [name, text] of Object.entries(EXPORT_DATA.progress || {})) {
        const el = document.getElementById(`progress-${name}`);
        if (el && text) el.textContent = text;
    }
}
```

Update init call (line 461): `renderAllMarkdown();`

### 1e. Update export modal to show new content badges

**File:** `vista/server/views/project.html` — line 455
**Action:** MODIFY `renderExportTree()`

After the requirements badge:
```javascript
${feature.has_progress ? '<span class="text-xs text-yellow-600">+ progress</span>' : ''}
${feature.has_agents ? '<span class="text-xs text-purple-600">+ agents</span>' : ''}
${feature.has_implementation_plan ? '<span class="text-xs text-blue-600">+ plan</span>' : ''}
```

### 1f. Tests

**File:** `vista/tests/test_export_service.py`

Extend `_setup_feature()` helper with optional `progress`, `agents`, `implementation_plan` params:
```python
def _setup_feature(project_path, feature_name, diagrams=None, requirements=None,
                   progress=None, agents=None, implementation_plan=None):
    # ... existing code ...
    if progress is not None:
        (feature_dir / "progress.txt").write_text(progress, encoding="utf-8")
    if agents is not None:
        (feature_dir / "AGENTS.md").write_text(agents, encoding="utf-8")
    if implementation_plan is not None:
        (feature_dir / "IMPLEMENTATION_PLAN.md").write_text(implementation_plan, encoding="utf-8")
```

| # | Test | Assert |
|---|------|--------|
| 1 | `test_exportable_features_includes_progress_only` | Feature with only `progress.txt` is exportable, `has_progress=True` |
| 2 | `test_exportable_features_includes_plan_only` | Feature with only `IMPLEMENTATION_PLAN.md` is exportable |
| 3 | `test_exportable_features_reports_new_flags` | All new boolean flags correctly set |
| 4 | `test_generate_html_includes_progress` | HTML `export_data` JSON contains progress content |
| 5 | `test_generate_html_includes_plan` | HTML contains implementation plan in `export_data` |
| 6 | `test_generate_html_includes_agents` | HTML contains agents content in `export_data` |

---

## Phase 2: Specs and Implementation Plans from Ralph Jobs

**Priority: HIGH** — Ralph jobs produce specs, plans, and progress that users want to share but currently can't.

### 2a. Add Ralph artifact scanning to ExportService

**File:** `vista/server/services/export_service.py`
**Action:** ADD new static method

```python
@staticmethod
def get_exportable_ralph_jobs(project_path: str) -> list[dict]:
    """Return Ralph jobs with exportable artifacts (plans, specs, progress).

    Scans .vista/ralph/ for job directories. Returns jobs that have at least
    one of: IMPLEMENTATION_PLAN.md, progress.txt, task.md, or specs/*.md.
    """
```

**Implementation details:**
- Scan `.vista/ralph/` for directories
- For each dir, try to load `job.json` (skip if missing/corrupt via try/except)
- Check for existence of: `IMPLEMENTATION_PLAN.md`, `progress.txt`, `task.md`
- Scan `specs/` subdirectory for `.md` files (some Ralph plan jobs create specs)
- Skip dirs with no exportable artifacts
- Sort by `created_at` descending (newest first)

Return shape:
```python
[{
    "dir_name": "share-docs-plan",          # directory name under .vista/ralph/
    "slug": "share-docs-plan",              # from job.json
    "mode": "plan",                         # from job.json
    "status": "completed",                  # from job.json
    "created_at": "2026-02-13T...",         # from job.json
    "has_plan": True,
    "has_progress": True,
    "has_task": True,
    "spec_files": [],                       # filenames from specs/ subdir
}]
```

**Note on `_resolve_plan_dir()`:** For Ralph jobs tied to a feature (where `.vista/features/{slug}/` exists), the plan lives in the feature directory and is already covered by Phase 1. This method focuses on **standalone Ralph jobs** and **build logs** where artifacts remain in the job directory.

### 2b. Add Ralph content reading method

**File:** `vista/server/services/export_service.py`
**Action:** ADD static method

```python
@staticmethod
def read_ralph_artifact(project_path: str, dir_name: str, filename: str) -> Optional[str]:
    """Read a file from a Ralph job directory with path traversal prevention.

    Uses the same resolve().relative_to() pattern as ProgressService.read_arch_file().
    Only allows reading .md and .txt files.
    """
```

Allowed files: `IMPLEMENTATION_PLAN.md`, `progress.txt`, `task.md`, `specs/*.md`.
Block: `job.json`, `output.log`, `loop.ps1`, `PROMPT_*.md` (these are internal/sensitive).

### 2c. Extend export API for Ralph jobs

**File:** `vista/server/routes/export.py`
**Action:** MODIFY

New request model:
```python
class ExportRalphJobSelection(BaseModel):
    dir_name: str                           # directory name under .vista/ralph/
    include_plan: bool = True
    include_progress: bool = True
    include_task: bool = True
    include_specs: list[str] = []           # specific spec filenames

class ExportRequest(BaseModel):
    features: list[ExportFeatureSelection]
    ralph_jobs: list[ExportRalphJobSelection] = []   # NEW, backward compatible
```

New endpoint:
```python
@router.get("/api/projects/{project_id}/export/ralph-jobs")
async def get_export_ralph_jobs(project_id: str):
    """Return Ralph jobs with exportable artifacts for the export modal."""
```

### 2d. Extend `generate_export_html()` for Ralph data

**File:** `vista/server/services/export_service.py`
**Action:** MODIFY signature and body

Add `selected_ralph_jobs: list[dict] = None` parameter. For each selected job, read requested artifacts via `read_ralph_artifact()`.

Add to export_data:
```python
export_data = {
    "diagrams": ...,
    "requirements": ...,
    "progress": ...,
    "agents": ...,
    "implementation_plans": ...,
    "ralph_jobs": [{                         # NEW
        "slug": "share-docs-plan",
        "dir_name": "share-docs-plan",
        "mode": "plan",
        "status": "completed",
        "task_md": "...",
        "plan_md": "...",
        "progress_text": "...",
        "specs": {"spec-name.md": "..."},
    }],
}
```

### 2e. Add Ralph section to export.html

**File:** `vista/server/views/export.html`
**Action:** MODIFY — after `</main>` closing tag (before modal)

Add "Development Loops" section:
```html
{% if ralph_jobs %}
<section class="max-w-7xl mx-auto px-6 py-8 mb-12">
    <h2 class="text-2xl font-bold mb-6">Development Loops</h2>
    {% for job in ralph_jobs %}
    <div class="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-4" id="ralph-{{ job.dir_name }}">
        <div class="flex items-center gap-3 mb-4">
            <h3 class="text-lg font-semibold">{{ job.slug }}</h3>
            <span class="badge {{ 'badge-arch' if job.mode == 'plan' else 'badge-tdd' }}">{{ job.mode }}</span>
            <span class="text-xs text-gray-500">{{ job.status }}</span>
        </div>
        <!-- Task, plan, progress, specs rendered via JS -->
    </div>
    {% endfor %}
</section>
{% endif %}
```

Add JS rendering in `renderAllMarkdown()`:
```javascript
// Ralph jobs
for (const job of (EXPORT_DATA.ralph_jobs || [])) {
    // task_md → markdown
    // plan_md → markdown
    // progress_text → plain text (textContent)
    // specs → markdown per file
}
```

### 2f. Add Ralph jobs section to export modal

**File:** `vista/server/views/project.html`
**Action:** MODIFY

In `openExportModal()`, additionally fetch from `GET /api/projects/${PROJECT_ID}/export/ralph-jobs`. Render below the feature checklist with:
- Section header "Development Loops"
- Per-job checkbox with slug + mode badge
- Expandable to show per-artifact checkboxes

Update `collectSelectedFeatures()` → `collectExportSelection()`:
```javascript
function collectExportSelection() {
    return {
        features: collectSelectedFeatures(),
        ralph_jobs: collectSelectedRalphJobs(),
    };
}
```

Update `startExport()` to use `collectExportSelection()`.

### 2g. Tests

| # | Test | Assert |
|---|------|--------|
| 1 | `test_get_exportable_ralph_jobs_finds_jobs` | Jobs with plans/progress/task are discovered |
| 2 | `test_get_exportable_ralph_jobs_excludes_empty` | Job dirs with only `job.json` are excluded |
| 3 | `test_get_exportable_ralph_jobs_handles_corrupt_json` | Corrupt `job.json` is skipped, not crash |
| 4 | `test_read_ralph_artifact_reads_plan` | Can read `IMPLEMENTATION_PLAN.md` |
| 5 | `test_read_ralph_artifact_blocks_path_traversal` | `../../../etc/passwd` returns None |
| 6 | `test_read_ralph_artifact_blocks_sensitive_files` | `job.json`, `output.log` return None |
| 7 | `test_generate_html_with_ralph_jobs` | HTML contains Ralph job sections in `export_data` |
| 8 | `test_export_ralph_jobs_endpoint` | GET endpoint returns correct shape |

Helper for Ralph job test setup:
```python
def _setup_ralph_job(project_path, dir_name, job_json=None, plan=None, progress=None, task=None):
    job_dir = project_path / ".vista" / "ralph" / dir_name
    job_dir.mkdir(parents=True, exist_ok=True)
    if job_json:
        (job_dir / "job.json").write_text(json.dumps(job_json), encoding="utf-8")
    if plan:
        (job_dir / "IMPLEMENTATION_PLAN.md").write_text(plan, encoding="utf-8")
    if progress:
        (job_dir / "progress.txt").write_text(progress, encoding="utf-8")
    if task:
        (job_dir / "task.md").write_text(task, encoding="utf-8")
```

---

## Phase 3: Offline-First (Inline CDN Dependencies)

**Priority: MEDIUM** — Important for sharing exported files where recipients may not have internet access.

### 3a. Approach: Hand-written CSS + vendored JS

The export template uses a **small, fixed set** of Tailwind utility classes. Rather than trying to run the Tailwind CLI at build time (which adds a Node.js dependency), **extract and hand-write the CSS equivalents** of the ~30 Tailwind classes used in the template.

**Inventory of Tailwind classes used in export.html:**
- Layout: `min-h-screen`, `max-w-7xl`, `mx-auto`, `px-6`, `py-4`, `py-8`, `py-2`, `mb-12`, `mb-6`, `mb-8`, `mb-4`, `mt-4`, `p-6`
- Flexbox: `flex`, `items-center`, `justify-between`, `gap-2`, `gap-3`, `gap-4`, `flex-1`, `min-w-0`, `flex-shrink-0`
- Typography: `text-xs`, `text-sm`, `text-lg`, `text-xl`, `text-2xl`, `font-semibold`, `font-bold`, `capitalize`, `truncate`, `hidden`, `sm:inline`
- Colors: `bg-gray-900`, `bg-gray-800`, `bg-gray-800/50`, `text-gray-100`, `text-gray-200`, `text-gray-400`, `text-gray-500`, `text-gray-600`, `text-green-400`, `border-gray-700`, `hover:text-gray-200`, `hover:text-blue-400`
- Spacing/layout: `space-y-6`, `space-y-1`, `rounded-lg`, `border`, `border-b`, `overflow-hidden`

This is ~60 utility classes → ~120 lines of CSS. Much smaller and more reliable than vendoring full Tailwind.

### 3b. Create vendor directory and files

**New files:**
- `vista/server/views/static/vendor/tailwind-export.css` — Hand-written CSS equivalents (~120 lines, ~3-4KB)
- `vista/server/views/static/vendor/mermaid.min.js` — Downloaded from `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js` (~1.5MB)
- `vista/server/views/static/vendor/marked.min.js` — Downloaded from `https://cdn.jsdelivr.net/npm/marked@15/marked.min.js` (~40KB)

**Download script:** `vista/server/views/static/vendor/update-deps.sh`
```bash
#!/bin/bash
# Download CDN dependencies for offline export support
cd "$(dirname "$0")"
curl -sL "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js" -o mermaid.min.js
curl -sL "https://cdn.jsdelivr.net/npm/marked@15/marked.min.js" -o marked.min.js
echo "Downloaded mermaid.min.js ($(wc -c < mermaid.min.js) bytes)"
echo "Downloaded marked.min.js ($(wc -c < marked.min.js) bytes)"
```

### 3c. Add `InlineDependencyService`

**File:** `vista/server/services/inline_deps_service.py` (NEW)

```python
class InlineDependencyService:
    """Reads vendored dependencies for offline HTML exports."""

    VENDOR_DIR = config.STATIC_DIR / "vendor"

    DEPS = {
        "tailwind_css": "tailwind-export.css",
        "mermaid_js": "mermaid.min.js",
        "marked_js": "marked.min.js",
    }

    @classmethod
    def get_inline_deps(cls) -> Optional[dict[str, str]]:
        """Return dependency contents for inlining. Returns None if any file missing."""
        result = {}
        for key, filename in cls.DEPS.items():
            path = cls.VENDOR_DIR / filename
            if not path.exists():
                logger.warning("Vendor file missing: %s", path)
                return None  # Fall back to CDN
            result[key] = path.read_text(encoding="utf-8")
        return result
```

### 3d. Add offline toggle to export API

**File:** `vista/server/routes/export.py`
**Action:** MODIFY `ExportRequest`

```python
class ExportRequest(BaseModel):
    features: list[ExportFeatureSelection]
    ralph_jobs: list[ExportRalphJobSelection] = []
    offline: bool = False                    # NEW
```

### 3e. Modify template for dual CDN/inline mode

**File:** `vista/server/views/export.html`
**Action:** MODIFY head section (lines 7-9)

```html
{% if inline_deps %}
<style>{{ inline_deps.tailwind_css }}</style>
<script>{{ inline_deps.mermaid_js }}</script>
<script>{{ inline_deps.marked_js }}</script>
{% else %}
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@15/marked.min.js"></script>
{% endif %}
```

**Important:** When using inline CSS, `<script src="https://cdn.tailwindcss.com">` is replaced by `<style>...</style>` because the CDN script is a JIT compiler, not a stylesheet. The vendored `tailwind-export.css` is pre-compiled CSS.

### 3f. Update `generate_export_html()` to pass inline deps

**File:** `vista/server/services/export_service.py`
**Action:** MODIFY

```python
def generate_export_html(
    ...,
    offline: bool = False,
) -> str:
    inline_deps = None
    if offline:
        from server.services.inline_deps_service import InlineDependencyService
        inline_deps = InlineDependencyService.get_inline_deps()

    return template.render(
        ...,
        inline_deps=inline_deps,  # None → CDN, dict → inline
    )
```

### 3g. Add offline toggle to export modal

**File:** `vista/server/views/project.html`
**Action:** MODIFY — in the modal footer (line 225-234)

Add checkbox:
```html
<label class="flex items-center gap-2 cursor-pointer">
    <input type="checkbox" id="export-offline" class="rounded">
    <span class="text-xs text-gray-400">Offline mode (larger file, no CDN)</span>
</label>
```

In `startExport()`, include in request body:
```javascript
body: JSON.stringify({
    features: selected,
    ralph_jobs: selectedRalphJobs,
    offline: document.getElementById('export-offline').checked,
}),
```

### 3h. Tests

| # | Test | Assert |
|---|------|--------|
| 1 | `test_inline_deps_returns_content` | Returns dict with all three keys when vendor files exist |
| 2 | `test_inline_deps_returns_none_when_missing` | Returns `None` when any vendor file is missing |
| 3 | `test_generate_html_offline_contains_inline` | Offline HTML has `<style>` tag, no CDN `<script src=` |
| 4 | `test_generate_html_online_uses_cdn` | Default HTML has CDN script tags, no `<style>` block |

---

## Phase 4: Template Customization (Theme Toggle + Table of Contents)

**Priority: MEDIUM** — Improves usability for printed/shared docs. Depends on Phases 1+2 being complete so all content sections exist.

### 4a. Add CSS custom properties for theming

**File:** `vista/server/views/export.html`
**Action:** MODIFY — replace hardcoded colors with CSS variables

**Color mapping (verified from current template):**

| Current Value | CSS Variable | Dark | Light |
|---|---|---|---|
| `#0f172a` (bg) | `--bg-primary` | `#0f172a` | `#ffffff` |
| `#1e293b` (card bg) | `--bg-card` | `#1e293b` | `#ffffff` |
| `#334155` (border) | `--border-primary` | `#334155` | `#e2e8f0` |
| `#475569` (border hover) | `--border-hover` | `#475569` | `#cbd5e1` |
| `#e2e8f0` (text primary) | `--text-primary` | `#e2e8f0` | `#1e293b` |
| `#cbd5e1` (text body) | `--text-body` | `#cbd5e1` | `#475569` |
| `#94a3b8` (text muted) | `--text-muted` | `#94a3b8` | `#64748b` |
| `#60a5fa` (accent blue) | `--accent-blue` | `#60a5fa` | `#3b82f6` |
| `#f472b6` (code text) | `--code-text` | `#f472b6` | `#db2777` |

Add `:root` and `:root.light` CSS blocks, then update all hardcoded colors in `<style>` and inline Tailwind classes. For Tailwind classes on elements (e.g., `bg-gray-900`), add corresponding CSS overrides:

```css
body { background: var(--bg-primary); color: var(--text-primary); }
.diagram-card { background: var(--bg-card); border-color: var(--border-primary); }
/* ... etc for all styled elements ... */
```

### 4b. Add theme toggle button

**File:** `vista/server/views/export.html`
**Action:** MODIFY header (line 211)

```html
<button onclick="toggleTheme()" id="theme-toggle"
        class="text-sm px-3 py-1 rounded border border-gray-600 hover:border-gray-400"
        title="Toggle light/dark theme">
    <span id="theme-icon">&#9728;</span>
</button>
```

JavaScript (uses Unicode sun/moon, no emoji — respects project convention):
```javascript
function toggleTheme() {
    const root = document.documentElement;
    const isLight = root.classList.toggle('light');
    document.getElementById('theme-icon').innerHTML = isLight ? '&#9789;' : '&#9728;';

    // Re-render Mermaid with appropriate theme
    mermaid.initialize({
        startOnLoad: false,
        theme: isLight ? 'default' : 'dark',
        themeVariables: isLight ? LIGHT_MERMAID_VARS : DARK_MERMAID_VARS,
    });
    mermaidCounter = 0;
    renderAllDiagrams();

    try { localStorage.setItem('vista-export-theme', isLight ? 'light' : 'dark'); } catch(e) {}
}

// Restore saved theme on load
try {
    if (localStorage.getItem('vista-export-theme') === 'light') {
        document.documentElement.classList.add('light');
        document.getElementById('theme-icon').innerHTML = '&#9789;';
    }
} catch(e) {}
```

**Note:** `renderAllDiagrams()` already exists and handles re-rendering. Mermaid diagrams need re-initialization with new theme variables, which requires resetting `mermaidCounter` and re-calling `mermaid.render()`.

### 4c. Add table of contents

**File:** `vista/server/views/export.html`
**Action:** MODIFY — after header, before `<main>`

```html
{% if features|length > 1 or ralph_jobs %}
<aside id="toc" class="max-w-7xl mx-auto px-6 pt-6">
    <details open>
        <summary class="cursor-pointer font-semibold text-sm mb-3" style="color: var(--text-muted)">
            Table of Contents
        </summary>
        <nav class="space-y-1 mb-4 pl-2" style="border-left: 2px solid var(--border-primary);">
            {% for feature in features %}
            <div class="py-0.5">
                <a href="#feature-{{ feature.name }}" class="text-sm hover:text-blue-400 capitalize"
                   style="color: var(--text-body);">
                    {{ feature.name | replace('_', ' ') }}
                </a>
            </div>
            {% endfor %}
            {% if ralph_jobs %}
            <div class="pt-2 mt-2" style="border-top: 1px solid var(--border-primary);">
                <span class="text-xs uppercase tracking-wider" style="color: var(--text-muted);">Development Loops</span>
                {% for job in ralph_jobs %}
                <div class="py-0.5">
                    <a href="#ralph-{{ job.dir_name }}" class="text-sm hover:text-blue-400"
                       style="color: var(--text-body);">{{ job.slug }}</a>
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </nav>
    </details>
</aside>
{% endif %}
```

Uses `<details open>` for native collapsibility without extra JS. Replaces the existing simple `<nav>` bar (lines 221-232) for multi-feature exports.

### 4d. Add default theme to export API

**File:** `vista/server/routes/export.py`

```python
class ExportRequest(BaseModel):
    features: list[ExportFeatureSelection]
    ralph_jobs: list[ExportRalphJobSelection] = []
    offline: bool = False
    default_theme: str = "dark"              # NEW: "dark" or "light"
```

Pass to template: `<html lang="en" class="{{ 'light' if default_theme == 'light' else '' }}">`.

### 4e. Tests

| # | Test | Assert |
|---|------|--------|
| 1 | `test_export_html_contains_toc` | Multiple features → `<aside id="toc">` present with links |
| 2 | `test_export_html_single_feature_no_toc` | Single feature → no TOC |
| 3 | `test_export_html_light_theme_default` | `default_theme="light"` → `class="light"` on `<html>` |
| 4 | `test_export_html_has_theme_toggle` | HTML contains `theme-toggle` button |
| 5 | `test_export_html_has_css_variables` | HTML contains `--bg-primary` CSS variable definition |

---

## Phase 5: Export History

**Priority: LOW** — Nice-to-have quality-of-life improvement.

### 5a. Create ExportHistory model

**File:** `vista/server/models/export_history.py` (NEW)

```python
from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid

@dataclass
class ExportHistoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    project_id: str = ""
    exported_at: str = field(default_factory=lambda: datetime.now().isoformat())
    filename: str = ""
    feature_count: int = 0
    feature_names: list[str] = field(default_factory=list)
    ralph_job_count: int = 0
    offline: bool = False
    file_size_bytes: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExportHistoryEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```

Follows the same `to_dict()`/`from_dict()` pattern as `Project` model (`vista/server/models/project.py`).

### 5b. Create ExportHistoryService

**File:** `vista/server/services/export_history_service.py` (NEW)

```python
class ExportHistoryService:
    """Tracks export history per project.

    Storage: ~/.vista/data/export-history/{project_id}.json
    Format: JSON array of ExportHistoryEntry dicts, newest first.
    Max entries: 50 per project (oldest auto-pruned).
    """
    HISTORY_DIR = config.DATA_DIR / "export-history"
    MAX_ENTRIES = 50

    @classmethod
    def record_export(cls, entry: ExportHistoryEntry) -> None: ...

    @classmethod
    def get_history(cls, project_id: str) -> list[dict]: ...

    @classmethod
    def clear_history(cls, project_id: str) -> None: ...
```

Follows `ChatSessionService` persistence pattern: JSON files in `config.DATA_DIR` subdirectory, `mkdir(parents=True, exist_ok=True)`, sorted by timestamp.

### 5c. Record exports in the export route

**File:** `vista/server/routes/export.py`
**Action:** MODIFY `export_documentation()`

After generating HTML and before returning:
```python
from server.models.export_history import ExportHistoryEntry
from server.services.export_history_service import ExportHistoryService

entry = ExportHistoryEntry(
    project_id=project_id,
    filename=filename,
    feature_count=len(body.features),
    feature_names=[f.name for f in body.features],
    ralph_job_count=len(body.ralph_jobs),
    offline=body.offline,
    file_size_bytes=len(html.encode("utf-8")),
)
ExportHistoryService.record_export(entry)
```

### 5d. Add export history API endpoint

**File:** `vista/server/routes/export.py`

```python
@router.get("/api/projects/{project_id}/export/history")
async def get_export_history(project_id: str):
    return ExportHistoryService.get_history(project_id)
```

### 5e. Show history in export modal

**File:** `vista/server/views/project.html`

Add a small "Recent Exports" indicator in the modal footer, fetched from the history endpoint. Shows the most recent export date and summary.

### 5f. Tests

| # | Test | Assert |
|---|------|--------|
| 1 | `test_record_export_creates_file` | First export creates `~/.vista/data/export-history/{id}.json` |
| 2 | `test_record_export_appends` | Multiple exports accumulate in array |
| 3 | `test_history_max_entries_pruned` | >50 entries prunes oldest |
| 4 | `test_get_history_empty` | No history → empty list |
| 5 | `test_export_route_records_history` | POST export creates history entry |

---

## Implementation Order

```
Phase 1 (Feature Artifacts) ──→ Phase 2 (Ralph Jobs)
         │                              │
         └──────── Phase 3 (Offline) ───┘
                        │
                   Phase 4 (Theme/TOC)
                        │
                   Phase 5 (History)
```

**Recommended build order:**
1. **Phase 1** — Foundation: extends existing data flow with minimal new code, no new files
2. **Phase 2** — Builds on Phase 1's template patterns and data structures, adds one new API endpoint
3. **Phase 3** — Independent but benefits from Phase 1+2 template changes being stable. Creates new service and vendor directory
4. **Phase 4** — CSS refactor is easier after all content sections exist. Template-only + CSS work
5. **Phase 5** — Pure additive, no dependencies on other phases. Creates new model + service

Phases 1 and 2 can be built in sequence in one iteration. Phase 3 is independent. Phases 4 and 5 are independent of each other.

---

## File Change Summary

| Action | File | Phase(s) |
|--------|------|----------|
| MODIFY | `vista/server/services/export_service.py` | 1, 2, 3 |
| MODIFY | `vista/server/routes/export.py` | 1, 2, 3, 4, 5 |
| MODIFY | `vista/server/views/export.html` | 1, 2, 3, 4 |
| MODIFY | `vista/server/views/project.html` | 1, 2, 3 |
| MODIFY | `vista/tests/test_export_service.py` | 1, 2, 3, 4, 5 |
| CREATE | `vista/server/services/inline_deps_service.py` | 3 |
| CREATE | `vista/server/views/static/vendor/tailwind-export.css` | 3 |
| CREATE | `vista/server/views/static/vendor/mermaid.min.js` | 3 |
| CREATE | `vista/server/views/static/vendor/marked.min.js` | 3 |
| CREATE | `vista/server/views/static/vendor/update-deps.sh` | 3 |
| CREATE | `vista/server/models/export_history.py` | 5 |
| CREATE | `vista/server/services/export_history_service.py` | 5 |

---

## Dependencies

- **No new Python packages** for any phase
- **Phase 3** requires a one-time download of `mermaid.min.js` (~1.5MB) and `marked.min.js` (~40KB) via the `update-deps.sh` script
- **Phase 3** requires hand-writing ~120 lines of CSS to replace Tailwind CDN classes

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Mermaid.min.js is ~1.5MB, making offline exports ~2MB+ | Large file size | Offline is opt-in; document the tradeoff |
| Tailwind hand-written CSS may miss some classes | Minor styling gaps in offline mode | Comprehensive audit of all classes used in template; keep CDN as default |
| Mermaid theme toggle requires full re-render | Brief flash/delay on theme switch | Acceptable for <20 diagrams; no special mitigation needed |
| Ralph job dirs may have corrupt job.json | Crash during scan | try/except per directory, skip corrupt jobs, log warning |
| Export history JSON could grow unbounded | Disk space | Cap at 50 entries per project, auto-prune oldest |
| `read_progress()` returns dict not string | Wrong data type in export | Extract `progress_data["content"]` (verified in this plan) |

## Acceptance Criteria

### Phase 1
- [ ] Export includes progress.txt content for features that have it
- [ ] Export includes IMPLEMENTATION_PLAN.md rendered as markdown
- [ ] Export includes AGENTS.md rendered as markdown
- [ ] Export modal shows indicator badges for new content types
- [ ] All new tests pass
- [ ] Backward compatible: existing export requests without new fields still work

### Phase 2
- [ ] Export modal shows Ralph jobs section with checkboxes
- [ ] Ralph job plans, tasks, and progress appear in exported HTML
- [ ] Path traversal prevention works for Ralph artifact reads
- [ ] Sensitive files (job.json, output.log) cannot be read via API
- [ ] Jobs without exportable artifacts are excluded from the tree

### Phase 3
- [ ] Offline mode checkbox in export modal
- [ ] Offline export file renders correctly without internet
- [ ] Online mode (default) still uses CDN
- [ ] Vendor files exist and update script works

### Phase 4
- [ ] Theme toggle button switches between dark and light
- [ ] Mermaid diagrams re-render with correct theme
- [ ] Table of contents lists all features and Ralph jobs
- [ ] TOC links scroll smoothly to target sections
- [ ] CSS custom properties replace all hardcoded colors

### Phase 5
- [ ] Each export creates a history entry
- [ ] History visible in export modal
- [ ] History capped at 50 entries per project
- [ ] History includes feature names, date, file size, offline flag

## Spec Versions

| Spec File | Latest Changelog Date |
|-----------|----------------------|
| `.vista/features/share-docs/specs/export-service.md` | Initial (no changelog) |
| `.vista/features/share-docs/specs/export-template.md` | Initial (no changelog) |
| `.vista/features/share-docs/specs/export-ui.md` | Initial (no changelog) |
