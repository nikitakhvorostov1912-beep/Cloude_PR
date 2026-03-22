"""Trading signal models."""
from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REDUCE = "reduce"


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class TradingSignal:
    """Signal emitted by a strategy."""

    ticker: str
    action: Action
    direction: Direction
    confidence: float = 0.0
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    reasoning: str = ""
    pre_score: float = 0.0
    time_stop_days: int | None = None

    def with_pre_score(self, score: float) -> TradingSignal:
        """Return a copy with pre_score set."""
        result = copy(self)
        result.pre_score = score
        return result
