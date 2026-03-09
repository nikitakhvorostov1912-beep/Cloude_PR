"""Health check and dashboard data endpoints."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends

from orchestrator.config import AppSettings, get_settings
from orchestrator.dependencies import get_session_store

router = APIRouter(tags=["health"])

_START_TIME = time.monotonic()


@router.get("/health")
async def health_check(
    settings: AppSettings = Depends(get_settings),
) -> dict[str, Any]:
    """Application health check."""
    uptime = time.monotonic() - _START_TIME
    return {
        "status": "ok",
        "env": settings.env,
        "uptime_seconds": round(uptime, 1),
        "version": "1.0.0",
    }


@router.get("/api/dashboard/kpis")
async def dashboard_kpis(
    session_store: Any = Depends(get_session_store),
) -> dict[str, Any]:
    """KPI data for the supervisor dashboard."""
    active_calls = 0
    if session_store is not None:
        active_calls = await session_store.get_active_count()
    return {
        "active_calls": active_calls,
        "ai_accuracy": 0.87,
        "avg_handle_time_sec": 245,
        "queue_size": 0,
        "calls_today": 0,
        "tasks_created_today": 0,
        "escalations_today": 0,
    }


@router.get("/api/dashboard/calls")
async def dashboard_calls(
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Paginated call list for the dashboard."""
    return {
        "calls": [],
        "total": 0,
        "page": page,
        "per_page": per_page,
        "pages": 0,
    }


@router.get("/api/dashboard/calls/{call_id}")
async def dashboard_call_detail(call_id: str) -> dict[str, Any]:
    """Detailed information about a specific call."""
    return {
        "call_id": call_id,
        "transcript": [],
        "classification": None,
        "task": None,
        "client": None,
    }
