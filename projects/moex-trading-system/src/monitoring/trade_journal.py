"""Trade journal — structured logging for signal decisions and trade execution."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def log_signal_decision(
    signal: Any,
    decision: str,
    reason: str,
    *,
    extra: dict | None = None,
) -> None:
    """Log a signal decision (approved/rejected) to structured log."""
    logger.info(
        "signal_decision",
        ticker=getattr(signal, "ticker", None),
        action=getattr(signal, "action", None),
        confidence=getattr(signal, "confidence", None),
        decision=decision,
        reason=reason,
        ts=datetime.utcnow().isoformat(),
        **(extra or {}),
    )


def log_trade(
    order: Any,
    fill_price: float,
    pnl: float,
    *,
    extra: dict | None = None,
) -> None:
    """Log a completed trade to structured log."""
    logger.info(
        "trade_executed",
        ticker=getattr(order, "ticker", None),
        order_id=getattr(order, "order_id", None),
        side=getattr(order, "side", None),
        quantity=getattr(order, "quantity", None),
        fill_price=fill_price,
        pnl=pnl,
        commission=getattr(order, "commission", 0.0),
        ts=datetime.utcnow().isoformat(),
        **(extra or {}),
    )


__all__ = ["log_signal_decision", "log_trade"]
