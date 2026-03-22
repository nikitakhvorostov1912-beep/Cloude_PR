"""Signal enrichment using ALL indicator modules.

Calculates every indicator on given OHLCV data and produces
a unified vote: how many indicators confirm long/short/neutral.

Uses REAL API of each module (dataclass results, not dict).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class IndicatorVote:
    """Single indicator's vote."""
    name: str
    vote: str  # "long", "short", "neutral"
    value: float = 0.0
    weight: float = 1.0
    detail: str = ""


@dataclass
class EnrichmentResult:
    """Full enrichment of one instrument at one point in time."""
    votes: list[IndicatorVote] = field(default_factory=list)
    long_count: int = 0
    short_count: int = 0
    neutral_count: int = 0
    confirmation_score: float = 0.5  # 0=all short, 0.5=neutral, 1=all long

    @property
    def direction(self) -> str:
        if self.long_count > self.short_count + 1:
            return "long"
        elif self.short_count > self.long_count + 1:
            return "short"
        return "neutral"


def enrich_signals(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    idx: int = -1,
) -> EnrichmentResult:
    """Calculate ALL indicators and produce votes for bar at idx.

    Args:
        open_, high, low, close, volume: full arrays
        idx: bar index to evaluate (default: last bar)

    Returns:
        EnrichmentResult with votes from all available indicators.
    """
    n = len(close)
    if n < 50:
        return EnrichmentResult()

    if idx < 0:
        idx = n + idx

    votes: list[IndicatorVote] = []

    # 1. SuperTrend
    try:
        from src.indicators.supertrend import supertrend
        st = supertrend(high, low, close)
        d = int(st.direction[idx])
        votes.append(IndicatorVote(
            "SuperTrend", "long" if d > 0 else "short",
            value=float(st.trend[idx]), weight=1.5,
            detail=f"dir={d}",
        ))
    except Exception as e:
        logger.debug("supertrend_failed", error=str(e))

    # 2. Squeeze Momentum
    try:
        from src.indicators.squeeze_momentum import squeeze_momentum
        sq = squeeze_momentum(high, low, close)
        mom = float(sq.momentum[idx])
        squeeze_on = int(sq.squeeze[idx])
        vote = "neutral" if squeeze_on == -1 else ("long" if mom > 0 else "short")
        votes.append(IndicatorVote(
            "Squeeze", vote, value=mom, weight=1.0,
            detail=f"mom={mom:.4f}, squeeze={'on' if squeeze_on == -1 else 'off'}",
        ))
    except Exception as e:
        logger.debug("squeeze_failed", error=str(e))

    # 3. Damiani Volatmeter
    try:
        from src.indicators.damiani import damiani_volatmeter
        dv = damiani_volatmeter(high, low, close)
        vol_val = float(dv.vol[idx])
        anti_val = float(dv.anti[idx])
        is_expanding = vol_val > anti_val
        votes.append(IndicatorVote(
            "Damiani", "long" if is_expanding else "neutral",
            value=vol_val, weight=0.5,
            detail=f"vol={vol_val:.4f}, expanding={is_expanding}",
        ))
    except Exception as e:
        logger.debug("damiani_failed", error=str(e))

    # 4. ChandeKrollStop
    try:
        from src.indicators.advanced import chande_kroll_stop
        ck = chande_kroll_stop(high, low, close)
        price = close[idx]
        above_stop = price > ck.stop_long[idx]
        votes.append(IndicatorVote(
            "ChandeKroll", "long" if above_stop else "short",
            value=float(ck.stop_long[idx]), weight=1.2,
            detail=f"stop_l={ck.stop_long[idx]:.2f}, stop_s={ck.stop_short[idx]:.2f}",
        ))
    except Exception as e:
        logger.debug("chandekroll_failed", error=str(e))

    # 5. ChoppinessIndex
    try:
        from src.indicators.advanced import choppiness_index
        chop = choppiness_index(high, low, close)
        chop_val = float(chop[idx])
        is_trending = chop_val < 50
        votes.append(IndicatorVote(
            "Choppiness", "long" if is_trending else "neutral",
            value=chop_val, weight=0.8,
            detail=f"chop={chop_val:.1f}, trending={is_trending}",
        ))
    except Exception as e:
        logger.debug("choppiness_failed", error=str(e))

    # 6. SchaffTrendCycle
    try:
        from src.indicators.advanced import schaff_trend_cycle
        stc = schaff_trend_cycle(close)
        stc_val = float(stc[idx])
        vote = "long" if stc_val > 75 else ("short" if stc_val < 25 else "neutral")
        votes.append(IndicatorVote(
            "STC", vote, value=stc_val, weight=1.0,
            detail=f"stc={stc_val:.1f}",
        ))
    except Exception as e:
        logger.debug("stc_failed", error=str(e))

    # 7. AugenPriceSpike
    try:
        from src.indicators.advanced import augen_price_spike
        spike = augen_price_spike(close)
        spike_val = float(spike[idx])
        vote = "long" if spike_val > 2.0 else ("short" if spike_val < -2.0 else "neutral")
        votes.append(IndicatorVote(
            "AugenSpike", vote, value=spike_val, weight=0.7,
            detail=f"spike={spike_val:.2f} sigma",
        ))
    except Exception as e:
        logger.debug("augen_failed", error=str(e))

    # 8. Ehlers (Voss + BandPass + Reflex)
    try:
        from src.indicators.ehlers import voss_filter, reflex
        vf = voss_filter(close)
        vote = "long" if vf.voss[idx] > vf.filt[idx] else "short"
        votes.append(IndicatorVote(
            "Ehlers_Voss", vote, value=float(vf.voss[idx]), weight=0.8,
            detail=f"voss={vf.voss[idx]:.4f}, filt={vf.filt[idx]:.4f}",
        ))
    except Exception as e:
        logger.debug("ehlers_failed", error=str(e))

    # 9. Support/Resistance
    try:
        from src.indicators.support_resistance import find_nearest_support, find_nearest_resistance
        price = close[idx]
        support = find_nearest_support(low, price)
        resistance = find_nearest_resistance(high, price)
        if support and resistance:
            dist_to_support = (price - support) / price
            dist_to_resistance = (resistance - price) / price
            vote = "long" if dist_to_support < dist_to_resistance else "short"
        else:
            vote = "neutral"
        votes.append(IndicatorVote(
            "S/R", vote, value=price, weight=0.6,
            detail=f"S={support}, R={resistance}",
        ))
    except Exception as e:
        logger.debug("sr_failed", error=str(e))

    # 10. Candle Patterns
    try:
        from src.indicators.candle_patterns import detect_patterns
        patterns = detect_patterns(open_, high, low, close)
        bullish = sum(1 for k in ["doji", "hammer", "engulfing_bullish", "bullish"]
                      if k in patterns and patterns[k][idx] != 0)
        bearish = sum(1 for k in ["engulfing_bearish", "bearish"]
                      if k in patterns and patterns[k][idx] != 0)
        vote = "long" if bullish > bearish else ("short" if bearish > bullish else "neutral")
        votes.append(IndicatorVote(
            "CandlePatterns", vote, value=float(bullish - bearish), weight=0.5,
            detail=f"bull={bullish}, bear={bearish}",
        ))
    except Exception as e:
        logger.debug("candle_failed", error=str(e))

    # 11. Trend Quality (path/distance ratio)
    try:
        from src.indicators.trend_quality import path_distance_ratio
        pdr = path_distance_ratio(close)
        pdr_val = float(pdr[idx]) if not np.isnan(pdr[idx]) else 1.0
        is_trending = pdr_val < 2.5  # low ratio = directional movement
        votes.append(IndicatorVote(
            "PathDistance", "long" if is_trending else "neutral",
            value=pdr_val, weight=0.6,
            detail=f"ratio={pdr_val:.2f}, trending={is_trending}",
        ))
    except Exception as e:
        logger.debug("pdr_failed", error=str(e))

    # Tally
    long_c = sum(1 for v in votes if v.vote == "long")
    short_c = sum(1 for v in votes if v.vote == "short")
    neutral_c = sum(1 for v in votes if v.vote == "neutral")
    total_w = sum(v.weight for v in votes) or 1.0
    long_w = sum(v.weight for v in votes if v.vote == "long")
    conf = long_w / total_w  # 0 = all short, 1 = all long

    return EnrichmentResult(
        votes=votes,
        long_count=long_c,
        short_count=short_c,
        neutral_count=neutral_c,
        confirmation_score=round(conf, 3),
    )
