"""ML label generators for trading — multi-threshold targets.

Inspired by asavinov/intelligent-trading-bot (MIT).
Written from scratch.

Instead of binary "price goes up/down", generates MULTIPLE labels
at different thresholds: "price rises >1%", ">2%", ">3%", etc.
ML model learns to predict MAGNITUDE, not just direction.

Also: TopBot labels — marks local extrema for supervised learning.

Usage:
    from src.ml.label_generators import (
        generate_highlow_labels, generate_topbot_labels,
    )

    labels = generate_highlow_labels(
        close, high, low, horizon=60,
        thresholds=[0.5, 1.0, 1.5, 2.0, 3.0],
    )
    # labels["high_1.0"] = True where max(high, 60 bars) > close * 1.01

    tops, bots = generate_topbot_labels(close, level=0.02, tolerance=0.005)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def generate_highlow_labels(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    horizon: int = 60,
    thresholds: list[float] | None = None,
) -> dict[str, np.ndarray]:
    """Generate multi-threshold high/low labels for ML training.

    For each threshold T, generates:
    - high_T: True if max(high[t+1:t+horizon]) > close[t] * (1 + T/100)
    - low_T:  True if min(low[t+1:t+horizon]) < close[t] * (1 - T/100)

    This gives the ML model richer targets than binary up/down:
    - "Will price rise by at least 1%?" → high_1.0
    - "Will price drop by at least 2%?" → low_2.0

    Args:
        close: Close price array.
        high: High price array.
        low: Low price array.
        horizon: Forward-looking window in bars.
        thresholds: List of threshold percentages (default [0.5, 1.0, 1.5, 2.0, 3.0]).

    Returns:
        Dict mapping label name → boolean array (same length as input,
        last `horizon` bars are False since no future data).
    """
    close = np.asarray(close, dtype=np.float64)
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    n = len(close)

    if thresholds is None:
        thresholds = [0.5, 1.0, 1.5, 2.0, 3.0]

    labels: dict[str, np.ndarray] = {}

    # Pre-compute rolling max(high) and min(low) over future horizon
    future_max_high = np.full(n, np.nan)
    future_min_low = np.full(n, np.nan)

    for i in range(n - horizon):
        future_max_high[i] = np.max(high[i + 1:i + 1 + horizon])
        future_min_low[i] = np.min(low[i + 1:i + 1 + horizon])

    # Relative changes from close
    # high_pct: how much did the max high exceed close (in %)
    safe_close = np.where(close > 0, close, 1.0)
    high_pct = (future_max_high - close) / safe_close * 100
    low_pct = (close - future_min_low) / safe_close * 100

    for t in thresholds:
        t_str = f"{t:.1f}".replace(".", "_")
        # high_T: max high exceeded close by at least T%
        labels[f"high_{t_str}"] = np.where(np.isnan(high_pct), False, high_pct >= t)
        # low_T: min low dropped below close by at least T%
        labels[f"low_{t_str}"] = np.where(np.isnan(low_pct), False, low_pct >= t)

    # Combined direction label: +1 if more up than down, -1 if more down, 0 neutral
    labels["direction"] = np.where(
        np.isnan(high_pct), 0,
        np.where(high_pct > low_pct, 1, np.where(low_pct > high_pct, -1, 0)),
    )

    # Magnitude: max of high_pct and low_pct (how much price moved)
    labels["magnitude"] = np.where(
        np.isnan(high_pct), 0.0,
        np.maximum(high_pct, low_pct),
    )

    return labels


@dataclass(frozen=True)
class Extremum:
    """A detected local extremum.

    Attributes:
        index: Bar index.
        price: Price at extremum.
        type: "top" or "bot".
        strength: How much price moved away from this extremum (%).
    """

    index: int
    price: float
    type: str  # "top" or "bot"
    strength: float


def generate_topbot_labels(
    close: np.ndarray,
    level: float = 0.02,
    tolerance: float = 0.005,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate top/bottom extremum labels for supervised learning.

    Finds local maxima ("tops") and minima ("bots") where price moved
    at least `level` percent away on both sides.

    Within `tolerance` of the extremum → label = True.

    Args:
        close: Close price array.
        level: Minimum price swing to qualify as extremum (0.02 = 2%).
        tolerance: Width of zone around extremum (0.005 = 0.5%).

    Returns:
        Tuple of (top_labels, bot_labels) — boolean arrays.
        top_labels[i] = True if bar i is near a local top.
        bot_labels[i] = True if bar i is near a local bottom.
    """
    close = np.asarray(close, dtype=np.float64)
    n = len(close)
    top_labels = np.zeros(n, dtype=bool)
    bot_labels = np.zeros(n, dtype=bool)

    if n < 5:
        return top_labels, bot_labels

    # Find extrema using level filter
    extrema: list[Extremum] = []

    # Track running high and low
    high_price = close[0]
    high_idx = 0
    low_price = close[0]
    low_idx = 0

    for i in range(1, n):
        # Update running extremes
        if close[i] > high_price:
            high_price = close[i]
            high_idx = i
        if close[i] < low_price:
            low_price = close[i]
            low_idx = i

        # Check if price dropped enough from high → confirm top
        if high_price > 0 and (high_price - close[i]) / high_price >= level:
            extrema.append(Extremum(high_idx, float(high_price), "top", level))
            # Reset: start tracking from this low
            low_price = close[i]
            low_idx = i
            high_price = close[i]
            high_idx = i

        # Check if price rose enough from low → confirm bot
        elif low_price > 0 and (close[i] - low_price) / low_price >= level:
            extrema.append(Extremum(low_idx, float(low_price), "bot", level))
            # Reset: start tracking from this high
            high_price = close[i]
            high_idx = i
            low_price = close[i]
            low_idx = i

    # Apply tolerance zones around extrema
    for ext in extrema:
        price = ext.price
        for j in range(max(0, ext.index - 1), min(n, ext.index + 2)):
            if abs(close[j] - price) / price <= tolerance:
                if ext.type == "top":
                    top_labels[j] = True
                else:
                    bot_labels[j] = True

    return top_labels, bot_labels


def generate_topbot_extrema(
    close: np.ndarray,
    level: float = 0.02,
) -> list[Extremum]:
    """Return list of detected extrema (for analysis/plotting).

    Args:
        close: Close price array.
        level: Minimum swing size (0.02 = 2%).

    Returns:
        List of Extremum objects.
    """
    close = np.asarray(close, dtype=np.float64)
    n = len(close)
    if n < 5:
        return []

    extrema: list[Extremum] = []
    hi = close[0]
    hi_idx = 0
    lo = close[0]
    lo_idx = 0

    for i in range(1, n):
        if close[i] > hi:
            hi = close[i]
            hi_idx = i
        if close[i] < lo:
            lo = close[i]
            lo_idx = i

        if hi > 0 and (hi - close[i]) / hi >= level:
            extrema.append(Extremum(hi_idx, float(hi), "top", level))
            lo = close[i]
            lo_idx = i
            hi = close[i]
            hi_idx = i
        elif lo > 0 and (close[i] - lo) / lo >= level:
            extrema.append(Extremum(lo_idx, float(lo), "bot", level))
            hi = close[i]
            hi_idx = i
            lo = close[i]
            lo_idx = i

    return extrema
