# Implementation Plan: diagram_representations

**Status:** IMPLEMENTATION COMPLETE — Phases 1-4 delivered, Phase 5 partial (SSE streaming done, Draw.io deferred)
**Last Updated:** 2026-02-15 (Spec alignment pass: chat architecture updated to protocol-native, session persistence documented)
**Next Action:** Phase 5.1 (Draw.io viewer), Phase 6 (Documentation)

---

## Invalidation Findings (Iteration 5 — stream-json Format Discovery)

| # | Previous Plan Claim | Verified Reality | Impact |
|---|---------------------|-----------------|--------|
| 1 | Phase 2 says "Gets invocation snippet via `provider.get_invocation(shell)`" then "Read stdout, return response text" | ClaudeProvider's `get_invocation()` uses `--output-format=stream-json` (provider_service.py:134,141). CLI output is structured JSON lines, NOT plain text. | Chat service must NOT reuse loop invocation template directly |

**Decision:** The chat service should build its own CLI command for the Claude provider, using `claude -p --model $Model` **without** `--output-format=stream-json` or `--verbose`. This produces plain text output suitable for JSON `{response}` wrapping. OpenCodeProvider's invocation (`opencode run --model $Model $PromptContent`) already returns plain text. See updated Phase 2.1 below.

### All Prior Findings Confirmed (Iterations 1-4 — Still Accurate)
- **Test suite: 104 passed, 5 failed, 2 warnings** — re-confirmed by running pytest
- 5 failing tests: all in `TestVistaPlanAPI` class (lines 271-427) testing removed endpoints
- plan-schema.json: 3 duplicated sections (uiFlows, dataModels, dataFlow) at exact line numbers + services once at 146-179

### Iteration 6 — BUILD Iteration Results (All Phases 1-4 Complete)

| Phase | Status | Tests | Files Changed |
|-------|--------|-------|---------------|
| 4 | ✅ COMPLETE | 139 passed, 0 failed (was 104 passed, 5 failed) | `test_api.py` — removed TestVistaPlanAPI class |
| 1 | ✅ COMPLETE | 139 passed, 0 failed | `plan-schema.json` — removed 7 legacy/duplicate sections |
| 2 | ✅ COMPLETE | 139 passed, 0 failed | `chat_service.py`, `chat.py`, `app.py` |
| 3 | ✅ COMPLETE | 139 passed, 0 failed | `test_architecture.py` (37 comprehensive tests + 6 schema validation tests fixed) |

**Files Created/Modified:**
- `vista/templates/plan-schema.json` — Schema cleanup complete
- `vista/server/services/chat_service.py` — Chat CLI with plain text output
- `vista/server/routes/chat.py` — POST /api/projects/{id}/chat endpoint
- `vista/server/app.py` — Chat router registered
- `vista/tests/test_architecture.py` — 37 tests for arch + chat features
- `vista/tests/test_api.py` — 5 failing tests removed

**Acceptance Criteria Status:**
- [x] **Phase 4:** Legacy test cleanup complete (5 failing tests deleted)
- [x] **Phase 1:** Schema cleanup complete (7 legacy/duplicate sections removed)
- [x] **Phase 2:** Chat service + API complete (chat now functional)
- [x] **Phase 3:** Test coverage complete (37 comprehensive tests + 6 schema validation tests fixed)
- [ ] **Phase 5:** Polish (Draw.io viewer, SSE streaming, markdown rendering)
- [ ] **Phase 6:** Documentation updates (AGENTS.md corrections)

### Schema Validation Tests Fixed (2026-02-11)

Fixed 6 failing schema validation tests in `test_architecture.py`:

| Test Fix | Description |
|----------|-------------|
| `_get_template_path()` | Added helper method to resolve template paths relative to test location |
| 5 path-related tests | Fixed tests using relative paths `'templates/*.json'` which would fail when run from root directory |
| `test_invoke_provider_returns_error_for_unknown_provider` | Fixed to instantiate ChatService before calling `invoke_provider()` |

**Result:** All 139 tests now pass consistently regardless of working directory.

**Tag:** 0.0.5 (released)

