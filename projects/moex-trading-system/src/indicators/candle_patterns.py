# ruff: noqa: E741  — 'l' (low) is standard OHLC convention in financial code
"""Candlestick pattern recognition for MOEX instruments.

Inspired by LiuAlgoTrader fincalcs/candle_patterns.py (MIT License).
Written from scratch with improvements:
- Vectorized numpy operations (process entire arrays, not per-candle)
- Configurable thresholds via CandleConfig
- Additional patterns: hammer, inverted_hammer, engulfing_bull, engulfing_bear
- Both scalar (single candle) and vectorized (array) APIs

Usage:
    from src.indicators.candle_patterns import detect_patterns, CandleConfig

    # Vectorized (recommended):
    patterns = detect_patterns(open, high, low, close)
    # patterns["doji"] = [False, True, False, ...]

    # Scalar:
    from src.indicators.candle_patterns import is_doji
    result = is_doji(300.0, 305.0, 295.0, 300.0)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CandleConfig:
    """Thresholds for candlestick pattern detection.

    All values are relative to the candle's total range (high - low).

    Attributes:
        body_doji_max: Max body/range ratio for doji patterns (default 0.1).
        body_strong_min: Min body/range ratio for strong candles (default 0.6).
        shadow_balance_min: Min shadow ratio for spinning top (default 0.4).
        shadow_balance_max: Max shadow ratio for spinning top (default 0.6).
        engulfing_min_ratio: Min ratio of current body to previous body (default 1.1).
    """

    body_doji_max: float = 0.1
    body_strong_min: float = 0.6
    shadow_balance_min: float = 0.4
    shadow_balance_max: float = 0.6
    engulfing_min_ratio: float = 1.1


_DEFAULT_CFG = CandleConfig()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _body(o: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Absolute body size."""
    return np.abs(c - o)


def _range(h: np.ndarray, l: np.ndarray) -> np.ndarray:
    """Total candle range (high - low)."""
    return h - l


def _upper_shadow(o: np.ndarray, h: np.ndarray, c: np.ndarray) -> np.ndarray:
    return h - np.maximum(o, c)


