"""Market regime detection for strategy routing.

Classifies market into 5 regimes:
- UPTREND: strong bullish (price > SMA200, ADX > 25, low vol)
- DOWNTREND: strong bearish (price < SMA200, ADX > 25)
- RANGE: sideways (ADX <= 25, low ATR)
- WEAK_TREND: mild trend (not strong enough for up/down)
- CRISIS: extreme volatility or drawdown (ATR > 3.5% or DD > 15%)
"""
from __future__ import annotations

import numpy as np
import polars as pl

from src.models.market import MarketRegime, OHLCVBar


def detect_regime(
    index_close: pl.Series,
    index_adx: float,
    index_atr_pct: float,
    current_drawdown: float = 0.0,
) -> MarketRegime:
    """Detect market regime from pre-calculated indicators.

    Args:
        index_close: Close price series (e.g. IMOEX).
        index_adx: Current ADX value.
        index_atr_pct: ATR as fraction of close (e.g. 0.02 = 2%).
        current_drawdown: Current portfolio drawdown fraction (e.g. 0.08 = 8%).

    Returns:
        MarketRegime enum value.
    """
    # Crisis conditions (highest priority)
    if current_drawdown >= 0.15:
        return MarketRegime.CRISIS
    if index_atr_pct >= 0.035:
        return MarketRegime.CRISIS

    # Trend detection via SMA200
    arr = index_close.to_numpy().astype(float)
    if len(arr) < 200:
        sma200 = np.nanmean(arr)
    else:
        sma200 = np.mean(arr[-200:])

    current_price = arr[-1]
    above_sma200 = current_price > sma200

    # Strong trend
    if index_adx > 25:
        if above_sma200:
            return MarketRegime.UPTREND
        else:
            return MarketRegime.DOWNTREND

    # Weak / Range
    if index_atr_pct < 0.02:
        return MarketRegime.RANGE

    return MarketRegime.WEAK_TREND


def detect_regime_from_index(
    candles: list[OHLCVBar],
    current_drawdown: float = 0.0,
) -> MarketRegime:
    """Detect regime directly from OHLCV bars (calculates indicators internally).

    Args:
        candles: List of OHLCVBar (minimum 14 for meaningful ADX).
        current_drawdown: Current portfolio drawdown.

    Returns:
        MarketRegime enum value.
    """
    if len(candles) < 14:
        return MarketRegime.WEAK_TREND

    closes = np.array([c.close for c in candles], dtype=float)
    highs = np.array([c.high for c in candles], dtype=float)
    lows = np.array([c.low for c in candles], dtype=float)

    # ATR (14-period)
    n = len(closes)
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

    atr_14 = np.mean(tr[-14:])
    atr_pct = atr_14 / closes[-1] if closes[-1] > 0 else 0.0

    # Simple ADX approximation (14-period)
    adx = _simple_adx(highs, lows, closes, 14)

    close_series = pl.Series("close", closes)
    return detect_regime(close_series, adx, atr_pct, current_drawdown)


def _simple_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    """Simplified ADX calculation (returns last value only)."""
    n = len(closes)
    if n < period + 1:
        return 20.0  # default neutral

    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]

    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0

    # Wilder smoothing
    def _rma(arr, p):
        out = np.zeros(len(arr))
        out[p - 1] = np.mean(arr[:p])
        for i in range(p, len(arr)):
            out[i] = (out[i - 1] * (p - 1) + arr[i]) / p
        return out

    atr_s = _rma(tr, period)
    plus_s = _rma(plus_dm, period)
    minus_s = _rma(minus_dm, period)

    plus_di = np.where(atr_s > 0, 100 * plus_s / atr_s, 0.0)
    minus_di = np.where(atr_s > 0, 100 * minus_s / atr_s, 0.0)

    dx = np.where((plus_di + minus_di) > 0, 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di), 0.0)
    adx_arr = _rma(dx, period)

    return float(adx_arr[-1]) if not np.isnan(adx_arr[-1]) else 20.0
