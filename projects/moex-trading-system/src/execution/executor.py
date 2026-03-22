"""Paper executor — simulates order execution for paper trading.

Implements the full interface expected by main.py TradingPipeline:
  submit_order, cancel_order, get_positions, get_portfolio, set_market_price
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

import structlog

from src.models.order import Order, OrderStatus

logger = structlog.get_logger(__name__)


@dataclass
class FillResult:
    """Result of an order fill (real or simulated)."""

    order_id: str
    ticker: str
    filled_price: float
    filled_qty: float
    commission: float
    filled_at: datetime


@dataclass
class PaperPosition:
    """Simulated open position."""

    ticker: str
    direction: str  # "long" / "short"
    lots: int
    lot_size: int = 1
    entry_price: float = 0.0
    current_price: float = 0.0
    stop_loss: float | None = None
    take_profit: float | None = None
    opened_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def unrealized_pnl(self) -> float:
        qty = self.lots * self.lot_size
        if self.direction == "long":
            return (self.current_price - self.entry_price) * qty
        return (self.entry_price - self.current_price) * qty


@dataclass
class PortfolioSnapshot:
    """Portfolio state snapshot for main.py compatibility."""

    equity: float = 1_000_000.0
    cash: float = 1_000_000.0
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    drawdown: float = 0.0
    exposure_pct: float = 0.0
    consecutive_losses: int = 0
    peak_equity: float = 1_000_000.0

    @property
    def total_value(self) -> float:
        return self.equity


class OrderStatusResult:
    """Minimal order status result."""

    def __init__(self, value: str = "filled"):
        self.value = value


class PaperExecutor:
    """Simulates order execution for paper trading.

    Fills all orders immediately at price + slippage.
    Commission: 0.01% of turnover (MOEX equity rate).
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000.0,
        slippage_pct: float = 0.001,
        commission_pct: float = 0.0001,
    ):
        self.initial_capital = initial_capital
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        self._cash = initial_capital
        self._peak_equity = initial_capital
        self._positions: dict[str, PaperPosition] = {}
        self._orders: dict[str, Order] = {}
        self._fills: list[FillResult] = []
        self._prices: dict[str, float] = {}
        self._consecutive_losses = 0
        logger.info(
            "paper_executor_init",
            capital=initial_capital,
            slippage_pct=slippage_pct,
        )

    def set_market_price(self, ticker: str, price: float) -> None:
        """Update market price for a ticker (used for MTM)."""
        self._prices[ticker] = price
        if ticker in self._positions:
            self._positions[ticker].current_price = price

    async def submit_order(self, order: Any) -> OrderStatusResult:
        """Simulate immediate fill with slippage and commission."""
        price = getattr(order, "limit_price", None) or getattr(order, "price", 0.0) or 0.0
        slippage = price * self.slippage_pct
        direction = getattr(order, "direction", "long")
        action = getattr(order, "action", "buy")

        if action == "buy":
            fill_price = price + slippage
        else:
            fill_price = price - slippage

        lots = getattr(order, "lots", 1)
        lot_size = getattr(order, "lot_size", 1)
        qty = lots * lot_size
        commission = fill_price * qty * self.commission_pct
        ticker = getattr(order, "ticker", "?")

        self._cash -= commission

        if action == "buy":
            self._positions[ticker] = PaperPosition(
                ticker=ticker,
                direction=direction,
                lots=lots,
                lot_size=lot_size,
                entry_price=fill_price,
                current_price=fill_price,
                stop_loss=getattr(order, "stop_loss", None),
                take_profit=getattr(order, "take_profit", None),
            )
        elif action == "sell" and ticker in self._positions:
            pos = self._positions.pop(ticker)
            pnl = pos.unrealized_pnl
            self._cash += pnl
            if pnl < 0:
                self._consecutive_losses += 1
            else:
                self._consecutive_losses = 0

        result = FillResult(
            order_id=getattr(order, "order_id", "?"),
            ticker=ticker,
            filled_price=fill_price,
            filled_qty=qty,
            commission=commission,
            filled_at=datetime.utcnow(),
        )
        self._fills.append(result)

        logger.info(
            "paper_order_filled",
            ticker=ticker,
            action=action,
            lots=lots,
            fill_price=round(fill_price, 4),
            commission=round(commission, 2),
        )
        return OrderStatusResult("filled")

    async def cancel_order(self, order_id: str) -> bool:
        return False

    async def get_positions(self) -> list[PaperPosition]:
        """Return open positions."""
        return list(self._positions.values())

    async def get_portfolio(self) -> PortfolioSnapshot:
        """Return portfolio snapshot."""
        positions_value = sum(
            p.current_price * p.lots * p.lot_size
            for p in self._positions.values()
        )
        equity = self._cash + positions_value
        if equity > self._peak_equity:
            self._peak_equity = equity
        dd = (self._peak_equity - equity) / self._peak_equity if self._peak_equity > 0 else 0.0
        exposure = positions_value / equity if equity > 0 else 0.0

        return PortfolioSnapshot(
            equity=equity,
            cash=self._cash,
            positions=dict(self._positions),
            drawdown=max(0.0, dd),
            exposure_pct=exposure,
            consecutive_losses=self._consecutive_losses,
            peak_equity=self._peak_equity,
        )

    @property
    def trade_log(self) -> list[dict]:
        """All fills as dicts for daily report."""
        return [
            {
                "ticker": f.ticker,
                "price": f.filled_price,
                "qty": f.filled_qty,
                "commission": f.commission,
                "date": f.filled_at.isoformat(),
                "pnl": 0,
            }
            for f in self._fills
        ]


__all__ = [
    "PaperExecutor", "FillResult", "PaperPosition",
    "PortfolioSnapshot", "OrderStatusResult",
]
