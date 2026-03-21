"""Damiani Volatmeter — volatility regime detector.

Adapted from jesse-ai/jesse indicators/damiani_volatmeter.py (MIT License).
Standalone NumPy + SciPy implementation.

vol > threshold AND vol > anti → high volatility regime (trade)
vol < threshold OR vol < anti → low volatility regime (avoid)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DamianiResult:
    """Damiani Volatmeter output."""
    vol: np.ndarray    # volatility line
    anti: np.ndarray   # anti-volatility (threshold) line


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """ATR using Wilder's EMA smoothing."""
    n = len(close)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr_arr = np.full(n, np.nan)
    if n < period:
        atr_arr[-1] = np.mean(tr)
        return atr_arr
    atr_arr[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        atr_arr[i] = (atr_arr[i - 1] * (period - 1) + tr[i]) / period
    return atr_arr


def _rolling_std(values: np.ndarray, period: int) -> np.ndarray:
    """Rolling standard deviation."""
    result = np.full_like(values, np.nan, dtype=float)
    for i in range(period - 1, len(values)):
        result[i] = np.std(values[i - period + 1:i + 1], ddof=0)
    return result


def damiani_volatmeter(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    vis_atr: int = 13,
    vis_std: int = 20,
    sed_atr: int = 40,
    sed_std: int = 100,
    threshold: float = 1.4,
) -> DamianiResult:
    """Calculate Damiani Volatmeter.

    Args:
        high: High prices.
        low: Low prices.
        close: Close prices.
        vis_atr: Fast ATR period (default 13).
        vis_std: Fast StdDev period (default 20).
        sed_atr: Slow ATR period (default 40).
        sed_std: Slow StdDev period (default 100).
        threshold: Anti-volatility threshold (default 1.4).

    Returns:
        DamianiResult with vol and anti arrays.
    """
    n = len(close)
    atrvis = _atr(high, low, close, vis_atr)
    atrsed = _atr(high, low, close, sed_atr)

    # Vol = ATR_fast / ATR_slow with lag filter
    lag_s = 0.5
    raw = np.zeros(n)
    for i in range(n):
        if not np.isnan(atrvis[i]) and not np.isnan(atrsed[i]) and atrsed[i] != 0:
            raw[i] = atrvis[i] / atrsed[i]

    # Apply recursive lag filter: vol[i] = raw[i] + lag_s * vol[i-1] - lag_s * vol[i-3]
    vol = np.zeros(n)
    for i in range(n):
        v1 = vol[i - 1] if i >= 1 else 0.0
        v3 = vol[i - 3] if i >= 3 else 0.0
        vol[i] = raw[i] + lag_s * v1 - lag_s * v3

    # Anti = threshold - StdDev_fast / StdDev_slow
    std_vis = _rolling_std(close, vis_std)
    std_sed = _rolling_std(close, sed_std)

    anti = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(std_vis[i]) and not np.isnan(std_sed[i]) and std_sed[i] != 0:
            anti[i] = threshold - std_vis[i] / std_sed[i]

    return DamianiResult(vol=vol, anti=anti)
