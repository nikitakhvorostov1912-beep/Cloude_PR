"""Tests for LEAN-inspired components: indicators, circuit breaker, PSR, slippage.

Formulas from QuantConnect LEAN (Apache 2.0), implementations from scratch.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.indicators.advanced import (
    ChandeKrollResult,
    augen_price_spike,
    chande_kroll_stop,
    choppiness_index,
    rogers_satchell_volatility,
    schaff_trend_cycle,
)
from src.risk.portfolio_circuit_breaker import (
    PortfolioCircuitBreaker,
)
from src.backtest.metrics import (
    probabilistic_sharpe_ratio,
    volume_share_slippage,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def trending_ohlc() -> tuple:
    """Steadily rising OHLC data (strong trend)."""
    n = 50
    base = np.linspace(100, 150, n)
    noise = np.random.default_rng(42).normal(0, 1, n)
    c = base + noise
    h = c + abs(noise) + 1
    l = c - abs(noise) - 1
    o = c - noise * 0.5
    return o, h, l, c


@pytest.fixture
def choppy_ohlc() -> tuple:
    """Ranging/choppy OHLC data (no trend)."""
    n = 50
    rng = np.random.default_rng(99)
    c = 100 + rng.normal(0, 2, n)
    h = c + rng.uniform(1, 3, n)
    l = c - rng.uniform(1, 3, n)
    o = c + rng.normal(0, 0.5, n)
    return o, h, l, c


# ===========================================================================
# ChandeKrollStop — 8 tests
# ===========================================================================


class TestChandeKrollStop:

    def test_returns_correct_type(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        result = chande_kroll_stop(h, l, c)
        assert isinstance(result, ChandeKrollResult)
        assert len(result.stop_long) == len(c)
        assert len(result.stop_short) == len(c)
        assert len(result.signal) == len(c)

    def test_uptrend_long_signal(self, trending_ohlc):
        """Trending up → mostly long signals."""
        o, h, l, c = trending_ohlc
        result = chande_kroll_stop(h, l, c)
        long_pct = (result.signal[-20:] > 0).mean()
        assert long_pct > 0.5

    def test_stop_long_below_close(self, trending_ohlc):
        """In uptrend, stop_long should be below close."""
        o, h, l, c = trending_ohlc
        result = chande_kroll_stop(h, l, c)
        # After warmup, stop_long < close for uptrend
        below = (result.stop_long[-20:] < c[-20:]).mean()
        assert below > 0.7

    def test_parameters_affect_output(self, trending_ohlc):
        """Different parameters → different stops."""
        o, h, l, c = trending_ohlc
        r1 = chande_kroll_stop(h, l, c, atr_mult=1.0)
        r2 = chande_kroll_stop(h, l, c, atr_mult=3.0)
        # Wider multiplier → wider stops
        assert not np.allclose(r1.stop_long, r2.stop_long)

    def test_short_array(self):
        """Very short arrays don't crash."""
        h = np.array([100.0, 102.0, 101.0])
        l = np.array([98.0, 99.0, 99.5])
        c = np.array([99.0, 101.0, 100.0])
        result = chande_kroll_stop(h, l, c, atr_period=2, stop_period=2)
        assert len(result.signal) == 3

    def test_signal_values_bounded(self, trending_ohlc):
        """Signals are -1, 0, or +1."""
        o, h, l, c = trending_ohlc
        result = chande_kroll_stop(h, l, c)
        unique = set(result.signal)
        assert unique.issubset({-1.0, 0.0, 1.0})

    def test_flat_data(self):
        """Flat price → stop_long ≈ stop_short ≈ price."""
        c = np.full(30, 100.0)
        h = np.full(30, 100.5)
        l = np.full(30, 99.5)
        result = chande_kroll_stop(h, l, c)
        # With tiny range, stops converge near price
        assert abs(result.stop_long[-1] - 100.0) < 5
        assert abs(result.stop_short[-1] - 100.0) < 5

    def test_default_parameters(self, trending_ohlc):
        """Default params (10, 1.5, 9) produce valid output."""
        o, h, l, c = trending_ohlc
        result = chande_kroll_stop(h, l, c)
        assert not np.any(np.isnan(result.stop_long))
        assert not np.any(np.isnan(result.stop_short))


# ===========================================================================
# ChoppinessIndex — 7 tests
# ===========================================================================


