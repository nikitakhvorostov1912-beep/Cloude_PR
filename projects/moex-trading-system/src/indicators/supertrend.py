"""SuperTrend indicator — trend-following with ATR-based bands.

Adapted from jesse-ai/jesse indicators/supertrend.py (MIT License).
Standalone NumPy implementation, no numba required.

Signal logic:
- trend > 0 (= lower band): BULLISH → price is above SuperTrend
- trend < 0 (= upper band): BEARISH → price is below SuperTrend
- changed == 1: trend direction flipped on this bar
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SuperTrendResult:
    """SuperTrend indicator output."""
    trend: np.ndarray       # SuperTrend line values
    direction: np.ndarray   # +1 = bullish, -1 = bearish
    changed: np.ndarray     # 1 = direction changed on this bar, 0 = no change


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Average True Range using Wilder's smoothing."""
    n = len(close)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    atr_arr = np.full(n, np.nan)
    atr_arr[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        atr_arr[i] = (atr_arr[i - 1] * (period - 1) + tr[i]) / period
    return atr_arr


def supertrend(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 10,
    factor: float = 3.0,
) -> SuperTrendResult:
    """Calculate SuperTrend indicator.

    Args:
        high: Array of high prices.
        low: Array of low prices.
        close: Array of close prices.
        period: ATR period (default 10).
        factor: ATR multiplier for band width (default 3.0).

    Returns:
        SuperTrendResult with trend, direction, and changed arrays.
    """
    n = len(close)
    atr_vals = _atr(high, low, close, period)

    mid = (high + low) / 2.0
    upper_basic = mid + factor * atr_vals
    lower_basic = mid - factor * atr_vals

    upper_band = upper_basic.copy()
    lower_band = lower_basic.copy()
    st = np.zeros(n)
    direction = np.ones(n)  # +1 bullish
    changed = np.zeros(n, dtype=np.int8)

    # Initialize at period-1
    idx = period - 1
    st[idx] = upper_band[idx] if close[idx] <= upper_band[idx] else lower_band[idx]
    direction[idx] = -1 if close[idx] <= upper_band[idx] else 1

    for i in range(period, n):
        p = i - 1

        # Update bands
        if close[p] <= upper_band[p]:
            upper_band[i] = min(upper_basic[i], upper_band[p])
        else:
            upper_band[i] = upper_basic[i]

        if close[p] >= lower_band[p]:
            lower_band[i] = max(lower_basic[i], lower_band[p])
        else:
            lower_band[i] = lower_basic[i]

        # Determine trend
        if st[p] == upper_band[p]:  # was bearish
            if close[i] <= upper_band[i]:
                st[i] = upper_band[i]
                direction[i] = -1
                changed[i] = 0
            else:
                st[i] = lower_band[i]
                direction[i] = 1
                changed[i] = 1
        else:  # was bullish
            if close[i] >= lower_band[i]:
                st[i] = lower_band[i]
                direction[i] = 1
                changed[i] = 0
            else:
                st[i] = upper_band[i]
                direction[i] = -1
                changed[i] = 1

    return SuperTrendResult(trend=st, direction=direction, changed=changed)
