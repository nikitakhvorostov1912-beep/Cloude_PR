"""Risk manager — validates signals through RulesEngine before execution.

Bridges the gap between signal generation and order execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from src.risk.rules import (
    PortfolioSnapshot,
    RiskApproved,
    RiskRefused,
    RulesEngine,
)

logger = structlog.get_logger(__name__)


class RiskDecision(str, Enum):
    APPROVE = "approved"
    REJECT = "refused"
    REDUCE = "reduced"


@dataclass
class ValidationResult:
    """Result of signal validation through risk rules."""

    decision: RiskDecision
    order: Any | None = None
    reason: str = ""
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def validate_signal(
    signal: Any,
    portfolio: Any,
    config: dict[str, Any] | None = None,
) -> ValidationResult:
    """Validate a trading signal through the RulesEngine.

    Args:
        signal: TradingSignal or similar object with .ticker, .action, .confidence.
        portfolio: PortfolioSnapshot or object with positions/equity info.
        config: Optional config dict with lot_size, risk_per_trade, etc.

    Returns:
        ValidationResult with decision APPROVE/REJECT/REDUCE.
    """
    config = config or {}

    # Build PortfolioSnapshot if needed
    if not isinstance(portfolio, PortfolioSnapshot):
        portfolio = _coerce_portfolio(portfolio)

    engine = RulesEngine()

    try:
        result = engine.check_order(signal, portfolio)
    except Exception as e:
        logger.warning("risk_check_failed", error=str(e))
        return ValidationResult(
            decision=RiskDecision.REJECT,
            order=None,
            reason=f"risk check error: {e}",
            errors=[str(e)],
        )

    if isinstance(result, RiskApproved):
        logger.info(
            "signal_approved",
            ticker=getattr(signal, "ticker", None),
        )
        return ValidationResult(
            decision=RiskDecision.APPROVE,
            order=result.order,
            reason="passed all risk rules",
        )

    # RiskRefused
    reason = getattr(result, "reason", "risk rules failed")
    rule_name = getattr(result, "rule_name", "unknown")
    logger.info(
        "signal_refused",
        ticker=getattr(signal, "ticker", None),
        reason=reason,
        rule=rule_name,
    )
    return ValidationResult(
        decision=RiskDecision.REJECT,
        order=None,
        reason=reason,
        errors=[reason],
        details={"rule": rule_name},
    )


def _coerce_portfolio(portfolio: Any) -> PortfolioSnapshot:
    """Convert various portfolio representations to PortfolioSnapshot."""
    from src.risk.rules import Position as RulesPosition

    if hasattr(portfolio, "positions") and hasattr(portfolio, "equity"):
        positions = []
        pos_dict = getattr(portfolio, "positions", {})
        if isinstance(pos_dict, dict):
            for ticker, pos in pos_dict.items():
                value = getattr(pos, "current_price", 0) * getattr(pos, "lots", 0) * getattr(pos, "lot_size", 1)
                positions.append(RulesPosition(symbol=ticker, value=value))
        elif isinstance(pos_dict, list):
            for pos in pos_dict:
                ticker = getattr(pos, "ticker", getattr(pos, "symbol", "?"))
                value = getattr(pos, "current_price", 0) * getattr(pos, "quantity", 0)
                positions.append(RulesPosition(symbol=ticker, value=value))

        return PortfolioSnapshot(
            positions=positions,
            total_value=getattr(portfolio, "equity", 0),
            current_drawdown=getattr(portfolio, "drawdown", 0),
        )

    return PortfolioSnapshot(positions=[], total_value=0)


__all__ = ["RiskDecision", "ValidationResult", "validate_signal"]
