"""Tests for hummingbot-inspired components: Triple Barrier, TWAP, Avellaneda-Stoikov.

Formulas from hummingbot (Apache 2.0), implementations from scratch.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.execution.triple_barrier import TripleBarrier, ExitReason, BarrierState
from src.execution.twap import TWAPExecutor, twap_schedule, TWAPSlice, TWAPResult
from src.strategies.market_making import AvellanedaStoikov, QuoteResult


# ===========================================================================
# Triple Barrier — 12 tests
# ===========================================================================


class TestTripleBarrier:

    def test_take_profit_long(self):
        """Long TP: exit when price >= entry * (1 + tp_pct)."""
        tb = TripleBarrier("long", 100.0, take_profit_pct=0.05)
        assert tb.update(104.0) == ExitReason.NONE
        assert tb.update(105.0) == ExitReason.TAKE_PROFIT
        assert tb.is_triggered

    def test_take_profit_short(self):
        """Short TP: exit when price <= entry * (1 - tp_pct)."""
        tb = TripleBarrier("short", 100.0, take_profit_pct=0.05)
        assert tb.update(96.0) == ExitReason.NONE
        assert tb.update(95.0) == ExitReason.TAKE_PROFIT

    def test_stop_loss_long(self):
        """Long SL: exit when price <= entry * (1 - sl_pct)."""
        tb = TripleBarrier("long", 100.0, stop_loss_pct=0.02)
        assert tb.update(99.0) == ExitReason.NONE
        assert tb.update(97.9) == ExitReason.STOP_LOSS

    def test_stop_loss_short(self):
        """Short SL: exit when price >= entry * (1 + sl_pct)."""
        tb = TripleBarrier("short", 100.0, stop_loss_pct=0.02)
        assert tb.update(101.0) == ExitReason.NONE
        assert tb.update(102.1) == ExitReason.STOP_LOSS

    def test_time_limit(self):
        """Exit when elapsed >= time_limit."""
        tb = TripleBarrier("long", 100.0, time_limit_seconds=3600)
        assert tb.update(100.0, elapsed_seconds=3500) == ExitReason.NONE
        assert tb.update(100.0, elapsed_seconds=3600) == ExitReason.TIME_LIMIT

    def test_trailing_stop_long(self):
        """Trailing: exit when price drops trailing_pct from peak."""
        tb = TripleBarrier("long", 100.0, trailing_stop_pct=0.03)
        tb.update(105.0)  # peak
        tb.update(110.0)  # new peak
        assert tb.update(106.5) == ExitReason.TRAILING_STOP  # 3.2% from 110

    def test_trailing_stop_short(self):
        """Short trailing: exit when price rises from trough."""
        tb = TripleBarrier("short", 100.0, trailing_stop_pct=0.03)
        tb.update(95.0)  # new trough
        assert tb.update(97.9) == ExitReason.TRAILING_STOP  # 3.05% from 95

    def test_trailing_activation(self):
        """Trailing activates only after activation_pct profit."""
        tb = TripleBarrier(
            "long", 100.0,
            trailing_stop_pct=0.02,
            trailing_activation_pct=0.05,
        )
        tb.update(103.0)   # +3%, trailing NOT active yet
        tb.update(100.0)   # drop, but trailing inactive → no trigger
        assert not tb.is_triggered
        tb.update(106.0)   # +6%, trailing activates
        tb.update(103.8)   # 2.1% from peak 106 → trigger
        assert tb.is_triggered
        assert tb.exit_reason == ExitReason.TRAILING_STOP

    def test_all_barriers_disabled(self):
        """No barriers → never triggers."""
        tb = TripleBarrier("long", 100.0)
        tb.update(50.0, elapsed_seconds=999999)
        assert not tb.is_triggered

    def test_tp_before_sl(self):
        """TP checked before SL (same bar)."""
        tb = TripleBarrier("long", 100.0, take_profit_pct=0.10, stop_loss_pct=0.10)
        # Price exactly at both: TP and SL (edge case)
        assert tb.update(110.0) == ExitReason.TAKE_PROFIT

    def test_state_property(self):
        """State dataclass populated correctly."""
        tb = TripleBarrier("long", 100.0, take_profit_pct=0.05)
        tb.update(103.0, elapsed_seconds=60)
        s = tb.state
        assert not s.is_triggered
        assert s.peak_price == 103.0
        assert abs(s.unrealized_pnl_pct - 0.03) < 0.001
        assert s.elapsed_seconds == 60

    def test_invalid_side(self):
        with pytest.raises(ValueError):
            TripleBarrier("invalid", 100.0)

    def test_idempotent_after_trigger(self):
        """After trigger, subsequent updates don't change reason."""
        tb = TripleBarrier("long", 100.0, stop_loss_pct=0.02)
        tb.update(97.0)
        assert tb.exit_reason == ExitReason.STOP_LOSS
        tb.update(110.0)  # would be TP, but already triggered
        assert tb.exit_reason == ExitReason.STOP_LOSS


# ===========================================================================
# TWAP — 10 tests
# ===========================================================================


