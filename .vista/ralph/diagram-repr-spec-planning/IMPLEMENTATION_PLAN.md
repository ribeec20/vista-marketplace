# Implementation Plan: Multi-Format Diagram Support & Markdown Editing

**Status:** PLANNING — Iteration 2 (refined, codebase-verified)
**Created:** 2026-02-15
**Updated:** 2026-02-15 (Iteration 2 — settings path fix, CDN verification, precise line refs)
**Spec Source:** `domain-requirements.md` Expansion section (added 2026-02-15)
**Parent Feature:** `.vista/features/diagram_representations/`

---

## Context

The existing diagram_representations feature is largely delivered (Phases 1-4 complete, Phase 5 partial). The domain-requirements.md has been expanded with three new areas:

1. **Multi-Format Rendering** — PlantUML (.puml), D2 (.d2), Graphviz (.dot), Markdown (.md)
2. **Markdown Inline Editing** — View/edit toggle, save to disk via PUT API, cancel/discard
3. **Manifest & Type System Updates** — Extended type enum, renderer dispatch, file extension mapping

This plan covers implementing these expansion requirements on top of the existing codebase.

---

## Current State Assessment (Verified Iteration 2)

### What Exists (Working)

| Component | Status | Location (verified) |
|-----------|--------|---------------------|
| Mermaid rendering | Complete | `architecture.html:1288-1307` — `mermaid.render()` |
| Renderer dispatch | Partial — only `.mmd` check + fallback `<pre>` | `architecture.html:1288-1311` — `renderDiagramContent()` |
| `_arch.json` schema | `type` enum: `["mermaid", "drawio"]` only | `arch-schema.json:29` |
| Diagram watcher | Watches `.mmd` and `.drawio` only | `diagram_watcher.py:26,124` — `WATCH_EXTENSIONS` (defined twice) |
| `_detect_diagram_type()` | Parses mermaid subtype from first line of `.mmd` | `diagram_watcher.py:102-118` |
| Manifest auto-update | Scans `.mmd`/`.drawio` in arch dir, builds `_arch.json` | `diagram_watcher.py:232-256` — `_update_manifest_sync()` |
| API: GET manifest | Complete | `architecture.py:15-26` |
| API: GET file | Complete (text/plain for .mmd, application/xml for .drawio) | `architecture.py:29-48` — `get_arch_file()` |
| API: PUT file | **Does not exist** | Needed for markdown save |
| Path traversal protection | Complete | `progress_service.py:78-97` — `read_arch_file()` |
| Pan/zoom per diagram | Complete | `architecture.html:1323-1375` |
| Settings file | Located at `~/.vista/settings.json`, managed by `config.py` | `config.py:23-35` — `_resolve_settings_file()` |
| `plantuml_server_url` | **Does not exist** anywhere | Not in `config.py` or any settings |
| CDN: mermaid.js | Loaded | `architecture.html:6` |
| CDN: marked.js | Loaded (for chat markdown) | `architecture.html:7` |
| Test suite | 29 tests in `test_architecture.py`, 24 in `test_diagram_watcher.py` | All passing (139 total) |

### What Needs to Change

1. **arch-schema.json** (line 29) — Extend `type` enum from 2 to 6 values
2. **diagram_watcher.py** (lines 26, 124) — Extend `WATCH_EXTENSIONS` and `_detect_diagram_type()` for new formats
3. **progress_service.py** — Add `write_arch_file()` method (after `read_arch_file()` at line 97)
4. **architecture.py** — Add `PUT` endpoint, update content-type mapping (lines 40-46)
5. **architecture.html** — Refactor renderer dispatch (lines 1288-1311), add 4 new renderers + markdown edit mode
6. **config.py** — Add `plantuml_server_url` to settings defaults (NOT a separate settings_service.py)
7. **Tests** — Cover all new renderers, PUT endpoint, security

---

## Phase 1: Schema & Backend Foundation

**Priority:** HIGH — All other phases depend on this
**Estimated Complexity:** Low
**Files:** 5 modified, 0 created

### 1.1 Extend arch-schema.json Type Enum

**File:** `vista/templates/arch-schema.json`
**Line:** 29

Change:
```json
"enum": ["mermaid", "drawio"]
```
To:
```json
"enum": ["mermaid", "drawio", "plantuml", "d2", "graphviz", "markdown"]
```

No other schema changes needed — `diagramType` enum already has `"custom"` as a catch-all for non-Mermaid diagrams. The `category` field is already optional with `architecture` and `tdd` values.

### 1.2 Add write_arch_file() to ProgressService

**File:** `vista/server/services/progress_service.py`
**Insert after:** `read_arch_file()` method (line 97)

```python
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
```

**Key decisions:**
- **Writable extensions restricted to `.md` only** — Diagram files (.mmd, .puml, .d2, .dot, .drawio) are NOT writable through this API. Only markdown documentation files are editable inline.
- **Same path traversal protection pattern** as existing `read_arch_file()` (lines 80-92).
- **File must be in an existing arch/ directory** — won't create directories.

### 1.3 Add PUT Endpoint for File Writing