---
- Chat API completely missing (no routes/chat.py, no services/chat_service.py, no router registration)
- Frontend uses `fetch()` + `.json()`, not SSE (architecture.html:457-458)
- Frontend POSTs to `POST /api/projects/${PROJECT_ID}/chat` (architecture.html:438)
- Provider `get_invocation("ps1")`/`get_invocation("sh")` returns shell snippets with `$PromptContent`/`$PROMPT_FILE` variables
- `_run_cli_with_timeout()` has 10s default — needs 120s+ for chat
- `sse_starlette.sse.EventSourceResponse` already available (stream.py:5,35)
- Zero test coverage for architecture features
- All 5 legacy files confirmed deleted
- Provider infrastructure complete and ready for reuse
- `scan_features_detailed()` returns `has_arch_manifest` and `arch_diagram_count` (project_service.py:132-133) — untested

---

## Phase Summary

| Phase | Description | Status | Blocking? |
|-------|-------------|--------|-----------|
| 1 | Schema Cleanup | COMPLETE | No |
| 2 | Chat Service & API | COMPLETE (superseded by architecture-chat v2) | No |
| 3 | Test Coverage | COMPLETE (59 tests across 3 files) | No |
| 4 | Legacy Test Cleanup | COMPLETE | No |
| 5 | Polish (Draw.io, SSE, markdown) | PARTIAL — SSE streaming done; Draw.io viewer not implemented | No |
| 6 | Documentation Updates | NOT STARTED | No |

---

## Phase 1: Schema Cleanup

**Priority:** HIGH
**Files:** `vista/templates/plan-schema.json`
**Spec Reference:** migration-cleanup.md:31

### Tasks

- [ ] Remove duplicate `uiFlows` (lines 180-212 duplicates lines 24-56)
- [ ] Remove duplicate `dataModels` (lines 213-256 duplicates lines 57-100)
- [ ] Remove duplicate `dataFlow` (lines 257-301 duplicates lines 101-145)
- [ ] Remove original `uiFlows` (lines 24-56)
- [ ] Remove original `dataModels` (lines 57-100)
- [ ] Remove original `dataFlow` (lines 101-145)
- [ ] Remove `services` (lines 146-179)
- [ ] Keep `architecture` section (lines 302-312) with `ref` field
- [ ] Keep `implementationPhases` section (lines 313-345)
- [ ] Verify `required` array remains `["implementationPhases"]`
- [ ] Validate resulting schema parses as valid JSON

### Expected Result

`sections.properties` should contain only:
- `architecture` (optional, with `ref` field, default `"./arch/_arch.json"`)
- `implementationPhases` (required)

### Tests (in Phase 3)

- [ ] Schema validates plan with only `implementationPhases`
- [ ] Schema validates plan with `architecture.ref` + `implementationPhases`
- [ ] Schema rejects plan missing `implementationPhases`

---

## Phase 2: Chat Service & API

**Priority:** CRITICAL — Chat UI is fully built but returns 404
**Create:** `vista/server/routes/chat.py`, `vista/server/services/chat_service.py`
**Modify:** `vista/server/app.py` (register chat router)
**Spec Reference:** chat-review.md:114-116

### 2.1 ChatService (`vista/server/services/chat_service.py`)

**Method: `build_prompt(message, context, history)`**
- Combines diagram context + chat history + user message into a single prompt string
- Context = concatenated .mmd/.drawio content (frontend pre-assembles this with `--- filename ---\n` separators at architecture.html:420-425)
- History = list of `{role, content}` dicts from previous messages
- Output format: System instruction + context block + history + user message

**Method: `invoke_provider(provider_name, model, prompt)`**
- Looks up provider via `provider_service.get_provider_by_name(provider_name)`
- Returns 400-style error if provider not found
- Determines shell type from platform (`platform.system() == "Windows"` → `"ps1"`, else `"sh"`)
- **IMPORTANT:** Do NOT use `provider.get_invocation(shell)` — that includes `--output-format=stream-json` (for loop output parsing) which produces structured JSON, not plain text
- **Instead, build a chat-specific CLI command:**
  - For Claude: `claude -p --model {model}` (plain text output, no --output-format flag)
  - For OpenCode: `opencode run --model {model} {prompt}` (already plain text)
  - Use `_find_command()` from provider_service to locate CLI executables
