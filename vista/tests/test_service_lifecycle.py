"""Tests for ServiceLifecycleManager."""

import pytest

from server.services.service_lifecycle import (
    ServiceConfig,
    ServiceInstance,
    ServiceLifecycleManager,
    ServiceStatus,
    _find_free_port,
)


class TestServiceConfig:
    def test_defaults(self):
        cfg = ServiceConfig(
            name="test",
            command=["echo", "hello"],
            cwd=".",
            preferred_port=3000,
            health_url_template="http://127.0.0.1:{port}/health",
        )
        assert cfg.max_restarts == 5
        assert cfg.health_timeout == 2.0
        assert cfg.startup_timeout == 30.0
        assert cfg.health_interval == 10.0
        assert cfg.consecutive_failures_threshold == 3
        assert cfg.env == {}
        assert cfg.prerequisite_binary == ""


class TestServiceInstance:
    def test_initial_state(self):
        cfg = ServiceConfig(
            name="test", command=["echo"], cwd=".",
            preferred_port=3000, health_url_template="http://localhost:{port}",
        )
        inst = ServiceInstance(config=cfg)
        assert inst.status == ServiceStatus.STOPPED
        assert inst.port == 0
        assert inst.pid is None
        assert inst.process is None
        assert inst.restart_count == 0
        assert inst.consecutive_health_failures == 0


class TestServiceLifecycleManager:
    def test_register(self):
        mgr = ServiceLifecycleManager()
        cfg = ServiceConfig(
            name="test", command=["echo"], cwd=".",
            preferred_port=3000, health_url_template="http://localhost:{port}",
        )
        mgr.register(cfg)
        status = mgr.get_status("test")
        assert status["name"] == "test"
        assert status["status"] == "stopped"

    def test_get_status_unknown(self):
        mgr = ServiceLifecycleManager()
        status = mgr.get_status("nonexistent")
        assert status["status"] == "unknown"

    def test_is_available_false_when_stopped(self):
        mgr = ServiceLifecycleManager()
        cfg = ServiceConfig(
            name="test", command=["echo"], cwd=".",
            preferred_port=3000, health_url_template="http://localhost:{port}",
        )
        mgr.register(cfg)
        assert mgr.is_available("test") is False

    def test_get_all_status(self):
        mgr = ServiceLifecycleManager()
        cfg1 = ServiceConfig(
            name="svc1", command=["echo"], cwd=".",
            preferred_port=3000, health_url_template="http://localhost:{port}",
        )
        cfg2 = ServiceConfig(
            name="svc2", command=["echo"], cwd=".",
            preferred_port=4000, health_url_template="http://localhost:{port}",
        )
        mgr.register(cfg1)
        mgr.register(cfg2)
        statuses = mgr.get_all_status()
        assert len(statuses) == 2
        names = {s["name"] for s in statuses}
        assert names == {"svc1", "svc2"}

    @pytest.mark.asyncio
    async def test_start_missing_prerequisite(self):
        mgr = ServiceLifecycleManager()
        cfg = ServiceConfig(
            name="test", command=["echo"], cwd=".",
            preferred_port=3000,
            health_url_template="http://localhost:{port}",
            prerequisite_binary="nonexistent_binary_xyz_123",
        )
        mgr.register(cfg)
        result = await mgr.start("test")
        assert result is False
        status = mgr.get_status("test")
        assert "not found" in status["last_error"]

    @pytest.mark.asyncio
    async def test_start_unregistered(self):
        mgr = ServiceLifecycleManager()
        result = await mgr.start("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_unregistered(self):
        mgr = ServiceLifecycleManager()
        # Should not raise
        await mgr.stop("nonexistent")

    @pytest.mark.asyncio
    async def test_restart_exceeds_max(self):
        mgr = ServiceLifecycleManager()
        cfg = ServiceConfig(
            name="test", command=["echo"], cwd=".",
            preferred_port=3000,
            health_url_template="http://localhost:{port}",
            max_restarts=0,
        )
        mgr.register(cfg)
        inst = mgr._services["test"]
        inst.restart_count = 0
        result = await mgr.restart("test")
        assert result is False
        assert inst.last_error == "Max restarts exceeded"


class TestFindFreePort:
    def test_finds_port(self):
        port = _find_free_port(49000)
        assert 49000 <= port <= 65535


class TestServiceStatus:
    def test_enum_values(self):
        assert ServiceStatus.STOPPED == "stopped"
        assert ServiceStatus.STARTING == "starting"
        assert ServiceStatus.RUNNING == "running"
        assert ServiceStatus.STOPPING == "stopping"
        assert ServiceStatus.ERROR == "error"
        assert ServiceStatus.RESTARTING == "restarting"