**File:** `vista/server/routes/architecture.py`
**Insert after:** `get_arch_file()` function (line 48)

```python
from pydantic import BaseModel

class FileContent(BaseModel):
    content: str

@router.put("/api/projects/{project_id}/features/{feature_name}/arch/{filename}")
async def put_arch_file(project_id: str, feature_name: str, filename: str, body: FileContent):
    """Write content to a markdown file in arch/."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    success = ProgressService.write_arch_file(project.path, feature_name, filename, body.content)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot write to this file")

    return {"status": "ok", "filename": filename}
```

**Note:** The `pydantic` import may already exist (check top of file). The `BaseModel` import should be added alongside existing imports if not present.

### 1.4 Update Content-Type Mapping in GET Endpoint

**File:** `vista/server/routes/architecture.py` — `get_arch_file()` function
**Lines:** 40-46

Replace the current if/elif content-type logic:
```python
if filename.endswith(".mmd"):
    media_type = "text/plain"
elif filename.endswith(".drawio"):
    media_type = "application/xml"
else:
    media_type = "text/plain"
```

With a dictionary-based lookup:
```python
ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
CONTENT_TYPES = {
    "mmd": "text/plain",
    "drawio": "application/xml",
    "puml": "text/plain",
    "d2": "text/plain",
    "dot": "text/plain",
    "md": "text/markdown",
}
media_type = CONTENT_TYPES.get(ext, "text/plain")
```

### 1.5 Add PlantUML Server URL to Settings

**File:** `vista/server/config.py`

The settings system uses `config.py` with defaults dicts and a `load_settings()` / `save_*()` pattern. Add a new section for diagram settings:

```python
_DIAGRAM_DEFAULTS = {
    "plantuml_server_url": "https://www.plantuml.com/plantuml",
}

def get_diagram_settings() -> dict:
    """Return merged diagram settings with defaults applied."""
    raw = load_settings().get("diagrams", {})
    if not isinstance(raw, dict):
        raw = {}
    return _merge_dicts(_DIAGRAM_DEFAULTS, raw)
```

**Also add:** A helper function or use `get_diagram_settings()` in the architecture page route to pass the PlantUML URL to the template.

**Settings file effect:** When `~/.vista/settings.json` contains no `diagrams` section, the default URL (`https://www.plantuml.com/plantuml`) is used. Users can override by adding:
```json
{
  "diagrams": {
    "plantuml_server_url": "http://localhost:8080/plantuml"
  }
}
```

### 1.6 Extend Diagram Watcher Extensions

**File:** `vista/server/services/diagram_watcher.py`

**Change 1:** Update `WATCH_EXTENSIONS` in BOTH locations (lines 26 and 124):
```python
WATCH_EXTENSIONS = {".mmd", ".drawio", ".puml", ".d2", ".dot", ".md"}
```

**Change 2:** Add file-type detection by extension (new function):
```python
EXT_TO_TYPE = {
    ".mmd": "mermaid",
    ".drawio": "drawio",
    ".puml": "plantuml",
    ".d2": "d2",
    ".dot": "graphviz",
    ".md": "markdown",
}

def _detect_file_type(path: Path) -> str:
    """Detect diagram type from file extension."""
    return EXT_TO_TYPE.get(path.suffix.lower(), "mermaid")
```

**Change 3:** Update `_update_manifest_sync()` (lines 232-256) to use `_detect_file_type()` for the `type` field. For non-mermaid formats, set `diagramType: "custom"`. For mermaid files, continue using `_detect_diagram_type()` for the subtype.

```python
# In _update_manifest_sync():
for f in sorted(arch_dir.iterdir()):
    if f.suffix in EXT_TO_TYPE and not f.name.startswith("_"):
        file_type = _detect_file_type(f)
        diagram_type = _detect_diagram_type(f) if file_type == "mermaid" else "custom"
        entry = {
            "name": f.stem.replace("-", " ").replace("_", " ").title(),
            "file": f.name,
            "type": file_type,
            "diagramType": diagram_type,
            "description": f"Auto-detected {file_type} diagram",
        }
        diagrams.append(entry)
```

### Acceptance Criteria (Phase 1)

- [ ] `arch-schema.json` validates manifests with all 6 type values
- [ ] `PUT /api/.../arch/{filename}` writes `.md` files successfully
- [ ] `PUT /api/.../arch/{filename}` returns 400 for non-`.md` files
- [ ] `PUT /api/.../arch/{filename}` blocks path traversal attempts
- [ ] `GET /api/.../arch/{filename}` returns correct Content-Type for all 6 extensions
- [ ] Diagram watcher detects changes in all 6 file types
- [ ] Manifest auto-update correctly identifies file types by extension
- [ ] `plantuml_server_url` available via `config.get_diagram_settings()`

---

## Phase 2: Client-Side Renderer Infrastructure

**Priority:** HIGH — Core rendering dispatch
**Depends on:** Phase 1
**Estimated Complexity:** Medium
**Files:** 1 modified (architecture.html), CDN scripts added

### 2.1 Refactor Renderer Dispatch

