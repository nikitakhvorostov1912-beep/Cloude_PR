"""Grid trading executor with dynamic range shifting.

Inspired by hummingbot GridExecutor (Apache 2.0), written from scratch.

Places buy and sell orders at evenly-spaced price levels within a range.
Profit comes from collecting the spread between adjacent levels.
When price exits the range, the grid shifts dynamically.

Best for sideways/ranging markets on MOEX (e.g. SBER in consolidation).

Usage:
    grid = GridExecutor(
        lower=290.0, upper=310.0, n_levels=10,
        total_amount=500_000, lot_size=10,
    )
    for level in grid.levels:
        print(f"{level.side} {level.quantity} @ {level.price}")
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GridLevel:
    """One level in the grid.

    Attributes:
        level_id: Sequential index.
        price: Price for this level.
        side: "buy" or "sell".
        quantity: Shares at this level.
        is_active: Whether order should be placed.
    """

    level_id: int
    price: float
    side: str
    quantity: float
    is_active: bool = True


@dataclass(frozen=True)
class GridStats:
    """Grid execution summary."""

    n_levels: int
    lower_price: float
    upper_price: float
    level_spacing: float
    level_spacing_pct: float
    total_buy_levels: int
    total_sell_levels: int
    estimated_profit_per_round: float


class GridExecutor:
    """Grid trading executor.

    Creates N evenly-spaced price levels between lower and upper.
    Below current mid → buy orders. Above current mid → sell orders.

    Args:
        lower: Lower bound of grid range.
        upper: Upper bound of grid range.
        n_levels: Number of grid levels.
        total_amount: Total capital (RUB).
        lot_size: MOEX lot size.
        max_open_orders: Max simultaneous active levels.
    """

    def __init__(
        self,
        lower: float,
        upper: float,
        n_levels: int = 10,
        total_amount: float = 100_000,
        lot_size: int = 1,
        max_open_orders: int | None = None,
    ) -> None:
        if lower >= upper:
            raise ValueError(f"lower must be < upper: {lower} >= {upper}")
        if n_levels < 2:
            raise ValueError(f"n_levels must be >= 2, got {n_levels}")
        self._lower = lower
        self._upper = upper
        self._n_levels = n_levels
        self._total_amount = total_amount
        self._lot_size = max(1, lot_size)
        self._max_open = max_open_orders or n_levels
        self._fills: list[tuple[float, float, str]] = []

    @property
    def levels(self) -> list[GridLevel]:
        return self._build_levels((self._lower + self._upper) / 2)

    def levels_for_price(self, current_price: float) -> list[GridLevel]:
        """Generate grid levels relative to current price."""
        return self._build_levels(current_price)

    def _build_levels(self, mid_price: float) -> list[GridLevel]:
        spacing = (self._upper - self._lower) / (self._n_levels - 1)
        amount_per_level = self._total_amount / self._n_levels
        result: list[GridLevel] = []

        for i in range(self._n_levels):
            price = self._lower + i * spacing
            qty = int(amount_per_level / price // self._lot_size) * self._lot_size
            if qty < self._lot_size:
                qty = self._lot_size
            side = "buy" if price < mid_price else "sell"
            active = i < self._max_open
            result.append(GridLevel(
                level_id=i, price=round(price, 6),
                side=side, quantity=float(qty), is_active=active,
            ))
        return result

    def shift_range(self, new_lower: float, new_upper: float) -> list[GridLevel]:
        """Shift grid to a new range (when price breaks out)."""
        self._lower = new_lower
        self._upper = new_upper
        return self.levels

    @property
    def stats(self) -> GridStats:
        spacing = (self._upper - self._lower) / (self._n_levels - 1)
        mid = (self._upper + self._lower) / 2
        spacing_pct = spacing / mid if mid > 0 else 0
        levels = self.levels
        n_buy = sum(1 for lv in levels if lv.side == "buy")
        n_sell = sum(1 for lv in levels if lv.side == "sell")
        est_profit = spacing * (self._total_amount / self._n_levels / mid)
        return GridStats(
            n_levels=self._n_levels,
            lower_price=self._lower,
            upper_price=self._upper,
            level_spacing=round(spacing, 4),
            level_spacing_pct=round(spacing_pct, 6),
            total_buy_levels=n_buy,
            total_sell_levels=n_sell,
            estimated_profit_per_round=round(est_profit, 2),
        )

    def record_fill(self, price: float, quantity: float, side: str) -> None:
        """Record a grid fill."""
        self._fills.append((price, quantity, side))

    @property
    def realized_pnl(self) -> float:
        """Simple PnL from matched buy-sell pairs."""
        buys = [(p, q) for p, q, s in self._fills if s == "buy"]
        sells = [(p, q) for p, q, s in self._fills if s == "sell"]
        pnl = 0.0
        for (bp, bq), (sp, sq) in zip(buys, sells):
            matched_qty = min(bq, sq)
            pnl += (sp - bp) * matched_qty
        return pnl
