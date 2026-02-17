"""Service lifecycle manager for Companion and OpenCode backend services.

Auto-starts/stops/restarts managed services alongside Vista.
State machine: Stopped -> Starting -> Running -> Stopping -> Stopped
               Running -> Error -> Restarting -> Starting
               Error -> Stopped (max retries exceeded)
"""

import asyncio
import logging
import os
import platform
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

_IS_WINDOWS = platform.system() == "Windows"
log = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    RESTARTING = "restarting"


@dataclass
class ServiceConfig:
    name: str  # "companion" | "opencode"
    command: list[str]  # e.g. ["bun", "run", "web/server/index.ts"]
    cwd: str  # working directory
    preferred_port: int
    health_url_template: str  # e.g. "http://127.0.0.1:{port}/api/sessions"
    env: dict[str, str] = field(default_factory=dict)
    prerequisite_binary: str = ""  # binary name to check in PATH
    max_restarts: int = 5
    health_timeout: float = 2.0  # seconds per health check request
    startup_timeout: float = 30.0  # max seconds to wait for startup
    health_interval: float = 10.0  # seconds between periodic health checks
    consecutive_failures_threshold: int = 3


@dataclass
class ServiceInstance:
    config: ServiceConfig
    status: ServiceStatus = ServiceStatus.STOPPED
    port: int = 0
    pid: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    started_at: Optional[float] = None
    restart_count: int = 0
    consecutive_health_failures: int = 0
    last_error: str = ""


def _find_free_port(preferred: int, host: str = "127.0.0.1") -> int:
    """Find a free port starting from preferred."""
    port = preferred
    while port <= 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                return port
        except OSError:
            port += 1
    raise RuntimeError(f"No free ports found starting from {preferred}")


