"""Trading signal models."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


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
