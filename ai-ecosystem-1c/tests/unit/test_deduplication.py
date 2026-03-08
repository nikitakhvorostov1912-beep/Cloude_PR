"""Tests for call deduplication logic."""

from __future__ import annotations

import pytest

from orchestrator.core.deduplication import DeduplicationService


@pytest.fixture
def dedup() -> DeduplicationService:
    return DeduplicationService(window_minutes=30)


class TestDeduplication:
    """Test deduplication with in-memory store."""

    @pytest.mark.asyncio
    async def test_no_duplicate_initially(self, dedup: DeduplicationService) -> None:
        result = await dedup.check("+74951234567")
        assert result is None

    @pytest.mark.asyncio
    async def test_registers_and_finds_duplicate(
        self, dedup: DeduplicationService
    ) -> None:
        await dedup.register(
            phone="+74951234567",
            call_id="call-001",
            task_number="SAK-100",
            department="support",
        )
        result = await dedup.check("+74951234567")
        assert result is not None
        assert result.call_id == "call-001"
        assert result.task_number == "SAK-100"

    @pytest.mark.asyncio
    async def test_different_phones_not_duplicated(
        self, dedup: DeduplicationService
    ) -> None:
        await dedup.register(
            phone="+74951111111",
            call_id="call-001",
        )
        result = await dedup.check("+74952222222")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_removes_entry(
        self, dedup: DeduplicationService
    ) -> None:
        await dedup.register(phone="+74951234567", call_id="call-001")
        await dedup.clear("+74951234567")
        result = await dedup.check("+74951234567")
        assert result is None

    @pytest.mark.asyncio
    async def test_register_updates_existing(
        self, dedup: DeduplicationService
    ) -> None:
        await dedup.register(
            phone="+74951234567",
            call_id="call-001",
            task_number="SAK-100",
        )
        await dedup.register(
            phone="+74951234567",
            call_id="call-002",
            task_number="SAK-101",
        )
        result = await dedup.check("+74951234567")
        assert result is not None
        assert result.call_id == "call-002"
        assert result.task_number == "SAK-101"
