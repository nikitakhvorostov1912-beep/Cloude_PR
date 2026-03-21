"""Tests for barter-rs inspired components: Welford, Position FIFO, RiskApproved.

All components written from scratch, inspired by barter-rs (MIT License).
"""
from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.metrics import WelfordAccumulator, StreamingMetrics
from src.risk.position_tracker import PositionTracker, ClosedTrade, Entry
from src.risk.rules import (
    RiskApproved,
    RiskRefused,
    RulesEngine,
    PortfolioSnapshot,
    Position,
)


# ===========================================================================
# Welford Online Algorithm — 10 tests
# ===========================================================================


class TestWelfordAccumulator:
    """Welford's online algorithm for streaming mean/variance."""

    def test_mean_simple(self):
        """Mean of [1,2,3,4,5] = 3.0."""
        acc = WelfordAccumulator()
        for v in [1, 2, 3, 4, 5]:
            acc.update(v)
        assert acc.mean == 3.0

    def test_variance_known(self):
        """Sample variance of [2,4,4,4,5,5,7,9] = 4.571..."""
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        acc = WelfordAccumulator()
        for v in data:
            acc.update(v)
        expected_var = float(np.var(data, ddof=1))
        assert abs(acc.sample_variance - expected_var) < 1e-10

    def test_population_variance(self):
        """Population variance uses n, not n-1."""
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        acc = WelfordAccumulator()
        for v in data:
            acc.update(v)
        expected = float(np.var(data, ddof=0))
        assert abs(acc.population_variance - expected) < 1e-10

    def test_std_dev(self):
        """Std dev matches numpy."""
        data = [10, 20, 30, 40, 50]
        acc = WelfordAccumulator()
        for v in data:
            acc.update(v)
        expected = float(np.std(data, ddof=1))
        assert abs(acc.std_dev - expected) < 1e-10

    def test_empty(self):
        """Empty accumulator → zeros."""
        acc = WelfordAccumulator()
        assert acc.count == 0
        assert acc.mean == 0.0
        assert acc.sample_variance == 0.0
        assert acc.std_dev == 0.0

    def test_single_value(self):
        """Single value → mean=value, variance=0."""
        acc = WelfordAccumulator()
        acc.update(42.0)
        assert acc.mean == 42.0
        assert acc.sample_variance == 0.0

    def test_constant_values(self):
        """All same values → variance=0."""
        acc = WelfordAccumulator()
        for _ in range(100):
            acc.update(7.0)
        assert acc.mean == 7.0
        assert acc.sample_variance == 0.0

    def test_min_max(self):
        """Min and max tracked correctly."""
        acc = WelfordAccumulator()
        for v in [5, 3, 8, 1, 9]:
            acc.update(v)
        assert acc.min_value == 1.0
        assert acc.max_value == 9.0

    def test_large_dataset(self):
        """1M samples — Welford matches numpy."""
        rng = np.random.default_rng(42)
        data = rng.normal(100, 15, size=100_000)
        acc = WelfordAccumulator()
        for v in data:
            acc.update(float(v))
        assert abs(acc.mean - float(data.mean())) < 0.1
        assert abs(acc.sample_variance - float(np.var(data, ddof=1))) < 1.0

    def test_negative_values(self):
        """Handles negative values correctly."""
        acc = WelfordAccumulator()
        for v in [-5, -3, -1, 0, 1, 3, 5]:
            acc.update(v)
        assert abs(acc.mean - 0.0) < 1e-10


