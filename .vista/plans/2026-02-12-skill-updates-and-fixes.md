# Vista Skills & Features Update — Implementation Plan

## Overview

Four updates to Vista skills and infrastructure: a critical bug fix for ralph job stopping, a project-setup skill enhancement, a ralph skill rewrite as an interactive wizard, and a model favorites feature for the settings/provider system.

## What We're NOT Doing

- No changes to skill-creator skill
- No changes to plan, add, specs, tdd, legacy, or vista skills
- No new MCP tools for favorites (exposed through existing `ralph_providers`)
- No changes to the ralph loop script template or execution logic

---

## Phase 1: Fix ralph_stop killing MCP server (BUG)

### Overview
`ralph_service.stop_job()` uses `taskkill /T /F /PID` which kills the entire process tree — including the MCP server that spawned the subprocess. This breaks both the dashboard stop button and the MCP `ralph_stop` tool.

### Changes Required

#### 1. Spawn with own process group
**File**: `vista/server/services/ralph_service.py` (line 97-98)

Change creation flags from:
```python
if platform.system() == "Windows":
    popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
```
To:
```python
if platform.system() == "Windows":
    popen_kwargs["creationflags"] = (
        subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    )
```

`CREATE_NEW_PROCESS_GROUP` (0x200) gives the subprocess its own process group so `taskkill /T` on it won't walk up to the parent MCP server.

#### 2. Stop only the subprocess tree
**File**: `vista/server/services/ralph_service.py` (lines 156-161)

The current Windows stop code is fine as-is:
```python
subprocess.run(
    ["taskkill", "/T", "/F", "/PID", str(pid)],
    capture_output=True,
    text=True,
)
```

With `CREATE_NEW_PROCESS_GROUP`, `taskkill /T /F /PID <child_pid>` will kill the child and its descendants only — it won't traverse up to the MCP server because the child is now in its own process group.

### Success Criteria

#### Automated Verification:
- [x] MCP server starts successfully with `python vista/mcp_server.py`
- [x] `ralph_start` creates a job and subprocess runs
- [x] `ralph_stop` stops the job without killing the MCP server
- [x] Dashboard remains accessible after stopping a job

#### Manual Verification:
- [ ] Start a ralph job from the dashboard or MCP tool
- [ ] Click "Stop Job" button on dashboard — page reloads with "Stopped" status
- [ ] Use `ralph_stop` MCP tool — server stays alive, dashboard stays up
- [ ] Start another job after stopping one — works normally

---

## Phase 2: Model Favorites

### Overview
Add a `favorites` array (max 3 model IDs) per provider in settings. Expose favorites through the existing `ralph_providers` MCP tool response. Add star toggles to the settings UI models table.

### Changes Required

#### 1. Settings schema
**File**: `vista/settings.json` — DONE

#### 2. Provider service — include favorites in response
**File**: `vista/server/services/provider_service.py` — DONE

#### 3. Settings API validation
**File**: `vista/server/routes/ralph_settings.py` — DONE

#### 4. Settings UI — star toggles
**File**: `vista/server/views/ralph_settings.html` — DONE

### Success Criteria

#### Automated Verification:
- [x] Settings API GET returns favorites array per provider
- [x] Settings API PUT accepts and persists favorites
- [x] `ralph_providers` MCP tool returns favorites in response
- [x] Validation rejects >3 favorites per provider

#### Manual Verification:
- [ ] Settings UI shows star toggles per model
- [ ] Clicking star toggles favorite on/off with visual feedback
- [ ] Cannot select more than 3 favorites (shows alert)
- [ ] Favorites persist after save and page reload

---

## Phase 3: Ralph Skill Rewrite — Interactive Wizard

### Overview
Rewrite `ralph/SKILL.md` to define an interactive wizard flow using `AskUserQuestion`. Remove old hardcoded Flutter patterns and template-copy approach.

### Changes Required

#### 1. Rewrite SKILL.md
**File**: `vista/skills/ralph/SKILL.md` — DONE

### Success Criteria

#### Manual Verification:
- [ ] `/ralph` command triggers the interactive wizard
- [ ] Each question presents correct options via AskUserQuestion
- [ ] Model question shows favorites for selected provider
- [ ] Agent correctly calls `ralph_start` with all collected parameters
- [ ] Selecting "Other" for any question allows free text input

---

## Phase 4: project-setup Skill — Add .vista/ Directory

### Overview
Update project-setup to also create `.vista/` directory structure during initialization.

### Changes Required

#### 1. Update SKILL.md
**File**: `vista/skills/project-setup/SKILL.md` — DONE

### Success Criteria

#### Manual Verification:
- [ ] Running project-setup on a fresh project creates `.vista/features/` and `.vista/ralph/`
- [ ] Running project-setup on a project with existing `.vista/` does not error or overwrite

---

## Implementation Order

1. **Phase 1** (bug fix) — highest priority, unblocks dashboard usage
2. **Phase 2** (model favorites) — needed before Phase 3 so ralph wizard can show favorites
3. **Phase 3** (ralph skill rewrite) — depends on Phase 2 favorites being available
4. **Phase 4** (project-setup) — independent, can be done anytime

## References

- Ralph service: `vista/server/services/ralph_service.py`
- Provider service: `vista/server/services/provider_service.py`
- Settings config: `vista/server/config.py`
- Settings API: `vista/server/routes/ralph_settings.py`
- Settings UI: `vista/server/views/ralph_settings.html`
- MCP server: `vista/mcp_server.py`
- Ralph skill: `vista/skills/ralph/SKILL.md`
- Project-setup skill: `vista/skills/project-setup/SKILL.md`
- Settings file: `vista/settings.json`
