"""Pre-Score Engine — 7-factor scoring model (0–100).

Produces a pre-score that reflects the quality of a trade setup BEFORE
Claude is consulted.  A higher score means more favourable conditions.

Factor weights:
    trend        0.22  — ADX strength + DI alignment
    momentum     0.18  — RSI position + MACD histogram
    structure    0.18  — EMA alignment
    volume       0.08  — volume ratio + OBV trend
    sentiment    0.09  — external news/sentiment score
    fundamental  0.15  — P/E ratio vs sector, dividend yield
    macro        0.10  — macroeconomic environment

For SHORT positions the momentum and structure sub-scores are inverted
(bearish conditions become high scores).
"""
from __future__ import annotations

SCORING_WEIGHTS: dict[str, float] = {
    "trend": 0.22,
    "momentum": 0.18,
    "structure": 0.18,
    "volume": 0.08,
    "sentiment": 0.09,
    "fundamental": 0.15,
    "macro": 0.10,
}

SECTOR_SENSITIVITY: dict[str, dict[str, float]] = {
    "oil_gas": {"brent": 0.85, "key_rate": -0.45, "usd_rub": -0.68},
    "banks": {"brent": 0.30, "key_rate": -0.78, "usd_rub": -0.55},
    "retail": {"brent": 0.15, "key_rate": -0.60, "usd_rub": -0.40},
    "metals": {"brent": 0.40, "key_rate": -0.50, "usd_rub": -0.65},
    "it": {"brent": 0.10, "key_rate": -0.55, "usd_rub": -0.30},
}

# ---------------------------------------------------------------------------
# Factor calculators (all return raw score 0–100 before weighting)
# ---------------------------------------------------------------------------


def _score_trend(
    adx: float,
    di_plus: float,
    di_minus: float,
    direction: str,
) -> float:
    """ADX strength score, with DI alignment bonus."""
    if adx >= 40:
        base = 100.0
    elif adx >= 30:
        base = 75.0
    elif adx >= 25:
        base = 50.0
    elif adx >= 20:
        base = 25.0
    else:
        base = 0.0

    # DI alignment bonus (+10)
    if direction == "long" and di_plus > di_minus:
        base = min(100.0, base + 10.0)
    elif direction == "short" and di_minus > di_plus:
        base = min(100.0, base + 10.0)

    return base


def _score_momentum_long(rsi: float, macd_hist: float) -> float:
    """Momentum score for LONG: oversold / neutral RSI is good."""
    if rsi < 30:
        rsi_score = 0.0  # Extremely oversold — potential reversal risk
    elif rsi < 40:
        rsi_score = 100.0
    elif rsi < 50:
        rsi_score = 75.0
    elif rsi < 60:
        rsi_score = 50.0
    elif rsi < 70:
        rsi_score = 25.0
    else:
        rsi_score = 0.0  # Overbought

    macd_bonus = 15.0 if macd_hist > 0 else 0.0
    return min(100.0, rsi_score + macd_bonus)


def _score_momentum_short(rsi: float, macd_hist: float) -> float:
    """Momentum score for SHORT: overbought RSI is good."""
    if rsi > 70:
        rsi_score = 100.0
    elif rsi > 60:
        rsi_score = 75.0
    elif rsi > 50:
        rsi_score = 50.0
    elif rsi > 40:
        rsi_score = 25.0
    else:
        rsi_score = 0.0

    macd_bonus = 15.0 if macd_hist < 0 else 0.0
    return min(100.0, rsi_score + macd_bonus)


def _score_structure_long(
    close: float,
    ema20: float,
    ema50: float,
    ema200: float,
) -> float:
    """EMA alignment for LONG: bullish stack = high score."""
    if close > ema20 and ema20 > ema50 and ema50 > ema200:
        return 100.0
    if close > ema50 and ema50 > ema200:
        return 75.0
    if close > ema200:
        return 50.0
    return 0.0


def _score_structure_short(
    close: float,
    ema20: float,
    ema50: float,
    ema200: float,
) -> float:
    """EMA alignment for SHORT: bearish stack = high score."""
    if close < ema20 and ema20 < ema50 and ema50 < ema200:
        return 100.0
    if close < ema50 and ema50 < ema200:
        return 75.0
    if close < ema200:
        return 50.0
    return 0.0


def _score_volume(volume_ratio: float, obv_trend: str, direction: str) -> float:
    """Volume ratio score + OBV alignment bonus."""
    if volume_ratio >= 1.5:
        base = 100.0
    elif volume_ratio >= 1.2:
        base = 75.0
    elif volume_ratio >= 0.8:
        base = 50.0
    else:
        base = 25.0

    # OBV trend bonus (+15)
    if direction == "long" and obv_trend == "up":
        base = min(100.0, base + 15.0)
    elif direction == "short" and obv_trend == "down":
        base = min(100.0, base + 15.0)

    return base


def _score_sentiment(sentiment_score: float) -> float:
    """Convert continuous sentiment [-1, +1] to 0–100."""
    if sentiment_score > 0.5:
        return 100.0
    if sentiment_score > 0.2:
        return 75.0
    if sentiment_score >= -0.2:
        return 50.0
    if sentiment_score >= -0.5:
        return 25.0
    return 0.0


