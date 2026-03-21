"""Market domain models: OHLCVBar, MarketRegime."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class MarketRegime(str, Enum):
    """Detected market regime for strategy routing."""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGE = "range"
    WEAK_TREND = "weak_trend"
    CRISIS = "crisis"


@dataclass
class OHLCVBar:
    """Single OHLCV candle."""
    ticker: str
    dt: date
    open: float
    high: float
    low: float
    close: float
    volume: float
