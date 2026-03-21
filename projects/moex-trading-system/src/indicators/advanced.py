"""Advanced indicators ported from QuantConnect LEAN formulas (Apache 2.0).

Written from scratch in Python/NumPy. Not copied — only formulas referenced.

Indicators:
- ChandeKrollStop: 2-pass ATR trailing stop (auto stop-loss levels)
- ChoppinessIndex: trend vs chop detector (38.2=trend, 61.8=chop)
- SchaffTrendCycle: 3-layer stochastic MACD (faster, less lag)
- AugenPriceSpike: normalized price spike in sigma units
- RogersSatchellVolatility: drift-adjusted volatility estimator

Usage:
    from src.indicators.advanced import (
        chande_kroll_stop, choppiness_index, schaff_trend_cycle,
        augen_price_spike, rogers_satchell_volatility,
    )
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wilder_ema(data: np.ndarray, period: int) -> np.ndarray:
    """Wilder's smoothing (EMA with alpha = 1/period)."""
    alpha = 1.0 / period
    result = np.empty_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """Standard EMA with alpha = 2/(period+1)."""
    alpha = 2.0 / (period + 1)
    result = np.empty_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def _true_range(
    high: np.ndarray, low: np.ndarray, close: np.ndarray,
) -> np.ndarray:
    """True Range array."""
    n = len(high)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    return tr


