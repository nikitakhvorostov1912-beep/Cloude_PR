"""TTM Squeeze Momentum Indicator (LazyBear version).

Adapted from jesse-ai/jesse indicators/squeeze_momentum.py (MIT License).
Standalone NumPy implementation.

The squeeze detects periods of low volatility (Bollinger Bands inside Keltner Channels).
When the squeeze fires (releases), a momentum burst is expected.

squeeze values: -1 = squeeze ON, 0 = no squeeze, 1 = squeeze OFF (fired)
momentum: positive = bullish, negative = bearish
momentum_signal: 1 = increasing bullish, 2 = decreasing bullish,
                -1 = increasing bearish, -2 = decreasing bearish
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SqueezeResult:
    """Squeeze Momentum indicator output."""
    squeeze: np.ndarray          # -1/0/1 squeeze state per bar
    momentum: np.ndarray         # momentum value per bar
    momentum_signal: np.ndarray  # 1/2/-1/-2 signal per bar


def _sma(values: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    result = np.full_like(values, np.nan, dtype=float)
    if len(values) < period:
        return result
    cumsum = np.cumsum(values)
    cumsum[period:] = cumsum[period:] - cumsum[:-period]
    result[period - 1:] = cumsum[period - 1:] / period
    return result


def _stddev(values: np.ndarray, period: int) -> np.ndarray:
    """Rolling standard deviation."""
    result = np.full_like(values, np.nan, dtype=float)
    for i in range(period - 1, len(values)):
        result[i] = np.std(values[i - period + 1:i + 1], ddof=0)
    return result


def _true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """True range."""
    n = len(close)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return tr


def _highest(values: np.ndarray, period: int) -> np.ndarray:
    """Rolling highest value."""
    result = np.full_like(values, np.nan, dtype=float)
    for i in range(period - 1, len(values)):
        result[i] = np.max(values[i - period + 1:i + 1])
    return result


def _lowest(values: np.ndarray, period: int) -> np.ndarray:
    """Rolling lowest value."""
    result = np.full_like(values, np.nan, dtype=float)
    for i in range(period - 1, len(values)):
        result[i] = np.min(values[i - period + 1:i + 1])
    return result


def _linreg(values: np.ndarray, period: int) -> np.ndarray:
    """Linear regression value (endpoint of fitted line)."""
    result = np.full_like(values, np.nan, dtype=float)
    x = np.arange(period, dtype=float)
    x_mean = x.mean()
    ss_xx = ((x - x_mean) ** 2).sum()
    for i in range(period - 1, len(values)):
        y = values[i - period + 1:i + 1]
        y_mean = np.nanmean(y)
        ss_xy = ((x - x_mean) * (y - y_mean)).sum()
        slope = ss_xy / ss_xx if ss_xx != 0 else 0
        intercept = y_mean - slope * x_mean
        result[i] = intercept + slope * (period - 1)
    return result


def squeeze_momentum(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    length: int = 20,
    bb_mult: float = 2.0,
    kc_mult: float = 1.5,
) -> SqueezeResult:
    """Calculate TTM Squeeze Momentum indicator.

    Args:
        high: Array of high prices.
        low: Array of low prices.
        close: Array of close prices.
        length: Lookback period for BB and KC (default 20).
        bb_mult: Bollinger Bands multiplier (default 2.0).
        kc_mult: Keltner Channel multiplier (default 1.5).

    Returns:
        SqueezeResult with squeeze state, momentum, and signal arrays.
    """
    n = len(close)

    # Bollinger Bands
    basis = _sma(close, length)
    dev = _stddev(close, length) * bb_mult
    upper_bb = basis + dev
    lower_bb = basis - dev

    # Keltner Channel
    ma = _sma(close, length)
    tr = _true_range(high, low, close)
    range_ma = _sma(tr, length)
    upper_kc = ma + range_ma * kc_mult
    lower_kc = ma - range_ma * kc_mult

    # Squeeze detection
    squeeze = np.zeros(n, dtype=int)
    for i in range(n):
        if np.isnan(lower_bb[i]) or np.isnan(lower_kc[i]):
            continue
        sqz_on = (lower_bb[i] > lower_kc[i]) and (upper_bb[i] < upper_kc[i])
        sqz_off = (lower_bb[i] < lower_kc[i]) and (upper_bb[i] > upper_kc[i])
        if sqz_on:
            squeeze[i] = -1
        elif sqz_off:
            squeeze[i] = 1

    # Momentum
    highs = np.nan_to_num(_highest(high, length), nan=0.0)
    lows = np.nan_to_num(_lowest(low, length), nan=0.0)
    sma_arr = np.nan_to_num(_sma(close, length), nan=0.0)

    raw_momentum = np.zeros(n)
    for i in range(n):
        raw_momentum[i] = close[i] - ((highs[i] + lows[i]) / 2 + sma_arr[i]) / 2

    momentum = _linreg(raw_momentum, length)

    # Signal: direction + acceleration
    signal = np.zeros(n, dtype=int)
    for i in range(1, n):
        if np.isnan(momentum[i]):
            continue
        if momentum[i] > 0:
            signal[i] = 1 if momentum[i] > momentum[i - 1] else 2
        else:
            signal[i] = -1 if momentum[i] < momentum[i - 1] else -2

    return SqueezeResult(squeeze=squeeze, momentum=momentum, momentum_signal=signal)
