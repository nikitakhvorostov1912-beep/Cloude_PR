"""Position FIFO lifecycle tracker for MOEX instruments.

Inspired by barter-rs engine/state/position.rs (MIT License).
Written from scratch in Python with MOEX-specific features:
- FIFO PnL accounting (required for Russian NDFL tax)
- Lot size validation
- Position flip (long→short in one trade)
- Fees tracking (enter + exit)
- Realized + unrealized PnL

Usage:
    tracker = PositionTracker(lot_size=10, price_step=0.01)
    tracker.open_trade(side="long", price=300.0, quantity=100, fee=30.0)
    tracker.open_trade(side="long", price=310.0, quantity=50, fee=15.0)
    closed = tracker.close_trade(price=320.0, quantity=80, fee=24.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from typing import Literal


@dataclass
class Entry:
    """Single entry (lot) in a position — FIFO tracking unit.

    Attributes:
        price: Entry price per share.
        quantity: Number of shares in this entry.
        side: "long" or "short".
        fee: Fees paid for this entry.
        timestamp: When the entry was created.
    """

    price: float
    quantity: float
    side: Literal["long", "short"]
    fee: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ClosedTrade:
    """Result of closing (fully or partially) a position.

    Attributes:
        side: "long" or "short".
        entry_price: Weighted average entry price for closed shares.
        exit_price: Price at which position was closed.
        quantity: Number of shares closed.
        pnl_gross: Gross PnL before fees.
        pnl_net: Net PnL after fees.
        fees_enter: Entry fees allocated to closed shares.
        fees_exit: Exit fees.
        holding_period_sec: Seconds from earliest entry to close.
    """

    side: Literal["long", "short"]
    entry_price: float
    exit_price: float
    quantity: float
    pnl_gross: float
    pnl_net: float
    fees_enter: float
    fees_exit: float
    holding_period_sec: float


class PositionTracker:
    """FIFO position lifecycle tracker.

    Handles:
    - Opening new positions (long or short)
    - Increasing existing positions (same side)
    - Partial reduction (opposite side trade, less than position)
    - Full close (opposite side trade, equal to position)
    - Position flip (opposite side trade, MORE than position — close + open new)

    All PnL is FIFO-based: earliest entries are closed first.
    This is required for Russian NDFL tax calculation.

    Args:
        lot_size: Shares per lot for MOEX instrument (e.g. SBER=10).
        price_step: Minimum price increment (e.g. SBER=0.01, Si=1.0).
    """

    def __init__(
        self,
        lot_size: int = 1,
        price_step: float = 0.01,
    ) -> None:
        self._entries: deque[Entry] = deque()
        self._lot_size = lot_size
        self._price_step = price_step
        self._side: Literal["long", "short"] | None = None
        self._total_quantity: float = 0.0
        self._quantity_max: float = 0.0
        self._realized_pnl: float = 0.0
        self._total_fees: float = 0.0

    # --- Properties ---

    @property
    def is_open(self) -> bool:
        return self._total_quantity > 0

    @property
    def side(self) -> Literal["long", "short"] | None:
        return self._side

    @property
    def quantity(self) -> float:
        return self._total_quantity

    @property
    def quantity_max(self) -> float:
        """Peak quantity ever held in this position direction."""
        return self._quantity_max

    @property
    def average_entry_price(self) -> float:
        """Weighted average entry price of all open entries."""
        if self._total_quantity <= 0:
            return 0.0
        total_cost = sum(e.price * e.quantity for e in self._entries)
        return total_cost / self._total_quantity

    @property
    def realized_pnl(self) -> float:
        """Cumulative realized PnL from all closed trades."""
        return self._realized_pnl

    @property
    def total_fees(self) -> float:
        return self._total_fees

    @property
    def entries_count(self) -> int:
        return len(self._entries)

    def unrealized_pnl(self, current_price: float) -> float:
        """Unrealized PnL at given market price."""
        if not self.is_open or self._side is None:
            return 0.0
        if self._side == "long":
            return (current_price - self.average_entry_price) * self._total_quantity
        return (self.average_entry_price - current_price) * self._total_quantity

    # --- Validation ---

    def _validate_lot_quantity(self, quantity: float) -> float:
        """Round quantity down to nearest lot boundary."""
        if self._lot_size <= 0:
            return quantity
        lots = int(quantity // self._lot_size)
        return float(lots * self._lot_size)

    # --- Trading ---

    def open_trade(
        self,
        side: Literal["long", "short"],
        price: float,
        quantity: float,
        fee: float = 0.0,
        timestamp: datetime | None = None,
    ) -> list[ClosedTrade]:
        """Process a new trade. Returns list of closed trades (if any).

        If the trade is the SAME side as current position → increase.
        If OPPOSITE side → reduce/close/flip. Flip returns a ClosedTrade
        for the closed portion and opens new position with remainder.
        """
        if price <= 0 or quantity <= 0:
            return []

        quantity = self._validate_lot_quantity(quantity)
        if quantity <= 0:
            return []

        ts = timestamp or datetime.now()
        self._total_fees += fee
        closed_trades: list[ClosedTrade] = []

        if not self.is_open:
            # No position — open new
            self._side = side
            self._entries.append(Entry(price, quantity, side, fee, ts))
            self._total_quantity = quantity
            self._quantity_max = quantity
            return closed_trades

        if side == self._side:
            # Same direction — increase position
            self._entries.append(Entry(price, quantity, side, fee, ts))
            self._total_quantity += quantity
            if self._total_quantity > self._quantity_max:
                self._quantity_max = self._total_quantity
            return closed_trades

        # Opposite direction — reduce / close / flip
        remaining = quantity
        total_closed_qty = 0.0
        total_entry_cost = 0.0
        total_entry_fees = 0.0
        earliest_ts = ts

        # FIFO: close earliest entries first
        while remaining > 0 and self._entries:
            entry = self._entries[0]
            if entry.timestamp < earliest_ts:
                earliest_ts = entry.timestamp

            if entry.quantity <= remaining:
                # Fully consume this entry
                total_closed_qty += entry.quantity
                total_entry_cost += entry.price * entry.quantity
                total_entry_fees += entry.fee
                remaining -= entry.quantity
                self._entries.popleft()
            else:
                # Partially consume this entry
                total_closed_qty += remaining
                total_entry_cost += entry.price * remaining
                fee_portion = entry.fee * (remaining / entry.quantity)
                total_entry_fees += fee_portion
                entry.quantity -= remaining
                entry.fee -= fee_portion
                remaining = 0.0

        self._total_quantity -= total_closed_qty

        if total_closed_qty > 0:
            avg_entry = total_entry_cost / total_closed_qty
            if self._side == "long":
                pnl_gross = (price - avg_entry) * total_closed_qty
            else:
                pnl_gross = (avg_entry - price) * total_closed_qty

            exit_fee_portion = fee * (total_closed_qty / quantity)
            pnl_net = pnl_gross - total_entry_fees - exit_fee_portion
            self._realized_pnl += pnl_net

            hold_sec = (ts - earliest_ts).total_seconds()
            closed_trades.append(ClosedTrade(
                side=self._side,
                entry_price=avg_entry,
                exit_price=price,
                quantity=total_closed_qty,
                pnl_gross=pnl_gross,
                pnl_net=pnl_net,
                fees_enter=total_entry_fees,
                fees_exit=exit_fee_portion,
                holding_period_sec=hold_sec,
            ))

        # Position flip: remaining quantity opens opposite direction
        if remaining > 0 and not self._entries:
            flip_fee = fee * (remaining / quantity)
            new_side = side
            self._side = new_side
            self._entries.append(Entry(price, remaining, new_side, flip_fee, ts))
            self._total_quantity = remaining
            self._quantity_max = remaining
        elif self._total_quantity <= 0:
            # Fully closed, no flip
            self._side = None
            self._total_quantity = 0.0
            self._quantity_max = 0.0

        return closed_trades

    def close_all(
        self,
        price: float,
        fee: float = 0.0,
        timestamp: datetime | None = None,
    ) -> list[ClosedTrade]:
        """Close entire position at given price."""
        if not self.is_open or self._side is None:
            return []
        opposite = "short" if self._side == "long" else "long"
        return self.open_trade(opposite, price, self._total_quantity, fee, timestamp)

    def reset(self) -> None:
        """Clear all state."""
        self._entries.clear()
        self._side = None
        self._total_quantity = 0.0
        self._quantity_max = 0.0
        self._realized_pnl = 0.0
        self._total_fees = 0.0
