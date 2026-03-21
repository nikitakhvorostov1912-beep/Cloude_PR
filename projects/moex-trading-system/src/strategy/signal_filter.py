"""Signal filtering — hard rejects and soft confidence boosts.

Entry filters: reject signals in bad conditions, boost confidence in good ones.
Macro filters: block signals based on IMOEX, Brent, CBR key rate.
Exit filters: check conditions for closing positions.

OIL_TICKERS — тикеры нефтяного сектора MOEX (блокируются при низком Brent).
"""
from __future__ import annotations

from copy import copy
from typing import Optional

from src.models.market import MarketRegime
from src.models.signal import Action, TradingSignal

# Нефтяники MOEX
OIL_TICKERS = {"GAZP", "LKOH", "NVTK", "ROSN", "TATN", "SNGS", "SIBN", "TRNFP"}


def apply_entry_filters(
    signal: TradingSignal,
    features: dict,
    regime: MarketRegime,
    pre_score: float,
    **kwargs,
) -> Optional[TradingSignal]:
    """Apply hard and soft entry filters.

    Hard rejects (return None):
    - CRISIS regime
    - ADX < 20 (no trend)
    - Price below EMA200 (for longs)
    - RSI < 30 or RSI > 75 (for longs)
    - Pre-score < 45
    - Confidence < 0.60

    Soft boosts (increase confidence):
    - S1: EMA20 > EMA50 → +0.05
    - S2: MACD histogram > 0 → +0.05
    - S3: Volume ratio > 1.2 → +0.03
    - S4: Sentiment > 0 → +0.02
    - S5: Close > BB middle → +0.02

    Args:
        signal: Trading signal to filter.
        features: Dict of indicator values.
        regime: Current market regime.
        pre_score: Pre-calculated signal score (0-100).

    Returns:
        Filtered signal (possibly with boosted confidence), or None if rejected.
    """
    # HOLD signals always pass
    if signal.action == Action.HOLD:
        return signal

    # --- Hard rejects ---
    if regime == MarketRegime.CRISIS:
        return None

    adx = features.get("adx", 0)
    if adx < 20:
        return None

    close = features.get("close", 0)
    ema_200 = features.get("ema_200", 0)
    if close < ema_200 and signal.action == Action.BUY:
        return None

    rsi = features.get("rsi_14", 50)
    if signal.action == Action.BUY:
        if rsi < 30 or rsi > 75:
            return None

    if pre_score < 45:
        return None

    if signal.confidence < 0.60:
        return None

    # --- Soft boosts ---
    result = copy(signal)
    boost = 0.0

    # S1: EMA20 > EMA50
    ema_20 = features.get("ema_20", 0)
    ema_50 = features.get("ema_50", 0)
    if ema_20 > ema_50:
        boost += 0.05

    # S2: MACD histogram positive
    macd_hist = features.get("macd_histogram", 0)
    if macd_hist > 0:
        boost += 0.05

    # S3: Volume ratio > 1.2
    vol_ratio = features.get("volume_ratio_20", 1.0)
    if vol_ratio > 1.2:
        boost += 0.03

    # S4: Sentiment positive
    sentiment = features.get("sentiment", 0)
    if sentiment > 0:
        boost += 0.02

    # S5: Close above BB middle
    bb_middle = features.get("bb_middle", 0)
    if close > bb_middle:
        boost += 0.02

    result.confidence = min(1.0, result.confidence + boost)
    return result


def apply_macro_filters(
    signal: TradingSignal,
    macro: dict,
    **kwargs,
) -> Optional[TradingSignal]:
    """Apply macro-level filters.

    M1: IMOEX below SMA200 → block all longs
    M2: Brent below SMA50 → block oil sector longs
    M3: Key rate rising → reduce confidence by 0.1

    Args:
        signal: Trading signal.
        macro: Dict with keys: imoex_above_sma200, brent_above_sma50,
               key_rate_direction, key_rate, usd_rub, brent.

    Returns:
        Filtered signal or None.
    """
    # HOLD always passes
    if signal.action == Action.HOLD:
        return signal

    # M1: IMOEX below SMA200 → block longs
    if signal.action == Action.BUY:
        if not macro.get("imoex_above_sma200", True):
            return None

    # M2: Brent below SMA50 → block oil longs
    if signal.action == Action.BUY and signal.ticker in OIL_TICKERS:
        if not macro.get("brent_above_sma50", True):
            return None

    # M3: Key rate rising → reduce confidence
    result = copy(signal)
    if macro.get("key_rate_direction") == "up":
        result.confidence = max(0.0, result.confidence - 0.1)

    return result


def check_exit_conditions(
    signal: TradingSignal,
    features: dict,
    regime: MarketRegime,
) -> bool:
    """Check if an open position should be exited.

    Returns True if position should be closed.
    """
    # Crisis → exit immediately
    if regime == MarketRegime.CRISIS:
        return True

    # RSI extreme → exit
    rsi = features.get("rsi_14", 50)
    if rsi > 85 or rsi < 15:
        return True

    return False