def _rolling_max(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling maximum."""
    n = len(data)
    result = np.empty(n)
    for i in range(n):
        start = max(0, i - period + 1)
        result[i] = np.max(data[start:i + 1])
    return result


def _rolling_min(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling minimum."""
    n = len(data)
    result = np.empty(n)
    for i in range(n):
        start = max(0, i - period + 1)
        result[i] = np.min(data[start:i + 1])
    return result


def _rolling_sum(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling sum."""
    n = len(data)
    result = np.empty(n)
    cumsum = np.cumsum(data)
    for i in range(n):
        if i < period:
            result[i] = cumsum[i]
        else:
            result[i] = cumsum[i] - cumsum[i - period]
    return result


def _rolling_std(data: np.ndarray, period: int) -> np.ndarray:
    """Rolling sample standard deviation."""
    n = len(data)
    result = np.empty(n)
    for i in range(n):
        start = max(0, i - period + 1)
        window = data[start:i + 1]
        result[i] = float(np.std(window, ddof=1)) if len(window) > 1 else 0.0
    return result


def _sma(data: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    return _rolling_sum(data, period) / np.minimum(
        np.arange(1, len(data) + 1), period
    )


# ---------------------------------------------------------------------------
# ChandeKrollStop
# ---------------------------------------------------------------------------


@dataclass
class ChandeKrollResult:
    """ChandeKrollStop output.

    Attributes:
        stop_long: Support line — stop for long positions (buy when above).
        stop_short: Resistance line — stop for short positions (sell when below).
        signal: +1 long (close > stop_short), -1 short (close < stop_long), 0 neutral.
    """

    stop_long: np.ndarray
    stop_short: np.ndarray
    signal: np.ndarray


def chande_kroll_stop(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr_period: int = 10,
    atr_mult: float = 1.5,
    stop_period: int = 9,
) -> ChandeKrollResult:
    """Chande Kroll Stop — 2-pass ATR trailing stop indicator.

    Pass 1: first_high_stop = highest(H, atr_period) - atr_mult * ATR
             first_low_stop  = lowest(L, atr_period) + atr_mult * ATR
    Pass 2: stop_short = highest(first_high_stop, stop_period)
             stop_long  = lowest(first_low_stop, stop_period)

    Signal: close > stop_short → long (+1), close < stop_long → short (-1).

    Args:
        high, low, close: OHLC arrays.
        atr_period: ATR and first-pass lookback (default 10).
        atr_mult: ATR multiplier (default 1.5).
        stop_period: Second-pass smoothing period (default 9).
    """
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)

    tr = _true_range(high, low, close)
    atr = _wilder_ema(tr, atr_period)

    # Pass 1
    highest_high = _rolling_max(high, atr_period)
    lowest_low = _rolling_min(low, atr_period)
    first_high_stop = highest_high - atr_mult * atr
    first_low_stop = lowest_low + atr_mult * atr

    # Pass 2
    stop_short = _rolling_max(first_high_stop, stop_period)
    stop_long = _rolling_min(first_low_stop, stop_period)

    # Signal
    signal = np.where(close > stop_short, 1.0, np.where(close < stop_long, -1.0, 0.0))

    return ChandeKrollResult(stop_long=stop_long, stop_short=stop_short, signal=signal)


# ---------------------------------------------------------------------------
# ChoppinessIndex
# ---------------------------------------------------------------------------


def choppiness_index(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """Choppiness Index — trend vs. consolidation detector.

    Formula: CHOP = 100 * log10(sum(TR, n) / (maxH(n) - minL(n))) / log10(n)

    Range: ~38.2 (strong trend) to ~61.8 (choppy/ranging).
    These thresholds are Fibonacci golden ratios, not arbitrary.

    Args:
        high, low, close: OHLC arrays.
        period: Lookback period (default 14).

    Returns:
        Array of choppiness values. Low = trending, high = choppy.
    """
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)
    n = len(high)

    tr = _true_range(high, low, close)
    sum_tr = _rolling_sum(tr, period)
    max_high = _rolling_max(high, period)
    min_low = _rolling_min(low, period)

    hl_range = max_high - min_low
    log_n = np.log10(period)

    result = np.zeros(n)
    for i in range(n):
        if hl_range[i] > 0 and log_n > 0:
            result[i] = 100.0 * np.log10(sum_tr[i] / hl_range[i]) / log_n
        else:
            result[i] = 100.0  # flat = max choppiness

    return result


# ---------------------------------------------------------------------------
# SchaffTrendCycle
# ---------------------------------------------------------------------------


def schaff_trend_cycle(
    close: np.ndarray,
    cycle_period: int = 10,
    fast_period: int = 23,
    slow_period: int = 50,
) -> np.ndarray:
    """Schaff Trend Cycle — 3-layer stochastic smoothing of MACD.

    Layer 1: MACD = EMA(fast) - EMA(slow)
    Layer 2: Stochastic of MACD over cycle_period, smoothed by SMA(3)
    Layer 3: Stochastic of Layer 2, smoothed by SMA(3) = STC

    Range: 0-100. <25 = oversold (bullish), >75 = overbought (bearish).
    Faster than MACD due to double stochastic normalization.

    Args:
        close: Close price array.
        cycle_period: Stochastic lookback (default 10).
        fast_period: Fast EMA period (default 23).
        slow_period: Slow EMA period (default 50).
    """
    close = np.asarray(close, dtype=np.float64)

    # Layer 1: MACD line
    fast_ema = _ema(close, fast_period)
    slow_ema = _ema(close, slow_period)
    macd = fast_ema - slow_ema

    # Layer 2: Stochastic of MACD
    macd_max = _rolling_max(macd, cycle_period)
    macd_min = _rolling_min(macd, cycle_period)
    macd_range = macd_max - macd_min
    safe_macd_range = np.where(macd_range > 0, macd_range, 1.0)

    pf = np.where(macd_range > 0, (macd - macd_min) / safe_macd_range * 100, 50.0)
    pf_smooth = _sma(pf, 3)  # %D1

    # Layer 3: Stochastic of %D1
    pf_max = _rolling_max(pf_smooth, cycle_period)
    pf_min = _rolling_min(pf_smooth, cycle_period)
    pf_range = pf_max - pf_min
    safe_pf_range = np.where(pf_range > 0, pf_range, 1.0)

    pff = np.where(pf_range > 0, (pf_smooth - pf_min) / safe_pf_range * 100, 50.0)
    stc = _sma(pff, 3)  # STC

    return np.clip(stc, 0.0, 100.0)


# ---------------------------------------------------------------------------
# AugenPriceSpike
# ---------------------------------------------------------------------------


def augen_price_spike(
    close: np.ndarray,
    period: int = 3,
) -> np.ndarray:
    """Augen Price Spike — normalized price movement in sigma units.

    From Jeff Augen "The Volatility Edge in Options Trading".

    Formula: spike = (C_t - C_{t-1}) / (std(log_returns, period) * C_{t-1})

    Values > +2σ = abnormal spike up, < -2σ = abnormal spike down.
    Useful for event detection (central bank decisions, earnings).

    Args:
        close: Close price array.
        period: Lookback for rolling std of log returns (default 3).
    """
    close = np.asarray(close, dtype=np.float64)
    n = len(close)

    result = np.zeros(n)
    if n < period + 2:
        return result

    # Log returns: ln(C_{t-1} / C_{t-2})
    log_ret = np.zeros(n)
    for i in range(2, n):
        if close[i - 2] > 0:
            log_ret[i] = np.log(close[i - 1] / close[i - 2])

    std_lr = _rolling_std(log_ret, period)

    for i in range(period + 1, n):
        if std_lr[i] > 0 and close[i - 1] > 0:
            result[i] = (close[i] - close[i - 1]) / (std_lr[i] * close[i - 1])

    return result


# ---------------------------------------------------------------------------
# RogersSatchellVolatility
# ---------------------------------------------------------------------------


def rogers_satchell_volatility(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 20,
) -> np.ndarray:
    """Rogers-Satchell volatility estimator — accounts for drift.

    Superior to close-to-close, Parkinson, and Garman-Klass estimators
    when the underlying has nonzero mean returns (drift).

    Formula per bar: RS_i = ln(H/C)*ln(H/O) + ln(L/C)*ln(L/O)
    RSV = sqrt(rolling_mean(RS_i, period))

    Useful for options pricing where drift-adjusted vol is needed.

    Args:
        open_, high, low, close: OHLC arrays.
        period: Rolling window (default 20).
    """
    open_ = np.asarray(open_, dtype=np.float64)
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)
    n = len(high)

    # Per-bar RS component
    rs = np.zeros(n)
    for i in range(n):
        if close[i] > 0 and open_[i] > 0 and high[i] > 0 and low[i] > 0:
            ln_hc = np.log(high[i] / close[i])
            ln_ho = np.log(high[i] / open_[i])
            ln_lc = np.log(low[i] / close[i])
            ln_lo = np.log(low[i] / open_[i])
            rs[i] = ln_hc * ln_ho + ln_lc * ln_lo

    # Rolling mean of RS
    rs_mean = _sma(rs, period)

    # sqrt, handling negative values (rare but possible with noisy data)
    result = np.where(rs_mean > 0, np.sqrt(rs_mean), 0.0)
    return result
