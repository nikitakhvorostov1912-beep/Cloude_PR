"""Trend quality and gap detection indicators.

Inspired by bbfamily/abu TLineBu (GPL-3 — formulas only, code from scratch).

Indicators:
- path_distance_ratio: measures "purity" of a trend (1.0 = perfect line)
- gap_detector: identifies significant price gaps with volume confirmation
- polynomial_complexity: market chaos level (1 = trend, 4+ = chaotic)

Usage:
    from src.indicators.trend_quality import (
        path_distance_ratio, gap_detector, polynomial_complexity,
    )

    pdr = path_distance_ratio(close, window=20)
    gaps = gap_detector(open, high, low, close, volume)
    complexity = polynomial_complexity(close, window=20)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def path_distance_ratio(
    close: np.ndarray,
    window: int = 20,
) -> np.ndarray:
    """Path/Distance Ratio — measures trend purity.

    Ratio of total path traveled to straight-line displacement.

    path = sum(|close[i] - close[i-1]|) over window
    distance = |close[end] - close[start]|
    ratio = path / distance  (1.0 = perfectly linear, higher = noisier)

    For normalized comparison across instruments:
    Uses price-normalized version: sqrt(dx² + dy²) where dx = window length.

    Args:
        close: Close price array.
        window: Rolling window (default 20).

    Returns:
        Array of PDR values. 1.0 = pure trend, >3 = chaotic.
    """
    close = np.asarray(close, dtype=np.float64)
    n = len(close)
    result = np.full(n, np.nan)

    for i in range(window, n):
        segment = close[i - window:i + 1]
        # Path: sum of all moves
        path = np.sum(np.abs(np.diff(segment)))
        # Displacement: straight line from start to end
        displacement = abs(segment[-1] - segment[0])

        if displacement > 0:
            result[i] = path / displacement
        else:
            result[i] = float("inf") if path > 0 else 1.0

    return result


@dataclass(frozen=True)
class GapEvent:
    """A detected gap event.

    Attributes:
        index: Bar index where gap occurred.
        direction: "up" or "down".
        gap_size: Absolute gap size in price units.
        gap_pct: Gap as percentage of price.
        power: Normalized gap power (gap / threshold).
        volume_confirmed: Whether volume exceeded average.
    """

    index: int
    direction: str
    gap_size: float
    gap_pct: float
    power: float
    volume_confirmed: bool


def gap_detector(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    avg_window: int = 21,
    volume_mult: float = 1.0,
    gap_factor: float = 1.5,
) -> list[GapEvent]:
    """Detect significant price gaps with 3-level filter.

    Filter 1: |change| > avg(|change|) over avg_window
    Filter 2: volume > avg(volume) * volume_mult
    Filter 3: gap > avg_change * gap_factor

    gap_power = gap_size / threshold — normalized strength.

    Args:
        open_, high, low, close, volume: OHLCV arrays.
        avg_window: Window for average calculations (default 21).
        volume_mult: Volume threshold multiplier (default 1.0).
        gap_factor: Gap threshold multiplier (default 1.5).

    Returns:
        List of GapEvent objects.
    """
    open_ = np.asarray(open_, dtype=np.float64)
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)
    volume = np.asarray(volume, dtype=np.float64)
    n = len(close)

    if n < avg_window + 2:
        return []

    gaps: list[GapEvent] = []

    for i in range(avg_window + 1, n):
        start = max(0, i - avg_window)
        pchange = np.abs(np.diff(close[start:i]))
        avg_change = pchange.mean() if len(pchange) > 0 else 0
        avg_vol = volume[start:i].mean()

        if avg_change == 0 or close[i - 1] == 0:
            continue

        # Current bar change
        change = abs(close[i] - close[i - 1])
        change_pct = change / close[i - 1]

        # Filter 1: change > average change
        if change <= avg_change:
            continue

        # Filter 2: volume > average volume
        vol_confirmed = volume[i] > avg_vol * volume_mult

        # Filter 3: gap size
        threshold = avg_change * gap_factor
        if change <= threshold:
            continue

        # Direction
        if close[i] > close[i - 1]:
            direction = "up"
            gap_size = low[i] - close[i - 1] if low[i] > close[i - 1] else change
        else:
            direction = "down"
            gap_size = close[i - 1] - high[i] if high[i] < close[i - 1] else change

        power = change / threshold if threshold > 0 else 0

        gaps.append(GapEvent(
            index=i,
            direction=direction,
            gap_size=round(abs(gap_size), 4),
            gap_pct=round(change_pct * 100, 4),
            power=round(power, 4),
            volume_confirmed=vol_confirmed,
        ))

    return gaps


def gap_detector_array(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    avg_window: int = 21,
    gap_factor: float = 1.5,
) -> np.ndarray:
    """Gap power as array (0 = no gap, positive = up gap, negative = down).

    Convenience wrapper for use as indicator in vectorized pipelines.
    """
    n = len(close)
    result = np.zeros(n)
    gaps = gap_detector(open_, high, low, close, volume, avg_window, gap_factor=gap_factor)
    for g in gaps:
        sign = 1.0 if g.direction == "up" else -1.0
        result[g.index] = sign * g.power
    return result


def polynomial_complexity(
    close: np.ndarray,
    window: int = 20,
    max_degree: int = 6,
    improvement_threshold: float = 0.05,
) -> np.ndarray:
    """Polynomial complexity — discrete measure of market chaos.

    Finds minimum polynomial degree that "adequately" fits price over window.
    1 = clean linear trend, 2 = U/V shape, 3+ = complex, 5+ = chaotic.

    Algorithm: for degrees 1..max, fit polynomial, check if R² improves
    by at least improvement_threshold over previous degree.
    First degree where improvement < threshold = complexity.

    Args:
        close: Close price array.
        window: Rolling window (default 20).
        max_degree: Maximum polynomial degree (default 6).
        improvement_threshold: Min R² improvement to continue (default 0.05).

    Returns:
        Array of complexity values (1 to max_degree).
    """
    close = np.asarray(close, dtype=np.float64)
    n = len(close)
    result = np.ones(n)  # default = 1 (simplest)

    for i in range(window, n):
        segment = close[i - window:i]
        x = np.arange(window, dtype=np.float64)
        ss_tot = np.sum((segment - segment.mean()) ** 2)
        if ss_tot == 0:
            result[i] = 1
            continue

        prev_r2 = 0.0
        best_degree = 1

        for deg in range(1, max_degree + 1):
            try:
                coeffs = np.polyfit(x, segment, deg)
                fitted = np.polyval(coeffs, x)
                ss_res = np.sum((segment - fitted) ** 2)
                r2 = 1.0 - ss_res / ss_tot
                improvement = r2 - prev_r2

                if improvement < improvement_threshold and deg > 1:
                    break
                best_degree = deg
                prev_r2 = r2
            except np.linalg.LinAlgError:
                break

        result[i] = best_degree

    return result
