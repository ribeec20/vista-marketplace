# Ralph Loop Plugin - Web Server Implementation Plan

## Implementation Status

All phases IMPLEMENTED and TESTED (92 tests passing):

**Initial Implementation (54 tests)**:
- **Phase 1-7**: Server core, services, routes, app entry, UI templates, scripts, hooks

**Iteration 2 Additions (38 new tests)**:
- TemplateResponse deprecation warnings fixed (modern signature)
- Health check endpoint added (`/health`)
- Loop service fully unit tested (35 new tests for subprocess lifecycle)
- Rich feature scanning with detailed metadata endpoint (`/api/projects/{id}/features/{name}/metadata`)

### Remaining Work

- httpx TestClient deprecation warning (cosmetic, requires httpx transport migration)
- End-to-end loop execution test (requires claude CLI installed)
- Verify SSE streaming in browser
- Test cross-platform (Mac/Linux) script generation
- Loop history tracking (log iterations to file, like src/backend's loop_history_service)
- Pause/resume loop support (file-based signal, like src/backend)

---

## Summary

Build a lightweight Python (FastAPI) web server in `server/` that replaces `ralph.py`'s terminal menu with a browser dashboard. The server uses **exactly the same execution pattern** as `ralph.py`:

1. Web form collects the same 4 inputs as ralph.py's menu: **feature, mode, model, iterations**
2. Server replicates `ralph.py`'s `run_loop()` logic: create prompt file + generate loop script in the feature directory
3. Server runs the generated loop script from the **project root** (`cwd=project_path`)
4. The loop script uses absolute paths for feature_dir so it works regardless of cwd

The existing `src/backend/` server (Docker/OpenCode) is left untouched. `ralph.py` is NOT modified - it's the **reference implementation** that the server mirrors.

---

## Key Design Decisions

1. **Python/FastAPI** (not Node.js) - consistent with ralph.py and the codebase. No new runtime.
2. **Mirror ralph.py's run_loop() exactly** - same prompt template substitution (`get_prompt_content()`), same `LOOP_SCRIPT_TEMPLATE` for Windows, equivalent bash template for Mac. Files are created in the feature directory and cleaned up after.
3. **Run from project root** - `cwd=project_path` so Claude starts in the project root and can edit files directly. The loop script receives the feature directory as an absolute path.
4. **JSON file storage** - `server/data/projects.json` for project registry. No database.
5. **SSE for live output** - stream subprocess stdout to browser via Server-Sent Events.
6. **Parse script output** - regex patterns for iteration markers, RALPH_CONTROL blocks, progress.txt (data ralph.py's scripts already output).
7. **Multi-project support** - one loop per project can run concurrently. Dashboard shows all.
8. **Cross-platform** - generates loop.ps1 on Windows (using ralph.py's `LOOP_SCRIPT_TEMPLATE`), generates loop.sh on Mac (equivalent bash template).

---

## Complete File Listing

```
plugin_1/
├── server/
│   ├── __init__.py
│   ├── app.py                          # FastAPI entry point
│   ├── config.py                       # Server configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py                  # Project dataclass
│   │   └── loop_state.py              # LoopInstance dataclass
│   ├── services/
│   │   ├── __init__.py
│   │   ├── project_service.py         # JSON-based project CRUD
│   │   ├── loop_service.py            # Subprocess lifecycle manager
│   │   ├── output_parser.py           # Script output regex parser
│   │   └── progress_service.py        # progress.txt / IMPLEMENTATION_PLAN.md reader
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── projects.py                # Project API endpoints
│   │   ├── loops.py                   # Loop control endpoints
│   │   ├── stream.py                  # SSE streaming endpoint
│   │   └── plans.py                   # Plan view endpoint
│   ├── views/
│   │   ├── _base.html                 # Shared layout template
│   │   ├── dashboard.html             # All projects overview
│   │   ├── project.html               # Single project detail + loop controls
│   │   ├── loop_status.html           # Live loop status view
│   │   ├── plan_preview.html          # Implementation plan rendered view
│   │   └── static/
│   │       ├── style.css              # Custom styles
│   │       └── app.js                 # SSE client + UI interactions
│   └── data/
│       └── projects.json              # Registry of activated projects (initially [])
├── scripts/
│   ├── start-server.ps1               # Windows server start
│   ├── start-server.sh                # Mac/Linux server start
│   ├── stop-server.ps1                # Windows server stop
│   ├── stop-server.sh                 # Mac/Linux server stop
│   └── start_server_check.py          # Cross-platform launcher for hooks
│   # NOTE: No scripts/loop.sh - loop scripts are generated in feature_dir
│   # at runtime (same pattern as ralph.py) and cleaned up after
└── hooks/
    └── hooks.json                     # SessionStart auto-start hook
```

---

## Phase 1: Server Core (config + models)

### 1.1 `server/__init__.py`

Empty package marker.

### 1.2 `server/config.py`

```python
"""Server configuration. All paths computed relative to plugin root."""
import os
from pathlib import Path

# Directory structure
PLUGIN_ROOT = Path(__file__).resolve().parent.parent   # plugin_1/
SERVER_DIR = Path(__file__).resolve().parent            # plugin_1/server/
PORTABLE_DIR = PLUGIN_ROOT / "portable"
TEMPLATES_DIR = PORTABLE_DIR / "templates"
DATA_DIR = SERVER_DIR / "data"
PROJECTS_FILE = DATA_DIR / "projects.json"
VIEWS_DIR = SERVER_DIR / "views"
STATIC_DIR = VIEWS_DIR / "static"

# Server settings
HOST = os.environ.get("RALPH_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("RALPH_SERVER_PORT", "3456"))
PID_FILE = SERVER_DIR / "server.pid"

# NOTE: No LOOP_PS1/LOOP_SH paths - loop scripts are generated at runtime
# in the feature directory, same pattern as ralph.py's run_loop()
```

### 1.3 `server/models/__init__.py`

Empty package marker.

### 1.4 `server/models/project.py`

```python
"""Project model - JSON-serializable dataclass for project registry."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""           # Derived from directory name
    path: str = ""           # Absolute path to project root
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```

### 1.5 `server/models/loop_state.py`

```python
"""Per-project loop state tracking."""
from dataclasses import dataclass, field
from typing import Optional
from collections import deque


@dataclass
class LoopInstance:
    project_id: str = ""
    feature_name: str = ""
    mode: str = ""                     # "plan" or "build"
    model: str = ""                    # "opus", "sonnet", "haiku"
    status: str = "idle"               # "idle", "starting", "running", "stopped", "completed", "failed"
    pid: Optional[int] = None          # OS process ID
    iteration: int = 0                 # Current iteration number
    max_iterations: int = 0            # 0 = unlimited
    start_time: Optional[str] = None   # ISO datetime
    end_time: Optional[str] = None     # ISO datetime
    error: Optional[str] = None
    output_lines: deque = field(default_factory=lambda: deque(maxlen=2000))
    last_ralph_control: Optional[dict] = None   # {"status": "done", "files_changed": "3"}
    progress_summary: Optional[str] = None      # Last contents of progress.txt

    def to_dict(self) -> dict:
        """Serialize for JSON/API response."""
        return {
            "project_id": self.project_id,
            "feature_name": self.feature_name,
            "mode": self.mode,
            "model": self.model,
            "status": self.status,
            "pid": self.pid,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error,
            "output_line_count": len(self.output_lines),
            "last_ralph_control": self.last_ralph_control,
            "progress_summary": self.progress_summary,
        }
```

---

## Phase 2: Services

### 2.1 `server/services/__init__.py`

Empty package marker.

### 2.2 `server/services/project_service.py`

```python
"""CRUD operations on server/data/projects.json. No database - just JSON file read/write."""
import json
from pathlib import Path
from typing import Optional
from server.config import PROJECTS_FILE, DATA_DIR
from server.models.project import Project


class ProjectService:
    """Manages the project registry stored in projects.json."""

    @staticmethod
    def _ensure_file():
        """Create data directory and projects.json if they don't exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROJECTS_FILE.exists():
            PROJECTS_FILE.write_text("[]", encoding="utf-8")

    @staticmethod
    def _load() -> list[dict]:
        ProjectService._ensure_file()
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))

    @staticmethod
    def _save(projects: list[dict]):
        ProjectService._ensure_file()
        PROJECTS_FILE.write_text(json.dumps(projects, indent=2), encoding="utf-8")

    @staticmethod
    def get_all() -> list[Project]:
        """Return all registered projects."""
        return [Project.from_dict(p) for p in ProjectService._load()]

    @staticmethod
    def get_by_id(project_id: str) -> Optional[Project]:
        """Get a single project by ID."""
        for p in ProjectService._load():
            if p["id"] == project_id:
                return Project.from_dict(p)
        return None

    @staticmethod
    def register(path: str) -> Project:
        """Register a new project. Validates path exists."""
        abs_path = Path(path).resolve()
        if not abs_path.is_dir():
            raise ValueError(f"Path does not exist or is not a directory: {path}")

        projects = ProjectService._load()

        # Check for duplicate path
        for p in projects:
            if Path(p["path"]).resolve() == abs_path:
                raise ValueError(f"Project already registered: {abs_path}")

        project = Project(
            name=abs_path.name,
            path=str(abs_path),
        )
        projects.append(project.to_dict())
        ProjectService._save(projects)
        return project

    @staticmethod
    def unregister(project_id: str) -> bool:
        """Remove a project from the registry."""
        projects = ProjectService._load()
        filtered = [p for p in projects if p["id"] != project_id]
        if len(filtered) == len(projects):
            return False
        ProjectService._save(filtered)
        return True

    @staticmethod
    def scan_features(project_path: str) -> list[str]:
        """Scan a project's .claude/features/ directory for feature names."""
        features_dir = Path(project_path) / ".claude" / "features"
        if not features_dir.exists():
            return []
        features = []
        for d in sorted(features_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("_"):
                features.append(d.name)
        return features
```

### 2.3 `server/services/output_parser.py`

```python
"""Parse ralph loop script stdout for structured data.

Matches output from:
- portable/ralph-loop.ps1 (iteration markers, timestamps, completion)
- PROMPT_build.md RALPH_CONTROL block (status, files_changed)
- PROMPT_plan.md progress updates
"""
import re
from dataclasses import dataclass
from typing import Optional


# Regex patterns matching actual script output
ITERATION_PATTERN = re.compile(r"=+ ITERATION (\d+) =+")
TIMESTAMP_PATTERN = re.compile(r"Started: (\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
ITERATION_COMPLETE = re.compile(r"\[.*?\] ITERATION (\d+) complete")
LOOP_FINISHED = re.compile(r"Loop finished after (\d+) iteration\(s\)")
MAX_REACHED = re.compile(r"Reached max iterations: (\d+)")
ALL_PHASES = re.compile(r"All phases complete")
RALPH_CONTROL_HEADER = re.compile(r"#\s*RALPH_CONTROL")
KV_LINE = re.compile(r"^(\w[\w_]*):\s*(.+)$")


@dataclass
class ParsedEvent:
    """A structured event parsed from script output."""
    event_type: str    # "iteration_start", "iteration_complete", "ralph_control",
                       # "loop_finished", "all_phases_complete", "raw"
    data: dict


class OutputParser:
    """Stateful parser that tracks multi-line RALPH_CONTROL blocks."""

    def __init__(self):
        self._in_ralph_control = False
        self._ralph_buffer: dict = {}

    def parse_line(self, line: str) -> list[ParsedEvent]:
        """Parse a single output line. May return 0 or more events."""
        events = []
        stripped = line.strip()

        # Check for RALPH_CONTROL block start
        if RALPH_CONTROL_HEADER.match(stripped):
            self._in_ralph_control = True
            self._ralph_buffer = {}
            return events

        # Inside RALPH_CONTROL block - collect key: value pairs
        if self._in_ralph_control:
            kv = KV_LINE.match(stripped)
            if kv:
                self._ralph_buffer[kv.group(1).lower()] = kv.group(2).strip()
                return events
            elif stripped == "" or stripped.startswith("```"):
                # End of block
                if self._ralph_buffer:
                    events.append(ParsedEvent("ralph_control", dict(self._ralph_buffer)))
                self._in_ralph_control = False
                self._ralph_buffer = {}
                return events

        # Iteration start
        m = ITERATION_PATTERN.search(line)
        if m:
            events.append(ParsedEvent("iteration_start", {"iteration": int(m.group(1))}))
            return events

        # Timestamp
        m = TIMESTAMP_PATTERN.search(line)
        if m:
            events.append(ParsedEvent("timestamp", {"time": m.group(1)}))
            return events

        # Iteration complete
        m = ITERATION_COMPLETE.search(line)
        if m:
            events.append(ParsedEvent("iteration_complete", {"iteration": int(m.group(1))}))
            return events

        # Loop finished
        m = LOOP_FINISHED.search(line)
        if m:
            events.append(ParsedEvent("loop_finished", {"total_iterations": int(m.group(1))}))
            return events

        # Max iterations reached
        m = MAX_REACHED.search(line)
        if m:
            events.append(ParsedEvent("max_reached", {"max": int(m.group(1))}))
            return events

        # All phases complete
        if ALL_PHASES.search(line):
            events.append(ParsedEvent("all_phases_complete", {}))
            return events

        return events
```

### 2.4 `server/services/progress_service.py`

```python
"""Read progress.txt and IMPLEMENTATION_PLAN.md from feature directories."""
import re
from pathlib import Path
from typing import Optional


class ProgressService:

    @staticmethod
    def read_progress(project_path: str, feature_name: str) -> dict:
        """Read and parse progress.txt for a feature."""
        feature_dir = Path(project_path) / ".claude" / "features" / feature_name
        progress_file = feature_dir / "progress.txt"

        if not progress_file.exists():
            return {"exists": False, "content": "", "all_complete": False}

        content = progress_file.read_text(encoding="utf-8")

        # Extract phase info
        phase_match = re.search(r"Phase:\s*(\w+)", content)
        current_phase_match = re.search(r"CurrentPhase:\s*(\d+)", content)

        return {
            "exists": True,
            "content": content,
            "phase": phase_match.group(1) if phase_match else None,
            "current_phase": int(current_phase_match.group(1)) if current_phase_match else None,
            "all_complete": content.strip().startswith("ALL PHASES COMPLETE")
                           or "ALL PHASES COMPLETE" in content,
        }

    @staticmethod
    def read_implementation_plan(project_path: str, feature_name: str) -> Optional[str]:
        """Read IMPLEMENTATION_PLAN.md if it exists."""
        plan_file = Path(project_path) / ".claude" / "features" / feature_name / "IMPLEMENTATION_PLAN.md"
        if plan_file.exists():
            return plan_file.read_text(encoding="utf-8")
        return None

    @staticmethod
    def read_agents_md(project_path: str, feature_name: str) -> Optional[str]:
        """Read AGENTS.md if it exists."""
        agents_file = Path(project_path) / ".claude" / "features" / feature_name / "AGENTS.md"
        if agents_file.exists():
            return agents_file.read_text(encoding="utf-8")
        return None
```

### 2.5 `server/services/loop_service.py` (THE CORE)

**This mirrors `portable/ralph.py`'s `run_loop()` (lines 178-244) exactly, adapted for async + web output.**

ralph.py's run_loop() does:
1. Create `PROMPT_{mode}.md` in feature_dir if not exists (from template with variable substitution)
2. Create `loop.ps1` in feature_dir (from LOOP_SCRIPT_TEMPLATE with config baked in)
3. Run `powershell -ExecutionPolicy Bypass -File loop.ps1` with `cwd=project_path`
4. Clean up created files when done

The server does the same, but:
- Uses `subprocess.Popen` instead of `subprocess.run` for non-blocking output capture
- Generates `loop.sh` on Mac instead of `loop.ps1`
- Streams output to SSE subscribers
- Accepts `project_path` as parameter (ralph.py hardcodes `PROJECT_ROOT = SCRIPT_DIR.parent`)

```python
"""Loop lifecycle management - mirrors ralph.py's run_loop() for web.

Execution pattern:
1. Create PROMPT_{mode}.md in feature_dir from template (if not exists)
2. Generate loop.ps1 (Windows) or loop.sh (Mac) in feature_dir with config baked in
3. Run the script with cwd=project_path (project root) so Claude starts there
4. Script uses absolute paths to feature_dir for prompt/progress files
5. Clean up generated files when done
"""
import asyncio
import json
import os
import platform
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from server import config
from server.models.loop_state import LoopInstance
from server.services.output_parser import OutputParser


# Identical to ralph.py's LOOP_SCRIPT_TEMPLATE (lines 24-119)
# The server uses the same template so the generated script behaves identically
LOOP_PS1_TEMPLATE = '''# Feature Loop - Auto-generated by server
# This file will be deleted after the loop completes

param(
    [ValidateSet("plan", "build")]
    [string]$Mode = "{mode}",
    [int]$MaxIterations = {max_iterations},
    [string]$Model = "{model}"
)

# Absolute paths baked in by server - no relative resolution needed
$FeatureDir = "{feature_dir}"
$ProjectRoot = "{project_root}"

$PromptFile = Join-Path $FeatureDir "PROMPT_$Mode.md"
$ProgressFile = Join-Path $FeatureDir "progress.txt"

$CurrentBranch = git branch --show-current

Write-Host "Feature: {feature_name}"
Write-Host "Mode:    $Mode"
Write-Host "Model:   $Model"
Write-Host "Branch:  $CurrentBranch"
Write-Host "Project: $ProjectRoot"
Write-Host "Prompt:  $PromptFile"
if ($MaxIterations -gt 0) {{
    Write-Host "Max:     $MaxIterations iterations"
}} else {{
    Write-Host "Max:     unlimited"
}}

if (-not (Test-Path $PromptFile)) {{
    Write-Host "Error: $PromptFile not found" -ForegroundColor Red
    exit 1
}}

$Iteration = 0

while ($true) {{
    if ($MaxIterations -gt 0 -and $Iteration -ge $MaxIterations) {{
        Write-Host "Reached max iterations: $MaxIterations"
        break
    }}

    $Iteration++
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

    Write-Host ""
    Write-Host "======================== ITERATION $Iteration ========================"
    Write-Host "Started: $Timestamp"
    Write-Host ""

    $PromptContent = Get-Content $PromptFile -Raw
    $PromptContent | claude -p `
        --dangerously-skip-permissions `
        --output-format=stream-json `
        --model $Model `
        --verbose

    git push origin $CurrentBranch
    if ($LASTEXITCODE -ne 0) {{
        Write-Host "Failed to push. Creating remote branch..."
        git push -u origin $CurrentBranch
    }}

    Write-Host ""
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] ITERATION $Iteration complete"

    if ($Mode -eq "build") {{
        $ProgressContent = Get-Content $ProgressFile -Raw -ErrorAction SilentlyContinue
        if ($ProgressContent -match "ALL PHASES COMPLETE") {{
            Write-Host "All phases complete! Stopping loop."
            break
        }}
    }}
}}

Write-Host ""
Write-Host "Loop finished after $Iteration iteration(s)"
Write-Host "Check: $ProgressFile"
'''

# Bash equivalent of the above for Mac/Linux
LOOP_SH_TEMPLATE = '''#!/bin/bash
# Feature Loop - Auto-generated by server
# This file will be deleted after the loop completes

MODE="{mode}"
MAX_ITERATIONS={max_iterations}
MODEL="{model}"

# Absolute paths baked in by server - no relative resolution needed
FEATURE_DIR="{feature_dir}"
PROJECT_ROOT="{project_root}"

PROMPT_FILE="$FEATURE_DIR/PROMPT_$MODE.md"
PROGRESS_FILE="$FEATURE_DIR/progress.txt"

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

echo "Feature: {feature_name}"
echo "Mode:    $MODE"
echo "Model:   $MODEL"
echo "Branch:  $CURRENT_BRANCH"
echo "Project: $PROJECT_ROOT"
echo "Prompt:  $PROMPT_FILE"
if [ "$MAX_ITERATIONS" -gt 0 ] 2>/dev/null; then
    echo "Max:     $MAX_ITERATIONS iterations"
else
    echo "Max:     unlimited"
fi

if [ ! -f "$PROMPT_FILE" ]; then
    echo "Error: $PROMPT_FILE not found"
    exit 1
fi

ITERATION=0

while true; do
    if [ "$MAX_ITERATIONS" -gt 0 ] 2>/dev/null && [ "$ITERATION" -ge "$MAX_ITERATIONS" ]; then
        echo "Reached max iterations: $MAX_ITERATIONS"
        break
    fi

    ITERATION=$((ITERATION + 1))
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

    echo ""
    echo "======================== ITERATION $ITERATION ========================"
    echo "Started: $TIMESTAMP"
    echo ""

    cat "$PROMPT_FILE" | claude -p \\
        --dangerously-skip-permissions \\
        --output-format=stream-json \\
        --model "$MODEL" \\
        --verbose

    git push origin "$CURRENT_BRANCH" 2>/dev/null || {{
        echo "Creating remote branch..."
        git push -u origin "$CURRENT_BRANCH" 2>/dev/null || true
    }}

    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M')] ITERATION $ITERATION complete"

    if [ "$MODE" = "build" ]; then
        if grep -q "ALL PHASES COMPLETE" "$PROGRESS_FILE" 2>/dev/null; then
            echo "All phases complete! Stopping loop."
            break
        fi
    fi
done

echo ""
echo "Loop finished after $ITERATION iteration(s)"
echo "Check: $PROGRESS_FILE"
'''


class LoopService:
    def __init__(self):
        self._loops: dict[str, LoopInstance] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._created_files: dict[str, list[Path]] = {}  # project_id -> files to clean up

    def get_state(self, project_id: str) -> Optional[LoopInstance]:
        return self._loops.get(project_id)

    def get_all_states(self) -> dict[str, LoopInstance]:
        return self._loops

    async def start_loop(
        self,
        project_id: str,
        project_path: str,
        feature_name: str,
        mode: str,
        model: str,
        max_iterations: int = 0,
    ) -> LoopInstance:
        """Start a ralph loop - mirrors ralph.py's run_loop() exactly."""

        # Check if already running
        existing = self._loops.get(project_id)
        if existing and existing.status in ("running", "starting"):
            raise ValueError("A loop is already running for this project")

        feature_dir = Path(project_path) / ".claude" / "features" / feature_name
        if not feature_dir.exists():
            raise ValueError(f"Feature directory not found: {feature_dir}")

        created_files = []

        # --- Step 1: Create prompt file (mirrors ralph.py lines 191-200) ---
        prompt_file = feature_dir / f"PROMPT_{mode}.md"
        if not prompt_file.exists():
            prompt_content = self._get_prompt_content(mode, feature_name, feature_dir, project_path)
            if not prompt_content:
                raise ValueError(f"No prompt template found for mode: {mode}")
            prompt_file.write_text(prompt_content, encoding="utf-8")
            created_files.append(prompt_file)

        # --- Step 2: Create loop script (mirrors ralph.py lines 203-214) ---
        # Normalize paths for the target platform
        feature_dir_str = str(feature_dir).replace("\\", "/")
        project_root_str = str(Path(project_path).resolve()).replace("\\", "/")

        if platform.system() == "Windows":
            loop_script = feature_dir / "loop.ps1"
            if not loop_script.exists():
                script_content = LOOP_PS1_TEMPLATE.format(
                    mode=mode,
                    max_iterations=max_iterations,
                    model=model,
                    feature_name=feature_name,
                    feature_dir=str(feature_dir),
                    project_root=str(Path(project_path).resolve()),
                )
                loop_script.write_text(script_content, encoding="utf-8")
                created_files.append(loop_script)
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(loop_script)]
        else:
            loop_script = feature_dir / "loop.sh"
            if not loop_script.exists():
                script_content = LOOP_SH_TEMPLATE.format(
                    mode=mode,
                    max_iterations=max_iterations,
                    model=model,
                    feature_name=feature_name,
                    feature_dir=feature_dir_str,
                    project_root=project_root_str,
                )
                loop_script.write_text(script_content, encoding="utf-8")
                os.chmod(str(loop_script), 0o755)
                created_files.append(loop_script)
            cmd = ["bash", str(loop_script)]

        self._created_files[project_id] = created_files

        # Create LoopInstance
        instance = LoopInstance(
            project_id=project_id,
            feature_name=feature_name,
            mode=mode,
            model=model,
            status="starting",
            max_iterations=max_iterations,
            start_time=datetime.now().isoformat(),
        )
        self._loops[project_id] = instance

        # --- Step 3: Run the script from the project root ---
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(Path(project_path).resolve()),  # Run from project root
            text=True,
            bufsize=1,
        )

        instance.pid = proc.pid
        instance.status = "running"
        self._processes[project_id] = proc

        # Start async output reader
        self._tasks[project_id] = asyncio.create_task(
            self._read_output(project_id, proc)
        )

        await self._broadcast(project_id, {
            "event": "loop_started",
            "data": instance.to_dict()
        })

        return instance

    @staticmethod
    def _get_prompt_content(mode: str, feature_name: str, feature_dir: Path, project_path: str) -> Optional[str]:
        """Get prompt content from template - mirrors ralph.py's get_prompt_content() lines 160-175."""
        template_file = config.TEMPLATES_DIR / f"PROMPT_{mode}.md"
        if not template_file.exists():
            return None

        content = template_file.read_text(encoding="utf-8")

        # Same variable substitution as ralph.py lines 171-173
        content = content.replace("{{FEATURE_NAME}}", feature_name)
        content = content.replace("{{FEATURE_DIR}}", str(feature_dir).replace("\\", "/"))
        content = content.replace("{{PROJECT_NAME}}", Path(project_path).name)

        return content

    def _cleanup_files(self, project_id: str):
        """Clean up generated files - mirrors ralph.py's finally block lines 233-244."""
        created = self._created_files.pop(project_id, [])
        for f in created:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass

    async def _read_output(self, project_id: str, proc: subprocess.Popen):
        """Read subprocess stdout line-by-line, parse events, update state."""
        instance = self._loops[project_id]
        parser = OutputParser()

        try:
            loop = asyncio.get_event_loop()
            while True:
                line = await loop.run_in_executor(None, proc.stdout.readline)
                if not line:
                    break

                line = line.rstrip("\n\r")
                instance.output_lines.append(line)

                events = parser.parse_line(line)
                for event in events:
                    if event.event_type == "iteration_start":
                        instance.iteration = event.data["iteration"]
                    elif event.event_type == "ralph_control":
                        instance.last_ralph_control = event.data
                    elif event.event_type == "loop_finished":
                        instance.status = "completed"
                    elif event.event_type == "all_phases_complete":
                        instance.status = "completed"

                await self._broadcast(project_id, {
                    "event": "output",
                    "data": {"line": line, "parsed": [{"type": e.event_type, **e.data} for e in events]}
                })

            await loop.run_in_executor(None, proc.wait)

            if instance.status == "running":
                instance.status = "completed" if proc.returncode == 0 else "failed"
                if proc.returncode != 0:
                    instance.error = f"Process exited with code {proc.returncode}"

        except asyncio.CancelledError:
            pass
        except Exception as e:
            instance.status = "failed"
            instance.error = str(e)
        finally:
            instance.end_time = datetime.now().isoformat()
            # Step 4: Clean up generated files (mirrors ralph.py's finally block)
            self._cleanup_files(project_id)
            await self._broadcast(project_id, {
                "event": "loop_ended",
                "data": instance.to_dict()
            })
            self._processes.pop(project_id, None)
            self._tasks.pop(project_id, None)

    async def stop_loop(self, project_id: str) -> Optional[LoopInstance]:
        """Stop a running loop by terminating the subprocess."""
        instance = self._loops.get(project_id)
        if not instance or instance.status not in ("running", "starting"):
            return instance

        proc = self._processes.get(project_id)
        if proc:
            try:
                if platform.system() == "Windows":
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
                # Give it 5 seconds to die
                try:
                    loop = asyncio.get_event_loop()
                    await asyncio.wait_for(
                        loop.run_in_executor(None, proc.wait),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    proc.kill()
            except ProcessLookupError:
                pass  # Already dead

        # Cancel the reader task
        task = self._tasks.get(project_id)
        if task and not task.done():
            task.cancel()

        instance.status = "stopped"
        instance.end_time = datetime.now().isoformat()

        await self._broadcast(project_id, {
            "event": "loop_stopped",
            "data": instance.to_dict()
        })

        return instance

    async def stop_all(self):
        """Stop all running loops (called on server shutdown)."""
        for project_id in list(self._loops.keys()):
            await self.stop_loop(project_id)

    # --- SSE Subscriber Management ---

    def subscribe(self, project_id: str) -> asyncio.Queue:
        """Register an SSE subscriber for a project's loop output."""
        if project_id not in self._subscribers:
            self._subscribers[project_id] = []
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[project_id].append(queue)
        return queue

    def unsubscribe(self, project_id: str, queue: asyncio.Queue):
        """Remove an SSE subscriber."""
        if project_id in self._subscribers:
            self._subscribers[project_id] = [
                q for q in self._subscribers[project_id] if q is not queue
            ]

    async def _broadcast(self, project_id: str, message: dict):
        """Send a message to all SSE subscribers for a project."""
        if project_id not in self._subscribers:
            return
        dead_queues = []
        for queue in self._subscribers[project_id]:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        for q in dead_queues:
            self._subscribers[project_id].remove(q)


# Singleton instance
loop_service = LoopService()
```

---

## Phase 3: Routes (API)

### 3.1 `server/routes/__init__.py`

Empty package marker.

### 3.2 `server/routes/projects.py`

```python
"""Project CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from server.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


class RegisterRequest(BaseModel):
    path: str


@router.get("")
async def list_projects():
    """List all registered projects."""
    projects = ProjectService.get_all()
    return [p.to_dict() for p in projects]


@router.post("")
async def register_project(req: RegisterRequest):
    """Register a new project by path."""
    try:
        project = ProjectService.register(req.path)
        return project.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get a single project."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.to_dict()


@router.delete("/{project_id}")
async def unregister_project(project_id: str):
    """Unregister a project."""
    if not ProjectService.unregister(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.get("/{project_id}/features")
async def list_features(project_id: str):
    """Scan and return features for a project."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    features = ProjectService.scan_features(project.path)
    return {"features": features}
```

### 3.3 `server/routes/loops.py`

```python
"""Loop control API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from server.services.loop_service import loop_service
from server.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/loop", tags=["loops"])


class StartLoopRequest(BaseModel):
    feature_name: str
    mode: str                              # "plan" or "build"
    model: str = "sonnet"                  # "opus", "sonnet", "haiku"
    max_iterations: int = 0                # 0 = unlimited


@router.post("/start")
async def start_loop(project_id: str, req: StartLoopRequest):
    """Start a ralph loop for a project."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if req.mode not in ("plan", "build"):
        raise HTTPException(status_code=400, detail="Mode must be 'plan' or 'build'")
    if req.model not in ("opus", "sonnet", "haiku"):
        raise HTTPException(status_code=400, detail="Model must be 'opus', 'sonnet', or 'haiku'")

    try:
        instance = await loop_service.start_loop(
            project_id=project_id,
            project_path=project.path,
            feature_name=req.feature_name,
            mode=req.mode,
            model=req.model,
            max_iterations=req.max_iterations,
        )
        return instance.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop_loop(project_id: str):
    """Stop a running loop."""
    instance = await loop_service.stop_loop(project_id)
    if not instance:
        raise HTTPException(status_code=404, detail="No loop found for this project")
    return instance.to_dict()


@router.get("/state")
async def get_loop_state(project_id: str):
    """Get current loop state."""
    instance = loop_service.get_state(project_id)
    if not instance:
        return {"status": "idle"}
    return instance.to_dict()


@router.get("/output")
async def get_loop_output(project_id: str, last: int = 100):
    """Get recent output lines."""
    instance = loop_service.get_state(project_id)
    if not instance:
        return {"lines": []}
    lines = list(instance.output_lines)
    return {"lines": lines[-last:]}
```

### 3.4 `server/routes/stream.py`

```python
"""SSE streaming endpoint for live loop output."""
import asyncio
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from server.services.loop_service import loop_service

router = APIRouter(tags=["stream"])


@router.get("/api/projects/{project_id}/loop/stream")
async def stream_loop_output(project_id: str, request: Request):
    """Stream loop output and parsed events via SSE."""
    queue = loop_service.subscribe(project_id)

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": message.get("event", "message"),
                        "data": json.dumps(message.get("data", {})),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "ping", "data": ""}
        finally:
            loop_service.unsubscribe(project_id, queue)

    return EventSourceResponse(event_generator())
```

### 3.5 `server/routes/plans.py`

```python
"""View implementation plans and progress."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from server import config
from server.services.project_service import ProjectService
from server.services.progress_service import ProgressService

router = APIRouter(tags=["plans"])
templates = Jinja2Templates(directory=str(config.VIEWS_DIR))


@router.get("/api/projects/{project_id}/features/{feature_name}/plan")
async def get_plan(project_id: str, feature_name: str):
    """Get implementation plan as JSON."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    plan = ProgressService.read_implementation_plan(project.path, feature_name)
    progress = ProgressService.read_progress(project.path, feature_name)
    agents = ProgressService.read_agents_md(project.path, feature_name)

    return {
        "feature_name": feature_name,
        "implementation_plan": plan,
        "progress": progress,
        "agents": agents,
    }


@router.get("/project/{project_id}/plan/{feature_name}")
async def plan_preview_page(request: Request, project_id: str, feature_name: str):
    """Render implementation plan as HTML page."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    plan = ProgressService.read_implementation_plan(project.path, feature_name)
    progress = ProgressService.read_progress(project.path, feature_name)

    return templates.TemplateResponse("plan_preview.html", {
        "request": request,
        "project": project.to_dict(),
        "feature_name": feature_name,
        "plan_content": plan or "No implementation plan found.",
        "progress": progress,
    })
```

---

## Phase 4: Server Entry Point

### 4.1 `server/app.py`

```python
"""FastAPI web server entry point - Ralph Loop Dashboard."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server import config
from server.services.project_service import ProjectService
from server.services.loop_service import loop_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup: write PID file, ensure data directory
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.PID_FILE.write_text(str(os.getpid()))
    yield
    # Shutdown: stop all loops, remove PID file
    await loop_service.stop_all()
    config.PID_FILE.unlink(missing_ok=True)


app = FastAPI(title="Ralph Loop Dashboard", version="1.0.0", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(config.VIEWS_DIR))

# Include routers
from server.routes import projects, loops, stream, plans
app.include_router(projects.router)
app.include_router(loops.router)
app.include_router(stream.router)
app.include_router(plans.router)


@app.get("/")
async def dashboard(request: Request):
    """Main dashboard showing all registered projects."""
    all_projects = ProjectService.get_all()
    states = loop_service.get_all_states()

    # Enrich projects with loop state
    project_data = []
    for p in all_projects:
        state = states.get(p.id)
        project_data.append({
            **p.to_dict(),
            "loop_status": state.status if state else "idle",
            "loop_iteration": state.iteration if state else 0,
            "loop_feature": state.feature_name if state else None,
            "loop_mode": state.mode if state else None,
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "projects": project_data,
    })


@app.get("/project/{project_id}")
async def project_detail(request: Request, project_id: str):
    """Single project detail page with loop controls."""
    project = ProjectService.get_by_id(project_id)
    if not project:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "projects": [],
            "error": "Project not found",
        })

    features = ProjectService.scan_features(project.path)
    state = loop_service.get_state(project_id)

    return templates.TemplateResponse("project.html", {
        "request": request,
        "project": project.to_dict(),
        "features": features,
        "loop_state": state.to_dict() if state else {"status": "idle"},
    })
