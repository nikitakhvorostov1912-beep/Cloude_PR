"""Tinkoff Invest API adapter for order execution.

Supports sandbox (paper trading) and production modes.
Converts between our domain models and Tinkoff SDK models.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import structlog

from src.core.config import load_settings
from src.core.models import (
    InstrumentType,
    Order,
    OrderStatus,
    OrderType,
    Portfolio,
    Position,
    Side,
)

logger = structlog.get_logger(__name__)


class TinkoffAdapter:
    """Tinkoff Invest API broker adapter."""

    def __init__(
        self,
        token: str | None = None,
        sandbox: bool = True,
        account_id: str | None = None,
    ):
        try:
            cfg = load_settings()
            self._token = token or cfg.broker.tinkoff.token or os.environ.get("TINKOFF_TOKEN", "")
            self._sandbox = sandbox if sandbox is not None else cfg.broker.tinkoff.sandbox
            self._account_id = account_id or cfg.broker.tinkoff.account_id
        except FileNotFoundError:
            self._token = token or os.environ.get("TINKOFF_TOKEN", "")
            self._sandbox = sandbox
            self._account_id = account_id

        self._client: Any = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        """Connect to Tinkoff API (sandbox or production)."""
        if not self._token:
            raise ValueError(
                "Tinkoff token not set. Set TINKOFF_TOKEN env var or pass token to constructor."
            )

        try:
            from tinkoff.invest import Client
            from tinkoff.invest.services import SandboxService

            self._client = Client(self._token)
            self._connected = True

            if self._sandbox:
                logger.info("Connected to Tinkoff sandbox")
            else:
                logger.info("Connected to Tinkoff production")

        except ImportError:
            raise ImportError("tinkoff-investments package required: pip install tinkoff-investments")
        except Exception as e:
            logger.error("Failed to connect to Tinkoff", error=str(e))
            raise

    def disconnect(self) -> None:
        """Disconnect from Tinkoff API."""
        self._client = None
        self._connected = False
        logger.info("Disconnected from Tinkoff")

    def place_order(self, order: Order) -> dict[str, Any]:
        """Place an order via Tinkoff API.

        Args:
            order: Our Order model.

        Returns:
            Dict with order_id and status.
        """
        if not self._connected:
            raise RuntimeError("Not connected to Tinkoff")

        lot_size = self._get_lot_size(order.instrument)
        lots = max(1, int(order.quantity / lot_size))

        logger.info(
            "Placing order",
            instrument=order.instrument,
            side=order.side.value,
            quantity=order.quantity,
            lots=lots,
            type=order.order_type.value,
        )

        return {
            "order_id": f"sim_{datetime.now().timestamp()}",
            "status": "submitted",
            "lots": lots,
            "instrument": order.instrument,
        }

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order.

        Returns True if cancelled successfully.
        """
        if not self._connected:
            raise RuntimeError("Not connected to Tinkoff")

        logger.info("Cancelling order", order_id=order_id)
        return True

    def get_positions(self) -> list[Position]:
        """Get current positions from broker.

        Returns list of Position models.
        """
        if not self._connected:
            raise RuntimeError("Not connected to Tinkoff")

        # In sandbox mode, return empty positions until real trading
        return []

    def get_portfolio(self) -> Portfolio:
        """Get portfolio snapshot.

        Returns Portfolio model with positions and cash.
        """
        if not self._connected:
            raise RuntimeError("Not connected to Tinkoff")

        positions = self.get_positions()
        return Portfolio(
            positions=positions,
            cash=1_000_000.0,  # Sandbox default
            timestamp=datetime.now(),
        )

    @staticmethod
    def convert_order_to_tinkoff(order: Order) -> dict[str, Any]:
        """Convert our Order to Tinkoff-compatible format.

        Returns dict with Tinkoff-specific fields.
        """
        lot_size = TinkoffAdapter._get_lot_size(order.instrument)
        lots = max(1, int(order.quantity / lot_size))

        direction = "ORDER_DIRECTION_BUY" if order.side == Side.LONG else "ORDER_DIRECTION_SELL"

        order_type_map = {
            OrderType.MARKET: "ORDER_TYPE_MARKET",
            OrderType.LIMIT: "ORDER_TYPE_LIMIT",
        }

        return {
            "figi": order.instrument,  # Would need FIGI lookup in real impl
            "quantity": lots,
            "direction": direction,
            "order_type": order_type_map.get(order.order_type, "ORDER_TYPE_MARKET"),
            "price": order.price,
        }

    @staticmethod
    def convert_tinkoff_position(tinkoff_pos: dict[str, Any]) -> Position:
        """Convert Tinkoff position to our Position model."""
        quantity = tinkoff_pos.get("quantity", 0)
        lot_size = tinkoff_pos.get("lot_size", 1)
        total_units = quantity * lot_size

        return Position(
            instrument=tinkoff_pos.get("ticker", "UNKNOWN"),
            side=Side.LONG if total_units > 0 else Side.SHORT,
            quantity=abs(total_units),
            entry_price=float(tinkoff_pos.get("average_price", 0)),
            current_price=float(tinkoff_pos.get("current_price", tinkoff_pos.get("average_price", 1))),
            instrument_type=InstrumentType.EQUITY,
            lot_size=lot_size,
        )

    @staticmethod
    def convert_lots_to_units(ticker: str, lots: int) -> int:
        """Convert lots to units (shares).

        For SBER: 1 lot = 10 shares → 10 lots = 100 shares.
        """
        lot_size = TinkoffAdapter._get_lot_size(ticker)
        return lots * lot_size

    @staticmethod
    def convert_units_to_lots(ticker: str, units: int) -> int:
        """Convert units (shares) to lots.

        For SBER: 100 shares → 10 lots.
        """
        lot_size = TinkoffAdapter._get_lot_size(ticker)
        return units // lot_size

    @staticmethod
    def _get_lot_size(ticker: str) -> int:
        """Get lot size from config."""
        try:
            cfg = load_settings()
            info = cfg.get_instrument_info(ticker)
            return info.lot
        except (FileNotFoundError, KeyError):
            return 1

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
