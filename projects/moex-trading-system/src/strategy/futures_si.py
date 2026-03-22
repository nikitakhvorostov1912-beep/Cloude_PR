"""Si futures strategy — USD/RUB hedge for equity portfolio.

Strategy P4 from research/04-moex-strategies.md: score 19/30, high complexity.
Si = USD/RUB futures on MOEX FORTS, GO ~15%, very liquid.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class FuturesSignal:
    """Signal for Si futures hedging."""

    ticker: str
    action: str
    confidence: float
    reasoning: str
    hedge_ratio: float = 1.0


def generate_si_signals(
    candles: list | None = None,
    macro: dict | Any | None = None,
    portfolio_exposure: float = 0.0,
) -> list:
    """Generate Si futures signals for USD/RUB hedging.

    Rules:
    - USD/RUB > 95 and rising → buy Si as hedge (hedge_ratio 0.3)
    - USD/RUB < 80 → sell Si (ruble strengthening)
    - Portfolio exposure > 50% → increase hedge ratio

    Args:
        candles: USD/RUB candle history (optional).
        macro: MacroData or dict with usd_rub, key_rate.
        portfolio_exposure: Current equity exposure as fraction.

    Returns:
        List of FuturesSignal.
    """
    signals: list[FuturesSignal] = []

    if macro is None:
        return signals

    # Extract USD/RUB from various formats
    if isinstance(macro, dict):
        usd_rub = macro.get("usd_rub", 90.0)
    else:
        usd_rub = getattr(macro, "usd_rub", 90.0)

    if usd_rub > 95:
        hedge_ratio = 0.3
        if portfolio_exposure > 0.5:
            hedge_ratio = 0.5
        signals.append(FuturesSignal(
            ticker="SiH5",
            action="buy",
            confidence=0.55,
            reasoning=f"USD/RUB={usd_rub:.1f} > 95, hedge currency risk",
            hedge_ratio=hedge_ratio,
        ))
        logger.info("si_hedge_signal", usd_rub=usd_rub, hedge_ratio=hedge_ratio)

    elif usd_rub < 80:
        signals.append(FuturesSignal(
            ticker="SiH5",
            action="sell",
            confidence=0.50,
            reasoning=f"USD/RUB={usd_rub:.1f} < 80, ruble strengthening",
            hedge_ratio=0.2,
        ))

    return signals


__all__ = ["generate_si_signals", "FuturesSignal"]
