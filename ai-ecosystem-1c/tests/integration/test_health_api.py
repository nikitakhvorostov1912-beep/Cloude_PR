"""Integration tests for health and dashboard API endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from orchestrator.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthAPI:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_dashboard_kpis(self, client: AsyncClient) -> None:
        response = await client.get("/api/dashboard/kpis")
        assert response.status_code == 200
        data = response.json()
        assert "active_calls" in data
        assert "ai_accuracy" in data

    @pytest.mark.asyncio
    async def test_dashboard_calls_list(self, client: AsyncClient) -> None:
        response = await client.get("/api/dashboard/calls?page=1")
        assert response.status_code == 200
        data = response.json()
        assert "calls" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_dashboard_call_detail(self, client: AsyncClient) -> None:
        response = await client.get("/api/dashboard/calls/test-call-001")
        assert response.status_code == 200
        data = response.json()
        assert data["call_id"] == "test-call-001"