- Execution approach:
  1. Write prompt to temp file
  2. Build CLI command specific to provider type (Claude: pipe stdin, OpenCode: pass as arg)
  3. Execute via `subprocess.Popen` (PowerShell on Windows, Bash on Unix)
  4. Use `CREATE_NO_WINDOW` flag on Windows (critical for MCP daemon context)
  5. Timeout: 120 seconds (AI responses can be long)
  6. On timeout: use `taskkill /T /F` on Windows for process tree cleanup
  7. Read stdout, return response text (plain text, no parsing needed)
  8. Clean up temp file in finally block
- **Alternative approach:** Add a `get_chat_invocation(shell)` method to Provider base class that omits stream-json flags. This is cleaner but requires modifying provider_service.py.

**Cross-platform subprocess pattern** (reuse from provider_service.py:44-81):
```
kwargs = {
    stdout: PIPE, stderr: PIPE, stdin: DEVNULL, text: True
}
if Windows: kwargs["creationflags"] = CREATE_NO_WINDOW
if cmd ends with .cmd/.bat: wrap with ["cmd.exe", "/c"] + cmd
```

### 2.2 Chat Route (`vista/server/routes/chat.py`)

**Endpoint:** `POST /api/projects/{project_id}/chat`

**Request body:**
```json
{
  "message": "string",
  "context": "string (optional, pre-assembled diagram content)",
  "provider": "string",
  "model": "string",
  "history": [{"role": "user|assistant", "content": "string"}]
}
```

**Response (JSON — matches existing frontend at architecture.html:457-458):**
```json
{
  "response": "string"
}
```

**Error responses:**
- 400: Missing required fields, invalid provider, invalid model
- 404: Project not found
- 500: CLI invocation failure (include error message in response body)

**Implementation notes:**
- Validate project exists via `ProjectService.get_by_id(project_id)`
- Validate provider via `get_provider_by_name(provider)`
- Run CLI in thread via `asyncio.to_thread()` to avoid blocking event loop (pattern from providers.py:31)
- **NO frontend changes needed** — current `sendChat()` already handles this exact format

### 2.3 Register Router

Add to `app.py`:
- Import: `from server.routes import ..., chat` (line 32)
- Register: `app.include_router(chat.router)` (after line 39)

### Tests (in Phase 3)

- [ ] `ChatService.build_prompt()` includes context before message
- [ ] `ChatService.build_prompt()` formats history correctly
- [ ] `ChatService.build_prompt()` works with empty context and history
- [ ] `ChatService.invoke_provider()` returns error for unknown provider
- [ ] `POST /api/projects/{id}/chat` returns 200 with mocked CLI response
- [ ] `POST /api/projects/{id}/chat` returns 400 for missing message
- [ ] `POST /api/projects/{id}/chat` returns 400 for invalid provider
- [ ] `POST /api/projects/{id}/chat` returns 404 for unknown project

---

## Phase 3: Test Coverage

**Priority:** HIGH — Zero tests for new architecture features
**Create:** `vista/tests/test_architecture.py`
**Spec Reference:** All 4 specs + PRD test cases (27 test scenarios in diagram_representations_prd.json)

### Fixture Needs

Create a new fixture `arch_project` that extends existing patterns (conftest.py:22-40):
- Creates a mock project with `.vista/features/test-feature/arch/` directory
- Includes a valid `_arch.json` with 2 mermaid entries and 1 drawio entry
- Includes sample `.mmd` and `.drawio` files
- Registers the project

### 3.1 Architecture API Tests

```python
class TestArchitectureAPI:
    def test_get_arch_manifest_success(self, api_env)
    def test_get_arch_manifest_not_found(self, api_env)
    def test_get_arch_manifest_malformed_json(self, api_env)
    def test_get_arch_file_mmd_success(self, api_env)          # text/plain content type
    def test_get_arch_file_drawio_content_type(self, api_env)   # application/xml
    def test_get_arch_file_path_traversal_dotdot(self, api_env) # ../../secrets blocked
    def test_get_arch_file_path_traversal_absolute(self, api_env) # /etc/passwd blocked
    def test_get_arch_file_not_found(self, api_env)
    def test_architecture_page_renders(self, api_env)
    def test_architecture_page_no_manifest(self, api_env)       # Shows empty state
```

