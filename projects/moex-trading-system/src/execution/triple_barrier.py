"""Triple Barrier position management — TP / SL / Time / Trailing.

Inspired by hummingbot PositionExecutor (Apache 2.0) and
Marcos Lopez de Prado "Advances in Financial Machine Learning" Ch.3.

Four exit conditions (barriers) for any open position:
1. Take Profit: price crosses TP level
2. Stop Loss: price crosses SL level
3. Time Limit: position held longer than max_duration
4. Trailing Stop: price retreats from peak by trailing_delta

Usage:
    barrier = TripleBarrier(
        side="long", entry_price=300.0,
        take_profit_pct=0.05, stop_loss_pct=0.02,
        time_limit_seconds=3600, trailing_stop_pct=0.03,
        trailing_activation_pct=0.02,
    )
    barrier.update(price=310.0, elapsed_seconds=600)
    if barrier.is_triggered:
        print(barrier.exit_reason)  # "take_profit"
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExitReason(str, Enum):
    NONE = "none"
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TIME_LIMIT = "time_limit"
    TRAILING_STOP = "trailing_stop"


@dataclass
class BarrierState:
    """Current state of the triple barrier.

    Attributes:
        is_triggered: True if any barrier hit.
        exit_reason: Which barrier triggered.
        exit_price: Price at trigger (last update price).
        peak_price: Best price seen since entry (for trailing).
        elapsed_seconds: Time since entry.
        unrealized_pnl_pct: Current PnL as % of entry.
    """

    is_triggered: bool = False
    exit_reason: ExitReason = ExitReason.NONE
    exit_price: float = 0.0
    peak_price: float = 0.0
    elapsed_seconds: float = 0.0
    unrealized_pnl_pct: float = 0.0


class TripleBarrier:
    """Four-barrier position exit manager.

    Tracks price against entry and triggers exit when any barrier is hit.
    Barriers are optional — set to None to disable.

    Args:
        side: "long" or "short".
        entry_price: Position entry price.
        take_profit_pct: TP as fraction of entry (0.05 = 5%). None to disable.
        stop_loss_pct: SL as fraction of entry (0.02 = 2%). None to disable.
        time_limit_seconds: Max hold time in seconds. None to disable.
        trailing_stop_pct: Trailing delta from peak as fraction. None to disable.
        trailing_activation_pct: Min profit before trailing activates. None = immediate.
    """

    def __init__(
        self,
        side: str,
        entry_price: float,
        take_profit_pct: float | None = None,
        stop_loss_pct: float | None = None,
        time_limit_seconds: float | None = None,
        trailing_stop_pct: float | None = None,
        trailing_activation_pct: float | None = None,
    ) -> None:
        if side not in ("long", "short"):
            raise ValueError(f"side must be 'long' or 'short', got '{side}'")
        if entry_price <= 0:
            raise ValueError(f"entry_price must be > 0, got {entry_price}")

        self._side = side
        self._entry_price = entry_price
        self._tp_pct = take_profit_pct
        self._sl_pct = stop_loss_pct
        self._time_limit = time_limit_seconds
        self._trailing_pct = trailing_stop_pct
        self._trailing_activation = trailing_activation_pct

        self._peak_price = entry_price
        self._trailing_active = trailing_activation_pct is None
        self._triggered = False
        self._exit_reason = ExitReason.NONE
        self._last_price = entry_price
        self._elapsed = 0.0

    @property
    def is_triggered(self) -> bool:
        return self._triggered

    @property
    def exit_reason(self) -> ExitReason:
        return self._exit_reason

    @property
    def state(self) -> BarrierState:
        return BarrierState(
            is_triggered=self._triggered,
            exit_reason=self._exit_reason,
            exit_price=self._last_price,
            peak_price=self._peak_price,
            elapsed_seconds=self._elapsed,
            unrealized_pnl_pct=self._pnl_pct(self._last_price),
        )

    def _pnl_pct(self, price: float) -> float:
        if self._entry_price <= 0:
            return 0.0
        if self._side == "long":
            return (price - self._entry_price) / self._entry_price
        return (self._entry_price - price) / self._entry_price

    def update(self, price: float, elapsed_seconds: float = 0.0) -> ExitReason:
        """Update with current price and elapsed time.

        Args:
            price: Current market price.
            elapsed_seconds: Total seconds since position opened.

        Returns:
            ExitReason if triggered on this update, else NONE.
        """
        if self._triggered:
            return self._exit_reason

        self._last_price = price
        self._elapsed = elapsed_seconds
        pnl_pct = self._pnl_pct(price)

        # Update peak for trailing
        if self._side == "long" and price > self._peak_price:
            self._peak_price = price
        elif self._side == "short" and price < self._peak_price:
            self._peak_price = price

        # 1. Take Profit
        if self._tp_pct is not None and pnl_pct >= self._tp_pct:
            return self._trigger(ExitReason.TAKE_PROFIT)

        # 2. Stop Loss
        if self._sl_pct is not None and pnl_pct <= -self._sl_pct:
            return self._trigger(ExitReason.STOP_LOSS)

        # 3. Time Limit
        if self._time_limit is not None and elapsed_seconds >= self._time_limit:
            return self._trigger(ExitReason.TIME_LIMIT)

        # 4. Trailing Stop
        if self._trailing_pct is not None:
            # Activate trailing when profit exceeds activation threshold
            if not self._trailing_active and self._trailing_activation is not None:
                if pnl_pct >= self._trailing_activation:
                    self._trailing_active = True

            if self._trailing_active:
                if self._side == "long":
                    trail_price = self._peak_price * (1 - self._trailing_pct)
                    if price <= trail_price:
                        return self._trigger(ExitReason.TRAILING_STOP)
                else:
                    trail_price = self._peak_price * (1 + self._trailing_pct)
                    if price >= trail_price:
                        return self._trigger(ExitReason.TRAILING_STOP)

        return ExitReason.NONE

    def _trigger(self, reason: ExitReason) -> ExitReason:
        self._triggered = True
        self._exit_reason = reason
        return reason