**File:** `vista/server/views/architecture.html`
**Replace:** `renderDiagramContent()` function (lines 1288-1311)

Currently checks `filename.endsWith('.mmd')` and falls back to `<pre>`. Refactor to a renderer map:

```javascript
const RENDERERS = {
    mermaid:  renderMermaid,
    plantuml: renderPlantUML,
    d2:       renderD2,
    graphviz: renderGraphviz,
    drawio:   renderDrawio,
    markdown: renderMarkdown,
};

async function renderDiagramContent(el, filename, content, idx, diagramType) {
    // diagramType is the 'type' field from manifest (mermaid, plantuml, etc.)
    const renderer = RENDERERS[diagramType];
    if (renderer) {
        return renderer(el, content, idx, filename);
    }
    // Unknown type fallback
    el.innerHTML = `<pre class="text-gray-400 text-xs whitespace-pre-wrap">${escapeHtml(content)}</pre>`;
}
```

**Critical change:** `loadDiagrams()` must pass the manifest `type` field to `renderDiagramContent()`. Currently only passes filename/content/idx. Add `diagram.type` as 5th parameter.

### 2.2 Mermaid Renderer (Extract from existing)

Extract the existing mermaid logic (lines 1289-1307) into a standalone function:

```javascript
async function renderMermaid(el, content, idx, filename) {
    try {
        const id = `mermaid-svg-${idx}-${++mermaidCounter}`;
        const { svg } = await mermaid.render(id, content);
        el.innerHTML = svg;
        // Existing node click handlers...
        el.querySelectorAll('.node').forEach(node => {
            node.style.cursor = 'pointer';
            node.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleNodeSelection(node, idx);
            });
        });
        reapplySelections(idx);
    } catch (e) {
        el.innerHTML = `<pre class="text-yellow-400 text-xs whitespace-pre-wrap">Mermaid parse error:\n${e.message || e}\n\n${content}</pre>`;
    }
}
```

### 2.3 PlantUML Renderer

**CDN dependency:** `plantuml-encoder` v1.4.0 (~10KB minified)
```html
<script src="https://cdn.jsdelivr.net/npm/plantuml-encoder@1.4.0/dist/plantuml-encoder.min.js"></script>
```

**Template variable needed:** Pass `PLANTUML_SERVER_URL` from server context.

**Implementation:**
```javascript
async function renderPlantUML(el, content, idx, filename) {
    try {
        const encoded = plantumlEncoder.encode(content);
        const svgUrl = `${PLANTUML_SERVER_URL}/svg/${encoded}`;
        const resp = await fetch(svgUrl);
        if (!resp.ok) throw new Error(`PlantUML server error: ${resp.status}`);
        const svg = await resp.text();
        el.innerHTML = svg;
    } catch (err) {
        el.innerHTML = `<div class="diagram-error">
            <p class="text-yellow-400 text-sm mb-2">PlantUML render error: ${escapeHtml(err.message)}</p>
            <pre class="text-gray-400 text-xs whitespace-pre-wrap">${escapeHtml(content)}</pre>
        </div>`;
    }
}
```

**Error handling:**
- Server unreachable → Show error message + raw source as fallback
- Invalid syntax → PlantUML server returns an error image; show the raw source too

### 2.4 D2 Renderer

**Dependency status:** `@terrastruct/d2` does NOT have a well-known browser-compatible WASM build available on CDN. After research:

- **d2 official repo** (`terrastruct/d2`) is a Go binary, no WASM distribution
- **No `@anthropic-ai/d2-wasm`** package exists on npm
- **Kroki** is a self-hosted diagram server that supports D2 (like PlantUML server)

**Revised approach — Server-side rendering via Kroki or raw source fallback:**

```javascript
async function renderD2(el, content, idx, filename) {
    // Attempt 1: If a Kroki server is configured, render via server
    if (window.KROKI_SERVER_URL) {
        try {
            const resp = await fetch(`${KROKI_SERVER_URL}/d2/svg`, {
                method: 'POST',
                headers: { 'Content-Type': 'text/plain' },
                body: content,
            });
            if (resp.ok) {
                el.innerHTML = await resp.text();
                return;
            }
        } catch (_) { /* fall through */ }
    }
    // Fallback: Syntax-highlighted raw source
    el.innerHTML = `<div class="diagram-raw-source">
        <p class="text-blue-400 text-sm mb-2">D2 diagram (raw source — install Kroki for live rendering)</p>
        <pre class="text-gray-300 text-xs whitespace-pre-wrap">${escapeHtml(content)}</pre>
    </div>`;
}
```

**Decision:** D2 rendering ships as raw-source-with-syntax-hint initially. Kroki integration (optional) is documented but not required. This avoids a hard dependency on a non-existent WASM package.

**Future enhancement:** If `@anthropic-ai/d2-wasm` or similar becomes available, swap in client-side rendering.

### 2.5 Graphviz Renderer

**CDN dependency:** `@viz-js/viz` v3 — well-established WASM package (~2.5MB)

The package provides a standalone build that works in browsers. Load lazily:

```javascript
let vizInstance = null;

async function loadViz() {
    if (vizInstance) return vizInstance;
    // Dynamic script load
    if (!window.Viz) {
        await new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/@viz-js/viz@3.11.0/lib/viz-standalone.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    vizInstance = await Viz.instance();
    return vizInstance;
}

async function renderGraphviz(el, content, idx, filename) {
    try {
        const viz = await loadViz();
        const svg = viz.renderSVGElement(content);
        el.innerHTML = '';
        el.appendChild(svg);
    } catch (err) {
        el.innerHTML = `<div class="diagram-error">
            <p class="text-yellow-400 text-sm mb-2">Graphviz render error: ${escapeHtml(err.message)}</p>
            <pre class="text-gray-400 text-xs whitespace-pre-wrap">${escapeHtml(content)}</pre>
        </div>`;
    }
}
```

**Engine selection:** Default to `dot` layout engine. Graphviz supports `dot`, `neato`, `fdp`, `sfdp`, `circo`, `twopi`, `osage`, `patchwork`. Could expose engine via manifest `layoutEngine` field in future — not in scope now.

### 2.6 Draw.io Renderer

**Current state:** Falls through to `<pre>` tag with escaped XML content. No rendering.

**Implementation using Draw.io viewer iframe:**
```javascript
function renderDrawio(el, content, idx, filename) {
    try {
        // Use postMessage API for large files (URL encoding may exceed limits)
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '500px';
        iframe.style.border = 'none';
        iframe.style.borderRadius = '8px';
        iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');

        // Base64 encode to avoid URL length limits
        const b64 = btoa(unescape(encodeURIComponent(content)));
        iframe.src = `https://viewer.diagrams.net/?highlight=0000ff&nav=1&title=${encodeURIComponent(filename)}#R${b64}`;

        el.innerHTML = '';
        el.appendChild(iframe);
    } catch (err) {
        el.innerHTML = `<div class="diagram-error">
            <p class="text-yellow-400 text-sm mb-2">Draw.io render error: ${escapeHtml(err.message)}</p>
            <pre class="text-gray-400 text-xs whitespace-pre-wrap">${escapeHtml(content)}</pre>
        </div>`;
    }
}
```

**Risk:** Very large `.drawio` files may exceed URL limits even with base64 encoding. For MVP, this approach is acceptable. For large files, the `postMessage` API approach can be added later.

### 2.7 Markdown Renderer

**Library:** `marked.js` — **already loaded** in `architecture.html` (line 7). No additional CDN script needed.

```javascript
function renderMarkdown(el, content, idx, filename) {
    try {
        const html = marked.parse(content);
        el.innerHTML = `<div class="markdown-content">${html}</div>`;
        // Store original content for edit mode
        el.dataset.rawContent = content;
        el.dataset.filename = filename;
        el.dataset.idx = idx;
    } catch (err) {
        el.innerHTML = `<pre class="text-gray-400 text-xs whitespace-pre-wrap">${escapeHtml(content)}</pre>`;
    }
}
```

### Acceptance Criteria (Phase 2)

- [ ] Mermaid diagrams continue to render correctly (no regression)
- [ ] PlantUML diagrams render as SVG via server fetch
- [ ] D2 diagrams show raw source with info message (or Kroki SVG if configured)
- [ ] Graphviz diagrams render via `@viz-js/viz` WASM
- [ ] Draw.io diagrams render in iframe (not raw XML)
- [ ] Markdown files render as formatted HTML via `marked.js`
- [ ] Each renderer shows error + raw source on failure
- [ ] WASM module (Graphviz) loads lazily
- [ ] PlantUML encoder loads eagerly (small, ~10KB)

---

## Phase 3: Markdown Inline Editor

**Priority:** HIGH — Key new user interaction
**Depends on:** Phase 1 (PUT endpoint), Phase 2 (markdown renderer)
**Estimated Complexity:** Medium-High
**Files:** 1 modified (architecture.html), 1 modified (arch-chat.css or inline styles)

### 3.1 Edit Button on Markdown Cards

When building diagram cards in JavaScript (NOT Jinja2 — cards are built client-side), check the diagram type from the manifest entry:

```javascript
function buildDiagramCard(diagram, idx) {
    // ... existing card structure ...
    const editButton = diagram.type === 'markdown'
        ? `<button class="md-edit-btn" onclick="toggleMarkdownEdit(${idx})" title="Edit markdown">✎</button>`
        : '';
    // Insert into card header alongside existing zoom controls
}
```

**Placement:** In the diagram card header template area of `architecture.html` — identify where card headers are constructed (likely near line 1016-1041) and add the edit button conditionally.

### 3.2 Edit Mode State Machine

**States:** `view` → `editing` → `saving` → `view`

```javascript
const markdownEditState = {};  // idx -> { editing: bool, saving: bool, originalContent: string }

function toggleMarkdownEdit(idx) {
    const state = markdownEditState[idx] || { editing: false };
    if (state.editing) {
        cancelMarkdownEdit(idx);
    } else {
        enterMarkdownEdit(idx);
    }
}