def _lower_shadow(o: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    return np.minimum(o, c) - l


# ---------------------------------------------------------------------------
# Scalar API (single candle)
# ---------------------------------------------------------------------------


def is_doji(
    o: float, h: float, l: float, c: float,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> bool:
    """Doji: tiny body relative to range, shadows on both sides."""
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    return (
        body / rng <= cfg.body_doji_max
        and (h - max(o, c)) > 0
        and (min(o, c) - l) > 0
    )


def is_gravestone_doji(
    o: float, h: float, l: float, c: float,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> bool:
    """Gravestone doji: tiny body near low, long upper shadow."""
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return (
        body / rng <= cfg.body_doji_max
        and upper > 2 * lower
        and upper > 0
    )


def is_dragonfly_doji(
    o: float, h: float, l: float, c: float,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> bool:
    """Dragonfly doji: tiny body near high, long lower shadow."""
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return (
        body / rng <= cfg.body_doji_max
        and lower > 2 * upper
        and lower > 0
    )


def is_spinning_top(
    o: float, h: float, l: float, c: float,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> bool:
    """Spinning top: small body, balanced upper and lower shadows."""
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    total_shadow = upper + lower
    if total_shadow <= 0:
        return False
    shadow_ratio = upper / total_shadow
    return (
        body / rng <= 0.3
        and cfg.shadow_balance_min <= shadow_ratio <= cfg.shadow_balance_max
    )


def is_hammer(
    o: float, h: float, l: float, c: float,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> bool:
    """Hammer: small body near high, long lower shadow (bullish reversal)."""
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    lower = min(o, c) - l
    upper = h - max(o, c)
    return (
        lower >= 2 * body
        and upper <= body * 0.5
        and body / rng > 0
    )


def is_inverted_hammer(
    o: float, h: float, l: float, c: float,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> bool:
    """Inverted hammer: small body near low, long upper shadow."""
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return (
        upper >= 2 * body
        and lower <= body * 0.5
        and body / rng > 0
    )


def is_bullish(o: float, h: float, l: float, c: float,
               cfg: CandleConfig = _DEFAULT_CFG) -> bool:
    """Strong bullish candle: large body, close > open."""
    rng = h - l
    if rng <= 0:
        return False
    body = c - o
    return body > 0 and body / rng >= cfg.body_strong_min


def is_bearish(o: float, h: float, l: float, c: float,
               cfg: CandleConfig = _DEFAULT_CFG) -> bool:
    """Strong bearish candle: large body, close < open."""
    rng = h - l
    if rng <= 0:
        return False
    body = o - c
    return body > 0 and body / rng >= cfg.body_strong_min


# ---------------------------------------------------------------------------
# Multi-candle scalar patterns
# ---------------------------------------------------------------------------


def is_engulfing_bullish(
    o1: float, h1: float, l1: float, c1: float,
    o2: float, h2: float, l2: float, c2: float,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> bool:
    """Bullish engulfing: bearish candle followed by larger bullish candle."""
    body1 = abs(c1 - o1)
    body2 = c2 - o2
    if body1 <= 0:
        return False
    return (
        c1 < o1  # first is bearish
        and c2 > o2  # second is bullish
        and body2 / body1 >= cfg.engulfing_min_ratio
        and o2 <= c1  # second opens at or below first close
        and c2 >= o1  # second closes at or above first open
    )


def is_engulfing_bearish(
    o1: float, h1: float, l1: float, c1: float,
    o2: float, h2: float, l2: float, c2: float,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> bool:
    """Bearish engulfing: bullish candle followed by larger bearish candle."""
    body1 = abs(c1 - o1)
    body2 = o2 - c2
    if body1 <= 0:
        return False
    return (
        c1 > o1  # first is bullish
        and c2 < o2  # second is bearish
        and body2 / body1 >= cfg.engulfing_min_ratio
        and o2 >= c1  # second opens at or above first close
        and c2 <= o1  # second closes at or below first open
    )


# ---------------------------------------------------------------------------
# Vectorized API (entire arrays)
# ---------------------------------------------------------------------------


def detect_doji(
    o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> np.ndarray:
    """Vectorized doji detection."""
    rng = _range(h, l)
    body = _body(o, c)
    safe_rng = np.where(rng > 0, rng, 1.0)
    ratio = body / safe_rng
    upper = _upper_shadow(o, h, c)
    lower = _lower_shadow(o, l, c)
    return (rng > 0) & (ratio <= cfg.body_doji_max) & (upper > 0) & (lower > 0)


def detect_hammer(
    o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> np.ndarray:
    """Vectorized hammer detection."""
    rng = _range(h, l)
    body = _body(o, c)
    lower = _lower_shadow(o, l, c)
    upper = _upper_shadow(o, h, c)
    return (rng > 0) & (lower >= 2 * body) & (upper <= body * 0.5) & (body > 0)


def detect_bullish(
    o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> np.ndarray:
    """Vectorized strong bullish candle detection."""
    rng = _range(h, l)
    body = c - o
    safe_rng = np.where(rng > 0, rng, 1.0)
    return (rng > 0) & (body > 0) & (body / safe_rng >= cfg.body_strong_min)


def detect_bearish(
    o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> np.ndarray:
    """Vectorized strong bearish candle detection."""
    rng = _range(h, l)
    body = o - c
    safe_rng = np.where(rng > 0, rng, 1.0)
    return (rng > 0) & (body > 0) & (body / safe_rng >= cfg.body_strong_min)


def detect_engulfing_bullish(
    o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> np.ndarray:
    """Vectorized bullish engulfing (pair: bar[i-1] + bar[i])."""
    n = len(o)
    result = np.zeros(n, dtype=bool)
    if n < 2:
        return result
    prev_bearish = c[:-1] < o[:-1]
    curr_bullish = c[1:] > o[1:]
    prev_body = np.abs(c[:-1] - o[:-1])
    curr_body = c[1:] - o[1:]
    safe_prev = np.where(prev_body > 0, prev_body, 1.0)
    engulfs = (
        prev_bearish & curr_bullish
        & (curr_body / safe_prev >= cfg.engulfing_min_ratio)
        & (o[1:] <= c[:-1])
        & (c[1:] >= o[:-1])
    )
    result[1:] = engulfs
    return result


def detect_engulfing_bearish(
    o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> np.ndarray:
    """Vectorized bearish engulfing (pair: bar[i-1] + bar[i])."""
    n = len(o)
    result = np.zeros(n, dtype=bool)
    if n < 2:
        return result
    prev_bullish = c[:-1] > o[:-1]
    curr_bearish = c[1:] < o[1:]
    prev_body = np.abs(c[:-1] - o[:-1])
    curr_body = o[1:] - c[1:]
    safe_prev = np.where(prev_body > 0, prev_body, 1.0)
    engulfs = (
        prev_bullish & curr_bearish
        & (curr_body / safe_prev >= cfg.engulfing_min_ratio)
        & (o[1:] >= c[:-1])
        & (c[1:] <= o[:-1])
    )
    result[1:] = engulfs
    return result


def detect_patterns(
    o: np.ndarray | list,
    h: np.ndarray | list,
    l: np.ndarray | list,
    c: np.ndarray | list,
    cfg: CandleConfig = _DEFAULT_CFG,
) -> dict[str, np.ndarray]:
    """Detect all supported patterns on OHLC arrays.

    Returns dict mapping pattern name → boolean array.

    Args:
        o, h, l, c: OHLC arrays of equal length.
        cfg: CandleConfig with thresholds.

    Returns:
        Dict with keys: doji, hammer, bullish, bearish,
        engulfing_bullish, engulfing_bearish.
    """
    oa = np.asarray(o, dtype=np.float64)
    ha = np.asarray(h, dtype=np.float64)
    la = np.asarray(l, dtype=np.float64)
    ca = np.asarray(c, dtype=np.float64)

    return {
        "doji": detect_doji(oa, ha, la, ca, cfg),
        "hammer": detect_hammer(oa, ha, la, ca, cfg),
        "bullish": detect_bullish(oa, ha, la, ca, cfg),
        "bearish": detect_bearish(oa, ha, la, ca, cfg),
        "engulfing_bullish": detect_engulfing_bullish(oa, ha, la, ca, cfg),
        "engulfing_bearish": detect_engulfing_bearish(oa, ha, la, ca, cfg),
    }