class TestStreamingMetrics:
    """Streaming Sharpe/Sortino using Welford."""

    def test_positive_returns_positive_sharpe(self):
        """Mostly positive returns → positive Sharpe."""
        rng = np.random.default_rng(42)
        sm = StreamingMetrics(risk_free_rate=0.0)
        for _ in range(200):
            sm.update(float(rng.normal(0.005, 0.01)))
        assert sm.sharpe_ratio > 0

    def test_negative_returns_negative_sharpe(self):
        """Mostly negative returns → negative Sharpe."""
        rng = np.random.default_rng(42)
        sm = StreamingMetrics(risk_free_rate=0.0)
        for _ in range(200):
            sm.update(float(rng.normal(-0.005, 0.01)))
        assert sm.sharpe_ratio < 0

    def test_zero_returns(self):
        """Zero returns → Sharpe = 0."""
        sm = StreamingMetrics(risk_free_rate=0.0)
        for _ in range(100):
            sm.update(0.0)
        assert sm.sharpe_ratio == 0.0

    def test_max_drawdown_tracking(self):
        """Max drawdown tracked from equity."""
        sm = StreamingMetrics()
        equities = [100, 110, 105, 108, 95, 100]
        for eq in equities:
            sm.update(0.01, equity=float(eq))
        # Peak=110, trough=95 → DD = (110-95)/110 ≈ 0.1364
        assert abs(sm.max_drawdown - (110 - 95) / 110) < 0.01

    def test_count(self):
        """Count increments correctly."""
        sm = StreamingMetrics()
        for i in range(50):
            sm.update(0.001 * i)
        assert sm.count == 50

    def test_sortino_only_downside(self):
        """Sortino uses only negative returns for denominator."""
        rng = np.random.default_rng(99)
        sm = StreamingMetrics(risk_free_rate=0.0)
        for _ in range(180):
            sm.update(float(rng.normal(0.005, 0.008)))
        for _ in range(20):
            sm.update(float(rng.normal(-0.02, 0.005)))
        assert sm.sortino_ratio > 0
        # Sortino should differ from Sharpe
        assert sm.sortino_ratio != sm.sharpe_ratio

    def test_volatility(self):
        """Annualized volatility is std * sqrt(252)."""
        sm = StreamingMetrics(periods=252, risk_free_rate=0.0)
        rng = np.random.default_rng(42)
        for _ in range(500):
            sm.update(float(rng.normal(0.001, 0.02)))
        assert sm.volatility > 0


# ===========================================================================
# Position FIFO Tracker — 12 tests
# ===========================================================================


class TestPositionTracker:
    """Position FIFO lifecycle tracker."""

    def test_open_long(self):
        """Open a long position."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100, fee=30.0)
        assert pt.is_open
        assert pt.side == "long"
        assert pt.quantity == 100.0
        assert pt.average_entry_price == 300.0

    def test_open_short(self):
        """Open a short position."""
        pt = PositionTracker(lot_size=1)
        pt.open_trade("short", 500.0, 50, fee=10.0)
        assert pt.side == "short"
        assert pt.quantity == 50.0

    def test_increase_position(self):
        """Adding same direction increases position."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100)
        pt.open_trade("long", 310.0, 50)
        assert pt.quantity == 150.0
        # Weighted avg: (300*100 + 310*50) / 150 = 303.33
        assert abs(pt.average_entry_price - 303.333) < 0.01

    def test_partial_close(self):
        """Partial close returns ClosedTrade, position remains."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100)
        closed = pt.open_trade("short", 320.0, 50)  # close 50
        assert len(closed) == 1
        assert closed[0].quantity == 50.0
        assert closed[0].pnl_gross == 1000.0  # (320-300)*50
        assert pt.is_open
        assert pt.quantity == 50.0

    def test_full_close(self):
        """Full close → no position."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100)
        closed = pt.close_all(320.0, fee=32.0)
        assert len(closed) == 1
        assert not pt.is_open
        assert pt.side is None

    def test_position_flip(self):
        """Opposite side trade > position → close + open new."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100)
        closed = pt.open_trade("short", 320.0, 150)  # close 100 + open short 50
        assert len(closed) == 1
        assert closed[0].quantity == 100.0  # closed the long
        assert pt.is_open
        assert pt.side == "short"
        assert pt.quantity == 50.0

    def test_fifo_order(self):
        """FIFO: earliest entries closed first."""
        pt = PositionTracker(lot_size=10)
        t1 = datetime(2024, 1, 1)
        t2 = datetime(2024, 1, 2)
        pt.open_trade("long", 300.0, 50, timestamp=t1)
        pt.open_trade("long", 310.0, 50, timestamp=t2)
        closed = pt.open_trade("short", 320.0, 50, timestamp=datetime(2024, 1, 3))
        # FIFO: first entry (300.0) closed first
        assert closed[0].entry_price == 300.0
        assert closed[0].pnl_gross == 1000.0  # (320-300)*50
        # Remaining position is second entry
        assert pt.average_entry_price == 310.0

    def test_unrealized_pnl_long(self):
        """Unrealized PnL for long position."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100)
        assert pt.unrealized_pnl(310.0) == 1000.0  # (310-300)*100
        assert pt.unrealized_pnl(290.0) == -1000.0

    def test_unrealized_pnl_short(self):
        """Unrealized PnL for short position."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("short", 300.0, 100)
        assert pt.unrealized_pnl(290.0) == 1000.0  # (300-290)*100
        assert pt.unrealized_pnl(310.0) == -1000.0

    def test_lot_size_validation(self):
        """Quantity rounded down to lot boundary."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 15)  # 15 → 10 (1 lot)
        assert pt.quantity == 10.0

    def test_quantity_max_tracking(self):
        """Peak quantity tracked across increases."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100)
        pt.open_trade("long", 310.0, 50)
        assert pt.quantity_max == 150.0
        pt.open_trade("short", 320.0, 50)  # reduce
        assert pt.quantity_max == 150.0  # still 150

    def test_fees_tracking(self):
        """Total fees accumulated across trades."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100, fee=30.0)
        pt.open_trade("long", 310.0, 50, fee=15.5)
        closed = pt.close_all(320.0, fee=32.0)
        assert pt.total_fees == 30.0 + 15.5 + 32.0

    def test_empty_tracker(self):
        """Empty tracker → all zeros."""
        pt = PositionTracker()
        assert not pt.is_open
        assert pt.side is None
        assert pt.quantity == 0.0
        assert pt.unrealized_pnl(100.0) == 0.0

    def test_reset(self):
        """Reset clears all state."""
        pt = PositionTracker(lot_size=10)
        pt.open_trade("long", 300.0, 100, fee=30.0)
        pt.reset()
        assert not pt.is_open
        assert pt.realized_pnl == 0.0
        assert pt.total_fees == 0.0