```

---

## Phase 5: Dashboard UI Templates

### 5.1 `server/views/_base.html`

Shared layout with:
- TailwindCSS CDN for styling
- HTMX CDN for dynamic interactions
- Navigation header with "Ralph Loop Dashboard" title and server status
- Content block for page-specific content
- Dark theme (matching terminal aesthetic)

### 5.2 `server/views/dashboard.html`

- Grid of project cards, each showing: name, path, loop status badge (colored: green=running, gray=idle, red=failed, blue=completed)
- For running loops: shows iteration count, feature name, mode
- Quick-action buttons per project: "View Details", "Stop" (if running)
- "Register Project" form at bottom with path input
- Auto-refresh running loop statuses via HTMX polling (`hx-get` every 2s on status badges)

### 5.3 `server/views/project.html`

- Project name, path, and metadata at top
- Features list (scanned from .claude/features/) displayed as selectable cards
- Loop control panel:
  - Feature dropdown (populated from scanned features)
  - Mode selector: Plan / Build (radio buttons)
  - Model selector: Sonnet / Opus / Haiku (radio buttons)
  - Max iterations input (number, 0 = unlimited)
  - Start Loop button (posts to `/api/projects/{id}/loop/start`)
  - Stop Loop button (shown when running)
- Live output terminal panel:
  - Connected via SSE to `/api/projects/{id}/loop/stream`
  - Auto-scrolling dark terminal (pre block with monospace font)
  - Parsed status sidebar showing: current iteration, status, files changed, elapsed time
- Progress panel (reads from progress.txt via API)
- Implementation plan link (opens plan_preview page)

### 5.4 `server/views/loop_status.html`

- Full-page terminal view for watching a loop
- Large auto-scrolling output area
- Compact sidebar: iteration, status, RALPH_CONTROL values, progress.txt summary
- Stop button
- Uses SSE events with different handlers per event type

### 5.5 `server/views/plan_preview.html`

- Renders IMPLEMENTATION_PLAN.md content
- Shows progress.txt status
- Simple markdown-rendered view (pre-formatted or basic HTML conversion)

### 5.6 `server/views/static/style.css`

Minimal custom CSS:
- Terminal styling (dark background, green/white text, monospace)
- Status badge colors
- Card layouts
- Responsive grid

### 5.7 `server/views/static/app.js`

Client-side JavaScript:
- SSE connection management (connect, reconnect, disconnect)
- Terminal auto-scroll
- Event handlers for iteration_start, ralph_control, loop_ended, output events
- Form submission helpers
- Status badge update on poll

```javascript
// Core SSE handler pattern
function connectSSE(projectId) {
    const evtSource = new EventSource(`/api/projects/${projectId}/loop/stream`);

    evtSource.addEventListener("output", function(event) {
        const data = JSON.parse(event.data);
        appendToTerminal(data.line);

        // Handle parsed events
        for (const parsed of (data.parsed || [])) {
            if (parsed.type === "iteration_start") {
                updateIterationDisplay(parsed.iteration);
            }
            if (parsed.type === "ralph_control") {
                updateStatusDisplay(parsed);
            }
        }
    });

    evtSource.addEventListener("loop_ended", function(event) {
        updateLoopStatus("completed");
        evtSource.close();
    });

    return evtSource;
}
```

---

## Phase 6: Cross-Platform Scripts

**NOTE**: There is no standalone `scripts/loop.sh` or `scripts/loop.ps1`. Loop scripts are generated at runtime in the feature directory and cleaned up after execution - exactly matching ralph.py's pattern. The loop script templates (`LOOP_PS1_TEMPLATE` and `LOOP_SH_TEMPLATE`) live inside `server/services/loop_service.py`.

### 6.1 `scripts/start-server.ps1` (Windows)

```powershell
# Start Ralph Loop Dashboard server (Windows)
$PluginDir = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $PluginDir "server\server.pid"
$Port = 3456

