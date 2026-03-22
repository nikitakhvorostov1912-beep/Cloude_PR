"""Dividend gap strategy — buy after ex-date, profit on gap closure.

Strategy P1 from research/04-moex-strategies.md: score 28/30, ~10% per trade.
SBER median gap closure: 24 days. MOEX div yield: 8-17%.

Dividend calendar source: MOEX ISS /iss/securities/{ticker}/dividends.json
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DivGapSignal:
    """Signal for dividend gap strategy."""

    ticker: str
    ex_date: datetime | None = None
    div_yield: float = 0.0
    expected_gap_pct: float = 0.0
    days_to_ex: int = 0
    action: str = "buy"
    confidence: float = 0.6


def find_dividend_gap_signals(
    candles_cache: dict[str, list],
    today: Any = None,
    lookahead_days: int = 5,
    min_yield: float = 0.04,
) -> list:
    """Find dividend gap trading opportunities.

    Strategy P1 from research/04-moex-strategies.md:
    - Buy after ex-dividend date when price drops by dividend amount
    - Gap typically closes in 2-4 weeks (SBER median: 24 days)
    - Expected return ~10% per trade

    Args:
        candles_cache: Dict of ticker -> list of candle dicts/objects.
        today: Reference date.
        lookahead_days: Days ahead to check for ex-dates.
        min_yield: Minimum dividend yield to consider.

    Returns:
        List of signals (empty until div calendar API is connected).
    """
    # Placeholder: real implementation needs MOEX dividend calendar API
    # GET /iss/securities/{ticker}/dividends.json
    logger.info(
        "div_gap_scan",
        tickers=len(candles_cache),
        lookahead_days=lookahead_days,
        min_yield=min_yield,
    )
    return []


__all__ = ["find_dividend_gap_signals", "DivGapSignal"]
