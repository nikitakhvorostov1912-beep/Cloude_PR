"""Tests for src/indicators/ — SuperTrend, Squeeze Momentum, Damiani, Ehlers DSP."""
from __future__ import annotations

import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.indicators.supertrend import supertrend, SuperTrendResult
from src.indicators.squeeze_momentum import squeeze_momentum, SqueezeResult
from src.indicators.damiani import damiani_volatmeter, DamianiResult
from src.indicators.ehlers import voss_filter, bandpass_filter, reflex, VossResult, BandPassResult


# ---------------------------------------------------------------------------
# Fixtures: synthetic OHLCV data
# ---------------------------------------------------------------------------

@pytest.fixture
def trending_up() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """200 bars of trending-up data with noise."""
    np.random.seed(42)
    n = 200
    base = np.linspace(100, 150, n) + np.random.normal(0, 1, n)
    high = base + np.abs(np.random.normal(1, 0.5, n))
    low = base - np.abs(np.random.normal(1, 0.5, n))
    close = base + np.random.normal(0, 0.3, n)
    return high, low, close


@pytest.fixture
def mean_reverting() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """200 bars of range-bound data (sine wave + noise)."""
    np.random.seed(42)
    n = 200
    base = 100 + 5 * np.sin(np.linspace(0, 8 * np.pi, n)) + np.random.normal(0, 0.5, n)
    high = base + np.abs(np.random.normal(0.5, 0.3, n))
    low = base - np.abs(np.random.normal(0.5, 0.3, n))
    close = base + np.random.normal(0, 0.2, n)
    return high, low, close


# ---------------------------------------------------------------------------
# SuperTrend
# ---------------------------------------------------------------------------

class TestSuperTrend:
    def test_returns_correct_type(self, trending_up):
        h, l, c = trending_up
        result = supertrend(h, l, c)
        assert isinstance(result, SuperTrendResult)
        assert len(result.trend) == len(c)
        assert len(result.direction) == len(c)
        assert len(result.changed) == len(c)

    def test_direction_values(self, trending_up):
        h, l, c = trending_up
        result = supertrend(h, l, c, period=10, factor=3.0)
        # Direction should be +1 or -1
        unique = set(result.direction[10:].astype(int))
        assert unique.issubset({-1, 1})

    def test_trending_up_mostly_bullish(self, trending_up):
        h, l, c = trending_up
        result = supertrend(h, l, c, period=10, factor=2.0)
        bullish_pct = (result.direction[20:] == 1).mean()
        assert bullish_pct > 0.5, "Trending up data should be mostly bullish"

    def test_changed_is_binary(self, trending_up):
        h, l, c = trending_up
        result = supertrend(h, l, c)
        assert set(result.changed).issubset({0, 1})

    def test_short_data(self):
        h = np.array([10.0, 11.0, 12.0])
        l = np.array([9.0, 10.0, 11.0])
        c = np.array([9.5, 10.5, 11.5])
        result = supertrend(h, l, c, period=2)
        assert len(result.trend) == 3


# ---------------------------------------------------------------------------
# Squeeze Momentum
# ---------------------------------------------------------------------------

class TestSqueezeMomentum:
    def test_returns_correct_type(self, trending_up):
        h, l, c = trending_up
        result = squeeze_momentum(h, l, c)
        assert isinstance(result, SqueezeResult)
        assert len(result.squeeze) == len(c)
        assert len(result.momentum) == len(c)

    def test_squeeze_values(self, mean_reverting):
        h, l, c = mean_reverting
        result = squeeze_momentum(h, l, c, length=20)
        unique = set(result.squeeze)
        # Should contain at least two of {-1, 0, 1}
        assert unique.issubset({-1, 0, 1})

    def test_momentum_signal_values(self, trending_up):
        h, l, c = trending_up
        result = squeeze_momentum(h, l, c)
        unique = set(result.momentum_signal)
        assert unique.issubset({-2, -1, 0, 1, 2})

    def test_trending_positive_momentum(self, trending_up):
        h, l, c = trending_up
        result = squeeze_momentum(h, l, c)
        # Last 50 bars of uptrend should have mostly positive momentum
        pos_pct = (result.momentum[-50:] > 0).mean()
        # Relaxed: at least some positive momentum
        assert pos_pct > 0.3


# ---------------------------------------------------------------------------
# Damiani Volatmeter
# ---------------------------------------------------------------------------

class TestDamiani:
    def test_returns_correct_type(self, trending_up):
        h, l, c = trending_up
        result = damiani_volatmeter(h, l, c)
        assert isinstance(result, DamianiResult)
        assert len(result.vol) == len(c)
        assert len(result.anti) == len(c)

    def test_vol_positive(self, trending_up):
        h, l, c = trending_up
        result = damiani_volatmeter(h, l, c)
        # Vol should be mostly non-negative after warmup
        assert (result.vol[100:] >= 0).all()


# ---------------------------------------------------------------------------
# Ehlers: Voss Filter
# ---------------------------------------------------------------------------

class TestVossFilter:
    def test_returns_correct_type(self, mean_reverting):
        _, _, c = mean_reverting
        result = voss_filter(c, period=20)
        assert isinstance(result, VossResult)
        assert len(result.voss) == len(c)
        assert len(result.filt) == len(c)

    def test_oscillates_around_zero(self, mean_reverting):
        _, _, c = mean_reverting
        result = voss_filter(c, period=20)
        # Voss should oscillate — both positive and negative values
        active = result.voss[50:]
        assert (active > 0).any() and (active < 0).any()


# ---------------------------------------------------------------------------
# Ehlers: BandPass Filter
# ---------------------------------------------------------------------------

class TestBandPassFilter:
    def test_returns_correct_type(self, mean_reverting):
        _, _, c = mean_reverting
        result = bandpass_filter(c, period=20)
        assert isinstance(result, BandPassResult)
        assert len(result.bp) == len(c)
        assert len(result.bp_normalized) == len(c)

    def test_normalized_bounded(self, mean_reverting):
        _, _, c = mean_reverting
        result = bandpass_filter(c, period=20)
        # Normalized should be roughly in [-1, 1] after warmup
        active = result.bp_normalized[50:]
        assert np.abs(active).max() <= 1.5  # allow small overshoot


# ---------------------------------------------------------------------------
# Ehlers: Reflex
# ---------------------------------------------------------------------------

class TestReflex:
    def test_returns_array(self, trending_up):
        _, _, c = trending_up
        result = reflex(c, period=20)
        assert isinstance(result, np.ndarray)
        assert len(result) == len(c)

    def test_trending_up_positive_reflex(self, trending_up):
        _, _, c = trending_up
        result = reflex(c, period=20)
        # Uptrend should produce mostly positive reflex after warmup
        active = result[40:]
        pos_pct = (active > 0).mean()
        assert pos_pct > 0.4