# Check if already running via PID file
if (Test-Path $PidFile) {
    $pid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($pid) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Server already running (PID: $pid) at http://127.0.0.1:$Port"
            exit 0
        }
    }
    Remove-Item $PidFile -Force
}

# Check if port is in use
$portCheck = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "Port $Port already in use"
    exit 0
}

# Start server in background
$proc = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", "$Port" `
    -WorkingDirectory $PluginDir `
    -PassThru -WindowStyle Hidden

Write-Host "Server started (PID: $($proc.Id)) at http://127.0.0.1:$Port"
```

### 6.3 `scripts/start-server.sh` (Mac/Linux)

```bash
#!/bin/bash
# Start Ralph Loop Dashboard server (Mac/Linux)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PLUGIN_DIR/server/server.pid"
PORT=3456

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Server already running (PID: $PID) at http://127.0.0.1:$PORT"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# Check port
if lsof -i :"$PORT" >/dev/null 2>&1; then
    echo "Port $PORT already in use"
    exit 0
fi

# Start server in background
cd "$PLUGIN_DIR"
nohup python -m uvicorn server.app:app --host 127.0.0.1 --port "$PORT" > /dev/null 2>&1 &
echo "Server started (PID: $!) at http://127.0.0.1:$PORT"
```

### 6.4 `scripts/stop-server.ps1` (Windows)

