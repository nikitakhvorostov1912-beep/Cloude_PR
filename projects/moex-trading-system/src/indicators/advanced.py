"""Advanced indicators ported from QuantConnect LEAN formulas (Apache 2.0).

Written from scratch in Python/NumPy. Not copied — only formulas referenced.

Indicators:
- ChandeKrollStop: 2-pass ATR trailing stop (auto stop-loss levels)
- ChoppinessIndex: trend vs chop detector (38.2=trend, 61.8=chop)
- SchaffTrendCycle: 3-layer stochastic MACD (faster, less lag)
- AugenPriceSpike: normalized price spike in sigma units
- RogersSatchellVolatility: drift-adjusted volatility estimator
- ZigZag: pivot point detection state machine
- KlingerVolumeOscillator: volume-force trend confirmation
- RelativeVigorIndex: close-open / high-low momentum quality

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


# ---------------------------------------------------------------------------
# ZigZag — pivot point detection
# ---------------------------------------------------------------------------


@dataclass
class ZigZagResult:
    """ZigZag output.

    Attributes:
        pivots: Array with non-zero values at pivot points (price at pivot).
        pivot_types: +1 at peak, -1 at trough, 0 elsewhere.
        last_pivot_price: Most recent pivot price.
        last_pivot_type: +1 (peak) or -1 (trough).
    """

    pivots: np.ndarray
    pivot_types: np.ndarray
    last_pivot_price: float
    last_pivot_type: int


def zigzag(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    sensitivity: float = 0.05,
    min_trend_bars: int = 3,
) -> ZigZagResult:
    """ZigZag indicator — pivot point detection state machine.

    Identifies significant swing highs and lows by filtering out
    moves smaller than sensitivity %. Useful for S/R detection,
    wave pattern recognition, and trend structure analysis.

    Algorithm:
        If last pivot was a Low:
            New High pivot if H >= lastLow * (1+sensitivity) AND bars >= min_trend
        If last pivot was a High:
            New Low pivot if L <= lastHigh * (1-sensitivity)

    Args:
        high, low, close: OHLC arrays.
        sensitivity: Minimum move to qualify as pivot (0.05 = 5%).
        min_trend_bars: Minimum bars between pivots.
    """
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)
    n = len(high)

    pivots = np.zeros(n)
    pivot_types = np.zeros(n, dtype=int)

    if n < 2:
        return ZigZagResult(pivots, pivot_types, 0.0, 0)

    # Initialize: first bar is a pivot (direction TBD)
    last_pivot_price = close[0]
    last_pivot_idx = 0
    last_pivot_was_high = True  # start looking for low

    for i in range(1, n):
        bars_since = i - last_pivot_idx

        if last_pivot_was_high:
            # Looking for a low pivot
            if low[i] <= last_pivot_price * (1 - sensitivity):
                pivots[i] = low[i]
                pivot_types[i] = -1
                last_pivot_price = low[i]
                last_pivot_idx = i
                last_pivot_was_high = False
            elif high[i] > last_pivot_price:
                # Update the existing high pivot
                pivots[last_pivot_idx] = 0
                pivot_types[last_pivot_idx] = 0
                pivots[i] = high[i]
                pivot_types[i] = 1
                last_pivot_price = high[i]
                last_pivot_idx = i
        else:
            # Looking for a high pivot
            if (
                high[i] >= last_pivot_price * (1 + sensitivity)
                and bars_since >= min_trend_bars
            ):
                pivots[i] = high[i]
                pivot_types[i] = 1
                last_pivot_price = high[i]
                last_pivot_idx = i
                last_pivot_was_high = True
            elif low[i] < last_pivot_price:
                # Update the existing low pivot
                pivots[last_pivot_idx] = 0
                pivot_types[last_pivot_idx] = 0
                pivots[i] = low[i]
                pivot_types[i] = -1
                last_pivot_price = low[i]
                last_pivot_idx = i

    last_type = 1 if last_pivot_was_high else -1
    return ZigZagResult(pivots, pivot_types, last_pivot_price, last_type)


# ---------------------------------------------------------------------------
# KlingerVolumeOscillator
# ---------------------------------------------------------------------------


def klinger_volume_oscillator(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    fast_period: int = 34,
    slow_period: int = 55,
    signal_period: int = 13,
) -> tuple[np.ndarray, np.ndarray]:
    """Klinger Volume Oscillator — volume-force trend confirmation.

    Measures the difference between buying and selling pressure
    based on volume and price movement.

    Volume Force formula:
        trend = sign(TP_t - TP_{t-1}) where TP = H + L + C
        DM = H - L (daily movement)
        CM = CM_{t-1} + DM if trend unchanged, else DM_{t-1} + DM
        VF = Volume * |2*DM/CM - 1| * trend * 100
        KVO = EMA(VF, fast) - EMA(VF, slow)
        Signal = EMA(KVO, signal_period)

    Args:
        high, low, close, volume: OHLCV arrays.
        fast_period: Fast EMA period (default 34).
        slow_period: Slow EMA period (default 55).
        signal_period: Signal line EMA (default 13).

    Returns:
        Tuple of (kvo, signal) arrays.
    """
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)
    volume = np.asarray(volume, dtype=np.float64)
    n = len(high)

    tp = high + low + close
    dm = high - low

    # Trend direction
    trend = np.zeros(n)
    for i in range(1, n):
        trend[i] = 1.0 if tp[i] > tp[i - 1] else -1.0

    # Cumulative Movement
    cm = np.zeros(n)
    cm[0] = dm[0]
    for i in range(1, n):
        if trend[i] == trend[i - 1]:
            cm[i] = cm[i - 1] + dm[i]
        else:
            cm[i] = dm[i - 1] + dm[i]

    # Volume Force
    vf = np.zeros(n)
    for i in range(n):
        if cm[i] != 0:
            vf[i] = volume[i] * abs(2.0 * dm[i] / cm[i] - 1.0) * trend[i] * 100
        else:
            vf[i] = 0.0

    # KVO = EMA(VF, fast) - EMA(VF, slow)
    kvo = _ema(vf, fast_period) - _ema(vf, slow_period)
    signal = _ema(kvo, signal_period)

    return kvo, signal


# ---------------------------------------------------------------------------
# RelativeVigorIndex
# ---------------------------------------------------------------------------


def relative_vigor_index(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 10,
) -> tuple[np.ndarray, np.ndarray]:
    """Relative Vigor Index — close-open / high-low momentum quality.

    Measures the conviction behind price moves: in a bull market,
    closes tend to be near highs (positive vigor).

    Uses triangular weighting of last 4 bars:
        NUM  = (a + 2b + 2c + d) / 6  where a..d = (C-O) of last 4 bars
        DENOM = (e + 2f + 2g + h) / 6 where e..h = (H-L) of last 4 bars
        RVI = SMA(NUM, period) / SMA(DENOM, period)
        Signal = (RVI + 2*RVI[1] + 2*RVI[2] + RVI[3]) / 6

    Args:
        open_, high, low, close: OHLC arrays.
        period: SMA period (default 10).

    Returns:
        Tuple of (rvi, signal) arrays.
    """
    open_ = np.asarray(open_, dtype=np.float64)
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)
    n = len(high)

    co = close - open_  # close-open
    hl = high - low      # high-low

    # Triangular weighted numerator and denominator
    num = np.zeros(n)
    den = np.zeros(n)
    for i in range(3, n):
        num[i] = (co[i] + 2 * co[i - 1] + 2 * co[i - 2] + co[i - 3]) / 6.0
        den[i] = (hl[i] + 2 * hl[i - 1] + 2 * hl[i - 2] + hl[i - 3]) / 6.0

    # RVI = SMA(num) / SMA(den)
    num_sma = _sma(num, period)
    den_sma = _sma(den, period)

    safe_den = np.where(den_sma != 0, den_sma, 1.0)
    rvi = np.where(den_sma != 0, num_sma / safe_den, 0.0)

    # Signal = triangular weighted RVI
    signal = np.zeros(n)
    for i in range(3, n):
        signal[i] = (rvi[i] + 2 * rvi[i - 1] + 2 * rvi[i - 2] + rvi[i - 3]) / 6.0

    return rvi, signal