class TestTWAP:

    def test_schedule_creates_slices(self):
        """Basic schedule with lot rounding."""
        plan = twap_schedule(1000, 5, 0, 300, lot_size=10)
        assert len(plan) == 5
        assert sum(s.quantity for s in plan) == 1000

    def test_schedule_timing(self):
        """Slices evenly spaced."""
        plan = twap_schedule(100, 4, 0, 400)
        times = [s.target_time for s in plan]
        assert times == [0, 100, 200, 300]

    def test_lot_rounding(self):
        """Quantities rounded to lot size."""
        plan = twap_schedule(100, 3, lot_size=10)
        for s in plan:
            assert s.quantity % 10 == 0

    def test_empty_on_zero_quantity(self):
        assert twap_schedule(0, 5) == []

    def test_empty_on_zero_slices(self):
        assert twap_schedule(100, 0) == []

    def test_executor_workflow(self):
        """Full executor lifecycle."""
        ex = TWAPExecutor(1000, n_slices=4, start_time=0, end_time=400, lot_size=10)
        assert ex.slices_remaining == 4
        assert not ex.is_complete

        assert ex.should_execute(0)
        ex.record_fill(fill_price=300.0)
        assert ex.slices_remaining == 3

        assert not ex.should_execute(50)  # too early
        assert ex.should_execute(100)
        ex.record_fill(fill_price=301.0)

        assert ex.slices_remaining == 2

    def test_spread_filter(self):
        """Skip when spread too wide."""
        ex = TWAPExecutor(100, n_slices=2, max_spread_pct=0.005)
        # Spread 1% > 0.5% → skip
        assert not ex.should_execute(0, bid=299.0, ask=302.0)
        # Spread 0.3% → OK
        assert ex.should_execute(0, bid=299.5, ask=300.5)

    def test_result_summary(self):
        """Result after partial execution."""
        ex = TWAPExecutor(200, n_slices=4, lot_size=1)
        ex.record_fill(300.0, 50)
        ex.record_fill(301.0, 50)
        r = ex.result
        assert r.slices_executed == 2
        assert r.total_filled == 100
        assert 300 < r.avg_fill_price < 301

    def test_skip_slice(self):
        """Skip moves to next slice."""
        ex = TWAPExecutor(100, n_slices=3, lot_size=1)
        ex.skip_slice()
        assert ex.slices_remaining == 2

    def test_complete_raises_on_overfill(self):
        """Can't record fill after completion."""
        ex = TWAPExecutor(100, n_slices=1, lot_size=1)
        ex.record_fill(300.0)
        assert ex.is_complete
        with pytest.raises(RuntimeError):
            ex.record_fill(301.0)


# ===========================================================================
# Avellaneda-Stoikov — 10 tests
# ===========================================================================


class TestAvellanedaStoikov:

    @pytest.fixture
    def model(self) -> AvellanedaStoikov:
        return AvellanedaStoikov(
            gamma=0.5, sigma=0.02, kappa=1.5,
            session_duration_seconds=31800,
        )

    def test_neutral_inventory_symmetric(self, model):
        """Zero inventory → bid and ask symmetric around mid."""
        q = model.compute_quotes(300.0, inventory=0)
        mid_of_quotes = (q.bid_price + q.ask_price) / 2
        assert abs(mid_of_quotes - q.reservation_price) < 0.01
        assert abs(q.reservation_price - 300.0) < 0.01

    def test_long_inventory_shifts_down(self, model):
        """Long inventory → reservation price < mid → sell-biased."""
        q = model.compute_quotes(300.0, inventory=100)
        assert q.reservation_price < 300.0
        assert q.inventory_skew > 0

    def test_short_inventory_shifts_up(self, model):
        """Short inventory → reservation price > mid → buy-biased."""
        q = model.compute_quotes(300.0, inventory=-100)
        assert q.reservation_price > 300.0
        assert q.inventory_skew < 0

    def test_spread_positive(self, model):
        """Spread is always positive."""
        q = model.compute_quotes(300.0, inventory=0)
        assert q.optimal_spread > 0
        assert q.ask_price > q.bid_price

    def test_higher_gamma_more_inventory_skew(self):
        """Higher gamma → larger inventory adjustment."""
        m1 = AvellanedaStoikov(gamma=0.5, sigma=0.02, kappa=1.5)
        m2 = AvellanedaStoikov(gamma=2.0, sigma=0.02, kappa=1.5)
        q1 = m1.compute_quotes(300.0, inventory=100)
        q2 = m2.compute_quotes(300.0, inventory=100)
        assert abs(q2.inventory_skew) > abs(q1.inventory_skew)

    def test_higher_sigma_wider_spread(self):
        """Higher volatility → wider spread."""
        m1 = AvellanedaStoikov(gamma=0.5, sigma=0.01, kappa=1.5)
        m2 = AvellanedaStoikov(gamma=0.5, sigma=0.05, kappa=1.5)
        q1 = m1.compute_quotes(300.0)
        q2 = m2.compute_quotes(300.0)
        assert q2.optimal_spread > q1.optimal_spread

    def test_less_time_narrower_spread(self, model):
        """Less time remaining → narrower spread (gamma term shrinks)."""
        q_full = model.compute_quotes(300.0, time_remaining=31800)
        q_end = model.compute_quotes(300.0, time_remaining=1000)
        assert q_end.optimal_spread <= q_full.optimal_spread

    def test_max_inventory_blocks_side(self):
        """At max inventory → don't quote aggravating side."""
        model = AvellanedaStoikov(gamma=0.5, sigma=0.02, kappa=1.5, max_inventory=100)
        q = model.compute_quotes(300.0, inventory=100)
        assert q.bid_price == 0.0  # don't buy more
        assert q.ask_price > 0  # still sell

    def test_min_spread_floor(self):
        """Spread doesn't go below min_spread_pct."""
        model = AvellanedaStoikov(
            gamma=0.01, sigma=0.001, kappa=100,
            min_spread_pct=0.002,
        )
        q = model.compute_quotes(300.0, time_remaining=100)
        assert q.optimal_spread >= 300.0 * 0.002 - 0.01

    def test_zero_price(self, model):
        """Zero mid price → zero quotes."""
        q = model.compute_quotes(0.0)
        assert q.bid_price == 0.0
        assert q.ask_price == 0.0