```powershell
# Stop Ralph Loop Dashboard server (Windows)
$PluginDir = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $PluginDir "server\server.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "Server not running (no PID file)"
    exit 0
}

$pid = Get-Content $PidFile
$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
if ($proc) {
    Stop-Process -Id $pid -Force
    Write-Host "Server stopped (PID: $pid)"
} else {
    Write-Host "Server process not found (stale PID file)"
}
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
```

### 6.5 `scripts/stop-server.sh` (Mac/Linux)

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PLUGIN_DIR/server/server.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Server not running (no PID file)"
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Server stopped (PID: $PID)"
else
    echo "Server process not found (stale PID file)"
fi
rm -f "$PID_FILE"
```

### 6.6 `scripts/start_server_check.py` (Cross-platform launcher for hooks)

```python
"""Cross-platform server launcher for use in hooks.json."""
import os
import sys
import platform
import subprocess
from pathlib import Path

plugin_root = Path(__file__).resolve().parent.parent
scripts_dir = plugin_root / "scripts"

if platform.system() == "Windows":
    script = scripts_dir / "start-server.ps1"
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)], cwd=str(plugin_root))
else:
    script = scripts_dir / "start-server.sh"
    subprocess.run(["bash", str(script)], cwd=str(plugin_root))
```

---

## Phase 7: Hook Configuration

### 7.1 `hooks/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "python \"${CLAUDE_PLUGIN_ROOT}/scripts/start_server_check.py\"",
        "timeout": 5000
      }
    ]
  }
}
```

### 7.2 `server/data/projects.json`

```json
[]
```

---

## How Loop Execution Works (mirrors ralph.py exactly)

```
Browser form collects same 4 inputs as ralph.py's menu:
  Feature, Mode (plan/build), Model (opus/sonnet/haiku), Max Iterations
  |
  v
