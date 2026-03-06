"""Тесты аналитики и Dashboard API."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CallLog
from services.analytics import AnalyticsService


# --- Analytics Service ---


class TestAnalyticsSummary:
    @pytest.mark.asyncio
    async def test_empty_summary(self, db_session):
        """Пустая БД -> нулевые метрики."""
        analytics = AnalyticsService(db_session)
        summary = await analytics.get_summary(period_days=7)

        assert summary.total_calls == 0
        assert summary.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_summary_with_data(self, db_session):
        """Сводка с данными."""
        # Создаём тестовые записи
        for i in range(5):
            log = CallLog(
                mango_call_id=f"call-{i}",
                caller_number=f"+7900000000{i}",
                event_type="call.completed",
                task_id=f"TASK-{i}" if i < 3 else None,  # 3 из 5 с задачей
                department="support" if i < 3 else None,
                duration_seconds=120 + i * 30,
            )
            db_session.add(log)
        await db_session.commit()

        analytics = AnalyticsService(db_session)
        summary = await analytics.get_summary(period_days=7)

        assert summary.total_calls == 5
        assert summary.successful_calls == 3
        assert summary.success_rate == 60.0
        assert summary.total_tasks_created == 3


class TestCallsList:
    @pytest.mark.asyncio
    async def test_empty_list(self, db_session):
        """Пустой список звонков."""
        analytics = AnalyticsService(db_session)
        calls = await analytics.get_calls_list(period_days=7)
        assert calls == []

    @pytest.mark.asyncio
    async def test_calls_with_data(self, db_session):
        """Список звонков с данными."""
        log = CallLog(
            mango_call_id="call-001",
            caller_number="+79001234567",
            event_type="call.completed",
            client_name="ООО Ромашка",
            department="support",
            priority="high",
            duration_seconds=180,
        )
        db_session.add(log)
        await db_session.commit()

        analytics = AnalyticsService(db_session)
        calls = await analytics.get_calls_list(period_days=7)

        assert len(calls) == 1
        assert calls[0].call_id == "call-001"
        assert calls[0].client_name == "ООО Ромашка"
        assert calls[0].department == "support"

    @pytest.mark.asyncio
    async def test_calls_pagination(self, db_session):
        """Пагинация списка звонков."""
        for i in range(10):
            db_session.add(
                CallLog(
                    mango_call_id=f"call-{i:03d}",
                    caller_number=f"+790000000{i:02d}",
                    event_type="call.completed",
                )
            )
        await db_session.commit()

        analytics = AnalyticsService(db_session)
        page1 = await analytics.get_calls_list(period_days=7, limit=3, offset=0)
        page2 = await analytics.get_calls_list(period_days=7, limit=3, offset=3)

        assert len(page1) == 3
        assert len(page2) == 3


class TestDepartmentBreakdown:
    @pytest.mark.asyncio
    async def test_empty_breakdown(self, db_session):
        """Пустое распределение."""
        analytics = AnalyticsService(db_session)
        breakdown = await analytics.get_department_breakdown(period_days=7)
        assert breakdown == []

    @pytest.mark.asyncio
    async def test_breakdown_with_data(self, db_session):
        """Распределение по отделам."""
        departments = ["support", "support", "support", "development", "implementation"]
        for i, dept in enumerate(departments):
            db_session.add(
                CallLog(
                    mango_call_id=f"call-{i}",
                    caller_number=f"+790000000{i}",
                    event_type="call.completed",
                    department=dept,
                )
            )
        await db_session.commit()

        analytics = AnalyticsService(db_session)
        breakdown = await analytics.get_department_breakdown(period_days=7)

        assert len(breakdown) == 3
        assert breakdown[0].department == "support"
        assert breakdown[0].count == 3
        assert breakdown[0].percentage == 60.0


# --- Dashboard API ---


class TestDashboardAPI:
    @pytest.mark.asyncio
    async def test_summary_endpoint(self, client):
        """GET /api/dashboard/summary -> 200."""
        response = await client.get("/api/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_calls" in data
        assert "success_rate" in data

    @pytest.mark.asyncio
    async def test_summary_with_period(self, client):
        """GET /api/dashboard/summary?period=30."""
        response = await client.get("/api/dashboard/summary?period=30")
        assert response.status_code == 200
        assert response.json()["period_days"] == 30

    @pytest.mark.asyncio
    async def test_calls_endpoint(self, client):
        """GET /api/dashboard/calls -> 200."""
        response = await client.get("/api/dashboard/calls")
        assert response.status_code == 200
        data = response.json()
        assert "calls" in data
        assert isinstance(data["calls"], list)

    @pytest.mark.asyncio
    async def test_departments_endpoint(self, client):
        """GET /api/dashboard/departments -> 200."""
        response = await client.get("/api/dashboard/departments")
        assert response.status_code == 200
        data = response.json()
        assert "departments" in data
