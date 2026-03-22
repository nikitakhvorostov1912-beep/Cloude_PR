"""Core domain models for the MOEX trading bot.

All models use Pydantic v2 for validation, serialization, and type safety.
These are the canonical data structures passed between all modules.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class InstrumentType(str, Enum):
    EQUITY = "equity"
    FUTURES = "futures"
    OPTIONS = "options"
    FX = "fx"


class Bar(BaseModel):
    """Single OHLCV bar."""

    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    instrument: str
    timeframe: str = "1d"

    @field_validator("low")
    @classmethod
    def high_gte_low(cls, v: float, info) -> float:
        if "high" in info.data and info.data["high"] < v:
            raise ValueError("high must be >= low")
        return v


class Signal(BaseModel):
    """Trading signal from a strategy."""

    instrument: str
    side: Side
    strength: float = Field(ge=-1.0, le=1.0)
    strategy_name: str
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    metadata: dict = Field(default_factory=dict)


class Order(BaseModel):
    """Order to be executed."""

    instrument: str
    side: Side
    quantity: float = Field(gt=0)
    order_type: OrderType = OrderType.MARKET
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    strategy_name: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    fill_price: float | None = None
    fill_timestamp: datetime | None = None
    commission: float = 0.0


class Position(BaseModel):
    """Open position."""

    instrument: str
    side: Side
    quantity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    stop_loss: float | None = None
    take_profit: float | None = None
    entry_timestamp: datetime = Field(default_factory=datetime.now)
    strategy_name: str = ""
    instrument_type: InstrumentType = InstrumentType.EQUITY
    lot_size: int = 1
    price_step: float = 0.01

    @property
    def unrealized_pnl(self) -> float:
        diff = self.current_price - self.entry_price
        if self.side == Side.SHORT:
            diff = -diff
        return diff * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        notional = self.entry_price * self.quantity
        if notional <= 0:
            return 0.0
        return self.unrealized_pnl / notional


class Portfolio(BaseModel):
    """Portfolio state snapshot."""

    positions: list[Position] = Field(default_factory=list)
    cash: float = Field(ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def total_value(self) -> float:
        positions_value = sum(p.current_price * p.quantity for p in self.positions)
        return self.cash + positions_value

    @property
    def exposure(self) -> float:
        tv = self.total_value
        if tv <= 0:
            return 0.0
        return sum(p.current_price * p.quantity for p in self.positions) / tv


class TradeResult(BaseModel):
    """Completed trade for backtest reporting."""

    instrument: str
    side: Side
    entry_price: float
    exit_price: float
    quantity: float
    entry_timestamp: datetime
    exit_timestamp: datetime
    strategy_name: str = ""
    commission: float = 0.0
    slippage: float = 0.0

    @property
    def gross_pnl(self) -> float:
        diff = self.exit_price - self.entry_price
        if self.side == Side.SHORT:
            diff = -diff
        return diff * self.quantity

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.commission - self.slippage

    @property
    def duration(self) -> float:
        return (self.exit_timestamp - self.entry_timestamp).total_seconds()

    @property
    def return_pct(self) -> float:
        notional = self.entry_price * self.quantity
        if notional <= 0:
            return 0.0
        return self.net_pnl / notional
