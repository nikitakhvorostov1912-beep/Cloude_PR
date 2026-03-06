"""Аналитика и метрики Voice Agent.

SQL-агрегации по CallLog для дашборда:
  - success_rate, avg_duration, calls_per_hour
  - top_request_types, escalation_reasons
  - classification_accuracy, latency percentiles
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CallLog

logger = logging.getLogger(__name__)


@dataclass
class DashboardSummary:
    """KPI карточки для дашборда."""

    total_calls: int = 0
    successful_calls: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    total_tasks_created: int = 0
    escalation_count: int = 0
    escalation_rate: float = 0.0
    avg_latency_ms: float = 0.0


@dataclass
class CallStats:
    """Статистика звонка для списка."""

    call_id: str
    caller_number: str
    client_name: str | None
    department: str | None
    priority: str | None
    duration_seconds: int | None
    created_at: str


@dataclass
class DepartmentBreakdown:
    """Распределение по отделам."""

    department: str
    count: int
    percentage: float


@dataclass
class LatencyMetrics:
    """Метрики латентности."""

    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    avg_ms: float = 0.0


class AnalyticsService:
    """Сервис аналитики.

    Usage:
        analytics = AnalyticsService(session)
        summary = await analytics.get_summary(period_days=7)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_summary(self, period_days: int = 7) -> DashboardSummary:
        """Получает сводные KPI за период."""
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Общее количество звонков
        total_q = select(func.count(CallLog.id)).where(
            CallLog.created_at >= since
        )
        total = (await self._session.execute(total_q)).scalar() or 0

        # Успешные (есть task_id)
        success_q = select(func.count(CallLog.id)).where(
            CallLog.created_at >= since,
            CallLog.task_id.isnot(None),
        )
        successful = (await self._session.execute(success_q)).scalar() or 0

        # Средняя длительность
        avg_dur_q = select(func.avg(CallLog.duration_seconds)).where(
            CallLog.created_at >= since,
            CallLog.duration_seconds.isnot(None),
        )
        avg_dur = (await self._session.execute(avg_dur_q)).scalar() or 0.0

        # Задачи созданы
        tasks_q = select(func.count(CallLog.id)).where(
            CallLog.created_at >= since,
            CallLog.task_id.isnot(None),
        )
        tasks_count = (await self._session.execute(tasks_q)).scalar() or 0

        success_rate = (successful / total * 100) if total > 0 else 0.0

        return DashboardSummary(
            total_calls=total,
            successful_calls=successful,
            success_rate=round(success_rate, 1),
            avg_duration_seconds=round(float(avg_dur), 1),
            total_tasks_created=tasks_count,
        )

    async def get_calls_list(
        self,
        period_days: int = 7,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CallStats]:
        """Получает список звонков за период."""
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        q = (
            select(CallLog)
            .where(CallLog.created_at >= since)
            .order_by(CallLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(q)
        rows = result.scalars().all()

        return [
            CallStats(
                call_id=row.mango_call_id,
                caller_number=row.caller_number,
                client_name=row.client_name,
                department=row.department,
                priority=row.priority,
                duration_seconds=row.duration_seconds,
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
            for row in rows
        ]

    async def get_department_breakdown(
        self, period_days: int = 7
    ) -> list[DepartmentBreakdown]:
        """Получает распределение по отделам."""
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        q = (
            select(
                CallLog.department,
                func.count(CallLog.id).label("cnt"),
            )
            .where(
                CallLog.created_at >= since,
                CallLog.department.isnot(None),
            )
            .group_by(CallLog.department)
            .order_by(func.count(CallLog.id).desc())
        )
        result = await self._session.execute(q)
        rows = result.all()

        total = sum(r.cnt for r in rows)
        return [
            DepartmentBreakdown(
                department=r.department or "unknown",
                count=r.cnt,
                percentage=round(r.cnt / total * 100, 1) if total > 0 else 0.0,
            )
            for r in rows
        ]
