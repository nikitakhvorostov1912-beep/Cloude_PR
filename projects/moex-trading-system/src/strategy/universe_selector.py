"""Dynamic Universe Selection — daily ranking and top-N selection.

Ranks all tickers in the universe by composite score and selects
the best candidates based on market regime.

Architecture:
    UNIVERSE (30 tickers) → FILTER → RANK → SELECT Top-N → Output

Composite Score = ML(40%) + Momentum(25%) + Macro Alignment(20%) + RS(15%)

Public API:
    rank_universe(tickers_data, regime, macro, selection_config) -> list[RankedTicker]
    select_top_n(ranked, regime, config) -> list[RankedTicker]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Sector-to-macro driver mapping
SECTOR_MACRO_DRIVER: dict[str, str] = {
    "oil_gas": "brent",
    "banks": "key_rate",
    "metals": "usd_rub",
    "chemicals": "usd_rub",
    "real_estate": "key_rate",
    "it": "domestic",
    "retail": "domestic",
    "telecom": "domestic",
    "transport": "domestic",
    "energy": "domestic",
}


@dataclass
class RankedTicker:
    """Ticker with composite ranking score."""

    ticker: str
    sector: str
    composite_score: float  # 0-100
    ml_score: float  # 0-100
    momentum_score: float  # 0-100
    macro_score: float  # 0-100
    rs_score: float  # 0-100 (relative strength vs IMOEX)
    close: float
    volume_ratio: float  # vs 20-day avg
    reason: str = ""


def _calc_momentum_score(
    returns_1m: float,
    returns_3m: float,
    rsi: float,
) -> float:
    """Momentum score: positive returns + RSI positioning.

    Higher score = stronger upward momentum.
    """
    score = 50.0

    # 1-month return
    if returns_1m > 0.10:
        score += 25.0
    elif returns_1m > 0.05:
        score += 15.0
    elif returns_1m > 0.02:
        score += 8.0
    elif returns_1m < -0.05:
        score -= 20.0
    elif returns_1m < -0.02:
        score -= 10.0

    # 3-month return
    if returns_3m > 0.15:
        score += 20.0
    elif returns_3m > 0.05:
        score += 10.0
    elif returns_3m < -0.10:
        score -= 15.0

    # RSI sweet spot (40-65 = ideal for trend entry)
    if 40 <= rsi <= 65:
        score += 5.0
    elif rsi > 75:
        score -= 15.0  # overbought
    elif rsi < 25:
        score -= 10.0  # oversold

    return max(0.0, min(100.0, score))


def _calc_macro_alignment(
    sector: str,
    brent_delta_pct: float,
    key_rate_delta: float,
    usd_rub_delta_pct: float,
) -> float:
    """How well does this sector align with current macro conditions?"""
    driver = SECTOR_MACRO_DRIVER.get(sector, "domestic")
    score = 50.0

    if driver == "brent":
        if brent_delta_pct > 5:
            score += 30.0
        elif brent_delta_pct > 0:
            score += 10.0
        elif brent_delta_pct < -5:
            score -= 25.0
        elif brent_delta_pct < 0:
            score -= 10.0

    elif driver == "key_rate":
        if key_rate_delta < -0.5:
            score += 30.0  # rate cut = bullish for banks
        elif key_rate_delta < 0:
            score += 15.0
        elif key_rate_delta > 0.5:
            score -= 30.0  # rate hike = bearish
        elif key_rate_delta > 0:
            score -= 15.0

    elif driver == "usd_rub":
        # Exporters benefit from weaker ruble
        if usd_rub_delta_pct > 3:
            score += 20.0  # weak ruble = good for exporters
        elif usd_rub_delta_pct < -3:
            score -= 15.0

    elif driver == "domestic":
        # Domestic sectors hurt by rate hikes and ruble stress
        if key_rate_delta < 0:
            score += 15.0
        elif key_rate_delta > 0.5:
            score -= 20.0
        if usd_rub_delta_pct > 5:
            score -= 15.0

    return max(0.0, min(100.0, score))


def _calc_relative_strength(
    ticker_return_20d: float,
    imoex_return_20d: float,
) -> float:
    """Relative strength vs IMOEX index (20-day)."""
    excess = ticker_return_20d - imoex_return_20d
    score = 50.0 + excess * 500  # scale: 0.02 excess = +10 points
    return max(0.0, min(100.0, score))


def rank_universe(
    tickers_data: list[dict[str, Any]],
    macro: dict[str, float],
    selection_config: dict[str, Any] | None = None,
) -> list[RankedTicker]:
    """Rank all tickers in the universe by composite score.

    Parameters
    ----------
    tickers_data:
        List of dicts per ticker with keys:
        ticker, sector, close, ml_score, rsi, returns_1m, returns_3m,
        returns_20d, imoex_return_20d, volume_ratio.
    macro:
        Macro indicators: brent_delta_pct, key_rate_delta, usd_rub_delta_pct.
    selection_config:
        Weights config from tickers.yaml selection section.

    Returns
    -------
    list[RankedTicker] sorted by composite_score descending.
    """
    config = selection_config or {}
    weights = config.get("weights", {})
    w_ml = weights.get("ml_score", 0.40)
    w_mom = weights.get("momentum", 0.25)
    w_macro = weights.get("macro_alignment", 0.20)
    w_rs = weights.get("relative_strength", 0.15)

    brent_delta = macro.get("brent_delta_pct", 0.0)
    rate_delta = macro.get("key_rate_delta", 0.0)
    rub_delta = macro.get("usd_rub_delta_pct", 0.0)

    ranked: list[RankedTicker] = []

    for td in tickers_data:
        ticker = td["ticker"]
        sector = td.get("sector", "banks")

        # Filter: skip if volume too low
        vol_ratio = float(td.get("volume_ratio", 1.0))
        if vol_ratio < 0.3:
            continue

        ml = float(td.get("ml_score", 50.0))
        rsi = float(td.get("rsi", 50.0))
        ret_1m = float(td.get("returns_1m", 0.0))
        ret_3m = float(td.get("returns_3m", 0.0))
        ret_20d = float(td.get("returns_20d", 0.0))
        imoex_20d = float(td.get("imoex_return_20d", 0.0))

        mom = _calc_momentum_score(ret_1m, ret_3m, rsi)
        macro_align = _calc_macro_alignment(sector, brent_delta, rate_delta, rub_delta)
        rs = _calc_relative_strength(ret_20d, imoex_20d)

        composite = ml * w_ml + mom * w_mom + macro_align * w_macro + rs * w_rs

        # Build reason string
        reasons = []
        if ml >= 60:
            reasons.append(f"ML={ml:.0f}")
        if mom >= 60:
            reasons.append(f"Mom={mom:.0f}")
        if macro_align >= 60:
            reasons.append(f"Macro={macro_align:.0f}")
        if rs >= 60:
            reasons.append(f"RS={rs:.0f}")

        ranked.append(RankedTicker(
            ticker=ticker,
            sector=sector,
            composite_score=round(composite, 2),
            ml_score=round(ml, 2),
            momentum_score=round(mom, 2),
            macro_score=round(macro_align, 2),
            rs_score=round(rs, 2),
            close=float(td.get("close", 0)),
            volume_ratio=round(vol_ratio, 2),
            reason=", ".join(reasons) if reasons else "neutral",
        ))

    ranked.sort(key=lambda x: x.composite_score, reverse=True)

    logger.info(
        "universe_ranked",
        total=len(ranked),
        top3=[f"{r.ticker}={r.composite_score}" for r in ranked[:3]],
    )

    return ranked


def select_top_n(
    ranked: list[RankedTicker],
    regime: str,
    selection_config: dict[str, Any] | None = None,
) -> list[RankedTicker]:
    """Select top-N tickers based on market regime.

    Parameters
    ----------
    ranked:
        Ranked tickers from rank_universe().
    regime:
        Market regime: "uptrend", "downtrend", "range", "crisis", "weak_trend".
    selection_config:
        Config from tickers.yaml selection section.

    Returns
    -------
    list[RankedTicker] — selected tickers for trading.
    """
    config = selection_config or {}
    overrides = config.get("regime_overrides", {})
    regime_lower = regime.lower().replace("_", "")

    # Map regime to config key
    regime_key = regime_lower
    if regime_key == "weaktrend":
        regime_key = "range"  # treat weak trend as range

    regime_cfg = overrides.get(regime_key, {})
    max_positions = regime_cfg.get("max_positions", config.get("max_positions", 7))
    min_score = regime_cfg.get("min_score", config.get("min_composite_score", 60))

    # Filter by minimum score
    eligible = [r for r in ranked if r.composite_score >= min_score]

    # Sector diversification: max 2 per sector
    selected: list[RankedTicker] = []
    sector_count: dict[str, int] = {}

    for r in eligible:
        if len(selected) >= max_positions:
            break
        count = sector_count.get(r.sector, 0)
        if count >= 2:
            continue  # skip: already 2 from this sector
        selected.append(r)
        sector_count[r.sector] = count + 1

    logger.info(
        "universe_selected",
        regime=regime,
        max_positions=max_positions,
        min_score=min_score,
        eligible=len(eligible),
        selected=len(selected),
        tickers=[s.ticker for s in selected],
    )

    return selected