POST /api/projects/{id}/loop/start
  {feature: "pose_detection", mode: "build", model: "opus", max_iterations: 5}
  |
  v
loop_service.start_loop() -- mirrors ralph.py's run_loop() lines 178-244:

  Step 1 (ralph.py lines 191-200): Create PROMPT_build.md in feature_dir
    - If feature_dir/PROMPT_build.md exists, use it (same as ralph.py line 199)
    - If not, read portable/templates/PROMPT_build.md and substitute variables:
      {{FEATURE_NAME}}, {{FEATURE_DIR}}, {{PROJECT_NAME}} (ralph.py lines 171-173)
    - Write to feature_dir/PROMPT_build.md
    - Track for cleanup

  Step 2 (ralph.py lines 203-214): Generate loop script in feature_dir
    - Windows: Create loop.ps1 using LOOP_PS1_TEMPLATE (same as ralph.py's LOOP_SCRIPT_TEMPLATE)
    - Mac: Create loop.sh using LOOP_SH_TEMPLATE (bash equivalent)
    - Config is baked into the script (mode, model, iterations, feature_name)
    - Track for cleanup

  Step 3: Run the script from the project root
    - Windows: powershell -ExecutionPolicy Bypass -File feature_dir/loop.ps1
    - Mac:     bash feature_dir/loop.sh
    - cwd = project_path (project root)
    - Absolute paths to feature_dir are baked into the script
    - Claude starts in project root so it can edit project files directly

  Step 4 (ralph.py lines 233-244): Clean up
    - Delete prompt file and loop script that were created (not pre-existing ones)

  ADDITIONALLY (web-only): Capture stdout asynchronously
    - Parse iteration markers, RALPH_CONTROL blocks, completion signals
    - Broadcast to SSE subscribers for live dashboard updates
  |
  v
Browser receives SSE events, updates terminal + status panel in real-time
```

---

## Implementation Order

| Step | Phase | Files | Description |
|------|-------|-------|-------------|
| 1 | Core | `server/__init__.py`, `server/config.py` | Package + configuration constants |
| 2 | Models | `server/models/__init__.py`, `server/models/project.py`, `server/models/loop_state.py` | Data models |
| 3 | Services | `server/services/__init__.py`, `server/services/project_service.py` | Project CRUD on JSON |
| 4 | Services | `server/services/output_parser.py` | Script output regex parser |
| 5 | Services | `server/services/progress_service.py` | progress.txt reader |
| 6 | Services | `server/services/loop_service.py` | Core: mirrors ralph.py's run_loop() with PS1/SH templates |
| 7 | Routes | `server/routes/__init__.py`, `server/routes/projects.py` | Project API |
| 8 | Routes | `server/routes/loops.py` | Loop control API |
| 9 | Routes | `server/routes/stream.py` | SSE streaming |
| 10 | Routes | `server/routes/plans.py` | Plan viewing |
| 11 | App | `server/app.py` | FastAPI assembly |
| 12 | UI | `server/views/_base.html`, `server/views/static/style.css` | Base layout + styles |
| 13 | UI | `server/views/static/app.js` | Client-side SSE + UI |
| 14 | UI | `server/views/dashboard.html` | Main dashboard |
| 15 | UI | `server/views/project.html` | Project detail + loop controls |
| 16 | UI | `server/views/loop_status.html` | Live loop view |
| 17 | UI | `server/views/plan_preview.html` | Plan preview |
| 18 | Scripts | `scripts/start-server.ps1`, `scripts/start-server.sh` | Server start |
| 19 | Scripts | `scripts/stop-server.ps1`, `scripts/stop-server.sh` | Server stop |
| 20 | Scripts | `scripts/start_server_check.py` | Cross-platform launcher |
| 21 | Hook | `hooks/hooks.json` | Auto-start hook |
| 22 | Data | `server/data/projects.json` | Empty registry |

---

## Dependencies

```
fastapi
uvicorn
jinja2
sse-starlette
```

No SQLAlchemy, no Docker SDK, no pydantic-settings. Minimal footprint.

---

## Verification Plan

1. Install deps: `pip install fastapi uvicorn jinja2 sse-starlette`
2. Start server: `cd plugin_1 && python -m uvicorn server.app:app --host 127.0.0.1 --port 3456`
3. Open `http://localhost:3456` - dashboard loads with empty project list
4. Register a test project via the UI form
5. Verify features scan shows features from `.claude/features/`
6. Start a loop from the project detail page
7. Verify output streams to the terminal in real-time
8. Verify iteration count updates in sidebar
9. Stop loop from dashboard, verify process terminates
10. Test start/stop scripts: `scripts/start-server.ps1` / `scripts/start-server.sh`
11. Test on both Windows (PowerShell loop) and Mac (bash loop)
