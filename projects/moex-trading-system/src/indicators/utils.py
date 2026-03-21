"""Strategy utility functions for signal detection.

Inspired by backtesting.py lib.py (AGPL — written from scratch).
Common building blocks for trading strategies: crossover detection,
bars counting, quantile ranking.
"""
from __future__ import annotations

from typing import Sequence, Union

import numpy as np


def crossover(series1: Sequence, series2: Union[Sequence, float]) -> bool:
    """Return True if series1 just crossed ABOVE series2.

    Compares the last two values: series1 was below series2, now above.

    Args:
        series1: Price or indicator array.
        series2: Price, indicator array, or scalar threshold.

    Returns:
        True if crossover occurred on the last bar.

    Example:
        >>> crossover(fast_ema, slow_ema)  # Golden cross
        True
    """
    s1 = _last_two(series1)
    s2 = _last_two(series2)
    if s1 is None or s2 is None:
        return False
    return s1[0] < s2[0] and s1[1] > s2[1]


def crossunder(series1: Sequence, series2: Union[Sequence, float]) -> bool:
    """Return True if series1 just crossed BELOW series2.

    Args:
        series1: Price or indicator array.
        series2: Price, indicator array, or scalar threshold.

    Returns:
        True if crossunder occurred on the last bar.

    Example:
        >>> crossunder(fast_ema, slow_ema)  # Death cross
        True
    """
    return crossover(series2, series1)


def cross(series1: Sequence, series2: Union[Sequence, float]) -> bool:
    """Return True if series1 and series2 just crossed in either direction.

    Args:
        series1: Price or indicator array.
        series2: Price, indicator array, or scalar threshold.

    Returns:
        True if any crossover or crossunder occurred.
    """
    return crossover(series1, series2) or crossover(series2, series1)


def barssince(condition: Sequence[bool], default: int = -1) -> int:
    """Return number of bars since condition was last True.

    Scans from most recent bar backward.

    Args:
        condition: Boolean array (e.g., close > sma).
        default: Value to return if condition was never True.

    Returns:
        Number of bars since last True, or default.

    Example:
        >>> barssince(close > open)  # How many bars since last bullish candle?
        3
    """
    for i in range(len(condition) - 1, -1, -1):
        if condition[i]:
            return len(condition) - 1 - i
    return default


def quantile_rank(series: Sequence, lookback: int | None = None) -> float:
    """Return quantile rank (0-1) of the last value relative to prior values.

    Useful for detecting if current value is historically high/low.

    Args:
        series: Value array.
        lookback: Optional window size. None = use entire history.

    Returns:
        Float in [0, 1]. 0.95 means current value is in the top 5%.

    Example:
        >>> quantile_rank(rsi_values)  # Is RSI historically high?
        0.87
    """
    arr = np.asarray(series, dtype=float)
    if len(arr) < 2:
        return 0.5
    if lookback is not None:
        arr = arr[-lookback:]
    last = arr[-1]
    prior = arr[:-1]
    if len(prior) == 0:
        return 0.5
    return float(np.mean(prior < last))


def highest(series: Sequence, period: int) -> float:
    """Return highest value in the last `period` bars (inclusive of current).

    Args:
        series: Value array.
        period: Lookback window.

    Returns:
        Maximum value in window.
    """
    arr = np.asarray(series, dtype=float)
    return float(np.nanmax(arr[-period:])) if len(arr) >= period else float(np.nanmax(arr))


def lowest(series: Sequence, period: int) -> float:
    """Return lowest value in the last `period` bars (inclusive of current).

    Args:
        series: Value array.
        period: Lookback window.

    Returns:
        Minimum value in window.
    """
    arr = np.asarray(series, dtype=float)
    return float(np.nanmin(arr[-period:])) if len(arr) >= period else float(np.nanmin(arr))


def _last_two(series: Union[Sequence, float]) -> tuple[float, float] | None:
    """Extract last two values from series or scalar."""
    if isinstance(series, (int, float)):
        return (series, series)
    try:
        if hasattr(series, "values"):
            series = series.values
        return (float(series[-2]), float(series[-1]))
    except (IndexError, TypeError):
        return None
