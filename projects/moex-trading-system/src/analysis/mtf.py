"""Multi-Timeframe (MTF) Analysis Engine.

Analyzes multiple timeframes independently, then synthesizes a weighted
consensus signal. Higher timeframes get more weight (trend > noise).

Weights:
    M5  = 10% (entry/exit timing — low weight)
    H1  = 30% (primary working timeframe)
    D1  = 40% (trend — highest weight)
    W1  = 20% (global context)

Tradeable = 2+ timeframes agree on direction.
Confidence boost = +0.15 if 75%+ agree, +0.08 if 50%+ agree.

Public API:
    analyze_single_tf(ticker, tf, candles) -> TFAnalysis
    analyze_mtf(ticker, candles_by_tf) -> MTFResult
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import polars as pl
import structlog

logger = structlog.get_logger(__name__)


class TFSignal(str, Enum):
    STRONG_BULL = "strong_bull"
    BULL = "bull"
    NEUTRAL = "neutral"
    BEAR = "bear"
    STRONG_BEAR = "strong_bear"


class TimeFrame(str, Enum):
    M5 = "5min"
    H1 = "1hour"
    D1 = "1day"
    W1 = "1week"


TF_WEIGHT: dict[TimeFrame, float] = {
    TimeFrame.M5: 0.10,
    TimeFrame.H1: 0.30,
    TimeFrame.D1: 0.40,
    TimeFrame.W1: 0.20,
}

TF_INTERVAL: dict[TimeFrame, int] = {
    TimeFrame.M5: 5,
    TimeFrame.H1: 60,
    TimeFrame.D1: 24,  # MOEX ISS interval=24 for daily
    TimeFrame.W1: 7,   # MOEX ISS interval=7 for weekly
}

TF_BARS_NEEDED: dict[TimeFrame, int] = {
    TimeFrame.M5: 100,
    TimeFrame.H1: 200,
    TimeFrame.D1: 250,
    TimeFrame.W1: 52,
}


# ── Dataclasses ────────────────────────────────────────────────────


@dataclass
class TFAnalysis:
    """Analysis result for a single timeframe."""

    tf: TimeFrame
    signal: TFSignal
    trend_score: float       # -1.0 .. +1.0
    momentum_score: float    # -1.0 .. +1.0
    volume_score: float      # 0.0 .. 1.0
    adx: float
    rsi: float
    ema_aligned: bool        # EMA20 > EMA50 > EMA200 (bull) or inverse
    bars_count: int
    weight: float = field(init=False)

    def __post_init__(self) -> None:
        self.weight = TF_WEIGHT[self.tf]

    @property
    def composite_score(self) -> float:
        return (
            self.trend_score * 0.5
            + self.momentum_score * 0.3
            + self.volume_score * 0.2
        )


@dataclass
class MTFResult:
    """Multi-timeframe synthesis result."""

    ticker: str
    analyses: dict[TimeFrame, TFAnalysis]
    mtf_score: float           # -1.0 .. +1.0 weighted
    agreement_count: int       # how many TFs agree on direction
    agreement_ratio: float     # 0.0 .. 1.0
    dominant_signal: TFSignal
    confidence_boost: float    # bonus for TF agreement
    tradeable: bool            # True if 2+ TFs agree

    @property
    def summary(self) -> str:
        parts = []
        for tf, a in self.analyses.items():
            parts.append(f"{tf.value}:{a.signal.value}({a.composite_score:+.2f})")
        return " | ".join(parts)


# ── Indicator helpers (no external dependencies) ───────────────────


def _calc_ema(series: list[float], period: int) -> list[float]:
    """Simple EMA without pandas."""
    if len(series) < period:
        return []
    k = 2.0 / (period + 1)
    ema = [sum(series[:period]) / period]
    for price in series[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def _calc_rsi(closes: list[float], period: int = 14) -> float:
    """RSI of the last bar."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0, d) for d in deltas[-period:]]
    losses = [abs(min(0, d)) for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _calc_adx(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> float:
    """Simplified ADX (last value only)."""
    if len(closes) < period * 2:
        return 20.0

    tr_list: list[float] = []
    pdm_list: list[float] = []
    ndm_list: list[float] = []

    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        pdm = max(up, 0) if up > down else 0
        ndm = max(down, 0) if down > up else 0
        tr_list.append(tr)
        pdm_list.append(pdm)
        ndm_list.append(ndm)

    def _smooth(lst: list[float]) -> list[float]:
        s = sum(lst[:period])
        result = [s]
        for v in lst[period:]:
            s = s - s / period + v
            result.append(s)
        return result

    atr = _smooth(tr_list)
    pdi = [100 * p / a if a else 0 for p, a in zip(_smooth(pdm_list), atr)]
    ndi = [100 * n / a if a else 0 for n, a in zip(_smooth(ndm_list), atr)]
    dx = [
        100 * abs(p - n) / (p + n) if (p + n) else 0
        for p, n in zip(pdi, ndi)
    ]
    return sum(dx[-period:]) / period if dx else 20.0


# ── Single TF analysis ────────────────────────────────────────────


def analyze_single_tf(
    ticker: str,
    tf: TimeFrame,
    candles: list[dict] | pl.DataFrame,
) -> TFAnalysis | None:
    """Analyze one timeframe, return TFAnalysis or None if insufficient data."""
    # Normalize to lists
    if isinstance(candles, pl.DataFrame):
        closes = candles["close"].to_list()
        highs = candles["high"].to_list()
        lows = candles["low"].to_list()
        volumes = candles["volume"].to_list()
    else:
        closes = [float(c.get("close", 0)) for c in candles]
        highs = [float(c.get("high", 0)) for c in candles]
        lows = [float(c.get("low", 0)) for c in candles]
        volumes = [float(c.get("volume", 0)) for c in candles]

    n = len(closes)
    if n < 20:
        return None

    # EMA
    ema20 = _calc_ema(closes, 20)
    ema50 = _calc_ema(closes, min(50, n - 1))
    ema200 = _calc_ema(closes, min(200, n - 1))

    last_close = closes[-1]
    last_ema20 = ema20[-1] if ema20 else last_close
    last_ema50 = ema50[-1] if ema50 else last_close
    last_ema200 = ema200[-1] if ema200 else last_close

    ema_bull = last_ema20 > last_ema50 > last_ema200
    ema_bear = last_ema20 < last_ema50 < last_ema200

    # RSI
    rsi = _calc_rsi(closes)

    # ADX
    adx = _calc_adx(highs, lows, closes)

    # ── Trend score [-1, +1] ──
    trend_score = 0.0
    if ema_bull:
        trend_score += 0.5
    elif ema_bear:
        trend_score -= 0.5

    if last_close > last_ema20:
        trend_score += 0.2
    elif last_close < last_ema20:
        trend_score -= 0.2

    if adx > 25:
        trend_score *= 1.3  # amplify on strong trend

    trend_score = max(-1.0, min(1.0, trend_score))

    # ── Momentum score [-1, +1] ──
    momentum_score = 0.0
    if 40 <= rsi <= 65:
        momentum_score = 0.3    # sweet spot for entry
    elif rsi > 70:
        momentum_score = -0.4   # overbought
    elif rsi < 30:
        momentum_score = -0.3   # oversold (risk)
    elif rsi > 55:
        momentum_score = 0.2
    elif rsi < 45:
        momentum_score = -0.2

    # ── Volume score [0, 1] ──
    volume_score = 0.5
    if len(volumes) >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        last_vol = volumes[-1]
        if avg_vol > 0:
            ratio = last_vol / avg_vol
            volume_score = min(1.0, ratio * 0.5)

    # ── Signal classification ──
    composite = trend_score * 0.5 + momentum_score * 0.3 + volume_score * 0.2

    if composite >= 0.4:
        signal = TFSignal.STRONG_BULL
    elif composite >= 0.15:
        signal = TFSignal.BULL
    elif composite <= -0.4:
        signal = TFSignal.STRONG_BEAR
    elif composite <= -0.15:
        signal = TFSignal.BEAR
    else:
        signal = TFSignal.NEUTRAL

    return TFAnalysis(
        tf=tf,
        signal=signal,
        trend_score=round(trend_score, 4),
        momentum_score=round(momentum_score, 4),
        volume_score=round(volume_score, 4),
        adx=round(adx, 1),
        rsi=round(rsi, 1),
        ema_aligned=ema_bull,
        bars_count=n,
    )


# ── Multi-TF synthesis ─────────────────────────────────────────────


async def analyze_mtf(
    ticker: str,
    candles_by_tf: dict[TimeFrame, list[dict] | pl.DataFrame],
) -> MTFResult:
    """Analyze all available timeframes and synthesize MTFResult.

    Args:
        ticker: MOEX ticker.
        candles_by_tf: {TimeFrame.H1: [...], TimeFrame.D1: [...], ...}

    Returns:
        MTFResult with weighted score, agreement, and tradeable flag.
    """
    analyses: dict[TimeFrame, TFAnalysis] = {}

    for tf, candles in candles_by_tf.items():
        if candles is None:
            continue
        if hasattr(candles, "__len__") and len(candles) < 20:
            continue
        analysis = analyze_single_tf(ticker, tf, candles)
        if analysis is not None:
            analyses[tf] = analysis

    if not analyses:
        return MTFResult(
            ticker=ticker,
            analyses={},
            mtf_score=0.0,
            agreement_count=0,
            agreement_ratio=0.0,
            dominant_signal=TFSignal.NEUTRAL,
            confidence_boost=0.0,
            tradeable=False,
        )

    # Weighted MTF score
    total_weight = sum(a.weight for a in analyses.values())
    mtf_score = (
        sum(a.composite_score * a.weight for a in analyses.values())
        / total_weight
    )

    # TF agreement
    bull_tfs = sum(
        1
        for a in analyses.values()
        if a.signal in (TFSignal.BULL, TFSignal.STRONG_BULL)
    )
    bear_tfs = sum(
        1
        for a in analyses.values()
        if a.signal in (TFSignal.BEAR, TFSignal.STRONG_BEAR)
    )
    total_tfs = len(analyses)
    agreement_count = max(bull_tfs, bear_tfs)
    agreement_ratio = agreement_count / total_tfs if total_tfs else 0

    # Dominant signal
    if bull_tfs > bear_tfs and bull_tfs >= 2:
        dominant = TFSignal.STRONG_BULL if bull_tfs >= 3 else TFSignal.BULL
    elif bear_tfs > bull_tfs and bear_tfs >= 2:
        dominant = TFSignal.STRONG_BEAR if bear_tfs >= 3 else TFSignal.BEAR
    else:
        dominant = TFSignal.NEUTRAL

    # Confidence boost for agreement
    if agreement_ratio >= 0.75:
        confidence_boost = 0.15
    elif agreement_ratio >= 0.50:
        confidence_boost = 0.08
    else:
        confidence_boost = 0.0

    tradeable = agreement_count >= 2

    logger.info(
        "mtf_analysis",
        ticker=ticker,
        tfs=[tf.value for tf in analyses],
        mtf_score=round(mtf_score, 3),
        bull_tfs=bull_tfs,
        bear_tfs=bear_tfs,
        dominant=dominant.value,
        tradeable=tradeable,
    )

    return MTFResult(
        ticker=ticker,
        analyses=analyses,
        mtf_score=round(mtf_score, 3),
        agreement_count=agreement_count,
        agreement_ratio=round(agreement_ratio, 2),
        dominant_signal=dominant,
        confidence_boost=round(confidence_boost, 3),
        tradeable=tradeable,
    )


__all__ = [
    "TimeFrame",
    "TFSignal",
    "TFAnalysis",
    "MTFResult",
    "TF_WEIGHT",
    "TF_INTERVAL",
    "TF_BARS_NEEDED",
    "analyze_single_tf",
    "analyze_mtf",
]
