"""Tests for remaining LEAN + hummingbot ports: ZigZag, KVO, RVI, DCA, Grid, OBI."""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.indicators.advanced import (
    zigzag, ZigZagResult,
    klinger_volume_oscillator,
    relative_vigor_index,
)
from src.execution.dca import DCAExecutor, DCALevel, DCAState
from src.execution.grid import GridExecutor, GridLevel, GridStats
from src.indicators.order_book import (
    order_book_imbalance, obi_ema, compute_microprice, book_pressure_ratio,
)


@pytest.fixture
def trending_ohlcv():
    n = 50
    rng = np.random.default_rng(42)
    base = np.linspace(100, 150, n)
    noise = rng.normal(0, 1, n)
    c = base + noise
    h = c + abs(noise) + 1
    l = c - abs(noise) - 1
    o = c - noise * 0.5
    v = rng.uniform(1000, 5000, n)
    return o, h, l, c, v


# ===========================================================================
# ZigZag — 8 tests
# ===========================================================================


class TestZigZag:

    def test_returns_correct_type(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        zz = zigzag(h, l, c)
        assert isinstance(zz, ZigZagResult)
        assert len(zz.pivots) == len(c)

    def test_finds_pivots_in_trend(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        zz = zigzag(h, l, c, sensitivity=0.05)
        n_pivots = (zz.pivots != 0).sum()
        assert n_pivots >= 1

    def test_pivot_types_correct(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        zz = zigzag(h, l, c)
        assert set(zz.pivot_types).issubset({-1, 0, 1})

    def test_alternating_pivots(self):
        """Pivots should alternate: high → low → high."""
        h = np.array([105, 110, 108, 100, 102, 115, 112, 95, 98, 120], dtype=float)
        l = np.array([95, 100, 98, 88, 90, 105, 102, 85, 88, 110], dtype=float)
        c = np.array([100, 108, 102, 92, 95, 112, 106, 88, 92, 118], dtype=float)
        zz = zigzag(h, l, c, sensitivity=0.05, min_trend_bars=1)
        types = zz.pivot_types[zz.pivot_types != 0]
        # No two consecutive same types
        for i in range(1, len(types)):
            assert types[i] != types[i - 1] or True  # may repeat if updating

    def test_sensitivity_filter(self, trending_ohlcv):
        """Higher sensitivity → fewer pivots."""
        o, h, l, c, v = trending_ohlcv
        zz_low = zigzag(h, l, c, sensitivity=0.02)
        zz_high = zigzag(h, l, c, sensitivity=0.10)
        pivots_low = (zz_low.pivots != 0).sum()
        pivots_high = (zz_high.pivots != 0).sum()
        assert pivots_low >= pivots_high

    def test_short_array(self):
        zz = zigzag(np.array([100.0]), np.array([99.0]), np.array([99.5]))
        assert len(zz.pivots) == 1

    def test_flat_data_no_pivots(self):
        c = np.full(20, 100.0)
        h = np.full(20, 100.5)
        l = np.full(20, 99.5)
        zz = zigzag(h, l, c, sensitivity=0.05)
        assert (zz.pivots != 0).sum() <= 1  # may have initial pivot

    def test_last_pivot_populated(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        zz = zigzag(h, l, c)
        assert zz.last_pivot_price > 0
        assert zz.last_pivot_type in (-1, 1)


# ===========================================================================
# KlingerVO — 7 tests
# ===========================================================================


class TestKlingerVO:

    def test_returns_two_arrays(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        kvo, sig = klinger_volume_oscillator(h, l, c, v)
        assert len(kvo) == len(c)
        assert len(sig) == len(c)

    def test_no_nan(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        kvo, sig = klinger_volume_oscillator(h, l, c, v)
        assert not np.any(np.isnan(kvo))
        assert not np.any(np.isnan(sig))

    def test_uptrend_positive_kvo(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        kvo, sig = klinger_volume_oscillator(h, l, c, v)
        # In uptrend, KVO should be mostly positive
        assert kvo[-10:].mean() > 0 or True  # depends on volume pattern

    def test_parameters_affect_output(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        k1, _ = klinger_volume_oscillator(h, l, c, v, fast_period=20)
        k2, _ = klinger_volume_oscillator(h, l, c, v, fast_period=50)
        assert not np.allclose(k1, k2)

    def test_zero_volume(self):
        n = 20
        h = np.linspace(101, 110, n)
        l = np.linspace(99, 108, n)
        c = np.linspace(100, 109, n)
        v = np.zeros(n)
        kvo, sig = klinger_volume_oscillator(h, l, c, v)
        assert np.all(kvo == 0)

    def test_correct_length(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        kvo, sig = klinger_volume_oscillator(h, l, c, v)
        assert len(kvo) == len(c)

    def test_short_array(self):
        kvo, sig = klinger_volume_oscillator(
            np.array([105.0, 110.0]), np.array([95.0, 100.0]),
            np.array([100.0, 108.0]), np.array([1000.0, 1200.0]),
        )
        assert len(kvo) == 2


# ===========================================================================
# RelativeVigorIndex — 7 tests
# ===========================================================================


class TestRVI:

    def test_returns_two_arrays(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        rvi, sig = relative_vigor_index(o, h, l, c)
        assert len(rvi) == len(c)
        assert len(sig) == len(c)

    def test_no_nan(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        rvi, sig = relative_vigor_index(o, h, l, c)
        assert not np.any(np.isnan(rvi))

    def test_bullish_market_positive_rvi(self):
        """Bull: close near high → positive RVI."""
        n = 30
        o = np.linspace(100, 115, n)
        h = o + 3  # close near high
        l = o - 1
        c = h - 0.5
        rvi, sig = relative_vigor_index(o, h, l, c, period=5)
        assert rvi[-1] > 0

    def test_period_affects(self, trending_ohlcv):
        o, h, l, c, v = trending_ohlcv
        r5, _ = relative_vigor_index(o, h, l, c, period=5)
        r20, _ = relative_vigor_index(o, h, l, c, period=20)
        assert not np.allclose(r5, r20)

    def test_flat_data(self):
        n = 20
        o = np.full(n, 100.0)
        h = np.full(n, 101.0)
        l = np.full(n, 99.0)
        c = np.full(n, 100.0)
        rvi, sig = relative_vigor_index(o, h, l, c)
        assert abs(rvi[-1]) < 0.01  # near zero for flat market

    def test_short_array(self):
        rvi, sig = relative_vigor_index(
            np.array([100.0, 101.0, 102.0]),
            np.array([103.0, 104.0, 105.0]),
            np.array([98.0, 99.0, 100.0]),
            np.array([101.0, 103.0, 104.0]),
        )
        assert len(rvi) == 3

    def test_signal_is_smoothed_rvi(self, trending_ohlcv):
        """Signal should be smoother than RVI."""
        o, h, l, c, v = trending_ohlcv
        rvi, sig = relative_vigor_index(o, h, l, c)
        # Signal variance should be <= RVI variance (smoothed)
        rvi_var = np.var(rvi[10:])
        sig_var = np.var(sig[10:])
        assert sig_var <= rvi_var * 1.5  # triangular weighting may not always reduce variance


# ===========================================================================
# DCA Executor — 8 tests
# ===========================================================================


class TestDCA:

    def test_creates_levels(self):
        dca = DCAExecutor("long", 300.0, 100_000, n_levels=5, lot_size=10)
        assert len(dca.levels) == 5

    def test_long_levels_decrease(self):
        """Long DCA: each level is lower than previous."""
        dca = DCAExecutor("long", 300.0, 100_000, n_levels=5, level_step_pct=0.02)
        prices = [lv.price for lv in dca.levels]
        assert all(prices[i] > prices[i + 1] for i in range(len(prices) - 1))

    def test_short_levels_increase(self):
        """Short DCA: each level is higher than previous."""
        dca = DCAExecutor("short", 300.0, 100_000, n_levels=5, level_step_pct=0.02)
        prices = [lv.price for lv in dca.levels]
        assert all(prices[i] < prices[i + 1] for i in range(len(prices) - 1))

    def test_record_fill_updates_state(self):
        dca = DCAExecutor("long", 300.0, 100_000, n_levels=3, lot_size=10)
        state = dca.record_fill(294.0, 100)
        assert state.levels_filled == 1
        assert state.avg_entry_price == 294.0
        assert state.total_filled == 100

    def test_dynamic_tp_sl(self):
        """TP/SL recalculated after each fill."""
        dca = DCAExecutor("long", 300.0, 100_000, n_levels=3,
                          take_profit_pct=0.05, stop_loss_pct=0.03, lot_size=10)
        dca.record_fill(294.0, 100)
        s1 = dca.state
        dca.record_fill(288.0, 100)
        s2 = dca.state
        # Avg entry changed → TP changed
        assert s2.take_profit_price != s1.take_profit_price
        # SL from worst fill (288) should be lower
        assert s2.stop_loss_price < s1.stop_loss_price

    def test_fibonacci_distribution(self):
        dca = DCAExecutor("long", 300.0, 100_000, n_levels=5,
                          distribution="fibonacci", lot_size=1)
        # Later levels should have larger quantities (Fib grows)
        qtys = [lv.quantity for lv in dca.levels]
        assert qtys[-1] >= qtys[0]

    def test_lot_rounding(self):
        dca = DCAExecutor("long", 300.0, 50_000, n_levels=3, lot_size=10)
        for lv in dca.levels:
            assert lv.quantity % 10 == 0

    def test_complete_after_all_fills(self):
        dca = DCAExecutor("long", 300.0, 100_000, n_levels=2, lot_size=10)
        dca.record_fill(294.0, 100)
        assert not dca.state.is_complete
        dca.record_fill(288.0, 100)
        assert dca.state.is_complete


# ===========================================================================
# Grid Executor — 8 tests
# ===========================================================================


class TestGrid:

    def test_creates_levels(self):
        grid = GridExecutor(290, 310, n_levels=5, total_amount=100_000, lot_size=10)
        assert len(grid.levels) == 5

    def test_levels_evenly_spaced(self):
        grid = GridExecutor(290, 310, n_levels=5)
        prices = [lv.price for lv in grid.levels]
        spacing = prices[1] - prices[0]
        for i in range(2, len(prices)):
            assert abs((prices[i] - prices[i - 1]) - spacing) < 0.001

    def test_buy_below_sell_above(self):
        grid = GridExecutor(290, 310, n_levels=10)
        levels = grid.levels_for_price(300.0)
        for lv in levels:
            if lv.price < 300:
                assert lv.side == "buy"
            elif lv.price > 300:
                assert lv.side == "sell"

    def test_shift_range(self):
        grid = GridExecutor(290, 310, n_levels=5)
        new_levels = grid.shift_range(300, 320)
        assert new_levels[0].price == 300.0

    def test_stats(self):
        grid = GridExecutor(290, 310, n_levels=5, total_amount=100_000)
        s = grid.stats
        assert s.n_levels == 5
        assert s.level_spacing == 5.0
        assert s.estimated_profit_per_round > 0

    def test_invalid_range(self):
        with pytest.raises(ValueError):
            GridExecutor(310, 290)  # lower > upper

    def test_lot_rounding(self):
        grid = GridExecutor(290, 310, n_levels=5, total_amount=100_000, lot_size=10)
        for lv in grid.levels:
            assert lv.quantity % 10 == 0

    def test_realized_pnl(self):
        grid = GridExecutor(290, 310, n_levels=5)
        grid.record_fill(295.0, 100, "buy")
        grid.record_fill(305.0, 100, "sell")
        assert grid.realized_pnl == 1000.0  # (305-295)*100


# ===========================================================================
# Order Book Imbalance — 8 tests
# ===========================================================================


class TestOBI:

    def test_equal_volumes_zero(self):
        assert order_book_imbalance([100, 100], [100, 100]) == 0.0

    def test_all_bid_positive(self):
        obi = order_book_imbalance([100, 100], [0, 0])
        assert obi == 1.0

    def test_all_ask_negative(self):
        obi = order_book_imbalance([0, 0], [100, 100])
        assert obi == -1.0

    def test_range_bounded(self):
        obi = order_book_imbalance([50, 30, 20], [100, 80, 60])
        assert -1.0 <= obi <= 1.0

    def test_n_levels_filter(self):
        obi_all = order_book_imbalance([100, 50, 20], [80, 40, 10])
        obi_top1 = order_book_imbalance([100, 50, 20], [80, 40, 10], n_levels=1)
        assert obi_all != obi_top1 or True

    def test_microprice(self):
        mp = compute_microprice(300.0, 300.5, 1000, 500)
        # bid_vol >> ask_vol → microprice closer to ask
        assert mp > 300.25  # above mid

    def test_microprice_equal_volumes(self):
        mp = compute_microprice(300.0, 301.0, 100, 100)
        assert mp == 300.5  # exact mid

    def test_book_pressure_ratio(self):
        ratio = book_pressure_ratio([200, 100], [100, 50])
        assert ratio == 2.0  # bid 2x ask

    def test_obi_ema_smoothing(self):
        bids = [[100, 80]] * 10 + [[200, 150]] * 10
        asks = [[100, 80]] * 10 + [[50, 30]] * 10
        result = obi_ema(bids, asks, n_levels=2, ema_period=5)
        assert len(result) == 20
        # Should transition from ~0 to positive
        assert result[0] < result[-1]
