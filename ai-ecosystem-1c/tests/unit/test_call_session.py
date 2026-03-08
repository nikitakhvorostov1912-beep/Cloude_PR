"""Tests for call session store."""

from __future__ import annotations

import pytest

from orchestrator.core.call_session import CallSessionStore


@pytest.fixture
def store() -> CallSessionStore:
    return CallSessionStore(ttl_seconds=1800)


class TestCallSessionStore:
    """Test in-memory session store."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, store: CallSessionStore) -> None:
        await store.set("call-001", {"phone": "+74951234567", "status": "active"})
        result = await store.get("call-001")
        assert result is not None
        assert result["phone"] == "+74951234567"
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(
        self, store: CallSessionStore
    ) -> None:
        result = await store.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_merges_fields(self, store: CallSessionStore) -> None:
        await store.set("call-001", {"phone": "+74951234567", "status": "active"})
        await store.update("call-001", status="classified", department="support")
        result = await store.get("call-001")
        assert result is not None
        assert result["status"] == "classified"
        assert result["department"] == "support"
        assert result["phone"] == "+74951234567"

    @pytest.mark.asyncio
    async def test_delete_removes_session(self, store: CallSessionStore) -> None:
        await store.set("call-001", {"status": "active"})
        await store.delete("call-001")
        result = await store.get("call-001")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, store: CallSessionStore) -> None:
        assert not await store.exists("call-001")
        await store.set("call-001", {"status": "active"})
        assert await store.exists("call-001")

    @pytest.mark.asyncio
    async def test_active_count(self, store: CallSessionStore) -> None:
        assert await store.get_active_count() == 0
        await store.set("call-001", {"status": "active"})
        await store.set("call-002", {"status": "active"})
        assert await store.get_active_count() == 2
