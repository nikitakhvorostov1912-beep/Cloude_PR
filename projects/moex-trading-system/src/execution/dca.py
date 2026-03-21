"""DCA (Dollar Cost Averaging) execution with dynamic average entry.

Inspired by hummingbot DCAExecutor (Apache 2.0), written from scratch.

Places a series of limit orders at predefined price levels below (buy)
or above (sell) current price. After each fill, recalculates average
entry and adjusts TP/SL accordingly.

Particularly useful for MOEX 2nd-tier stocks where entering a full
position at one price causes significant market impact.

Usage:
    dca = DCAExecutor(
        side="long", base_price=300.0, total_amount=100_000,
        n_levels=5, level_step_pct=0.02, lot_size=10,
        take_profit_pct=0.05, stop_loss_pct=0.03,
    )
    for level in dca.levels:
        print(f"Order #{level.level_id}: {level.quantity} @ {level.price}")
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DCALevel:
    """One level in a DCA plan.

    Attributes:
        level_id: Sequential number (0 = closest to base price).
        price: Target price for this level.
        quantity: Shares at this level.
        amount_pct: Fraction of total_amount allocated.
    """

    level_id: int
    price: float
    quantity: float
    amount_pct: float


@dataclass
class DCAState:
    """Current DCA execution state.

    Attributes:
        avg_entry_price: Volume-weighted average fill price.
        total_filled: Total shares filled across all levels.
        total_cost: Total capital deployed.
        levels_filled: Number of levels filled.
        take_profit_price: Dynamic TP (from avg_entry).
        stop_loss_price: Dynamic SL (from worst fill).
        is_complete: All levels filled or stopped.
    """

    avg_entry_price: float = 0.0
    total_filled: float = 0.0
    total_cost: float = 0.0
    levels_filled: int = 0
    take_profit_price: float = 0.0
    stop_loss_price: float = 0.0
    is_complete: bool = False


class DCAExecutor:
    """Dollar Cost Averaging executor with dynamic TP/SL.

    Args:
        side: "long" (buy dips) or "short" (sell rallies).
        base_price: Starting price (current market).
        total_amount: Total capital to deploy (in quote currency, e.g. RUB).
        n_levels: Number of entry levels.
        level_step_pct: Distance between levels as % (0.02 = 2%).
        lot_size: MOEX lot size for rounding.
        take_profit_pct: TP from avg_entry (0.05 = 5%).
        stop_loss_pct: SL from worst level (0.03 = 3%).
        distribution: "equal" | "fibonacci" | "geometric".
    """

    def __init__(
        self,
        side: str,
        base_price: float,
        total_amount: float,
        n_levels: int = 5,
        level_step_pct: float = 0.02,
        lot_size: int = 1,
        take_profit_pct: float = 0.05,
        stop_loss_pct: float = 0.03,
        distribution: str = "equal",
    ) -> None:
        self._side = side
        self._base_price = base_price
        self._total_amount = total_amount
        self._n_levels = n_levels
        self._step_pct = level_step_pct
        self._lot_size = max(1, lot_size)
        self._tp_pct = take_profit_pct
        self._sl_pct = stop_loss_pct

        self._fills: list[tuple[float, float]] = []  # (price, quantity)
        self._levels = self._build_levels(distribution)

    def _distribute(self, n: int, method: str) -> list[float]:
        """Generate allocation weights."""
        if method == "fibonacci":
            fib = [1.0, 1.0]
            for _ in range(n - 2):
                fib.append(fib[-1] + fib[-2])
            weights = fib[:n]
        elif method == "geometric":
            weights = [2.0 ** i for i in range(n)]
        else:  # equal
            weights = [1.0] * n
        total = sum(weights)
        return [w / total for w in weights]

    def _build_levels(self, distribution: str) -> list[DCALevel]:
        weights = self._distribute(self._n_levels, distribution)
        levels: list[DCALevel] = []
        for i in range(self._n_levels):
            if self._side == "long":
                price = self._base_price * (1 - self._step_pct * (i + 1))
            else:
                price = self._base_price * (1 + self._step_pct * (i + 1))
            amount = self._total_amount * weights[i]
            qty = int(amount / price // self._lot_size) * self._lot_size
            if qty < self._lot_size:
                qty = self._lot_size
            levels.append(DCALevel(
                level_id=i, price=round(price, 6),
                quantity=float(qty), amount_pct=weights[i],
            ))
        return levels

    @property
    def levels(self) -> list[DCALevel]:
        return list(self._levels)

    @property
    def state(self) -> DCAState:
        if not self._fills:
            return DCAState()
        total_qty = sum(q for _, q in self._fills)
        total_cost = sum(p * q for p, q in self._fills)
        avg = total_cost / total_qty if total_qty > 0 else 0.0

        if self._side == "long":
            tp = avg * (1 + self._tp_pct)
            worst = min(p for p, _ in self._fills)
            sl = worst * (1 - self._sl_pct)
        else:
            tp = avg * (1 - self._tp_pct)
            worst = max(p for p, _ in self._fills)
            sl = worst * (1 + self._sl_pct)

        return DCAState(
            avg_entry_price=round(avg, 6),
            total_filled=total_qty,
            total_cost=round(total_cost, 2),
            levels_filled=len(self._fills),
            take_profit_price=round(tp, 6),
            stop_loss_price=round(sl, 6),
            is_complete=len(self._fills) >= self._n_levels,
        )

    def record_fill(self, price: float, quantity: float) -> DCAState:
        """Record a fill at one of the DCA levels."""
        self._fills.append((price, quantity))
        return self.state
