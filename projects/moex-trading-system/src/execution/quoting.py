"""Smart execution engine — passive quoting strategies for optimal order placement.

Ported from StockSharp QuotingProcessor architecture (Apache 2.0) to Python.
Implements Strategy pattern: QuotingEngine + pluggable IQuotingBehavior.

Behaviors:
- BestByPrice: quote at best bid/ask with offset
- BestByVolume: find price level with target volume ahead
- LastTrade: quote at last trade price
- Limit: fixed price quoting
- Level: quote at specific order book depth
- Market: follow/oppose/mid best prices
- TWAP: time-weighted average price (periodic slicing)
- VWAP: volume-weighted average price (cumulative)

Designed for MOEX: supports price step rounding, lot sizes.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class ActionType(str, Enum):
    NONE = "none"
    REGISTER = "register"
    CANCEL = "cancel"
    FINISH = "finish"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


@dataclass
class QuoteLevel:
    """Single order book level."""
    price: float
    volume: float


@dataclass
class QuotingInput:
    """Market data snapshot for quoting decision."""
    current_time: float = 0.0            # unix timestamp
    best_bid: float | None = None
    best_ask: float | None = None
    last_trade_price: float | None = None
    last_trade_volume: float | None = None
    bids: list[QuoteLevel] = field(default_factory=list)
    asks: list[QuoteLevel] = field(default_factory=list)
    position: float = 0.0                # current filled qty (signed)
    current_order_price: float | None = None
    current_order_volume: float | None = None
    is_order_pending: bool = False
    is_trading_allowed: bool = True


@dataclass
class QuotingAction:
    """Recommended action from the quoting engine."""
    action: ActionType
    price: float = 0.0
    volume: float = 0.0
    order_type: OrderType = OrderType.LIMIT
    reason: str = ""

    @classmethod
    def none(cls, reason: str = "") -> QuotingAction:
        return cls(ActionType.NONE, reason=reason)

    @classmethod
    def register(cls, price: float, volume: float,
                 order_type: OrderType = OrderType.LIMIT, reason: str = "") -> QuotingAction:
        return cls(ActionType.REGISTER, price, volume, order_type, reason)

    @classmethod
    def cancel(cls, reason: str = "") -> QuotingAction:
        return cls(ActionType.CANCEL, reason=reason)

    @classmethod
    def finish(cls, success: bool = True, reason: str = "") -> QuotingAction:
        return cls(ActionType.FINISH, reason=reason)


# ---------------------------------------------------------------------------
# Quoting Behavior interface
# ---------------------------------------------------------------------------

class QuotingBehavior(ABC):
    """Abstract base for price calculation strategy."""

    @abstractmethod
    def calculate_best_price(
        self,
        side: Side,
        best_bid: float | None,
        best_ask: float | None,
        last_trade_price: float | None,
        last_trade_volume: float | None,
        bids: list[QuoteLevel],
        asks: list[QuoteLevel],
    ) -> float | None:
        """Calculate the target price for quoting."""
        ...

    @abstractmethod
    def need_requote(
        self,
        current_price: float | None,
        current_volume: float | None,
        new_volume: float,
        best_price: float | None,
        current_time: float = 0.0,
    ) -> float | None:
        """Check if requoting needed. Returns new price or None."""
        ...


# ---------------------------------------------------------------------------
# Concrete behaviors
# ---------------------------------------------------------------------------

class BestByPriceBehavior(QuotingBehavior):
    """Quote at best bid/ask. Requote when price drifts beyond offset."""

    def __init__(self, price_offset: float = 0.0):
        self.price_offset = price_offset

    def calculate_best_price(self, side, best_bid, best_ask, last_trade_price,
                             last_trade_volume, bids, asks) -> float | None:
        price = (best_bid if side == Side.BUY else best_ask) or last_trade_price
        return price

    def need_requote(self, current_price, current_volume, new_volume,
                     best_price, current_time=0.0) -> float | None:
        if best_price is None:
            return None
        if current_price is None:
            return best_price
        if abs(current_price - best_price) >= self.price_offset or current_volume != new_volume:
            return best_price
        return None


class BestByVolumeBehavior(QuotingBehavior):
    """Quote at the price level where cumulative volume reaches threshold."""

    def __init__(self, volume_threshold: float = 100.0):
        self.volume_threshold = volume_threshold

    def calculate_best_price(self, side, best_bid, best_ask, last_trade_price,
                             last_trade_volume, bids, asks) -> float | None:
        quotes = bids if side == Side.BUY else asks
        if not quotes:
            return last_trade_price
        cumulative = 0.0
        for q in quotes:
            cumulative += q.volume
            if cumulative > self.volume_threshold:
                return q.price
        return quotes[-1].price if quotes else last_trade_price

    def need_requote(self, current_price, current_volume, new_volume,
                     best_price, current_time=0.0) -> float | None:
        if best_price is None:
            return None
        if current_price is None or current_price != best_price or current_volume != new_volume:
            return best_price
        return None


class LastTradeBehavior(QuotingBehavior):
    """Quote at last trade price."""

    def __init__(self, price_offset: float = 0.0):
        self.price_offset = price_offset

    def calculate_best_price(self, side, best_bid, best_ask, last_trade_price,
                             last_trade_volume, bids, asks) -> float | None:
        return last_trade_price

    def need_requote(self, current_price, current_volume, new_volume,
                     best_price, current_time=0.0) -> float | None:
        if best_price is None:
            return None
        if current_price is None:
            return best_price
        if abs(current_price - best_price) >= self.price_offset or current_volume != new_volume:
            return best_price
        return None


class LimitBehavior(QuotingBehavior):
    """Quote at a fixed limit price."""

    def __init__(self, limit_price: float):
        self.limit_price = limit_price

    def calculate_best_price(self, side, best_bid, best_ask, last_trade_price,
                             last_trade_volume, bids, asks) -> float | None:
        return self.limit_price

    def need_requote(self, current_price, current_volume, new_volume,
                     best_price, current_time=0.0) -> float | None:
        if best_price is None:
            return None
        if current_price is None or current_price != best_price or current_volume != new_volume:
            return best_price
        return None


class MarketFollowBehavior(QuotingBehavior):
    """Follow same-side best price with optional offset.

    price_type: 'follow' = same side, 'oppose' = opposite side, 'mid' = midpoint
    """

    def __init__(self, price_type: str = "follow", price_offset: float = 0.0,
                 requote_offset: float = 0.0):
        self.price_type = price_type
        self.price_offset = price_offset
        self.requote_offset = requote_offset

    def calculate_best_price(self, side, best_bid, best_ask, last_trade_price,
                             last_trade_volume, bids, asks) -> float | None:
        if self.price_type == "follow":
            base = best_bid if side == Side.BUY else best_ask
        elif self.price_type == "oppose":
            base = best_ask if side == Side.BUY else best_bid
        elif self.price_type == "mid":
            if best_bid is not None and best_ask is not None:
                base = (best_bid + best_ask) / 2
            else:
                base = None
        else:
            base = None

        base = base or last_trade_price
        if base is None:
            return None

        return base + self.price_offset if side == Side.BUY else base - self.price_offset

    def need_requote(self, current_price, current_volume, new_volume,
                     best_price, current_time=0.0) -> float | None:
        if best_price is None:
            return None
        if current_price is None:
            return best_price
        if abs(current_price - best_price) >= self.requote_offset or current_volume != new_volume:
            return best_price
        return None


class LevelBehavior(QuotingBehavior):
    """Quote at a specific depth level in the order book."""

    def __init__(self, min_level: int = 0, max_level: int = 2, price_step: float = 0.01):
        self.min_level = min_level
        self.max_level = max_level
        self.price_step = price_step

    def calculate_best_price(self, side, best_bid, best_ask, last_trade_price,
                             last_trade_volume, bids, asks) -> float | None:
        quotes = bids if side == Side.BUY else asks
        if not quotes:
            return last_trade_price

        min_q = quotes[self.min_level] if len(quotes) > self.min_level else None
        max_q = quotes[self.max_level] if len(quotes) > self.max_level else None

        if min_q is None:
            return None

        from_price = min_q.price
        to_price = max_q.price if max_q else quotes[-1].price
        mid = (from_price + to_price) / 2

        if self.price_step > 0:
            mid = round(mid / self.price_step) * self.price_step
        return mid

    def need_requote(self, current_price, current_volume, new_volume,
                     best_price, current_time=0.0) -> float | None:
        if best_price is None:
            return None
        if current_price is None or current_price != best_price or current_volume != new_volume:
            return best_price
        return None


class TWAPBehavior(QuotingBehavior):
    """Time-Weighted Average Price — periodic order placement with rolling average."""

    def __init__(self, interval_seconds: float = 60.0, buffer_size: int = 10):
        self.interval = interval_seconds
        self.buffer_size = buffer_size
        self._prices: list[float] = []
        self._last_order_time: float | None = None

    def calculate_best_price(self, side, best_bid, best_ask, last_trade_price,
                             last_trade_volume, bids, asks) -> float | None:
        if last_trade_price is not None:
            self._prices.append(last_trade_price)
            if len(self._prices) > self.buffer_size:
                self._prices = self._prices[-self.buffer_size:]
        return sum(self._prices) / len(self._prices) if self._prices else None

    def need_requote(self, current_price, current_volume, new_volume,
                     best_price, current_time=0.0) -> float | None:
        if best_price is None:
            return None
        if self._last_order_time is not None and (current_time - self._last_order_time) < self.interval:
            return None
        if current_price is None or current_price != best_price or current_volume != new_volume:
            self._last_order_time = current_time
            return best_price
        return None


class VWAPBehavior(QuotingBehavior):
    """Volume-Weighted Average Price — cumulative price×volume tracking."""

    def __init__(self, requote_offset: float = 0.0):
        self.requote_offset = requote_offset
        self._cum_pv: float = 0.0
        self._cum_vol: float = 0.0

    def calculate_best_price(self, side, best_bid, best_ask, last_trade_price,
                             last_trade_volume, bids, asks) -> float | None:
        if last_trade_price is not None and last_trade_volume is not None:
            self._cum_pv += last_trade_price * last_trade_volume
            self._cum_vol += last_trade_volume
        return self._cum_pv / self._cum_vol if self._cum_vol > 0 else None

    def need_requote(self, current_price, current_volume, new_volume,
                     best_price, current_time=0.0) -> float | None:
        if best_price is None:
            return None
        if current_price is None:
            return best_price
        if abs(current_price - best_price) >= self.requote_offset or current_volume != new_volume:
            return best_price
        return None


# ---------------------------------------------------------------------------
# Quoting Engine
# ---------------------------------------------------------------------------

class QuotingEngine:
    """Smart execution engine — decides when and where to place/modify orders.

    Pure functional: receives QuotingInput, returns QuotingAction.
    Does NOT submit orders — the caller (adapter/broker) does that.

    Usage:
        engine = QuotingEngine(
            behavior=TWAPBehavior(interval_seconds=30),
            side=Side.BUY,
            total_volume=100,
            max_order_volume=10,
            timeout=300,  # 5 min
            price_step=0.01,  # SBER tick size
        )

        action = engine.process(QuotingInput(
            best_bid=280.50, best_ask=280.60,
            last_trade_price=280.55, last_trade_volume=10,
            current_time=time.time(),
        ))

        if action.action == ActionType.REGISTER:
            broker.submit_limit_order(action.price, action.volume)
    """

    def __init__(
        self,
        behavior: QuotingBehavior,
        side: Side,
        total_volume: float,
        max_order_volume: float | None = None,
        timeout: float = 0.0,
        price_step: float = 0.01,
        start_time: float = 0.0,
    ):
        self.behavior = behavior
        self.side = side
        self.total_volume = total_volume
        self.max_order_volume = max_order_volume or total_volume
        self.timeout = timeout
        self.price_step = price_step
        self.start_time = start_time
        self._filled: float = 0.0

    @property
    def remaining_volume(self) -> float:
        return max(0.0, self.total_volume - self._filled)

    @property
    def is_complete(self) -> bool:
        return self.remaining_volume <= 0

    def on_fill(self, volume: float) -> None:
        """Call when an order fill occurs."""
        self._filled += abs(volume)

    def _round_price(self, price: float) -> float:
        if self.price_step > 0:
            return round(price / self.price_step) * self.price_step
        return price

    def process(self, inp: QuotingInput) -> QuotingAction:
        """Process market data and return recommended action.

        Args:
            inp: Current market snapshot and order state.

        Returns:
            QuotingAction with recommendation (register/cancel/none/finish).
        """
        # Check timeout
        if self.timeout > 0 and self.start_time > 0:
            if (inp.current_time - self.start_time) >= self.timeout:
                return QuotingAction.finish(False, "Timeout reached")

        # Check completion
        remaining = self.remaining_volume
        if remaining <= 0:
            return QuotingAction.finish(True, "Target volume filled")

        # Don't interfere with pending orders
        if inp.is_order_pending:
            return QuotingAction.none("Order pending")

        # Calculate target volume
        new_volume = min(self.max_order_volume, remaining)

        # Calculate best price via behavior
        best_price = self.behavior.calculate_best_price(
            self.side, inp.best_bid, inp.best_ask,
            inp.last_trade_price, inp.last_trade_volume,
            inp.bids, inp.asks,
        )

        if best_price is None:
            return QuotingAction.none("No market data")

        best_price = self._round_price(best_price)

        # Check if requoting needed
        quoting_price = self.behavior.need_requote(
            inp.current_order_price, inp.current_order_volume,
            new_volume, best_price, inp.current_time,
        )

        if quoting_price is None:
            return QuotingAction.none("Current order optimal")

        quoting_price = self._round_price(quoting_price)

        # Decide: register new or cancel existing
        if inp.current_order_price is None:
            if not inp.is_trading_allowed:
                return QuotingAction.none("Trading not allowed")
            order_type = OrderType.MARKET if quoting_price == 0 else OrderType.LIMIT
            return QuotingAction.register(
                quoting_price, new_volume, order_type,
                f"{self.side.value} {new_volume} @ {quoting_price}",
            )
        else:
            return QuotingAction.cancel(
                f"Requote: {inp.current_order_price}→{quoting_price}",
            )
