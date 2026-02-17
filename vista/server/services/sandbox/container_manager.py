"""Docker container lifecycle management for sandboxed Ralph loops."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from server.models.sandbox import ContainerInfo, MountSpec
from server.services.sandbox.sandbox_errors import (
    ContainerCreateError,
    ContainerStartError,
    DockerDaemonNotRunningError,
    ImageBuildError,
)

logger = logging.getLogger(__name__)

DOCKERFILE_DIR = Path(__file__).resolve().parent.parent.parent / "docker"


class ContainerManager:
    """Manage Docker containers for sandboxed Ralph loops."""

    def __init__(self, session_id: str, client: Any = None):
        self.session_id = session_id
        if client is not None:
            self._client = client
        else:
            from server.services.sandbox.docker_client import get_docker_client

            self._client = get_docker_client()
        self._containers: dict[str, dict] = {}

    def check_docker_available(self) -> tuple[bool, str]:
        """Ping Docker daemon. Returns (ok, message)."""
        try:
            self._client.ping()
            return True, "Docker is running"
        except Exception as e:
            return False, f"Docker daemon is not running: {e}"

    def ensure_image(
        self,
        image_name: str = "vista-ralph:latest",
        check_only: bool = False,
    ) -> bool:
        """Check if image exists. Build if missing and check_only=False."""
        try:
            self._client.images.get(image_name)
            return True
        except Exception:
            if check_only:
                return False

        # Build from Dockerfile
        if not DOCKERFILE_DIR.exists():
            raise ImageBuildError(
                f"Vista Dockerfile directory not found at {DOCKERFILE_DIR}"
            )

        try:
            image, build_logs = self._client.images.build(
                path=str(DOCKERFILE_DIR),
                tag=image_name,
                rm=True,
            )
            logger.info(f"Built Docker image: {image_name}")
            return True
        except Exception as e:
            raise ImageBuildError(
                f"Docker image build failed: {e}",
                build_log=str(e),
            )

    def create_container(
        self,
        job_id: str,
        provider: str,
        image: str = "vista-ralph:latest",
        mounts: Optional[list[MountSpec]] = None,
        env_vars: Optional[dict] = None,
        network_enabled: bool = True,
        ttl_seconds: int = 7200,
    ) -> ContainerInfo:
        """Create a Docker container for a sandboxed job."""
        container_name = f"vista-ralph-{job_id[:8]}"
        labels = {
            "managed-by": "vista-ralph",
            "vista-job-id": job_id,
            "vista-provider": provider,
            "vista-session": self.session_id,
        }

        environment = {"DEVCONTAINER": "true"}
        if env_vars:
            environment.update(env_vars)

        docker_mounts = mounts or []

        try:
            container = self._client.containers.create(
                image=image,
                name=container_name,
                command="sleep infinity",
                labels=labels,
                environment=environment,
                working_dir="/workspace",
                network_mode="bridge" if network_enabled else "none",
                extra_hosts={"host.docker.internal": "host-gateway"},
                detach=True,
                mounts=docker_mounts,
            )
        except Exception as e:
            raise ContainerCreateError(f"Failed to create container: {e}")

        now = datetime.now(timezone.utc)
        info = ContainerInfo(
            container_id=container.id,
            name=container.name,
            job_id=job_id,
            provider=provider,
            status="created",
            image=image,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=ttl_seconds)).isoformat(),
        )
        self._containers[container.id] = {
            "info": info,
            "created_at": now,
            "ttl_seconds": ttl_seconds,
        }
        return info

    def start_container(self, container_id: str) -> None:
        """Start a previously created container."""
        try:
            container = self._client.containers.get(container_id)
            container.start()
        except Exception as e:
            raise ContainerStartError(f"Failed to start container: {e}")

        if container_id in self._containers:
            self._containers[container_id]["info"].status = "running"

    def stop_container(
        self, container_id: str, remove: bool = False, timeout: int = 10
    ) -> None:
        """Stop a running container. Idempotent — no error if already stopped."""
        try:
            container = self._client.containers.get(container_id)
            container.stop(timeout=timeout)
            if remove:
                container.remove(force=True)
        except Exception:
            # Container already gone or not found — idempotent
            pass

        if container_id in self._containers:
            self._containers[container_id]["info"].status = "removed"

    def exec_in_container(
        self,
        container_id: str,
        command: list[str],
        workdir: str = "/workspace",
        env: Optional[dict] = None,
    ) -> tuple[int, bytes]:
        """Execute a command inside a running container."""
        container = self._client.containers.get(container_id)
        exit_code, output = container.exec_run(
            cmd=command,
            workdir=workdir,
            environment=env,
            demux=False,
        )
        return exit_code, output

    def cleanup_orphans(self) -> list[str]:
        """Remove containers from old sessions."""
        removed = []
        try:
            containers = self._client.containers.list(
                all=True,
                filters={"label": "managed-by=vista-ralph"},
            )
        except Exception:
            return removed

        for container in containers:
            session = container.labels.get("vista-session", "")
            if session != self.session_id:
                try:
                    container.stop(timeout=5)
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass
                removed.append(container.name)
                logger.info(f"Cleaned up orphaned container: {container.name}")

        return removed

    def shutdown_all(self) -> None:
        """Stop and remove all containers from this session."""
        try:
            containers = self._client.containers.list(
                all=True,
                filters={
                    "label": [
                        "managed-by=vista-ralph",
                        f"vista-session={self.session_id}",
                    ]
                },
            )
        except Exception:
            return

        for container in containers:
            try:
                container.stop(timeout=5)
            except Exception:
                pass
            try:
                container.remove(force=True)
            except Exception:
                pass

    def list_containers(self) -> list[ContainerInfo]:
        """List all managed containers with status."""
        result = []
        try:
            containers = self._client.containers.list(
                all=True,
                filters={"label": "managed-by=vista-ralph"},
            )
        except Exception:
            return result

        for c in containers:
            info = ContainerInfo(
                container_id=c.id,
                name=c.name,
                job_id=c.labels.get("vista-job-id", ""),
                provider=c.labels.get("vista-provider", ""),
                status=c.status,
            )
            result.append(info)
        return result