function enterMarkdownEdit(idx) {
    const el = document.getElementById(`diagram-viewport-${idx}`);
    const content = el.dataset.rawContent || diagramContents[DIAGRAMS[idx].file];

    markdownEditState[idx] = { editing: true, saving: false, originalContent: content };

    el.innerHTML = `
        <div class="md-editor-container">
            <div class="md-editor-toolbar">
                <button class="md-save-btn" onclick="saveMarkdown(${idx})" title="Save">✓ Save</button>
                <button class="md-cancel-btn" onclick="cancelMarkdownEdit(${idx})" title="Cancel">✕ Cancel</button>
                <span class="md-save-indicator" id="md-indicator-${idx}"></span>
            </div>
            <textarea class="md-editor" id="md-textarea-${idx}" spellcheck="false">${escapeHtml(content)}</textarea>
        </div>
    `;

    const textarea = document.getElementById(`md-textarea-${idx}`);
    textarea.focus();
    autoResizeTextarea(textarea);
    textarea.addEventListener('input', () => autoResizeTextarea(textarea));

    updateEditButton(idx, true);
}

function cancelMarkdownEdit(idx) {
    const state = markdownEditState[idx];
    if (!state) return;

    const el = document.getElementById(`diagram-viewport-${idx}`);
    renderMarkdown(el, state.originalContent, idx, DIAGRAMS[idx].file);

    markdownEditState[idx] = { editing: false };
    updateEditButton(idx, false);
}

async function saveMarkdown(idx) {
    const state = markdownEditState[idx];
    if (!state || state.saving) return;

    const textarea = document.getElementById(`md-textarea-${idx}`);
    const newContent = textarea.value;
    const filename = DIAGRAMS[idx].file;
    const indicator = document.getElementById(`md-indicator-${idx}`);

    state.saving = true;
    indicator.textContent = 'Saving...';
    indicator.className = 'md-save-indicator saving';

    try {
        const resp = await fetch(
            `/api/projects/${PROJECT_ID}/features/${FEATURE_NAME}/arch/${filename}`,
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newContent }),
            }
        );

        if (!resp.ok) throw new Error(`Save failed: ${resp.status}`);

        indicator.textContent = 'Saved!';
        indicator.className = 'md-save-indicator saved';

        // Update stored content
        diagramContents[filename] = newContent;

        // Return to view mode after brief success indicator
        setTimeout(() => {
            const el = document.getElementById(`diagram-viewport-${idx}`);
            renderMarkdown(el, newContent, idx, filename);
            markdownEditState[idx] = { editing: false };
            updateEditButton(idx, false);
        }, 800);

    } catch (err) {
        indicator.textContent = `Error: ${err.message}`;
        indicator.className = 'md-save-indicator error';
        state.saving = false;
    }
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.max(200, textarea.scrollHeight) + 'px';
}

function updateEditButton(idx, isEditing) {
    const btn = document.querySelector(`[data-edit-idx="${idx}"]`);
    if (btn) {
        btn.textContent = isEditing ? '✕' : '✎';
        btn.title = isEditing ? 'Cancel editing' : 'Edit markdown';
    }
}
```

### 3.3 Keyboard Shortcuts

```javascript
document.addEventListener('keydown', (e) => {
    for (const [idx, state] of Object.entries(markdownEditState)) {
        if (state.editing) {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                saveMarkdown(parseInt(idx));
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelMarkdownEdit(parseInt(idx));
            }
        }
    }
});
```

### 3.4 Editor CSS Styles

**File:** `vista/server/views/static/arch-chat.css` (or inline in architecture.html `<style>` block)

```css
.md-editor-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 200px;
}

