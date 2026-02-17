"""Job lifecycle management for ralph MCP tools."""

from __future__ import annotations

import json
import logging
import os
import platform
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from portable.ralph import LOOP_SCRIPT_TEMPLATE
from server import config
from server.services.output_parser import (
    parse_plaintext_activity,
    parse_stream_json_activity,
)
from server.services.provider_service import Provider

# Lazy imports for sandbox — only imported when sandbox=True (DS-NF6)
# These are imported at function scope to avoid Docker SDK dependency for native jobs.
# For testing, they are patched at the module level:
#   server.services.ralph_service.ContainerManager
#   server.services.ralph_service.CredentialMounter
#   server.services.ralph_service.BashLoopGenerator
from server.services.sandbox.container_manager import ContainerManager
from server.services.sandbox.credential_mounter import CredentialMounter
from server.services.sandbox.bash_loop_generator import BashLoopGenerator

logger = logging.getLogger(__name__)


class RalphService:
    """Manage ralph loop jobs persisted to disk."""

    def __init__(self) -> None:
        self._ralph_dir_name = "ralph"

    def create_job(
        self,
        project_root: Path,
        slug: str,
        mode: str,
        task_description: str,
        provider: Provider,
        model: str,
        iterations: int,
        sandbox: bool = False,
    ) -> dict:
        if sandbox:
            return self._create_sandboxed_job(
                project_root,
                slug,
                mode,
                task_description,
                provider,
                model,
                iterations,
            )
        return self._create_native_job(
            project_root,
            slug,
            mode,
            task_description,
            provider,
            model,
            iterations,
        )

    def _create_native_job(
        self,
        project_root: Path,
        slug: str,
        mode: str,
        task_description: str,
        provider: Provider,
        model: str,
        iterations: int,
    ) -> dict:
        """Existing native subprocess execution path (DS-F28: unchanged)."""
        job_id = str(uuid4())
        job_dir = self._job_dir(project_root, slug, job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        self._clear_runtime_artifacts(job_dir)

        # For plan mode, if a feature directory exists, use it as the working
        # directory so plans, progress, and task live in the feature — not in
        # the ephemeral ralph job dir.  Multiple plan loops then overwrite the
        # same IMPLEMENTATION_PLAN.md instead of creating separate copies.
        plan_dir = self._resolve_plan_dir(mode, slug, job_dir, project_root)
        feature_dir = plan_dir if (mode == "plan" and plan_dir != job_dir) else job_dir

        task_file = feature_dir / "task.md"
        task_file.write_text(task_description, encoding="utf-8")

        prompt_content = self._get_prompt_content(
            mode=mode,
            slug=slug,
            job_dir=job_dir,
            project_root=project_root,
        )
        if prompt_content is None:
            raise ValueError(f"No prompt template found for mode: {mode}")

        prompt_file = feature_dir / f"PROMPT_{mode}.md"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        loop_script = job_dir / (
            "loop.ps1" if platform.system() == "Windows" else "loop.sh"
        )
        script_content = LOOP_SCRIPT_TEMPLATE.format(
            mode=mode,
            max_iterations=iterations,
            model=model,
            feature_name=slug,
            feature_dir_abs=str(feature_dir.resolve()),
            project_root_abs=str(project_root.resolve()),
            provider_name=provider.display_name,
            invocation_block=provider.get_invocation(
                "ps1" if platform.system() == "Windows" else "sh"
            ),
        )
        loop_script.write_text(script_content, encoding="utf-8")
        if platform.system() != "Windows":
            os.chmod(loop_script, 0o755)

        output_log = job_dir / "output.log"
        output_handle = output_log.open("w", encoding="utf-8")

        cmd = (
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(loop_script)]
            if platform.system() == "Windows"
            else ["bash", str(loop_script)]
        )
        popen_kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": output_handle,
            "stderr": subprocess.STDOUT,
            "cwd": str(project_root.resolve()),
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            )

        proc = subprocess.Popen(cmd, **popen_kwargs)  # type: ignore[arg-type]
        output_handle.close()

        now = self._now()
        job = {
            "job_id": job_id,
            "slug": slug,
            "mode": mode,
            "status": "running",
            "provider": provider.name,
            "model": model,
            "iterations": iterations,
            "current_iteration": 0,
            "pid": proc.pid,
            "sandbox": False,
            "container_id": None,
            "created_at": now,
            "started_at": now,
            "completed_at": None,
            "error": None,
        }
        self._save_job_json(job_dir, job)
        return job

    def _create_sandboxed_job(
        self,
        project_root: Path,
        slug: str,
        mode: str,
        task_description: str,
        provider: Provider,
        model: str,
        iterations: int,
    ) -> dict:
        """Docker sandbox execution path (DS-F20 through DS-F26)."""
        from server.services.sandbox.sandbox_errors import (
            DockerNotAvailableError,
            ImageBuildError,
        )
        from server.config import get_sandbox_settings

        # Step 1: Check Docker availability (DS-F21)
        mgr = ContainerManager(session_id="ralph-sandbox")
        available, msg = mgr.check_docker_available()
        if not available:
            raise DockerNotAvailableError(
                f"Docker is not available: {msg}. "
                "Install Docker Desktop or start the daemon."
            )

        # Step 2: Ensure image exists (DS-F22)
        sandbox_settings = get_sandbox_settings()
        image_name = sandbox_settings.get("image", "vista-ralph:latest")
        image_ok = mgr.ensure_image(image_name)
        if not image_ok:
            raise ImageBuildError(
                f"Failed to build or find Docker image: {image_name}. "
                "Try POST /api/ralph/sandbox/build to rebuild."
            )

        # Step 3: Create job directory and files (same as native)
        job_id = str(uuid4())
        job_dir = self._job_dir(project_root, slug, job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        self._clear_runtime_artifacts(job_dir)

        task_file = job_dir / "task.md"
        task_file.write_text(task_description, encoding="utf-8")

        prompt_content = self._get_prompt_content(
            mode=mode,
            slug=slug,
            job_dir=job_dir,
            project_root=project_root,
        )
        if prompt_content is None:
            raise ValueError(f"No prompt template found for mode: {mode}")

        prompt_file = job_dir / f"PROMPT_{mode}.md"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        # Step 4: Generate bash loop script (DS-F23 — always bash, even on Windows)
        # Compute relative paths for inside the container (project_root = /workspace)
        job_dir_rel = str(job_dir.relative_to(project_root)).replace("\\", "/")
        feature_dir = str(
            self._resolve_plan_dir(mode, slug, job_dir, project_root).relative_to(
                project_root
            )
            if self._resolve_plan_dir(mode, slug, job_dir, project_root) != job_dir
            else job_dir.relative_to(project_root)
        ).replace("\\", "/")

        script_content = BashLoopGenerator.generate(
            mode=mode,
            max_iterations=iterations,
            model=model,
            feature_name=slug,
            feature_dir=feature_dir,
            project_root="/workspace",
            job_dir=job_dir_rel,
            provider=provider.name,
        )
        loop_script = job_dir / "loop.sh"
        loop_script.write_text(script_content, encoding="utf-8")

        # Step 5: Resolve credential mounts (DS-F24)
        cred_mounter = CredentialMounter(
            credential_config=sandbox_settings.get("credential_mounts", {}),
        )
        cred_mounts = cred_mounter.get_mounts()

        # Step 6: Build mount list — project RW + credentials RO (DS-F24, DS-F31)
        from server.models.sandbox import MountSpec

        mounts = [
            MountSpec(
                host_path=str(project_root.resolve()),
                container_path="/workspace",
                mode="rw",
            ),
        ]
        for cm in cred_mounts:
            mounts.append(
                MountSpec(
                    host_path=cm.host_path,
                    container_path=cm.container_path,
                    mode=cm.mode,
                )
            )

        # Step 7: Create and start container (DS-F25)
        container_info = mgr.create_container(
            job_id=job_id,
            provider=provider.name,
            image=image_name,
            mounts=mounts,  # type: ignore[arg-type]
            network_enabled=sandbox_settings.get("network_enabled", True),
            ttl_seconds=sandbox_settings.get("ttl_seconds", 7200),
        )
        mgr.start_container(container_info.container_id)

        # Execute the loop script inside the container
        mgr.exec_in_container(
            container_info.container_id,
            ["bash", f"/workspace/{job_dir_rel}/loop.sh"],
            workdir="/workspace",
        )

        # Step 8: Persist job.json (DS-F26)
        now = self._now()
        job = {
            "job_id": job_id,
            "slug": slug,
            "mode": mode,
            "status": "running",
            "provider": provider.name,
            "model": model,
            "iterations": iterations,
            "current_iteration": 0,
            "pid": None,
            "sandbox": True,
            "container_id": container_info.container_id,
            "created_at": now,
            "started_at": now,
            "completed_at": None,
            "error": None,
        }
        self._save_job_json(job_dir, job)
        return job

    def get_job_status(self, project_root: Path, job_id: str) -> Optional[dict]:
        job_dir = self._find_job_dir_by_id(project_root, job_id)
        if job_dir is None:
            return None
        job = self._load_job_json(job_dir)
        if job is None:
            return None

        pid = job.get("pid")
        if job.get("status") == "stopped":
            return job
        if job.get("status") == "running":
            if pid is not None and not isinstance(pid, int):
                return job

        # Always parse output.log for dashboard display (tool calls, assistant text).
        # progress.txt is only for inter-loop agent context, not display.
        progress_tail, iteration = self._read_activity(
            job_dir, provider=job.get("provider", "")
        )
        # Also check progress.txt for iteration tracking (may have markers output.log missed)
        _, progress_iteration = self._read_progress(job_dir)
        if progress_iteration is not None and (
            iteration is None or progress_iteration > iteration
        ):
            iteration = progress_iteration
        if iteration is not None:
            job["current_iteration"] = iteration
        job["progress_tail"] = progress_tail

        status_value = job.get("status")
        if status_value == "running":
            if isinstance(pid, int) and self._is_process_running(pid):
                if not self._is_expected_job_process(pid, job_dir):
                    job["status"] = "failed"
                    job["error"] = "Stale PID: process does not match job"
                    job["completed_at"] = self._now()
                    self._save_job_json(job_dir, job)
                    return job
            if isinstance(pid, int) and not self._is_process_running(pid):
                if self._completed_successfully(job, progress_tail, iteration, job_dir):
                    job["status"] = "completed"
                    job["error"] = None
                else:
                    normalized = "\n".join(progress_tail).lower()
                    has_markers = any(
                        m in normalized
                        for m in (
                            "loop finished after",
                            "all phases complete",
                            "reached max iterations",
                        )
                    )
                    job["status"] = "failed"
                    if has_markers:
                        job["error"] = "No model output detected"
                    else:
                        output_tail = self._read_output_tail(job_dir, last=20)
                        if output_tail:
                            job["error"] = (
                                "Process ended unexpectedly (PID not alive). "
                                "Last output:\n" + "\n".join(output_tail)
                            )
                        else:
                            job["error"] = "Process ended unexpectedly (PID not alive)"
                job["completed_at"] = self._now()
                self._save_job_json(job_dir, job)
            elif pid is None:
                job["status"] = "failed"
                job["error"] = "Process ended unexpectedly (PID not alive)"
                job["completed_at"] = self._now()
                self._save_job_json(job_dir, job)
        if status_value == "stopped":
            return job

        return job

    def _completed_successfully(
        self,
        job: dict,
        progress_tail: list[str],
        iteration: Optional[int],
        job_dir: Path,
    ) -> bool:
        """Infer normal completion from loop markers AND model activity evidence."""
        normalized = "\n".join(progress_tail).lower()
        completion_markers = (
            "loop finished after",
            "all phases complete",
            "reached max iterations",
        )
        if not any(marker in normalized for marker in completion_markers):
            return False
        return self._has_model_activity(job, job_dir)

    def _has_model_activity(self, job: dict, job_dir: Path) -> bool:
        """Check whether output.log contains evidence of actual model output."""
        output_file = job_dir / "output.log"
        if not output_file.exists():
            return False
        try:
            text = output_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False

        if job.get("provider") == "claude":
            # Stream-json: look for assistant message type
            return '"type":"assistant"' in text.replace(" ", "")

        # OpenCode/other: any non-boilerplate line counts as activity
        boilerplate = (
            "iteration",
            "started:",
            "loop finished",
            "reached max iterations",
            "all phases complete",
            "feature:",
            "provider:",
            "mode:",
            "model:",
            "branch:",
            "prompt:",
            "max:",
            "check:",
            "\u2501",
            "========================",
            "failed to push",
            "git push",
            "creating remote branch",
        )
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if any(marker in stripped.lower() for marker in boilerplate):
                continue
            return True  # Any non-boilerplate line = model activity
        return False

    def stop_job(self, project_root: Path, job_id: str) -> Optional[dict]:
        job_dir = self._find_job_dir_by_id(project_root, job_id)
        if job_dir is None:
            return None
        job = self._load_job_json(job_dir)
        if job is None:
            return None

        # DS-F27: Branch on sandbox flag for stop behavior
        if job.get("sandbox") and job.get("container_id"):
            return self._stop_sandboxed_job(job, job_dir)

        return self._stop_native_job(job, job_dir)

    def _stop_sandboxed_job(self, job: dict, job_dir: Path) -> dict:
        """Stop a sandboxed job by stopping its Docker container (DS-F27)."""
        container_id = job["container_id"]

        # Persist "stopped" before attempting container stop
        job["status"] = "stopped"
        job["completed_at"] = self._now()
        self._save_job_json(job_dir, job)

        try:
            mgr = ContainerManager(session_id="ralph-sandbox")
            mgr.stop_container(container_id, remove=True)
        except Exception:
            # Container may already be stopped/removed — idempotent
            logger.debug(
                "Container stop failed (may already be stopped): %s", container_id
            )

        return job

    def _stop_native_job(self, job: dict, job_dir: Path) -> dict:
        """Stop a native subprocess job (existing behavior)."""
        pid = job.get("pid")
        if isinstance(pid, int):
            is_running = self._is_process_running(pid)
            if is_running and not self._is_expected_job_process(pid, job_dir):
                job["status"] = "failed"
                job["completed_at"] = self._now()
                job["error"] = (
                    "Refused to stop process: PID belongs to a different process "
                    "(possible stale PID)."
                )
                self._save_job_json(job_dir, job)
                return job

            # Persist "stopped" BEFORE kill attempt — defensive against kill crashes
            job["status"] = "stopped"
            job["completed_at"] = self._now()
            self._save_job_json(job_dir, job)

            if is_running:
                try:
                    os.kill(pid, signal.SIGTERM)
                except (ProcessLookupError, OSError):
                    pass
                if platform.system() != "Windows" and self._is_process_running(pid):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
        else:
            job["status"] = "stopped"
            job["completed_at"] = self._now()
            self._save_job_json(job_dir, job)

        return job

    def list_jobs(self, project_root: Path) -> list[dict]:
        jobs: list[dict] = []
        ralph_dir = project_root / ".vista" / self._ralph_dir_name
        if not ralph_dir.exists():
            return jobs
        for slug_dir in ralph_dir.iterdir():
            if not slug_dir.is_dir():
                continue
            job = self._load_job_json(slug_dir)
            if job:
                jobs.append(job)
        jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return jobs

    def _job_dir(self, project_root: Path, slug: str, job_id: str) -> Path:
        safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in {"-", "_"})
        if not safe_slug:
            safe_slug = "job"
        base_dir = project_root / ".vista" / self._ralph_dir_name / safe_slug
        if not base_dir.exists():
            return base_dir
        return project_root / ".vista" / self._ralph_dir_name / f"{safe_slug}-{job_id}"

    def _find_job_dir_by_slug(self, project_root: Path, slug: str) -> Optional[Path]:
        safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in {"-", "_"})
        if not safe_slug:
            safe_slug = "job"
        job_dir = project_root / ".vista" / self._ralph_dir_name / safe_slug
        if job_dir.is_dir():
            return job_dir
        return None

    def _find_job_dir_by_id(self, project_root: Path, job_id: str) -> Optional[Path]:
        ralph_dir = project_root / ".vista" / self._ralph_dir_name
        if not ralph_dir.exists():
            return None
        for slug_dir in ralph_dir.iterdir():
            if not slug_dir.is_dir():
                continue
            job = self._load_job_json(slug_dir)
            if job and job.get("job_id") == job_id:
                return slug_dir
        return None

    def _load_job_json(self, job_dir: Path) -> Optional[dict]:
        job_file = job_dir / "job.json"
        if not job_file.exists():
            return None
        try:
            return json.loads(job_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _save_job_json(self, job_dir: Path, job: dict) -> None:
        job_file = job_dir / "job.json"
        job_file.write_text(json.dumps(job, indent=2), encoding="utf-8")

    def _resolve_plan_dir(
        self,
        mode: str,
        slug: str,
        job_dir: Path,
        project_root: Path,
    ) -> Path:
        """Determine where the implementation plan lives (or should be written).

        Resolution order:
        1. Feature directory (.vista/features/{slug}/) — if it exists, plans
           always live alongside the feature specs.
        2. For build mode only: search existing ralph job dirs for the most
           recent IMPLEMENTATION_PLAN.md matching this slug.
        3. Fallback: the current job directory.
        """
        feature_dir = project_root / ".vista" / "features" / slug
        if feature_dir.is_dir():
            return feature_dir

        if mode == "build":
            ralph_dir = project_root / ".vista" / self._ralph_dir_name
            if ralph_dir.is_dir():
                candidates: list[tuple[float, Path]] = []
                for d in ralph_dir.iterdir():
                    if not d.is_dir() or not d.name.startswith(slug):
                        continue
                    plan_file = d / "IMPLEMENTATION_PLAN.md"
                    if plan_file.exists():
                        candidates.append((plan_file.stat().st_mtime, d))
                if candidates:
                    # Most recently modified plan wins
                    candidates.sort(key=lambda c: c[0], reverse=True)
                    return candidates[0][1]

        return job_dir

    def _get_prompt_content(
        self,
        mode: str,
        slug: str,
        job_dir: Path,
        project_root: Path,
    ) -> Optional[str]:
        template_file = config.TEMPLATES_DIR / f"PROMPT_{mode}_adhoc.md"
        if not template_file.exists():
            return None
        content = template_file.read_text(encoding="utf-8")

        plan_dir = self._resolve_plan_dir(mode, slug, job_dir, project_root)

        # For plan mode with an existing feature directory, point FEATURE_DIR
        # at the feature dir so plans, progress, and task live there — not in
        # the ephemeral ralph job dir.  This ensures successive plan loops
        # overwrite the same IMPLEMENTATION_PLAN.md instead of creating new ones.
        feature_dir = plan_dir if (mode == "plan" and plan_dir != job_dir) else job_dir

        content = content.replace("{{FEATURE_NAME}}", slug)
        content = content.replace(
            "{{FEATURE_DIR}}", str(feature_dir).replace("\\", "/")
        )
        content = content.replace("{{PLAN_DIR}}", str(plan_dir).replace("\\", "/"))
        content = content.replace("{{PROJECT_NAME}}", project_root.name)
        return content

    def _read_progress(self, job_dir: Path) -> tuple[list[str], Optional[int]]:
        progress_file = job_dir / "progress.txt"
        if not progress_file.exists():
            return [], None
        lines = progress_file.read_text(encoding="utf-8").splitlines()
        tail = lines[-5:]
        iteration = None
        for line in reversed(lines):
            if "ITERATION" in line:
                parts = line.strip().split()
                for part in parts:
                    if part.isdigit():
                        iteration = int(part)
                        break
                if iteration is not None:
                    break
        return tail, iteration

    def _read_activity(
        self, job_dir: Path, provider: str = ""
    ) -> tuple[list[str], Optional[int]]:
        """Parse output.log for human-readable activity lines.

        Dispatches to stream-json parser for Claude, plaintext parser for others.
        """
        output_file = job_dir / "output.log"
        if not output_file.exists():
            return [], None
        try:
            text = output_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return [], None
        lines = text.splitlines()
        # Only parse last 500 lines for efficiency on large logs
        if provider == "claude":
            activity, iteration = parse_stream_json_activity(lines[-500:])
        else:
            activity, iteration = parse_plaintext_activity(lines[-500:])
        # Return last 50 activity entries as the tail
        return activity[-50:], iteration

    def _read_output_tail(self, job_dir: Path, last: int = 20) -> list[str]:
        output_file = job_dir / "output.log"
        if not output_file.exists():
            return []
        try:
            lines = output_file.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            return lines[-last:]
        except OSError:
            return []

    def _clear_runtime_artifacts(self, job_dir: Path) -> None:
        """Delete per-run generated runtime files from previous executions."""
        runtime_files = [
            job_dir / "progress.txt",
            job_dir / "output.log",
            job_dir / "loop.ps1",
            job_dir / "loop.sh",
        ]
        for file_path in runtime_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError:
                # Non-fatal: file will be overwritten where possible.
                pass

    def _is_process_running(self, pid: int) -> bool:
        if pid <= 0:
            return False
        if platform.system() == "Windows":
            try:
                import ctypes

                # PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SYNCHRONIZE
                handle = ctypes.windll.kernel32.OpenProcess(
                    0x1000 | 0x00100000, False, pid
                )
                if not handle:
                    return False

                # Get exit code - STILL_ACTIVE = 259
                exit_code = ctypes.c_ulong()
                result = ctypes.windll.kernel32.GetExitCodeProcess(
                    handle, ctypes.byref(exit_code)
                )
                ctypes.windll.kernel32.CloseHandle(handle)

                if not result:
                    return False

                # If exit code is STILL_ACTIVE (259), process is still running
                STILL_ACTIVE = 259
                return exit_code.value == STILL_ACTIVE
            except Exception:
                return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _is_expected_job_process(self, pid: int, job_dir: Path) -> bool:
        """Best-effort check that PID still belongs to this Ralph job loop process."""
        try:
            if platform.system() == "Windows":
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    (
                        f'$p = Get-CimInstance Win32_Process -Filter "ProcessId={pid}" '
                        "-ErrorAction SilentlyContinue; if ($p) { $p.ParentProcessId; $p.CommandLine }"
                    ),
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                output = [
                    line.strip()
                    for line in (proc.stdout or "").splitlines()
                    if line.strip()
                ]
                if not output:
                    return False
                command_line = ""
                parent_pid = None
                for line in output:
                    if line.isdigit() and parent_pid is None:
                        try:
                            parent_pid = int(line)
                        except ValueError:
                            parent_pid = None
                    elif command_line == "":
                        command_line = line.lower()
                if not command_line and parent_pid is not None:
                    return True
                loop_marker = (
                    str((job_dir / "loop.ps1").resolve()).lower().replace("/", "\\")
                )
                if (
                    command_line
                    and "loop.ps1" in command_line
                    and loop_marker in command_line
                ):
                    return True
                if parent_pid == os.getpid():
                    return True
                if command_line and "python" in command_line:
                    return True
                if command_line and "sleep" in command_line:
                    return True
                return False

            cmdline_path = Path("/proc") / str(pid) / "cmdline"
            if cmdline_path.exists():
                raw = (
                    cmdline_path.read_bytes()
                    .replace(b"\x00", b" ")
                    .decode("utf-8", errors="ignore")
                    .lower()
                )
                loop_marker = str((job_dir / "loop.sh").resolve()).lower()
                if "loop.sh" in raw and loop_marker in raw:
                    return True

            return False
        except (OSError, subprocess.SubprocessError, ValueError):
            return False

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


ralph_service = RalphService()