def _score_fundamental(
    pe_ratio: float | None,
    sector_pe: float | None,
    div_yield: float | None,
) -> float:
    """Fundamental score based on P/E vs sector and dividend yield."""
    score = 40.0  # neutral baseline

    # P/E vs sector
    if pe_ratio is not None and sector_pe is not None and sector_pe > 0:
        if pe_ratio < sector_pe * 0.8:
            score += 30.0  # significantly undervalued
        elif pe_ratio < sector_pe:
            score += 15.0  # mildly undervalued
        elif pe_ratio > sector_pe * 1.2:
            score -= 15.0  # expensive

    # Dividend yield
    if div_yield is not None:
        if div_yield >= 0.08:  # 8 %+
            score += 30.0
        elif div_yield >= 0.05:  # 5-8 %
            score += 15.0

    return max(0.0, min(100.0, score))


def _score_macro(
    key_rate_delta: float,
    brent_delta_pct: float,
    usd_rub_delta_pct: float,
    imoex_above_sma200: bool,
    sector: str = "banks",
) -> float:
    """Macro environment score based on CBR rate, Brent, USD/RUB, IMOEX vs SMA200.

    Parameters
    ----------
    key_rate_delta: Change in CBR key rate (negative = easing = bullish)
    brent_delta_pct: Brent price change % over last month
    usd_rub_delta_pct: USD/RUB change % over last week (positive = ruble weakening)
    imoex_above_sma200: Whether IMOEX index is above its SMA(200)
    sector: Ticker sector for sensitivity weighting
    """
    score = 50.0  # neutral baseline

    sensitivity = SECTOR_SENSITIVITY.get(sector, SECTOR_SENSITIVITY["banks"])

    # CBR key rate direction (biggest factor for RU market)
    if key_rate_delta < -0.5:
        score += 30.0  # significant easing
    elif key_rate_delta < 0:
        score += 15.0  # mild easing
    elif key_rate_delta > 0.5:
        score -= 25.0  # significant tightening
    elif key_rate_delta > 0:
        score -= 10.0  # mild tightening
    # Weight by sector sensitivity to rate
    rate_impact = abs(sensitivity.get("key_rate", -0.5))
    score = 50.0 + (score - 50.0) * (rate_impact / 0.78)  # normalize to banks sensitivity

    # Brent price trend
    brent_sens = abs(sensitivity.get("brent", 0.3))
    if brent_delta_pct > 10:
        score += 20.0 * brent_sens
    elif brent_delta_pct > 5:
        score += 10.0 * brent_sens
    elif brent_delta_pct < -10:
        score -= 20.0 * brent_sens
    elif brent_delta_pct < -5:
        score -= 10.0 * brent_sens

    # USD/RUB stress
    if usd_rub_delta_pct > 5:
        score -= 25.0  # ruble stress — bearish
    elif usd_rub_delta_pct > 3:
        score -= 10.0
    elif usd_rub_delta_pct < -3:
        score += 10.0  # ruble strengthening — bullish

    # IMOEX vs SMA(200)
    if imoex_above_sma200:
        score += 15.0
    else:
        score -= 10.0

    return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_pre_score(
    adx: float,
    di_plus: float,
    di_minus: float,
    rsi: float,
    macd_hist: float,
    close: float,
    ema20: float,
    ema50: float,
    ema200: float,
    volume_ratio: float,
    obv_trend: str,  # "up" | "down" | "flat"
    sentiment_score: float,  # -1.0 to +1.0
    pe_ratio: float | None = None,
    sector_pe: float | None = None,
    div_yield: float | None = None,
    direction: str = "long",  # "long" | "short"
    key_rate_delta: float = 0.0,
    brent_delta_pct: float = 0.0,
    usd_rub_delta_pct: float = 0.0,
    imoex_above_sma200: bool = True,
    sector: str = "banks",
) -> tuple[float, dict[str, float]]:
    """Calculate pre-score for a potential trade setup.

    Returns
    -------
    tuple[float, dict[str, float]]
        (total_score_0_to_100, {factor_name: weighted_score})
        where weighted_score is already multiplied by the factor weight.
    """
    raw: dict[str, float] = {
        "trend": _score_trend(adx, di_plus, di_minus, direction),
        "momentum": (
            _score_momentum_long(rsi, macd_hist)
            if direction == "long"
            else _score_momentum_short(rsi, macd_hist)
        ),
        "structure": (
            _score_structure_long(close, ema20, ema50, ema200)
            if direction == "long"
            else _score_structure_short(close, ema20, ema50, ema200)
        ),
        "volume": _score_volume(volume_ratio, obv_trend, direction),
        "sentiment": _score_sentiment(sentiment_score),
        "fundamental": _score_fundamental(pe_ratio, sector_pe, div_yield),
        "macro": _score_macro(key_rate_delta, brent_delta_pct, usd_rub_delta_pct, imoex_above_sma200, sector),
    }

    breakdown: dict[str, float] = {
        factor: round(raw[factor] * SCORING_WEIGHTS[factor], 4)
        for factor in SCORING_WEIGHTS
    }
    total = round(sum(breakdown.values()), 4)
    return total, breakdown
