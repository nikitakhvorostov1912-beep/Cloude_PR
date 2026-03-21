"""Technical indicator features on Polars DataFrames for MOEX analysis."""
from __future__ import annotations

import numpy as np
import polars as pl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ewm(series: np.ndarray, span: int) -> np.ndarray:
    """Exponential weighted moving average (pandas-compatible)."""
    alpha = 2.0 / (span + 1)
    out = np.empty_like(series, dtype=float)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _rma(series: np.ndarray, period: int) -> np.ndarray:
    """Wilder's smoothed moving average (RMA)."""
    out = np.full_like(series, np.nan, dtype=float)
    out[period - 1] = np.mean(series[:period])
    for i in range(period, len(series)):
        out[i] = (out[i - 1] * (period - 1) + series[i]) / period
    return out


# ---------------------------------------------------------------------------
# Individual indicators
# ---------------------------------------------------------------------------

def calculate_ema(close: pl.Series, period: int) -> pl.Series:
    """EMA of given period."""
    arr = close.to_numpy().astype(float)
    result = _ewm(arr, period)
    return pl.Series(f"ema_{period}", result)


def calculate_rsi(close: pl.Series, period: int = 14) -> pl.Series:
    """RSI (Relative Strength Index), 0-100."""
    arr = close.to_numpy().astype(float)
    deltas = np.diff(arr, prepend=arr[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = _rma(gains, period)
    avg_loss = _rma(losses, period)
    rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100.0)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return pl.Series("rsi_14", rsi)


def calculate_macd(
    close: pl.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, pl.Series]:
    """MACD, signal, histogram."""
    arr = close.to_numpy().astype(float)
    ema_fast = _ewm(arr, fast)
    ema_slow = _ewm(arr, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ewm(macd_line, signal)
    histogram = macd_line - signal_line
    return {
        "macd": pl.Series("macd", macd_line),
        "signal": pl.Series("macd_signal", signal_line),
        "histogram": pl.Series("macd_histogram", histogram),
    }


def calculate_bollinger(
    close: pl.Series, period: int = 20, mult: float = 2.0
) -> dict[str, pl.Series]:
    """Bollinger Bands: upper, middle, lower, %B, bandwidth."""
    arr = close.to_numpy().astype(float)
    n = len(arr)
    middle = np.full(n, np.nan)
    std = np.full(n, np.nan)
    for i in range(period - 1, n):
        window = arr[i - period + 1: i + 1]
        middle[i] = window.mean()
        std[i] = window.std(ddof=0)
    upper = middle + mult * std
    lower = middle - mult * std
    bw = np.where(middle != 0, (upper - lower) / middle, 0.0)
    pct_b = np.where((upper - lower) != 0, (arr - lower) / (upper - lower), 0.5)
    return {
        "bb_upper": pl.Series("bb_upper", upper),
        "bb_middle": pl.Series("bb_middle", middle),
        "bb_lower": pl.Series("bb_lower", lower),
        "bb_pct_b": pl.Series("bb_pct_b", pct_b),
        "bb_bandwidth": pl.Series("bb_bandwidth", bw),
    }


def calculate_atr(
    high: pl.Series, low: pl.Series, close: pl.Series, period: int = 14
) -> pl.Series:
    """Average True Range."""
    h = high.to_numpy().astype(float)
    l = low.to_numpy().astype(float)
    c = close.to_numpy().astype(float)
    n = len(c)
    tr = np.empty(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = _rma(tr, period)
    return pl.Series("atr_14", atr)


def calculate_volume_ratio(volume: pl.Series, period: int = 20) -> pl.Series:
    """Volume ratio = current volume / SMA(volume, period)."""
    arr = volume.to_numpy().astype(float)
    n = len(arr)
    result: list[float | None] = [None] * n
    for i in range(period - 1, n):
        avg = arr[i - period + 1: i + 1].mean()
        result[i] = float(arr[i] / avg) if avg > 0 else 1.0
    return pl.Series("volume_ratio_20", result)


def _calculate_adx(high: pl.Series, low: pl.Series, close: pl.Series, period: int = 14):
    """ADX + DI+ + DI-."""
    h = high.to_numpy().astype(float)
    l = low.to_numpy().astype(float)
    c = close.to_numpy().astype(float)
    n = len(c)

    tr = np.empty(n)
    plus_dm = np.empty(n)
    minus_dm = np.empty(n)
    tr[0] = h[0] - l[0]
    plus_dm[0] = 0.0
    minus_dm[0] = 0.0

    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        up_move = h[i] - h[i - 1]
        down_move = l[i - 1] - l[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    atr_s = _rma(tr, period)
    plus_di_raw = _rma(plus_dm, period)
    minus_di_raw = _rma(minus_dm, period)

    plus_di = np.where(atr_s > 0, 100 * plus_di_raw / atr_s, 0.0)
    minus_di = np.where(atr_s > 0, 100 * minus_di_raw / atr_s, 0.0)

    dx = np.where(
        (plus_di + minus_di) > 0,
        100 * np.abs(plus_di - minus_di) / (plus_di + minus_di),
        0.0,
    )
    adx = _rma(dx, period)

    return (
        pl.Series("adx", adx),
        pl.Series("di_plus", plus_di),
        pl.Series("di_minus", minus_di),
    )


def _calculate_stochastic(high: pl.Series, low: pl.Series, close: pl.Series,
                          k_period: int = 14, d_period: int = 3):
    """Stochastic %K, %D."""
    h = high.to_numpy().astype(float)
    l = low.to_numpy().astype(float)
    c = close.to_numpy().astype(float)
    n = len(c)
    k = np.full(n, np.nan)
    for i in range(k_period - 1, n):
        hh = h[i - k_period + 1: i + 1].max()
        ll = l[i - k_period + 1: i + 1].min()
        k[i] = 100 * (c[i] - ll) / (hh - ll) if (hh - ll) > 0 else 50.0
    # %D = SMA(%K, d_period)
    d = np.full(n, np.nan)
    for i in range(k_period - 1 + d_period - 1, n):
        window = k[i - d_period + 1: i + 1]
        d[i] = np.nanmean(window)
    return pl.Series("stoch_k", k), pl.Series("stoch_d", d)


def _calculate_obv(close: pl.Series, volume: pl.Series) -> pl.Series:
    """On-Balance Volume."""
    c = close.to_numpy().astype(float)
    v = volume.to_numpy().astype(float)
    obv = np.zeros(len(c))
    for i in range(1, len(c)):
        if c[i] > c[i - 1]:
            obv[i] = obv[i - 1] + v[i]
        elif c[i] < c[i - 1]:
            obv[i] = obv[i - 1] - v[i]
        else:
            obv[i] = obv[i - 1]
    return pl.Series("obv", obv)


def _calculate_mfi(high: pl.Series, low: pl.Series, close: pl.Series,
                   volume: pl.Series, period: int = 14) -> pl.Series:
    """Money Flow Index."""
    tp = ((high.to_numpy() + low.to_numpy() + close.to_numpy()) / 3).astype(float)
    mf = tp * volume.to_numpy().astype(float)
    n = len(tp)
    result = np.full(n, np.nan)
    for i in range(period, n):
        pos = sum(mf[j] for j in range(i - period + 1, i + 1) if tp[j] > tp[j - 1])
        neg = sum(mf[j] for j in range(i - period + 1, i + 1) if tp[j] < tp[j - 1])
        result[i] = 100 - 100 / (1 + pos / neg) if neg > 0 else 100.0
    return pl.Series("mfi", result)


def _calculate_vwap(close: pl.Series, volume: pl.Series) -> pl.Series:
    """Cumulative VWAP."""
    c = close.to_numpy().astype(float)
    v = volume.to_numpy().astype(float)
    cum_pv = np.cumsum(c * v)
    cum_v = np.cumsum(v)
    vwap = np.where(cum_v > 0, cum_pv / cum_v, c)
    return pl.Series("vwap", vwap)


# ---------------------------------------------------------------------------
# All-in-one
# ---------------------------------------------------------------------------

def calculate_all_features(df: pl.DataFrame) -> pl.DataFrame:
    """Add all technical features to an OHLCV DataFrame.

    Expects columns: open, high, low, close, volume.
    Returns DataFrame with all original + indicator columns.
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    cols: dict[str, pl.Series] = {}

    # EMAs
    for p in (20, 50, 200):
        cols[f"ema_{p}"] = calculate_ema(close, p)

    # RSI
    cols["rsi_14"] = calculate_rsi(close, 14)

    # MACD
    macd = calculate_macd(close)
    cols["macd"] = macd["macd"]
    cols["macd_signal"] = macd["signal"]
    cols["macd_histogram"] = macd["histogram"]

    # ADX
    adx, di_plus, di_minus = _calculate_adx(high, low, close)
    cols["adx"] = adx
    cols["di_plus"] = di_plus
    cols["di_minus"] = di_minus

    # Bollinger
    bb = calculate_bollinger(close)
    for k, v in bb.items():
        cols[k] = v

    # ATR
    cols["atr_14"] = calculate_atr(high, low, close)

    # Stochastic
    stoch_k, stoch_d = _calculate_stochastic(high, low, close)
    cols["stoch_k"] = stoch_k
    cols["stoch_d"] = stoch_d

    # OBV
    cols["obv"] = _calculate_obv(close, volume)

    # Volume ratio
    cols["volume_ratio_20"] = calculate_volume_ratio(volume)

    # MFI
    cols["mfi"] = _calculate_mfi(high, low, close, volume)

    # VWAP
    cols["vwap"] = _calculate_vwap(close, volume)

    return df.with_columns([v.alias(k) for k, v in cols.items()])
