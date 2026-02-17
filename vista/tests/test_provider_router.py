"""Tests for ProviderRouter."""

import pytest

from server.services.provider_router import ProviderRouter


class TestProviderRouter:
    def test_initial_state(self):
        router = ProviderRouter()
        assert router._session_map == {}
        assert router._claude_clients == {}
        assert router._opencode_clients == {}

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_session(self):
        router = ProviderRouter()
        # Should not raise
        await router.cleanup_session("nonexistent")

    @pytest.mark.asyncio
    async def test_cleanup_all_empty(self):
        router = ProviderRouter()
        # Should not raise
        await router.cleanup_all()

    @pytest.mark.asyncio
    async def test_send_message_unknown_provider(self):
        router = ProviderRouter()
        events = []
        async for event in router.send_message(
            provider="unknown", model="test", prompt="hello",
            session_id="s1", cwd="/tmp",
        ):
            events.append(event)
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "Failed to create backend session" in events[0]["detail"]

    @pytest.mark.asyncio
    async def test_create_backend_session_unknown_provider(self):
        router = ProviderRouter()
        with pytest.raises(ValueError, match="Unknown provider"):
            await router.create_backend_session("unknown", "model", "s1", "/tmp")
