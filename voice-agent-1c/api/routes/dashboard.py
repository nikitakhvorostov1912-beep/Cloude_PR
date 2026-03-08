"""Dashboard API — KPI и аналитика.

GET /api/dashboard/summary — KPI карточки
GET /api/dashboard/calls — список звонков
GET /api/dashboard/departments — распределение по отделам
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from services.analytics import AnalyticsService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary(
    period: int = Query(default=7, ge=1, le=90, description="Период в днях"),
    session: AsyncSession = Depends(get_session),
):
    """KPI карточки дашборда."""
    analytics = AnalyticsService(session)
    summary = await analytics.get_summary(period_days=period)
    return {
        "period_days": period,
        "total_calls": summary.total_calls,
        "successful_calls": summary.successful_calls,
        "success_rate": summary.success_rate,
        "avg_duration_seconds": summary.avg_duration_seconds,
        "total_tasks_created": summary.total_tasks_created,
        "escalation_count": summary.escalation_count,
        "escalation_rate": summary.escalation_rate,
    }


@router.get("/calls")
async def dashboard_calls(
    period: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Список звонков за период."""
    analytics = AnalyticsService(session)
    calls = await analytics.get_calls_list(
        period_days=period, limit=limit, offset=offset
    )
    return {
        "period_days": period,
        "count": len(calls),
        "calls": [
            {
                "call_id": c.call_id,
                "caller_number": c.caller_number,
                "client_name": c.client_name,
                "department": c.department,
                "priority": c.priority,
                "duration_seconds": c.duration_seconds,
                "created_at": c.created_at,
            }
            for c in calls
        ],
    }


@router.get("/departments")
async def dashboard_departments(
    period: int = Query(default=7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Распределение по отделам."""
    analytics = AnalyticsService(session)
    breakdown = await analytics.get_department_breakdown(period_days=period)
    return {
        "period_days": period,
        "departments": [
            {
                "department": d.department,
                "count": d.count,
                "percentage": d.percentage,
            }
            for d in breakdown
        ],
    }


@router.get("/calls/{call_id}")
async def dashboard_call_detail(
    call_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Детали конкретного звонка."""
    analytics = AnalyticsService(session)
    detail = await analytics.get_call_detail(call_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Звонок не найден",
        )
    return detail
