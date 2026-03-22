"""Tests for Tinkoff broker adapter.

Unit tests use mocked connections.
Integration tests with real API are marked @pytest.mark.integration.
"""
from __future__ import annotations

import os
from datetime import datetime

import pytest

from src.core.models import Order, OrderType, Position, Side
from src.execution.adapters.tinkoff import TinkoffAdapter

has_tinkoff_token = bool(os.environ.get("TINKOFF_TOKEN"))


class TestTinkoffAdapter:
    def test_connect_requires_token(self):
        """Connection without token raises ValueError."""
        adapter = TinkoffAdapter(token="", sandbox=True)
        with pytest.raises(ValueError, match="token not set"):
            adapter.connect()

    def test_order_conversion(self):
        """Our Order converts to Tinkoff format and back."""
        order = Order(
            instrument="SBER",
            side=Side.LONG,
            quantity=100,
            order_type=OrderType.MARKET,
            price=250.0,
        )
        tinkoff_order = TinkoffAdapter.convert_order_to_tinkoff(order)
        assert tinkoff_order["direction"] == "ORDER_DIRECTION_BUY"
        assert tinkoff_order["quantity"] == 10  # 100 shares / 10 lot = 10 lots
        assert tinkoff_order["order_type"] == "ORDER_TYPE_MARKET"

    def test_position_conversion(self):
        """Tinkoff position converts to our Position model."""
        tinkoff_pos = {
            "ticker": "SBER",
            "quantity": 10,
            "lot_size": 10,
            "average_price": 250.0,
            "current_price": 260.0,
        }
        pos = TinkoffAdapter.convert_tinkoff_position(tinkoff_pos)
        assert pos.instrument == "SBER"
        assert pos.quantity == 100  # 10 lots * 10 shares
        assert pos.entry_price == 250.0
        assert pos.current_price == 260.0
        assert pos.side == Side.LONG

    def test_lot_conversion(self):
        """100 shares SBER = 10 lots."""
        lots = TinkoffAdapter.convert_units_to_lots("SBER", 100)
        assert lots == 10

        units = TinkoffAdapter.convert_lots_to_units("SBER", 10)
        assert units == 100

    def test_error_handling_not_connected(self):
        """Operations on disconnected adapter raise RuntimeError."""
        adapter = TinkoffAdapter(token="fake", sandbox=True)
        with pytest.raises(RuntimeError, match="Not connected"):
            adapter.place_order(
                Order(instrument="SBER", side=Side.LONG, quantity=10)
            )
        with pytest.raises(RuntimeError, match="Not connected"):
            adapter.get_positions()

    def test_portfolio_snapshot(self):
        """Portfolio returns correct structure."""
        # Mock connection
        adapter = TinkoffAdapter(token="fake", sandbox=True)
        adapter._connected = True  # bypass real connection

        portfolio = adapter.get_portfolio()
        assert portfolio.cash > 0
        assert isinstance(portfolio.positions, list)
        assert portfolio.timestamp is not None

    def test_cancel_order(self):
        """Cancel order returns True."""
        adapter = TinkoffAdapter(token="fake", sandbox=True)
        adapter._connected = True

        result = adapter.cancel_order("test_order_123")
        assert result is True

    def test_sell_direction(self):
        """SHORT order converts to SELL direction."""
        order = Order(
            instrument="SBER",
            side=Side.SHORT,
            quantity=50,
            order_type=OrderType.LIMIT,
            price=260.0,
        )
        tinkoff_order = TinkoffAdapter.convert_order_to_tinkoff(order)
        assert tinkoff_order["direction"] == "ORDER_DIRECTION_SELL"
        assert tinkoff_order["order_type"] == "ORDER_TYPE_LIMIT"

    def test_lot_conversion_vtbr(self):
        """VTBR lot = 10000 shares."""
        lots = TinkoffAdapter.convert_units_to_lots("VTBR", 50000)
        assert lots == 5

    def test_context_manager(self):
        """Context manager raises if no token."""
        with pytest.raises(ValueError):
            with TinkoffAdapter(token="", sandbox=True):
                pass
