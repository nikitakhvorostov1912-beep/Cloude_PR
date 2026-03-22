"""Tests for src/core/models.py — Pydantic domain models."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.core.models import (
    Bar,
    InstrumentType,
    Order,
    OrderStatus,
    OrderType,
    Portfolio,
    Position,
    Side,
    Signal,
    TradeResult,
)

NOW = datetime(2024, 6, 15, 12, 0, 0)


class TestBar:
    def test_bar_creation(self):
        bar = Bar(
            timestamp=NOW, open=100.0, high=105.0, low=99.0,
            close=103.0, volume=10000, instrument="SBER",
        )
        assert bar.close == 103.0
        assert bar.instrument == "SBER"
        assert bar.timeframe == "1d"

    def test_bar_high_gte_low(self):
        with pytest.raises(ValidationError, match="high must be >= low"):
            Bar(
                timestamp=NOW, open=100.0, high=95.0, low=99.0,
                close=97.0, volume=100, instrument="SBER",
            )

    def test_bar_negative_price(self):
        with pytest.raises(ValidationError):
            Bar(
                timestamp=NOW, open=-1.0, high=105.0, low=99.0,
                close=103.0, volume=100, instrument="SBER",
            )


class TestSignal:
    def test_signal_creation(self):
        sig = Signal(
            instrument="GAZP", side=Side.LONG, strength=0.8,
            strategy_name="ema_cross", timestamp=NOW, confidence=0.9,
        )
        assert sig.instrument == "GAZP"
        assert sig.side == Side.LONG
        assert sig.strength == 0.8
        assert sig.confidence == 0.9

    def test_signal_strength_range(self):
        with pytest.raises(ValidationError):
            Signal(
                instrument="GAZP", side=Side.LONG, strength=1.5,
                strategy_name="test", timestamp=NOW,
            )


class TestOrder:
    def test_order_default_status(self):
        order = Order(
            instrument="SBER", side=Side.LONG, quantity=10,
        )
        assert order.status == OrderStatus.PENDING
        assert order.order_type == OrderType.MARKET

    def test_order_serialization(self):
        order = Order(
            instrument="SBER", side=Side.LONG, quantity=10,
            price=250.0, strategy_name="ema",
        )
        data = order.model_dump()
        assert data["instrument"] == "SBER"
        assert data["side"] == "long"
        restored = Order.model_validate(data)
        assert restored.instrument == order.instrument
        assert restored.quantity == order.quantity


class TestPosition:
    def test_position_unrealized_pnl_long(self):
        pos = Position(
            instrument="SBER", side=Side.LONG, quantity=100,
            entry_price=250.0, current_price=260.0,
        )
        assert pos.unrealized_pnl == 1000.0  # (260-250)*100

    def test_position_unrealized_pnl_short(self):
        pos = Position(
            instrument="SBER", side=Side.SHORT, quantity=100,
            entry_price=260.0, current_price=250.0,
        )
        assert pos.unrealized_pnl == 1000.0  # (260-250)*100 for short

    def test_position_pnl_pct(self):
        pos = Position(
            instrument="SBER", side=Side.LONG, quantity=100,
            entry_price=200.0, current_price=210.0,
        )
        assert abs(pos.unrealized_pnl_pct - 0.05) < 1e-9  # 10/200


class TestPortfolio:
    def test_portfolio_total_value(self):
        pos = Position(
            instrument="SBER", side=Side.LONG, quantity=10,
            entry_price=250.0, current_price=260.0,
        )
        pf = Portfolio(positions=[pos], cash=100_000)
        assert pf.total_value == 100_000 + 260.0 * 10

    def test_portfolio_exposure(self):
        pf_empty = Portfolio(positions=[], cash=1_000_000)
        assert pf_empty.exposure == 0.0

        pos = Position(
            instrument="SBER", side=Side.LONG, quantity=100,
            entry_price=250.0, current_price=250.0,
        )
        pf = Portfolio(positions=[pos], cash=75_000)
        expected = 25_000 / 100_000  # 25k positions / 100k total
        assert abs(pf.exposure - expected) < 1e-9


class TestTradeResult:
    def test_trade_result_gross_pnl(self):
        tr = TradeResult(
            instrument="SBER", side=Side.LONG,
            entry_price=250.0, exit_price=260.0, quantity=100,
            entry_timestamp=NOW, exit_timestamp=NOW + timedelta(hours=5),
        )
        assert tr.gross_pnl == 1000.0

    def test_trade_result_net_pnl(self):
        tr = TradeResult(
            instrument="SBER", side=Side.LONG,
            entry_price=250.0, exit_price=260.0, quantity=100,
            entry_timestamp=NOW, exit_timestamp=NOW + timedelta(hours=5),
            commission=5.0, slippage=2.0,
        )
        assert tr.net_pnl == 1000.0 - 5.0 - 2.0

    def test_trade_result_duration(self):
        tr = TradeResult(
            instrument="SBER", side=Side.LONG,
            entry_price=250.0, exit_price=260.0, quantity=100,
            entry_timestamp=NOW,
            exit_timestamp=NOW + timedelta(hours=3),
        )
        assert tr.duration == 3 * 3600

    def test_trade_result_return_pct(self):
        tr = TradeResult(
            instrument="SBER", side=Side.LONG,
            entry_price=200.0, exit_price=210.0, quantity=100,
            entry_timestamp=NOW,
            exit_timestamp=NOW + timedelta(days=1),
            commission=0.0, slippage=0.0,
        )
        assert abs(tr.return_pct - 0.05) < 1e-9  # 1000/20000

    def test_trade_result_short_pnl(self):
        tr = TradeResult(
            instrument="GAZP", side=Side.SHORT,
            entry_price=200.0, exit_price=190.0, quantity=50,
            entry_timestamp=NOW,
            exit_timestamp=NOW + timedelta(hours=2),
        )
        assert tr.gross_pnl == 500.0  # (200-190)*50


class TestEnums:
    def test_enums(self):
        assert Side.LONG.value == "long"
        assert Side.SHORT.value == "short"
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderStatus.FILLED.value == "filled"
        assert InstrumentType.EQUITY.value == "equity"
        assert InstrumentType.FUTURES.value == "futures"