.md-editor-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: var(--surface-2, #1e293b);
    border-bottom: 1px solid var(--border, #334155);
}

.md-editor {
    flex: 1;
    resize: vertical;
    min-height: 200px;
    padding: 16px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 14px;
    line-height: 1.6;
    background: var(--surface-1, #0f172a);
    color: var(--text-primary, #e2e8f0);
    border: none;
    outline: none;
}

.md-edit-btn {
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    opacity: 0.6;
    transition: opacity 0.2s;
}
.md-edit-btn:hover { opacity: 1; }

.md-save-btn { color: #4ade80; cursor: pointer; }
.md-cancel-btn { color: #f87171; cursor: pointer; }
.md-save-indicator.saving { color: #facc15; }
.md-save-indicator.saved { color: #4ade80; }
.md-save-indicator.error { color: #f87171; }

.markdown-content {
    padding: 16px;
    line-height: 1.7;
}
.markdown-content h1, .markdown-content h2, .markdown-content h3 {
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}
.markdown-content pre {
    background: var(--surface-2, #1e293b);
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
}
.markdown-content code {
    background: var(--surface-2, #1e293b);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.9em;
}
.markdown-content table {
    border-collapse: collapse;
    width: 100%;
}
.markdown-content th, .markdown-content td {
    border: 1px solid var(--border, #334155);
    padding: 8px 12px;
    text-align: left;
}
```

### Acceptance Criteria (Phase 3)

- [ ] Markdown files render as formatted HTML with GFM support (tables, code blocks, task lists)
- [ ] Edit button appears only on markdown-type diagram cards
- [ ] Clicking edit switches to textarea with raw content
- [ ] Save writes content to disk via PUT API and returns to rendered view
- [ ] Cancel discards changes and returns to rendered view
- [ ] Save indicator shows progress (saving → saved → hidden)
- [ ] Save failure shows error message, does not lose edits
- [ ] Ctrl+S / Cmd+S saves, Escape cancels
- [ ] Content stored in `diagramContents` is updated after successful save

---

## Phase 4: Template & Watcher Integration

**Priority:** MEDIUM
**Depends on:** Phases 1-3
**Estimated Complexity:** Low-Medium
**Files:** 2 modified (architecture.html, architecture.py route)

### 4.1 Pass Manifest Type to Renderers

**File:** `vista/server/views/architecture.html`

Update `loadDiagrams()` to pass the manifest `type` field:

```javascript
async function loadDiagrams() {
    for (let i = 0; i < DIAGRAMS.length; i++) {
        const diagram = DIAGRAMS[i];
        const resp = await fetch(`/api/projects/${PROJECT_ID}/features/${FEATURE_NAME}/arch/${diagram.file}`);
        const content = await resp.text();
        diagramContents[diagram.file] = content;

        const el = document.getElementById(`diagram-viewport-${i}`);
        renderDiagramContent(el, diagram.file, content, i, diagram.type);  // 5th arg: type
    }
}
```

### 4.2 Conditionally Show Edit Button in Card Header

When building diagram cards (JavaScript), check the diagram type:

```javascript
// Inside card header construction
const editButton = diagram.type === 'markdown'
    ? `<button class="md-edit-btn" data-edit-idx="${idx}" onclick="toggleMarkdownEdit(${idx})" title="Edit">✎</button>`
    : '';
```

### 4.3 CDN Script Loading

**File:** `vista/server/views/architecture.html` — `<head>` section

Add after existing mermaid.js and marked.js CDN lines:

```html
<!-- PlantUML encoder (small, ~10KB) — loaded eagerly -->
<script src="https://cdn.jsdelivr.net/npm/plantuml-encoder@1.4.0/dist/plantuml-encoder.min.js"></script>

<!-- @viz-js/viz loaded lazily by renderGraphviz() — no eager script needed -->
<!-- Draw.io viewer loaded as iframe — no script needed -->
```

### 4.4 PlantUML Server URL Injection

**File:** `vista/server/routes/architecture.py` — `architecture_viewer_page()` (line 51-66)

Add the PlantUML server URL to the template context:

```python
from server.config import get_diagram_settings

@router.get("/project/{project_id}/arch/{feature_name}", response_class=HTMLResponse)
async def architecture_viewer_page(request: Request, project_id: str, feature_name: str):
    # ... existing code ...
    diagram_settings = get_diagram_settings()
    plantuml_url = diagram_settings.get("plantuml_server_url", "https://www.plantuml.com/plantuml")
    return templates.TemplateResponse("architecture.html", {
        "request": request,
        # ... existing context vars ...
        "plantuml_url": plantuml_url,
    })
```

And in the template:
```html
<script>
    const PLANTUML_SERVER_URL = {{ plantuml_url | tojson }};
</script>
```

### Acceptance Criteria (Phase 4)

- [ ] All 6 diagram types dispatch to their correct renderer via `diagram.type`
- [ ] Edit button only appears on markdown cards
- [ ] PlantUML server URL passed from settings to frontend
- [ ] PlantUML encoder CDN script loaded
- [ ] Graphviz WASM loads lazily on first Graphviz diagram

---

## Phase 5: Tests

**Priority:** HIGH — Must validate security and correctness
**Depends on:** Phases 1-4
**Estimated Complexity:** Medium
**Files:** 2 modified (test_architecture.py, test_diagram_watcher.py)

### 5.1 PUT Endpoint Tests

**File:** `vista/tests/test_architecture.py`
**Add class:** `TestArchWriteAPI` (after existing `TestArchitectureAPI` at line 227)

```python
class TestArchWriteAPI:
    def test_put_markdown_file_success(self, api_env):
        """PUT .md file writes content and returns 200."""

    def test_put_non_markdown_file_rejected(self, api_env):
        """PUT .mmd file returns 400."""

    def test_put_path_traversal_blocked(self, api_env):
        """PUT ../../evil.md returns 400."""

    def test_put_dotdot_in_filename(self, api_env):
        """PUT with '..' anywhere in filename returns 400."""

    def test_put_project_not_found(self, api_env):
        """PUT to nonexistent project returns 404."""

    def test_put_no_arch_directory(self, api_env):
        """PUT to feature without arch/ returns 400."""

    def test_put_verify_file_written(self, api_env):
        """After successful PUT, GET returns the new content."""
```

### 5.2 ProgressService Write Tests

**File:** `vista/tests/test_architecture.py`
**Add class:** `TestProgressServiceWrite` (after existing `TestProgressServiceArch` at line 318)

```python
class TestProgressServiceWrite:
    def test_write_arch_file_md_success(self, tmp_path):
        """write_arch_file() writes .md content to arch/."""

    def test_write_arch_file_mmd_rejected(self, tmp_path):
        """write_arch_file() rejects .mmd files."""

    def test_write_arch_file_puml_rejected(self, tmp_path):
        """write_arch_file() rejects .puml files."""

    def test_write_arch_file_path_traversal(self, tmp_path):
        """write_arch_file() blocks ../evil path."""

    def test_write_arch_file_no_arch_dir(self, tmp_path):
        """write_arch_file() returns False when arch/ doesn't exist."""

    def test_write_arch_file_overwrites_existing(self, tmp_path):
        """write_arch_file() overwrites an existing .md file."""
```

### 5.3 Extended Schema Validation Tests

**File:** `vista/tests/test_architecture.py`
**Add to existing `TestSchemaValidation` class** (line 320)

```python
def test_arch_schema_accepts_plantuml_type(self):
def test_arch_schema_accepts_d2_type(self):
def test_arch_schema_accepts_graphviz_type(self):
def test_arch_schema_accepts_markdown_type(self):
# Note: test_arch_schema_rejects_invalid_type already exists (line 416)
```

### 5.4 Content-Type Tests

**File:** `vista/tests/test_architecture.py`
**Add class:** `TestContentTypes`

```python
class TestContentTypes:
    def test_get_puml_returns_text_plain(self, api_env):
    def test_get_d2_returns_text_plain(self, api_env):
    def test_get_dot_returns_text_plain(self, api_env):
    def test_get_md_returns_text_markdown(self, api_env):
```

### 5.5 Diagram Watcher Extension Tests

**File:** `vista/tests/test_diagram_watcher.py`
**Add class:** `TestExtendedFileTypes` (after existing `TestManifestUpdate` at line 193)

```python
class TestExtendedFileTypes:
    def test_watches_puml_files(self):
        """WATCH_EXTENSIONS includes .puml."""

    def test_watches_d2_files(self):
        """WATCH_EXTENSIONS includes .d2."""

    def test_watches_dot_files(self):
        """WATCH_EXTENSIONS includes .dot."""

    def test_watches_md_files(self):
        """WATCH_EXTENSIONS includes .md."""

    def test_detect_file_type_plantuml(self):
        """_detect_file_type() returns 'plantuml' for .puml."""

    def test_detect_file_type_d2(self):
        """_detect_file_type() returns 'd2' for .d2."""

    def test_detect_file_type_graphviz(self):
        """_detect_file_type() returns 'graphviz' for .dot."""

    def test_detect_file_type_markdown(self):
        """_detect_file_type() returns 'markdown' for .md."""

    def test_manifest_update_assigns_correct_type_plantuml(self):
        """Manifest update sets type='plantuml' for .puml files."""

    def test_manifest_update_assigns_correct_type_markdown(self):
        """Manifest update sets type='markdown' for .md files."""
```

### 5.6 Settings Tests

**File:** `vista/tests/test_architecture.py` (or new `test_config.py` if appropriate)

```python
class TestDiagramSettings:
    def test_get_diagram_settings_default(self):
        """Default plantuml_server_url is plantuml.com."""

    def test_get_diagram_settings_override(self):
        """Custom plantuml_server_url from settings.json is returned."""
```

### Test Count Summary

| Category | New Tests | Location |
|----------|-----------|----------|
| PUT endpoint | 7 | `test_architecture.py` |
| ProgressService write | 6 | `test_architecture.py` |
| Schema validation | 4 | `test_architecture.py` |
| Content types | 4 | `test_architecture.py` |
| Diagram watcher extensions | 10 | `test_diagram_watcher.py` |
| Settings | 2 | `test_architecture.py` |
| **Total new** | **33** | |

### Acceptance Criteria (Phase 5)

- [ ] All PUT endpoint tests pass (including security: path traversal, extension whitelist)
- [ ] All schema validation tests pass for 6 types
- [ ] Content-type tests pass for all new extensions
- [ ] Watcher tests pass for all 6 file types
- [ ] Settings tests pass for defaults and overrides
- [ ] No regressions in existing 53 tests (29 arch + 24 watcher)
- [ ] Total test count: ~86 (53 existing + 33 new)

---

## Phase 6: Documentation & Skill Updates

**Priority:** LOW
**Depends on:** All prior phases
**Estimated Complexity:** Low

### 6.1 Update Plan Skill SKILL.md

**File:** `vista/skills/plan/SKILL.md`

Update Step 3 (architecture generation) to mention all supported formats:
- Default: Mermaid (.mmd) for all diagram types
- Optional: PlantUML (.puml) for detailed UML class/sequence diagrams
- Optional: D2 (.d2) for architecture diagrams (raw source unless Kroki configured)
- Optional: Graphviz (.dot) for dependency graphs
- Optional: Markdown (.md) for prose documentation (design rationale, ADRs)

### 6.2 Update Diagrams Skill

**File:** `vista/skills/diagrams/SKILL.md`

Document the expanded format support.

### 6.3 Update Specs

**arch-directory.md:**
- Update supported types from `"mermaid" | "drawio"` to all 6 values
- Update data model DiagramEntry type union
- Add markdown editing workflow

**rendering-pipeline.md:**
- Update renderer table to include all 6 renderers
- Add CDN dependency table
- Document lazy vs eager loading strategy

### Acceptance Criteria (Phase 6)

- [ ] Plan skill lists all supported formats
- [ ] Diagrams skill documents expanded support
- [ ] Specs updated to reflect all 6 types
- [ ] Renderer table complete in rendering-pipeline.md

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| D2 WASM not available as browser-compatible package | **Confirmed** | Low | Ship with raw source display + optional Kroki integration |
| PlantUML server rate limiting or network issues | Low | Low | Self-hosted server option in settings; error + raw source fallback |
| `@viz-js/viz` WASM too large (>5MB) | Low | Medium | Lazy load only when Graphviz diagram appears; ~2.5MB actual |
| Draw.io viewer base64 URL exceeds limits for large files | Medium | Medium | Base64 approach for MVP; postMessage API for future |
| Markdown editor unsaved changes lost on navigation | Low | Medium | Add `beforeunload` warning when editing (enhancement) |
| `marked.js` XSS via user-edited markdown | Low | High | Use `marked` with default sanitization; content is user-owned files |

---

## Implementation Order (Recommended)

1. **Phase 1** — Backend foundation (schema, PUT endpoint, watcher extensions, settings)
2. **Phase 5 partial** — Backend tests for Phase 1 (schema, PUT, watcher, settings) — validate before frontend
3. **Phase 2** — Renderer infrastructure (dispatch refactor + all 6 renderers)
4. **Phase 3** — Markdown editor (edit mode, save/cancel, keyboard shortcuts)
5. **Phase 4** — Template integration (type passing, CDN loading, URL injection)
6. **Phase 5 remainder** — Content type tests, integration tests
7. **Phase 6** — Documentation

**Estimated total:** ~3-4 build iterations

---

## Files Summary

### Files to Modify

| File | Changes |
|------|---------|
| `vista/templates/arch-schema.json` | Extend `type` enum: add `plantuml`, `d2`, `graphviz`, `markdown` (line 29) |
| `vista/server/services/progress_service.py` | Add `write_arch_file()` method (after line 97) |
| `vista/server/routes/architecture.py` | Add PUT endpoint (after line 48), update content-type mapping (lines 40-46) |
| `vista/server/views/architecture.html` | Refactor renderer dispatch (lines 1288-1311), add 5 new renderers, add markdown editor, CDN scripts |
| `vista/server/views/static/arch-chat.css` | Add markdown editor + content styles |
| `vista/server/services/diagram_watcher.py` | Extend `WATCH_EXTENSIONS` (lines 26, 124), add `_detect_file_type()`, update `_update_manifest_sync()` |
| `vista/server/config.py` | Add `_DIAGRAM_DEFAULTS` and `get_diagram_settings()` |
| `vista/tests/test_architecture.py` | Add ~23 new tests (PUT, schema, content types, settings) |
| `vista/tests/test_diagram_watcher.py` | Add ~10 new tests (extended file types, type detection) |

### Files to Create

None — all changes are modifications to existing files.

### Settings Changes

| Setting | Default Value | Location |
|---------|--------------|----------|
| `diagrams.plantuml_server_url` | `"https://www.plantuml.com/plantuml"` | `~/.vista/settings.json` via `config.py` |

---

## Key Corrections from Iteration 1

| # | Iteration 1 Claim | Correction |
|---|-------------------|------------|
| 1 | "File: `settings_service.py`" for settings | **Corrected:** Settings service is `config.py` — no `settings_service.py` exists |
| 2 | D2 renders via `@terrastruct/d2` WASM or `@anthropic-ai/d2-wasm` | **Corrected:** Neither package exists. D2 ships as raw source + optional Kroki server |
| 3 | `@viz-js/viz` CDN path left unspecified | **Corrected:** `@viz-js/viz@3.11.0/lib/viz-standalone.js` — lazy-loaded script tag |
| 4 | `WATCH_EXTENSIONS` referenced once | **Corrected:** Defined in TWO locations (lines 26 and 124) — both must be updated |
| 5 | ~20 new tests estimated | **Corrected:** 33 new tests planned (more thorough coverage) |

---

## Spec Versions

| Spec File | Latest Changelog Date | Notes |
|-----------|-----------------------|-------|
| `specs/arch-directory.md` | 2026-02-15 | `diagramType` enum and category aligned with arch-schema.json |
| `specs/rendering-pipeline.md` | 2026-02-15 | Draw.io status clarified, acceptance criteria updated |
| `specs/chat-review.md` | 2026-02-15 | Protocol-native streaming alignment |
| `specs/migration-cleanup.md` | 2026-02-15 | All acceptance criteria verified complete |
| `domain-requirements.md` (Expansion) | 2026-02-15 | Multi-format diagrams, markdown editing, type system updates |