class TestChoppinessIndex:

    def test_trending_low_chop(self, trending_ohlc):
        """Strong trend → low choppiness (near 38.2)."""
        o, h, l, c = trending_ohlc
        ci = choppiness_index(h, l, c)
        assert ci[-1] < 55  # below midpoint = trending

    def test_choppy_high_chop(self, choppy_ohlc):
        """Ranging market → high choppiness (near 61.8)."""
        o, h, l, c = choppy_ohlc
        ci = choppiness_index(h, l, c)
        assert ci[-1] > 45  # above midpoint = choppy

    def test_range_bounded(self, trending_ohlc):
        """CHOP is between ~38 and 100."""
        o, h, l, c = trending_ohlc
        ci = choppiness_index(h, l, c)
        assert np.all(ci >= 0)
        assert np.all(ci <= 100)

    def test_flat_data_max_chop(self):
        """Flat data → CHOP = 100 (maximum choppiness)."""
        c = np.full(20, 100.0)
        h = np.full(20, 100.0)
        l = np.full(20, 100.0)
        ci = choppiness_index(h, l, c)
        assert ci[-1] == 100.0

    def test_period_affects_output(self, trending_ohlc):
        """Different periods → different values."""
        o, h, l, c = trending_ohlc
        ci14 = choppiness_index(h, l, c, period=14)
        ci7 = choppiness_index(h, l, c, period=7)
        assert not np.allclose(ci14, ci7)

    def test_correct_length(self, trending_ohlc):
        """Output same length as input."""
        o, h, l, c = trending_ohlc
        ci = choppiness_index(h, l, c)
        assert len(ci) == len(c)

    def test_no_nan(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        ci = choppiness_index(h, l, c)
        assert not np.any(np.isnan(ci))


# ===========================================================================
# SchaffTrendCycle — 7 tests
# ===========================================================================


class TestSchaffTrendCycle:

    def test_range_0_100(self, trending_ohlc):
        """STC bounded [0, 100]."""
        o, h, l, c = trending_ohlc
        stc = schaff_trend_cycle(c)
        assert np.all(stc >= 0)
        assert np.all(stc <= 100)

    def test_uptrend_stc_not_zero(self):
        """Strong uptrend with enough data → STC is computed (not NaN)."""
        rng = np.random.default_rng(42)
        c = np.linspace(100, 200, 200) + rng.normal(0, 2, 200)
        stc = schaff_trend_cycle(c, cycle_period=10, fast_period=12, slow_period=26)
        assert not np.any(np.isnan(stc))
        assert 0.0 <= stc[-1] <= 100.0

    def test_correct_length(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        stc = schaff_trend_cycle(c)
        assert len(stc) == len(c)

    def test_parameters_affect_output(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        stc1 = schaff_trend_cycle(c, cycle_period=10)
        stc2 = schaff_trend_cycle(c, cycle_period=20)
        assert not np.allclose(stc1, stc2)

    def test_flat_data(self):
        """Flat data → STC around 50."""
        c = np.full(60, 100.0)
        stc = schaff_trend_cycle(c)
        assert 40 <= stc[-1] <= 60

    def test_no_nan(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        stc = schaff_trend_cycle(c)
        assert not np.any(np.isnan(stc))

    def test_short_array(self):
        stc = schaff_trend_cycle(np.array([100, 101, 99, 102, 98]))
        assert len(stc) == 5


# ===========================================================================
# AugenPriceSpike — 7 tests
# ===========================================================================


class TestAugenPriceSpike:

    def test_normal_returns_near_zero(self):
        """Normal price movement → spike near 0."""
        rng = np.random.default_rng(42)
        c = 100 + np.cumsum(rng.normal(0, 0.5, 50))
        spike = augen_price_spike(c)
        # Most values should be within [-3, 3] sigma
        valid = spike[spike != 0]
        assert np.abs(valid).mean() < 3

    def test_spike_detection(self):
        """Large jump → high spike value."""
        c = np.concatenate([
            np.full(10, 100.0),
            [100.5, 99.5, 100.2, 115.0, 115.0],  # jump at index 13
        ])
        spike = augen_price_spike(c, period=3)
        # The jump bar (index 13) should have a large spike
        jump_idx = 13
        assert abs(spike[jump_idx]) > 1.0  # significant movement

    def test_correct_length(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        spike = augen_price_spike(c)
        assert len(spike) == len(c)

    def test_short_array(self):
        """Too short → all zeros."""
        spike = augen_price_spike(np.array([100, 101]))
        assert np.all(spike == 0)

    def test_flat_data_zero_spike(self):
        """No movement → spike = 0 (std = 0)."""
        c = np.full(20, 100.0)
        spike = augen_price_spike(c)
        assert np.all(spike == 0)

    def test_no_nan(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        spike = augen_price_spike(c)
        assert not np.any(np.isnan(spike))

    def test_period_affects(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        s3 = augen_price_spike(c, period=3)
        s10 = augen_price_spike(c, period=10)
        assert not np.allclose(s3[-10:], s10[-10:])


# ===========================================================================
# RogersSatchellVolatility — 7 tests
# ===========================================================================


class TestRogersSatchell:

    def test_positive_volatility(self, trending_ohlc):
        """Volatility should be positive for moving prices."""
        o, h, l, c = trending_ohlc
        rsv = rogers_satchell_volatility(o, h, l, c)
        assert rsv[-1] > 0

    def test_flat_data_zero_vol(self):
        """No movement → vol = 0."""
        n = 30
        v = np.full(n, 100.0)
        rsv = rogers_satchell_volatility(v, v, v, v)
        assert rsv[-1] == 0.0

    def test_higher_vol_for_volatile(self):
        """More volatile data → higher RS vol."""
        rng = np.random.default_rng(42)
        n = 50
        c1 = 100 + np.cumsum(rng.normal(0, 0.5, n))
        c2 = 100 + np.cumsum(rng.normal(0, 2.0, n))
        for c in [c1, c2]:
            c[:] = np.abs(c)  # ensure positive
        h1, l1, o1 = c1 + 1, c1 - 1, c1 - 0.3
        h2, l2, o2 = c2 + 3, c2 - 3, c2 - 1
        rs1 = rogers_satchell_volatility(o1, h1, l1, c1, period=10)
        rs2 = rogers_satchell_volatility(o2, h2, l2, c2, period=10)
        assert rs2[-1] > rs1[-1]

    def test_correct_length(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        rsv = rogers_satchell_volatility(o, h, l, c)
        assert len(rsv) == len(c)

    def test_no_nan(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        rsv = rogers_satchell_volatility(o, h, l, c)
        assert not np.any(np.isnan(rsv))

    def test_period_affects(self, trending_ohlc):
        o, h, l, c = trending_ohlc
        r5 = rogers_satchell_volatility(o, h, l, c, period=5)
        r20 = rogers_satchell_volatility(o, h, l, c, period=20)
        assert not np.allclose(r5, r20)

    def test_short_array(self):
        rsv = rogers_satchell_volatility(
            np.array([100.0]), np.array([105.0]),
            np.array([95.0]), np.array([102.0]),
        )
        assert len(rsv) == 1


# ===========================================================================
# PortfolioCircuitBreaker — 10 tests
# ===========================================================================


class TestPortfolioCircuitBreaker:

    def test_no_trigger_within_threshold(self):
        cb = PortfolioCircuitBreaker(max_dd_pct=0.15)
        cb.update(100_000)
        cb.update(110_000)  # new peak
        triggered = cb.update(95_000)  # DD = 13.6% < 15%
        assert not triggered
        assert not cb.is_triggered

    def test_trigger_on_threshold(self):
        cb = PortfolioCircuitBreaker(max_dd_pct=0.15)
        cb.update(100_000)
        cb.update(110_000)
        triggered = cb.update(93_000)  # DD = 15.5% >= 15%
        assert triggered
        assert cb.is_triggered

    def test_trailing_mode_peak_updates(self):
        """Peak tracks equity highs."""
        cb = PortfolioCircuitBreaker(max_dd_pct=0.10, trailing=True)
        cb.update(100_000)
        cb.update(120_000)  # new peak
        triggered = cb.update(109_000)  # DD from 120K = 9.2% < 10%
        assert not triggered
        triggered = cb.update(107_000)  # DD from 120K = 10.8% >= 10%
        assert triggered

    def test_static_mode(self):
        """Static mode uses initial capital, not peak."""
        cb = PortfolioCircuitBreaker(max_dd_pct=0.10, trailing=False)
        cb.update(100_000)
        cb.update(120_000)  # peak, but static ignores
        triggered = cb.update(91_000)  # DD from 100K = 9%
        assert not triggered
        triggered = cb.update(89_000)  # DD from 100K = 11%
        assert triggered

    def test_trigger_count(self):
        cb = PortfolioCircuitBreaker(max_dd_pct=0.10, cooldown_bars=1)
        cb.update(100_000)
        cb.update(89_000)   # trigger 1
        assert cb.state.trigger_count == 1
        cb.update(88_000)   # still triggered, cooldown
        cb.update(95_000)   # cooldown over, reset
        cb.update(84_000)   # trigger 2
        assert cb.state.trigger_count == 2

    def test_cooldown(self):
        cb = PortfolioCircuitBreaker(max_dd_pct=0.10, cooldown_bars=3)
        cb.update(100_000)
        cb.update(89_000)   # trigger
        assert cb.is_triggered
        cb.update(88_000)   # bar 1
        cb.update(87_000)   # bar 2
        assert cb.is_triggered
        cb.update(86_000)   # bar 3
        assert cb.is_triggered
        cb.update(90_000)   # bar 4 → cooldown over
        assert not cb.is_triggered

    def test_reset(self):
        cb = PortfolioCircuitBreaker(max_dd_pct=0.10)
        cb.update(100_000)
        cb.update(89_000)
        assert cb.is_triggered
        cb.reset(100_000)
        assert not cb.is_triggered

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            PortfolioCircuitBreaker(max_dd_pct=0.0)
        with pytest.raises(ValueError):
            PortfolioCircuitBreaker(max_dd_pct=1.0)

    def test_first_update_no_trigger(self):
        cb = PortfolioCircuitBreaker(max_dd_pct=0.01)
        triggered = cb.update(100_000)
        assert not triggered

    def test_growing_equity_never_triggers(self):
        cb = PortfolioCircuitBreaker(max_dd_pct=0.05)
        for eq in range(100_000, 200_000, 1000):
            triggered = cb.update(float(eq))
            assert not triggered


# ===========================================================================
# Probabilistic Sharpe Ratio — 7 tests
# ===========================================================================


class TestPSR:

    def test_positive_sharpe_high_psr(self):
        """Positive Sharpe with enough data → PSR high."""
        rng = np.random.default_rng(42)
        returns = rng.normal(0.002, 0.01, 500)
        psr = probabilistic_sharpe_ratio(returns)
        assert psr > 0.9  # strong positive mean → high confidence

    def test_negative_mean_low_psr(self):
        """Negative mean returns → PSR low."""
        rng = np.random.default_rng(42)
        returns = rng.normal(-0.002, 0.01, 500)
        psr = probabilistic_sharpe_ratio(returns, sr_benchmark=0)
        assert psr < 0.1

    def test_strong_strategy_psr_near_one(self):
        """Very strong strategy → PSR near 1."""
        rng = np.random.default_rng(42)
        returns = rng.normal(0.005, 0.005, 1000)
        psr = probabilistic_sharpe_ratio(returns)
        assert psr > 0.95

    def test_short_history_lower_confidence(self):
        """Short history → PSR can still be high but depends on signal."""
        rng = np.random.default_rng(42)
        returns = rng.normal(0.002, 0.01, 20)
        psr = probabilistic_sharpe_ratio(returns)
        assert 0.0 <= psr <= 1.0

    def test_empty_returns(self):
        psr = probabilistic_sharpe_ratio(np.array([]))
        assert psr == 0.0

    def test_constant_positive_returns(self):
        """Constant positive → std≈0 → PSR=1.0."""
        psr = probabilistic_sharpe_ratio(np.full(100, 0.01))
        assert psr == 1.0

    def test_range_0_1(self):
        """PSR always in [0, 1]."""
        for seed in range(20):
            r = np.random.default_rng(seed).normal(0.001, 0.02, 100)
            psr = probabilistic_sharpe_ratio(r)
            assert 0.0 <= psr <= 1.0


# ===========================================================================
# VolumeShareSlippage — 7 tests
# ===========================================================================


class TestVolumeShareSlippage:

    def test_small_order_small_slip(self):
        """Small order (1% of volume) → tiny slippage."""
        slip = volume_share_slippage(500, 50_000, 300.0)
        assert 0 < slip < 0.1  # < 10 kopeks for 300 RUB stock

    def test_large_order_larger_slip(self):
        """Larger order → more slippage (quadratic)."""
        small = volume_share_slippage(100, 50_000, 300.0)
        large = volume_share_slippage(1000, 50_000, 300.0)
        assert large > small

    def test_quadratic_growth(self):
        """Slippage grows quadratically with volume fraction."""
        s1 = volume_share_slippage(500, 100_000, 100.0)
        s2 = volume_share_slippage(1000, 100_000, 100.0)
        # 2x quantity → ~4x slippage (quadratic)
        ratio = s2 / s1 if s1 > 0 else 0
        assert 3.5 < ratio < 4.5

    def test_volume_limit_cap(self):
        """Orders beyond volume_limit are capped."""
        huge = volume_share_slippage(100_000, 1_000, 100.0)  # 100x volume
        capped = volume_share_slippage(25, 1_000, 100.0, volume_limit=0.025)
        # Both should be capped at the same fraction
        assert abs(huge - capped) < 0.001

    def test_zero_volume(self):
        """Zero volume → zero slippage (avoid div by zero)."""
        assert volume_share_slippage(100, 0, 300.0) == 0.0

    def test_zero_price(self):
        assert volume_share_slippage(100, 1000, 0.0) == 0.0

    def test_proportional_to_price(self):
        """Same volume fraction, higher price → more slippage in RUB."""
        s1 = volume_share_slippage(100, 10_000, 100.0)
        s2 = volume_share_slippage(100, 10_000, 300.0)
        assert abs(s2 / s1 - 3.0) < 0.01