### 3.2 Chat API Tests

```python
class TestChatAPI:
    def test_post_chat_success(self, api_env)                   # Mock CLI subprocess
    def test_post_chat_missing_message(self, api_env)
    def test_post_chat_invalid_provider(self, api_env)
    def test_post_chat_with_diagram_context(self, api_env)
    def test_post_chat_project_not_found(self, api_env)
    def test_post_chat_empty_history(self, api_env)
```

### 3.3 ProgressService Arch Tests

```python
class TestProgressServiceArch:
    def test_read_arch_manifest_valid(self, tmp_path)
    def test_read_arch_manifest_missing_file(self, tmp_path)
    def test_read_arch_manifest_invalid_json(self, tmp_path)
    def test_read_arch_file_valid_mmd(self, tmp_path)
    def test_read_arch_file_valid_drawio(self, tmp_path)
    def test_read_arch_file_path_traversal_dotdot(self, tmp_path)   # SECURITY
    def test_read_arch_file_path_traversal_absolute(self, tmp_path) # SECURITY
    def test_read_arch_file_not_found(self, tmp_path)
```

### 3.4 Schema Validation Tests

```python
class TestSchemaValidation:
    def test_plan_schema_valid_minimal(self)                    # Only implementationPhases
    def test_plan_schema_valid_with_architecture(self)          # With architecture.ref
    def test_plan_schema_rejects_missing_phases(self)
    def test_arch_schema_valid_manifest(self)
    def test_arch_schema_rejects_invalid_type(self)             # Not mermaid/drawio
    def test_arch_schema_rejects_missing_fields(self)
```

### 3.5 Project Service Arch Tests

```python
class TestProjectServiceArch:
    def test_scan_features_detailed_has_arch_manifest(self)     # New field in project_service.py:132
    def test_scan_features_detailed_arch_diagram_count(self)    # New field in project_service.py:133
    def test_scan_features_detailed_no_arch(self)               # Feature without arch/ dir
```

---

## Phase 4: Legacy Test Cleanup

**Priority:** HIGH — **5 tests currently failing** (test suite: 104 passed, 5 failed, 2 warnings)
**Files:** `vista/tests/test_api.py`

### Tasks

- [ ] Remove entire `TestVistaPlanAPI` class (lines 271-427) — ALL methods test removed routes:
  - `test_get_vista_plan_exists` → Tests `/api/.../vista-plan` route (REMOVED)
  - `test_get_vista_plan_not_found` → Tests `/api/.../vista-plan` route (REMOVED)
  - `test_get_vista_plan_empty` → Tests `/api/.../vista-plan` route (REMOVED)
  - `test_vista_preview_page` → Tests `/project/{id}/vista/{name}` route (REMOVED)
  - `test_submit_review` → Tests `/api/.../review` route (REMOVED)
  - `test_submit_review_invalid` → Tests `/api/.../review` route (REMOVED)
  - `test_features_detailed_has_plan_fields` → Tests `has_plan_json`, `has_review_json` (REMOVED fields)
- [ ] Remove `_create_project_with_plan()` helper (lines 274-287) — creates old-format plan files
- [ ] Verify remaining test classes still pass after cleanup

### What to Keep