def _find_bun() -> Optional[str]:
    """Find the bun binary, checking PATH and common Windows install locations."""
    found = shutil.which("bun")
    if found:
        return found
    if _IS_WINDOWS:
        candidates = [
            Path(os.environ.get("USERPROFILE", "")) / ".bun" / "bin" / "bun.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "bun" / "bun.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
    return None


class ServiceLifecycleManager:
    """Manages Companion and OpenCode processes alongside Vista."""

    def __init__(self):
        self._services: dict[str, ServiceInstance] = {}
        self._health_task: Optional[asyncio.Task] = None

    def register(self, config: ServiceConfig) -> None:
        """Register a service configuration."""
        self._services[config.name] = ServiceInstance(config=config)

    async def start(self, name: str) -> bool:
        """Start a single service. Returns True if successfully started."""
        instance = self._services.get(name)
        if not instance:
            log.warning("Service %s not registered", name)
            return False

        if instance.status in (ServiceStatus.RUNNING, ServiceStatus.STARTING):
            return True

        cfg = instance.config

        # Check prerequisite binary
        if cfg.prerequisite_binary:
            binary_path = shutil.which(cfg.prerequisite_binary)
            if not binary_path and cfg.prerequisite_binary == "bun":
                binary_path = _find_bun()
            if not binary_path:
                log.info(
                    "Skipping %s: prerequisite '%s' not found",
                    name, cfg.prerequisite_binary,
                )
                instance.status = ServiceStatus.STOPPED
                instance.last_error = f"Prerequisite '{cfg.prerequisite_binary}' not found"
                return False

        instance.status = ServiceStatus.STARTING

        try:
            port = _find_free_port(cfg.preferred_port)
            instance.port = port

            # Build command with port substitution
            cmd = [c.replace("{port}", str(port)) for c in cfg.command]

            # Resolve the executable to its full path so Windows can find
            # .cmd/.bat wrappers that Popen won't locate by bare name.
            if cfg.prerequisite_binary:
                resolved = shutil.which(cmd[0])
                if resolved:
                    cmd[0] = resolved
            if _IS_WINDOWS and cmd[0].endswith((".cmd", ".bat")):
                cmd = ["cmd.exe", "/c"] + cmd

            # Build environment
            env = dict(os.environ)
            for k, v in cfg.env.items():
                env[k] = v.replace("{port}", str(port))

            # Check CWD exists
            if not Path(cfg.cwd).is_dir():
                instance.status = ServiceStatus.ERROR
                instance.last_error = f"Working directory not found: {cfg.cwd}"
                log.error("Service %s: %s", name, instance.last_error)
                return False

            # Spawn process
            kwargs: dict = {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "cwd": cfg.cwd,
                "env": env,
            }
            if _IS_WINDOWS:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(cmd, **kwargs)
            instance.process = proc
            instance.pid = proc.pid
            instance.started_at = time.time()

            log.info("Starting %s (pid=%d, port=%d)", name, proc.pid, port)

            # Wait for health check to pass
            health_url = cfg.health_url_template.replace("{port}", str(port))
            started = await self._wait_for_health(
                name, health_url, cfg.startup_timeout, cfg.health_timeout
            )

            if started:
                instance.status = ServiceStatus.RUNNING
                instance.consecutive_health_failures = 0
                log.info("Service %s is running (pid=%d, port=%d)", name, proc.pid, port)
                self._ensure_health_task()
                return True
            else:
                # Process may have died during startup
                if proc.poll() is not None:
                    instance.last_error = f"Process exited during startup (code {proc.returncode})"
                else:
                    instance.last_error = "Health check did not pass within timeout"
                instance.status = ServiceStatus.ERROR
                log.error("Service %s failed to start: %s", name, instance.last_error)
                self._kill_process(instance)
                return False

        except Exception as e:
            instance.status = ServiceStatus.ERROR
            instance.last_error = str(e)
            log.error("Failed to start %s: %s", name, e)
            return False

    async def stop(self, name: str) -> None:
        """Gracefully stop a service (terminate, wait 5s, force kill)."""
        instance = self._services.get(name)
        if not instance or instance.status == ServiceStatus.STOPPED:
            return

        instance.status = ServiceStatus.STOPPING
        log.info("Stopping service %s", name)
        self._kill_process(instance)
        instance.status = ServiceStatus.STOPPED
        instance.pid = None
        instance.process = None
        log.info("Service %s stopped", name)

    async def restart(self, name: str) -> bool:
        """Stop then start with backoff."""
        instance = self._services.get(name)
        if not instance:
            return False

        if instance.restart_count >= instance.config.max_restarts:
            log.error(
                "Service %s exceeded max restarts (%d), giving up",
                name, instance.config.max_restarts,
            )
            instance.status = ServiceStatus.STOPPED
            instance.last_error = "Max restarts exceeded"
            return False

        instance.status = ServiceStatus.RESTARTING
        instance.restart_count += 1

        # Exponential backoff: 1s, 2s, 4s, 8s, 16s cap
        backoff = min(2 ** (instance.restart_count - 1), 16)
        log.info(
            "Restarting %s (attempt %d/%d, backoff %ds)",
            name, instance.restart_count, instance.config.max_restarts, backoff,
        )
        await asyncio.sleep(backoff)

        await self.stop(name)
        return await self.start(name)

    async def start_all(self) -> None:
        """Start all registered services (skip if prerequisite missing)."""
        for name in list(self._services.keys()):
            await self.start(name)

    async def stop_all(self) -> None:
        """Stop all running services."""
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        for name in list(self._services.keys()):
            await self.stop(name)

    def get_status(self, name: str) -> dict:
        """Return status snapshot for a service."""
        instance = self._services.get(name)
        if not instance:
            return {"name": name, "status": "unknown"}
        return {
            "name": name,
            "status": instance.status.value,
            "port": instance.port,
            "pid": instance.pid,
            "started_at": instance.started_at,
            "restart_count": instance.restart_count,
            "last_error": instance.last_error,
        }

    def get_all_status(self) -> list[dict]:
        """Return status for all services."""
        return [self.get_status(name) for name in self._services]

    def is_available(self, name: str) -> bool:
        """True if service is running and healthy."""
        instance = self._services.get(name)
        return instance is not None and instance.status == ServiceStatus.RUNNING

    # --- Internal helpers ---

    def _kill_process(self, instance: ServiceInstance) -> None:
        """Kill a service process and its tree."""
        proc = instance.process
        if proc is None:
            return
        try:
            if proc.poll() is not None:
                return
            if _IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                    capture_output=True,
                    timeout=5,
                )
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
        except Exception as e:
            log.warning("Error killing process %s: %s", instance.config.name, e)

    async def _wait_for_health(
        self, name: str, health_url: str, timeout: float, request_timeout: float
    ) -> bool:
        """Poll health endpoint until it responds 2xx or timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(health_url, timeout=request_timeout)
                    if resp.status_code < 400:
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False

    def _ensure_health_task(self) -> None:
        """Start the periodic health check task if not running."""
        if self._health_task is None or self._health_task.done():
            self._health_task = asyncio.create_task(self._periodic_health_check())

    async def _periodic_health_check(self) -> None:
        """Periodically check health of all running services."""
        try:
            while True:
                running = [
                    name for name, inst in self._services.items()
                    if inst.status == ServiceStatus.RUNNING
                ]
                if not running:
                    break

                for name in running:
                    instance = self._services.get(name)
                    if not instance or instance.status != ServiceStatus.RUNNING:
                        continue

                    # Check if process is still alive
                    if instance.process and instance.process.poll() is not None:
                        log.warning("Service %s process died (code %s)", name, instance.process.returncode)
                        instance.status = ServiceStatus.ERROR
                        instance.last_error = f"Process exited with code {instance.process.returncode}"
                        asyncio.create_task(self.restart(name))
                        continue

                    # HTTP health check
                    health_url = instance.config.health_url_template.replace(
                        "{port}", str(instance.port)
                    )
                    healthy = False
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(
                                health_url, timeout=instance.config.health_timeout
                            )
                            healthy = resp.status_code < 400
                    except Exception:
                        pass

                    if healthy:
                        instance.consecutive_health_failures = 0
                    else:
                        instance.consecutive_health_failures += 1
                        if instance.consecutive_health_failures >= instance.config.consecutive_failures_threshold:
                            log.warning(
                                "Service %s failed %d consecutive health checks, restarting",
                                name, instance.consecutive_health_failures,
                            )
                            instance.status = ServiceStatus.ERROR
                            asyncio.create_task(self.restart(name))

                # Use the minimum health interval across running services
                interval = min(
                    (self._services[n].config.health_interval for n in running
                     if n in self._services),
                    default=10.0,
                )
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass


# Singleton instance
service_lifecycle = ServiceLifecycleManager()


# --- Default service configurations ---

def companion_config() -> ServiceConfig:
    """Build ServiceConfig for the Companion WebSocket bridge."""
    from server import config as cfg

    companion_dir = cfg.PLUGIN_ROOT / "companion"
    bun_path = _find_bun() or "bun"

    return ServiceConfig(
        name="companion",
        command=[bun_path, "run", str(companion_dir / "web" / "server" / "index.ts")],
        cwd=str(companion_dir),
        preferred_port=3457,
        health_url_template="http://127.0.0.1:{port}/api/sessions",
        env={"PORT": "{port}", "NODE_ENV": "production"},
        prerequisite_binary="bun",
    )


def opencode_config() -> ServiceConfig:
    """Build ServiceConfig for OpenCode serve."""
    return ServiceConfig(
        name="opencode",
        command=["opencode", "serve", "--port", "{port}", "--mdns", "--mdns-domain", "vista.local"],
        cwd=str(Path.cwd()),
        preferred_port=4096,
        health_url_template="http://127.0.0.1:{port}/global/health",
        prerequisite_binary="opencode",
    )