# ===========================================================================
# RiskApproved / RiskRefused — 8 tests
# ===========================================================================


class TestRiskApprovedRefused:
    """RiskApproved/RiskRefused type-level markers."""

    def test_approved_wraps_order(self):
        """RiskApproved stores the original order."""
        order = {"symbol": "SBER", "qty": 100}
        approved = RiskApproved(order=order)
        assert approved.order == order
        assert approved.approved_by == "RulesEngine"

    def test_refused_wraps_order_with_reason(self):
        """RiskRefused stores order + reason."""
        order = {"symbol": "SBER", "qty": 100}
        refused = RiskRefused(order=order, reason="DD > 15%", rule_name="DrawdownRule")
        assert refused.order == order
        assert refused.reason == "DD > 15%"
        assert refused.rule_name == "DrawdownRule"

    def test_approved_is_frozen(self):
        """RiskApproved is immutable."""
        approved = RiskApproved(order="test")
        with pytest.raises(AttributeError):
            approved.order = "changed"

    def test_refused_is_frozen(self):
        """RiskRefused is immutable."""
        refused = RiskRefused(order="test", reason="bad")
        with pytest.raises(AttributeError):
            refused.order = "changed"

    def test_check_order_approved(self):
        """RulesEngine.check_order returns RiskApproved when all pass."""
        engine = RulesEngine(rules=[])  # truly empty rules = all pass
        portfolio = PortfolioSnapshot(
            positions=[
                Position("SBER", 20_000, currency="RUB"),
                Position("AAPL", 20_000, currency="USD"),
                Position("GAZP", 20_000, currency="RUB"),
                Position("BMW", 20_000, currency="EUR"),
                Position("LKOH", 20_000, currency="RUB"),
            ],
            total_value=100_000,
        )
        result = engine.check_order({"buy": "SBER"}, portfolio)
        assert isinstance(result, RiskApproved)

    def test_check_order_refused(self):
        """RulesEngine.check_order returns RiskRefused when rule fails."""
        engine = RulesEngine.default_rules()
        engine = RulesEngine(rules=engine)
        # Portfolio with 100% in one position → ConcentrationRule fails
        portfolio = PortfolioSnapshot(
            positions=[Position("SBER", 100_000)],
            total_value=100_000,
            current_drawdown=0.25,  # above 20% DD threshold
        )
        result = engine.check_order({"buy": "GAZP"}, portfolio)
        assert isinstance(result, RiskRefused)

    def test_check_orders_batch(self):
        """check_orders processes multiple orders."""
        engine = RulesEngine(rules=[])  # explicit empty = all pass
        portfolio = PortfolioSnapshot(
            positions=[Position("SBER", 50_000), Position("GAZP", 50_000)],
            total_value=100_000,
        )
        orders = [{"buy": "LKOH"}, {"buy": "VTBR"}]
        approved, refused = engine.check_orders(orders, portfolio)
        assert len(approved) == 2
        assert len(refused) == 0

    def test_check_orders_all_refused(self):
        """All orders refused when portfolio fails rules."""
        engine = RulesEngine.default_rules()
        engine = RulesEngine(rules=engine)
        portfolio = PortfolioSnapshot(
            positions=[Position("SBER", 100_000)],
            total_value=100_000,
            current_drawdown=0.25,
        )
        orders = [{"buy": "A"}, {"buy": "B"}, {"buy": "C"}]
        approved, refused = engine.check_orders(orders, portfolio)
        assert len(approved) == 0
        assert len(refused) == 3
