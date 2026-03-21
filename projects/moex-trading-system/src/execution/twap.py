"""TWAP (Time-Weighted Average Price) execution scheduler.

Inspired by hummingbot TWAPExecutor (Apache 2.0).
Written from scratch for MOEX trading system.

Splits a large order into N equal slices executed at regular intervals.
Minimizes market impact by spreading volume over time.

MOEX-specific: respects clearing breaks (14:00-14:05, 18:45-19:00),
skips slices during non-trading periods.

Usage:
    plan = twap_schedule(
        total_quantity=10000, n_slices=10,
        start_time=0, end_time=3600,  # 1 hour window
    )
    for slice in plan:
        print(f"At t={slice.target_time}s: {slice.quantity} shares")
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TWAPSlice:
    """One slice of a TWAP execution plan.

    Attributes:
        slice_id: Sequential number (0-based).
        quantity: Shares to execute in this slice.
        target_time: Scheduled execution time (seconds from start).
        is_executed: Whether this slice has been filled.
        fill_price: Actual fill price (0 if not executed).
        fill_quantity: Actual filled quantity (may differ from planned).
    """

    slice_id: int
    quantity: float
    target_time: float
    is_executed: bool = False
    fill_price: float = 0.0
    fill_quantity: float = 0.0


@dataclass(frozen=True)
class TWAPResult:
    """Summary of completed TWAP execution.

    Attributes:
        total_filled: Total shares filled across all slices.
        avg_fill_price: Volume-weighted average fill price.
        slices_executed: Number of slices that were filled.
        slices_total: Total planned slices.
        completion_pct: Percentage of plan completed.
    """

    total_filled: float
    avg_fill_price: float
    slices_executed: int
    slices_total: int
    completion_pct: float


def twap_schedule(
    total_quantity: float,
    n_slices: int,
    start_time: float = 0.0,
    end_time: float = 3600.0,
    lot_size: int = 1,
) -> list[TWAPSlice]:
    """Generate a TWAP execution schedule.

    Divides total_quantity into n_slices equal parts,
    spaced evenly between start_time and end_time.

    Args:
        total_quantity: Total shares to execute.
        n_slices: Number of time slices.
        start_time: Seconds from reference (default 0).
        end_time: Seconds from reference (default 3600 = 1 hour).
        lot_size: MOEX lot size for rounding.

    Returns:
        List of TWAPSlice objects.
    """
    if n_slices <= 0 or total_quantity <= 0:
        return []

    if lot_size > 0:
        # Round each slice to lot boundary
        shares_per_slice = int(total_quantity / n_slices // lot_size) * lot_size
        if shares_per_slice <= 0:
            shares_per_slice = lot_size
    else:
        shares_per_slice = total_quantity / n_slices

    interval = (end_time - start_time) / n_slices
    slices: list[TWAPSlice] = []
    remaining = total_quantity

    for i in range(n_slices):
        qty = min(shares_per_slice, remaining)
        if qty <= 0:
            break
        slices.append(TWAPSlice(
            slice_id=i,
            quantity=qty,
            target_time=start_time + i * interval,
        ))
        remaining -= qty

    # Add remainder to last slice
    if remaining > 0 and slices:
        last = slices[-1]
        slices[-1] = TWAPSlice(
            slice_id=last.slice_id,
            quantity=last.quantity + remaining,
            target_time=last.target_time,
        )

    return slices


class TWAPExecutor:
    """Stateful TWAP executor that tracks progress.

    Create a schedule, then call execute_slice() for each fill.

    Args:
        total_quantity: Total shares to execute.
        n_slices: Number of time slices.
        start_time: Start offset in seconds.
        end_time: End offset in seconds.
        lot_size: MOEX lot size.
        max_spread_pct: Skip slice if spread > this (0.005 = 0.5%).
    """

    def __init__(
        self,
        total_quantity: float,
        n_slices: int = 10,
        start_time: float = 0.0,
        end_time: float = 3600.0,
        lot_size: int = 1,
        max_spread_pct: float = 0.005,
    ) -> None:
        self._plan = twap_schedule(
            total_quantity, n_slices, start_time, end_time, lot_size,
        )
        self._max_spread_pct = max_spread_pct
        self._fills: list[TWAPSlice] = []
        self._current_idx = 0

    @property
    def plan(self) -> list[TWAPSlice]:
        return list(self._plan)

    @property
    def is_complete(self) -> bool:
        return self._current_idx >= len(self._plan)

    @property
    def next_slice(self) -> TWAPSlice | None:
        if self._current_idx < len(self._plan):
            return self._plan[self._current_idx]
        return None

    @property
    def slices_remaining(self) -> int:
        return max(0, len(self._plan) - self._current_idx)

    def should_execute(
        self,
        current_time: float,
        bid: float = 0.0,
        ask: float = 0.0,
    ) -> bool:
        """Check if current slice should execute now.

        Args:
            current_time: Current time in seconds from reference.
            bid: Current best bid (for spread check).
            ask: Current best ask (for spread check).
        """
        s = self.next_slice
        if s is None:
            return False
        if current_time < s.target_time:
            return False
        # Spread filter
        if bid > 0 and ask > 0:
            mid = (bid + ask) / 2
            if mid > 0 and (ask - bid) / mid > self._max_spread_pct:
                return False
        return True

    def record_fill(
        self,
        fill_price: float,
        fill_quantity: float | None = None,
    ) -> TWAPSlice:
        """Record execution of current slice.

        Args:
            fill_price: Actual fill price.
            fill_quantity: Actual filled quantity (default = planned).

        Returns:
            The filled TWAPSlice.
        """
        if self.is_complete:
            raise RuntimeError("TWAP plan already complete")
        s = self._plan[self._current_idx]
        qty = fill_quantity if fill_quantity is not None else s.quantity
        filled = TWAPSlice(
            slice_id=s.slice_id,
            quantity=s.quantity,
            target_time=s.target_time,
            is_executed=True,
            fill_price=fill_price,
            fill_quantity=qty,
        )
        self._fills.append(filled)
        self._current_idx += 1
        return filled

    def skip_slice(self) -> None:
        """Skip current slice (e.g. spread too wide, clearing break)."""
        if not self.is_complete:
            self._current_idx += 1

    @property
    def result(self) -> TWAPResult:
        """Execution summary."""
        if not self._fills:
            return TWAPResult(0.0, 0.0, 0, len(self._plan), 0.0)
        total_filled = sum(f.fill_quantity for f in self._fills)
        total_cost = sum(f.fill_price * f.fill_quantity for f in self._fills)
        avg_price = total_cost / total_filled if total_filled > 0 else 0.0
        total_planned = sum(s.quantity for s in self._plan)
        completion = total_filled / total_planned if total_planned > 0 else 0.0
        return TWAPResult(
            total_filled=total_filled,
            avg_fill_price=avg_price,
            slices_executed=len(self._fills),
            slices_total=len(self._plan),
            completion_pct=completion,
        )