- `TestProjectAPI` (lines 30-102) — Still valid
- `TestLoopAPI` (lines 104-150) — Still valid
- `TestDashboard` (lines 152-174) — Still valid
- `TestHealthAPI` (lines 176-237) — Still valid (but `test_list_features_detailed` doesn't test `has_arch_manifest`/`arch_diagram_count` — this is covered in Phase 3)
- `TestPlanAPI` (lines 239-269) — Still valid

---

## Phase 5: Polish

**Priority:** LOW — MVP works without these

### 5.1 Draw.io Embedded Viewer
- **Current:** `.drawio` rendered as raw XML in `<pre>` (architecture.html:304)
- **Target:** Embed via `https://viewer.diagrams.net/` iframe
- **Files:** `vista/server/views/architecture.html` only
- **Approach:** For drawio entries, create iframe with `src="https://viewer.diagrams.net/?..."` and pass file content via URL encoding or postMessage
- **Spec:** rendering-pipeline.md:32-33

### 5.2 SSE Streaming for Chat ✅ COMPLETE
- **Implemented:** Protocol-native streaming via `ProviderRouter` (not CLI subprocess)
- Claude: WebSocket streaming via `ClaudeWSClient` -> Companion server
- OpenCode: HTTP SSE streaming via `OpenCodeClient`
- SSE endpoint: `GET /api/projects/{id}/chat/sessions/{sid}/stream` delivers merged chat tokens + diagram change events
- Uses `sse_starlette.sse.EventSourceResponse` with per-session pub/sub queues
- **Note:** This replaced the original CLI subprocess approach entirely. The `ChatService` is now a deprecated placeholder.

### 5.3 Markdown Rendering in Chat
- **Current:** Chat responses rendered as plain text
- **Target:** Render markdown (code blocks, lists, headers)
- **Library:** `marked.js` from CDN (already mentioned in AGENTS.md)
- **Files:** `architecture.html` — modify `addChatMessage()` function (line 401)

---

## Phase 6: Documentation Updates

**Priority:** LOW
**Files:** `AGENTS.md`

### Tasks

- [ ] Update "New Endpoints" section: Architecture routes are implemented, not "to implement"
- [ ] Fix chat endpoint URL: `POST /api/projects/{project_id}/chat` (not `POST /api/chat/send`)
- [ ] Add architecture viewer URL pattern: `/project/{id}/arch/{feature_name}`
- [ ] Update project structure to show new files (routes/chat.py, services/chat_service.py)
- [ ] Remove reference to `preview.py` as legacy (already deleted)
- [ ] Update "Chat Not Working" troubleshooting once chat is implemented

---

## Completed Items (Verified by Source Analysis)

### Architecture Directory Structure ✅
- `setup-feature.py` creates `arch/` + `_arch.json` (lines 38-49)
- `arch-schema.json` valid JSON Schema (64 lines, supports mermaid/drawio types, architecture/tdd categories)
- Schema supports diagramTypes: flowchart, sequence, state, er, gantt, architecture, wireframe, custom, logic-flow, decision-tree, test-contract

### Server API for Architecture Files ✅
- `GET /api/projects/{id}/features/{name}/arch` — manifest (architecture.py:14-25)
- `GET /api/projects/{id}/features/{name}/arch/{filename}` — file content (architecture.py:28-47)
- `GET /project/{id}/arch/{feature_name}` — viewer page (architecture.py:50-63)
- Path traversal protection: strips to basename, rejects `..`, validates resolved path (progress_service.py:63-82)
- Router registered in app.py (line 39)

### Web App Rendering ✅
- Mermaid.js from CDN (architecture.html:6)
- `mermaid.render()` client-side rendering (architecture.html:301-302)
- Dark theme with custom colors (architecture.html:272-285)
- Error handling per diagram card (architecture.html:307)
- Empty state placeholder when no diagrams (architecture.html:190-194)
- Zero custom SVG code — fully delegated to mermaid.js

### Chat Panel UI ✅
- Floating toggle button bottom-right (architecture.html:75-96)
- Slide-out panel 40% width (architecture.html:57-74)
- Provider dropdown from `/api/providers` (architecture.html:353-372)
- Model dropdown from `/api/providers/{name}/models` (architecture.html:374-390)
- Diagram click-to-attach with removable chips (architecture.html:213-215, 319-351)
- Multiple attachment support via Set (architecture.html:267-269)
- Message thread with user/assistant styling (architecture.html:97-146)
- `sendChat()` already POSTs to correct URL with correct payload (architecture.html:411-463)

### Migration & Cleanup ✅
- 5 legacy files deleted: template.html, collect-review.py, review-schema.json, preview.py, vista_preview.html
- Review routes removed from plans.py (verified — no /review or /vista-plan endpoints)
- Review methods removed from progress_service.py (verified — only arch methods remain)
- Plan skill updated for arch/ workflow (SKILL.md Step 3: lines 128-235)

### Provider Infrastructure ✅ (Ready for Chat)
- ClaudeProvider: `get_invocation("ps1")` returns PowerShell with `$PromptContent` variable (provider_service.py:129-144)
- ClaudeProvider: `get_invocation("sh")` returns Bash with `$PROMPT_FILE` variable (provider_service.py:129-144)
- OpenCodeProvider: Dynamic model discovery via CLI (provider_service.py:151-176)
- `_run_cli_with_timeout()`: Subprocess utility with Windows CREATE_NO_WINDOW, .cmd wrapping, taskkill cleanup (provider_service.py:44-81)
- `_find_command()`: CLI discovery in PATH + common install locations (provider_service.py:21-41)
- `get_provider_by_name()`: Provider lookup by name (provider_service.py:220-225)

---

## Acceptance Criteria Status (Updated 2026-02-15)

### arch-directory.md:
- [x] setup-feature.py creates arch/ directory and _arch.json
- [x] _arch.json validates against schema
- [x] _plan.json schema includes architecture.ref field
- [x] plan-schema.json no longer has legacy sections
- [x] Server API reads _arch.json manifest
- [x] Server API reads individual diagram files

### rendering-pipeline.md:
- [x] Mermaid .mmd files render as interactive SVG
- [ ] Draw.io .drawio files in embedded viewer (not implemented)
- [x] Each diagram shows title/description from manifest
- [x] Mermaid parse errors display inline with source
- [x] Missing files show placeholder
- [x] No custom SVG layout code

### chat-review.md:
- [x] Chat button visible on architecture page
- [x] Panel slides out to side-by-side layout
- [x] Provider dropdown loads from API
- [x] Model dropdown loads when provider selected
- [x] Clicking diagram attaches as context chip
- [x] Multiple diagrams attachable
- [x] Sending invokes provider with context (via ProviderRouter, not CLI)
- [x] Response streams back via SSE
- [x] Chat thread displays messages
- [x] Connection errors shown as system messages

### migration-cleanup.md:
- [x] plan-schema.json no longer has old sections
- [x] Legacy files removed
- [x] Review routes removed
- [x] Review methods removed
- [x] setup-feature.py updated
- [x] Plan skill documentation updated

---

## Files Summary

### ✅ Complete (No Changes Needed)
| File | Evidence |
|------|---------|
| `vista/templates/arch-schema.json` | Valid schema, 64 lines |
| `vista/scripts/setup-feature.py` | Creates arch/ + _arch.json (lines 38-49) |
| `vista/server/services/progress_service.py` | Arch methods + path traversal protection |
| `vista/server/routes/architecture.py` | 3 routes working |
| `vista/server/views/architecture.html` | Full UI, awaiting backend chat API |
| `vista/server/app.py` | Architecture router registered |
| `vista/skills/plan/SKILL.md` | Arch workflow documented (Step 3: lines 128-235) |
| `vista/server/services/provider_service.py` | CLI invocation ready |
| `vista/server/routes/providers.py` | Provider/model endpoints |

### Completed Since Original Plan
| File | Status | Notes |
|------|--------|-------|
| `vista/templates/plan-schema.json` | DONE | Legacy sections removed |
| `vista/tests/test_api.py` | DONE | TestVistaPlanAPI class removed |
| `vista/server/services/chat_service.py` | DONE | Deprecated placeholder (replaced by ProviderRouter) |
| `vista/tests/test_architecture.py` | DONE | 30 tests for arch API, ProgressService, schema, ProjectService |
| `vista/tests/test_diagram_watcher.py` | DONE | 18 tests for diagram watcher |
| `vista/tests/test_context_assembler.py` | DONE | 11 tests for context assembly |

### Known Gaps
| Gap | Notes |
|-----|-------|
| No test file for chat_sessions.py routes | Chat CRUD, SSE streaming, send_message flow untested |
| No test file for ChatSessionService | Session persistence untested |
| watchdog not installed in test env | Blocks 28 tests (10 API integration + 18 watcher) |
| Draw.io viewer not implemented | .drawio files may render as raw XML |

---

## Implementation Order

1. **Phase 4** — Legacy test cleanup (5 min, fixes 5 currently failing tests — do first for green CI)
2. **Phase 1** — Schema cleanup (10 min, removes technical debt)
3. **Phase 2** — Chat service + API (unblocks primary missing functionality)
4. **Phase 3** — Tests (validates correctness, especially path traversal security)
5. **Phase 5** — Polish (Draw.io viewer, SSE streaming, markdown rendering)
6. **Phase 6** — Documentation updates (AGENTS.md corrections)
