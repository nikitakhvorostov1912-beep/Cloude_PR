"""Pairs trading — statistical arbitrage for MOEX.

Strategy P2 from research/04-moex-strategies.md: score 24/30, medium complexity.
Pairs: SBER/VTBR (state banks), LKOH/ROSN (oil majors).
Method: spread z-score → mean reversion.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

PAIRS = [
    ("SBER", "VTBR"),
    ("LKOH", "ROSN"),
]


@dataclass
class PairSignal:
    """Signal for pairs trading strategy."""

    long_ticker: str
    short_ticker: str
    zscore: float
    confidence: float
    reasoning: str


def generate_pairs_signals(
    candles: dict[str, list],
    today: Any = None,
    zscore_threshold: float = 2.0,
    lookback: int = 60,
) -> list:
    """Generate pairs trading signals based on spread z-score.

    Strategy P2: SBER/VTBR, LKOH/ROSN — cointegrated pairs on MOEX.
    Signal when z-score exceeds threshold → expect mean reversion.

    Args:
        candles: Dict of ticker -> list of candle dicts with "close" key.
        today: Reference date (unused, for interface compatibility).
        zscore_threshold: Z-score threshold to trigger signal.
        lookback: Number of bars for spread calculation.

    Returns:
        List of PairSignal (or compatible signal objects).
    """
    signals: list[PairSignal] = []

    for ticker_a, ticker_b in PAIRS:
        if ticker_a not in candles or ticker_b not in candles:
            continue

        try:
            raw_a = candles[ticker_a][-lookback:]
            raw_b = candles[ticker_b][-lookback:]

            prices_a = _extract_close(raw_a)
            prices_b = _extract_close(raw_b)

            min_len = min(len(prices_a), len(prices_b))
            if min_len < 20:
                continue

            prices_a = prices_a[-min_len:]
            prices_b = prices_b[-min_len:]

            # Price ratio spread
            spread = [a / b for a, b in zip(prices_a, prices_b) if b != 0]
            if len(spread) < 20:
                continue

            mean = statistics.mean(spread)
            std = statistics.stdev(spread)
            if std == 0:
                continue

            zscore = (spread[-1] - mean) / std

            if abs(zscore) > zscore_threshold:
                # Negative z-score: A underperformed B → long A, short B
                long_t = ticker_a if zscore < 0 else ticker_b
                short_t = ticker_b if zscore < 0 else ticker_a
                conf = min(0.8, 0.5 + abs(zscore) * 0.1)

                signals.append(PairSignal(
                    long_ticker=long_t,
                    short_ticker=short_t,
                    zscore=round(zscore, 3),
                    confidence=round(conf, 3),
                    reasoning=f"z-score={zscore:.2f}, threshold={zscore_threshold}",
                ))
                logger.info(
                    "pairs_signal",
                    long=long_t,
                    short=short_t,
                    zscore=round(zscore, 3),
                )

        except Exception as e:
            logger.warning("pairs_error", pair=f"{ticker_a}/{ticker_b}", error=str(e))

    return signals


def _extract_close(candles: list) -> list[float]:
    """Extract close prices from various candle formats."""
    prices = []
    for c in candles:
        if isinstance(c, dict):
            val = c.get("close", 0)
        elif hasattr(c, "close"):
            val = c.close
        else:
            continue
        if val and val > 0:
            prices.append(float(val))
    return prices


__all__ = ["generate_pairs_signals", "PairSignal", "PAIRS"]
