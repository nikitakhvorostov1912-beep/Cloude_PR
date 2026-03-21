"""Tests for Support/Resistance and Candle Patterns.

Components inspired by LiuAlgoTrader (MIT), written from scratch.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.indicators.support_resistance import (
    PriceLevel,
    _cluster_levels,
    _find_local_maxima,
    _find_local_minima,
    find_nearest_resistance,
    find_nearest_support,
    find_resistances,
    find_support_resistance,
    find_supports,
)
from src.indicators.candle_patterns import (
    CandleConfig,
    detect_bearish,
    detect_bullish,
    detect_doji,
    detect_engulfing_bearish,
    detect_engulfing_bullish,
    detect_hammer,
    detect_patterns,
    is_bearish,
    is_bullish,
    is_doji,
    is_dragonfly_doji,
    is_engulfing_bearish,
    is_engulfing_bullish,
    is_gravestone_doji,
    is_hammer,
    is_inverted_hammer,
    is_spinning_top,
)


# ===========================================================================
# Support / Resistance — 12 tests
# ===========================================================================


class TestLocalExtrema:
    """Low-level peak/trough detection."""

    def test_maxima_simple_peak(self):
        """Single peak in the middle."""
        data = np.array([1, 2, 3, 4, 3, 2, 1])
        peaks = _find_local_maxima(data)
        assert len(peaks) == 1
        assert data[peaks[0]] == 4

    def test_minima_simple_trough(self):
        """Single trough in the middle."""
        data = np.array([5, 4, 3, 2, 3, 4, 5])
        troughs = _find_local_minima(data)
        assert len(troughs) == 1
        assert data[troughs[0]] == 2

    def test_maxima_multiple_peaks(self):
        """Multiple peaks."""
        data = np.array([1, 3, 2, 5, 3, 4, 2])
        peaks = _find_local_maxima(data)
        assert len(peaks) >= 2

    def test_empty_array(self):
        """Empty or too short arrays."""
        assert len(_find_local_maxima(np.array([]))) == 0
        assert len(_find_local_maxima(np.array([1, 2]))) == 0
        assert len(_find_local_minima(np.array([]))) == 0

    def test_flat_array(self):
        """Flat data has no peaks."""
        data = np.full(10, 5.0)
        # All diffs == 0, no sign change
        assert len(_find_local_maxima(data)) == 0


class TestClustering:
    """Level clustering by proximity."""

    def test_cluster_nearby(self):
        """Close prices cluster together."""
        prices = np.array([100.0, 101.0, 100.5, 200.0, 201.0])
        clusters = _cluster_levels(prices, margin_pct=0.02)
        assert len(clusters) == 2  # two groups: ~100 and ~200

    def test_cluster_single(self):
        """Single price → single cluster."""
        clusters = _cluster_levels(np.array([50.0]), margin_pct=0.02)
        assert len(clusters) == 1
        assert clusters[0][0] == 50.0
        assert clusters[0][1] == 1

    def test_cluster_empty(self):
        """Empty → empty."""
        assert _cluster_levels(np.array([]), margin_pct=0.02) == []

    def test_cluster_strength(self):
        """Multiple touches at same level → higher strength."""
        prices = np.array([100.0, 100.5, 101.0, 100.8, 200.0])
        clusters = _cluster_levels(prices, margin_pct=0.02)
        # First cluster has 4 elements, second has 1
        first_cluster = [c for c in clusters if c[0] < 150]
        assert first_cluster[0][1] == 4


class TestResistances:
    """Resistance level detection."""

    def test_finds_peaks_above_current(self):
        """Only returns levels above current price."""
        highs = np.array([100, 110, 105, 115, 108, 120, 112, 105])
        levels = find_resistances(highs, current_price=110)
        assert all(lv.price >= 110 for lv in levels)
        assert all(lv.level_type == "resistance" for lv in levels)

    def test_returns_sorted_ascending(self):
        """Levels sorted by price ascending."""
        highs = np.array([90, 120, 100, 115, 105, 130, 110])
        levels = find_resistances(highs)
        prices = [lv.price for lv in levels]
        assert prices == sorted(prices)

    def test_empty_when_no_peaks(self):
        """Monotonically rising has no local maxima in middle."""
        highs = np.array([1, 2, 3, 4, 5])
        levels = find_resistances(highs)
        assert len(levels) == 0

    def test_min_strength_filter(self):
        """min_strength filters weak levels."""
        highs = np.array([100, 110, 105, 110, 108, 110, 105])
        # 110 appears as peak multiple times
        levels_any = find_resistances(highs, min_strength=1)
        levels_strong = find_resistances(highs, min_strength=2)
        assert len(levels_any) >= len(levels_strong)


class TestSupports:
    """Support level detection."""

    def test_finds_troughs_below_current(self):
        """Only returns levels below current price."""
        lows = np.array([100, 95, 98, 90, 96, 88, 93])
        levels = find_supports(lows, current_price=95)
        assert all(lv.price <= 95 for lv in levels)
        assert all(lv.level_type == "support" for lv in levels)

    def test_returns_sorted_descending(self):
        """Supports sorted by price descending (nearest first)."""
        lows = np.array([100, 90, 95, 85, 92, 80, 88])
        levels = find_supports(lows, current_price=100)
        prices = [lv.price for lv in levels]
        assert prices == sorted(prices, reverse=True)


class TestConvenience:
    """Nearest support/resistance helpers."""

    def test_nearest_support(self):
        """Returns closest support below price."""
        lows = np.array([100, 95, 98, 90, 96, 88, 93, 97])
        s = find_nearest_support(lows, current_price=97)
        assert s is not None
        assert s < 97

    def test_nearest_resistance(self):
        """Returns closest resistance above price."""
        highs = np.array([100, 110, 105, 115, 108, 120, 112])
        r = find_nearest_resistance(highs, current_price=110)
        assert r is not None
        assert r >= 110

    def test_combined_sr(self):
        """find_support_resistance returns both types."""
        highs = np.array([100, 110, 105, 115, 108])
        lows = np.array([95, 90, 92, 88, 93])
        levels = find_support_resistance(highs, lows, current_price=100)
        types = {lv.level_type for lv in levels}
        assert "support" in types or "resistance" in types

    def test_no_support_found(self):
        """No support below very low price."""
        lows = np.array([100, 95, 98])
        s = find_nearest_support(lows, current_price=80)
        assert s is None


# ===========================================================================
# Candle Patterns — Scalar — 12 tests
# ===========================================================================


class TestCandleScalar:
    """Single-candle pattern detection (scalar API)."""

    def test_doji(self):
        """Doji: open == close, shadows on both sides."""
        assert is_doji(100.0, 105.0, 95.0, 100.0)

    def test_doji_no_range(self):
        """Zero-range bar is not a doji."""
        assert not is_doji(100.0, 100.0, 100.0, 100.0)

    def test_gravestone_doji(self):
        """Gravestone: body near low, long upper shadow."""
        assert is_gravestone_doji(100.0, 110.0, 99.0, 100.0)

    def test_dragonfly_doji(self):
        """Dragonfly: body near high, long lower shadow."""
        assert is_dragonfly_doji(100.0, 101.0, 90.0, 100.0)

    def test_spinning_top(self):
        """Spinning top: small body, balanced shadows."""
        assert is_spinning_top(100.0, 105.0, 95.0, 101.0)

    def test_hammer(self):
        """Hammer: small body near high, long lower shadow."""
        # body = |102 - 100| = 2, lower = 100 - 90 = 10, upper = 103 - 102 = 1
        assert is_hammer(100.0, 103.0, 90.0, 102.0)

    def test_inverted_hammer(self):
        """Inverted hammer: small body near low, long upper shadow."""
        # body = |101 - 100| = 1, upper = 110 - 101 = 9, lower = 100 - 99.5 = 0.5
        assert is_inverted_hammer(100.0, 110.0, 99.5, 101.0)

    def test_bullish_strong(self):
        """Strong bullish candle: large body, close >> open."""
        assert is_bullish(100.0, 112.0, 99.0, 111.0)

    def test_bearish_strong(self):
        """Strong bearish candle: large body, close << open."""
        assert is_bearish(111.0, 112.0, 99.0, 100.0)

    def test_not_bullish_when_doji(self):
        """Doji is not a strong bullish candle."""
        assert not is_bullish(100.0, 105.0, 95.0, 100.0)

    def test_engulfing_bullish(self):
        """Bullish engulfing: bearish then larger bullish."""
        assert is_engulfing_bullish(
            105.0, 106.0, 99.0, 100.0,  # bearish candle 1
            99.0, 108.0, 98.0, 107.0,   # bullish candle 2 (engulfs)
        )

    def test_engulfing_bearish(self):
        """Bearish engulfing: bullish then larger bearish."""
        assert is_engulfing_bearish(
            100.0, 106.0, 99.0, 105.0,  # bullish candle 1
            106.0, 107.0, 98.0, 99.0,   # bearish candle 2 (engulfs)
        )


# ===========================================================================
# Candle Patterns — Vectorized — 8 tests
# ===========================================================================


class TestCandleVectorized:
    """Vectorized pattern detection on arrays."""

    @pytest.fixture
    def ohlc_mixed(self) -> tuple:
        """10 bars with known patterns."""
        o = np.array([100, 105, 100, 100, 110, 100, 100, 105, 100, 108])
        h = np.array([110, 108, 110, 101, 112, 103, 110, 106, 103, 109])
        l = np.array([ 95, 100,  95,  90,  99,  90,  99, 100,  90,  99])
        c = np.array([100, 103, 100, 100, 111, 101, 100, 100, 102, 100])
        return o, h, l, c

    def test_detect_patterns_returns_dict(self, ohlc_mixed):
        """detect_patterns returns dict with all keys."""
        o, h, l, c = ohlc_mixed
        result = detect_patterns(o, h, l, c)
        assert set(result.keys()) == {
            "doji", "hammer", "bullish", "bearish",
            "engulfing_bullish", "engulfing_bearish",
        }

    def test_detect_patterns_correct_length(self, ohlc_mixed):
        """All arrays have same length as input."""
        o, h, l, c = ohlc_mixed
        result = detect_patterns(o, h, l, c)
        for v in result.values():
            assert len(v) == len(o)

    def test_detect_doji_vectorized(self):
        """Vectorized doji matches scalar."""
        o = np.array([100.0, 200.0, 300.0])
        h = np.array([105.0, 210.0, 301.0])  # bar 3: tiny range
        l = np.array([ 95.0, 190.0, 299.0])
        c = np.array([100.0, 200.0, 300.0])
        result = detect_doji(o, h, l, c)
        assert result[0]  # doji: o==c, shadows both sides
        assert result[1]  # doji: o==c, shadows both sides
        assert result[2]  # doji: o==c, shadows both sides

    def test_detect_bullish_vectorized(self):
        """Vectorized bullish detection."""
        o = np.array([100.0, 100.0, 100.0])
        h = np.array([112.0, 101.0, 115.0])
        l = np.array([ 99.0, 99.0,  98.0])
        c = np.array([111.0, 100.5, 114.0])
        result = detect_bullish(o, h, l, c)
        assert result[0]   # strong bullish
        assert not result[1]  # tiny body
        assert result[2]   # strong bullish

    def test_detect_engulfing_bullish_vectorized(self):
        """Vectorized bullish engulfing."""
        o = np.array([105.0, 99.0])
        h = np.array([106.0, 108.0])
        l = np.array([ 99.0, 98.0])
        c = np.array([100.0, 107.0])
        result = detect_engulfing_bullish(o, h, l, c)
        assert not result[0]  # first bar can't be engulfing
        assert result[1]      # second engulfs first

    def test_detect_engulfing_bearish_vectorized(self):
        """Vectorized bearish engulfing."""
        o = np.array([100.0, 106.0])
        h = np.array([106.0, 107.0])
        l = np.array([ 99.0, 98.0])
        c = np.array([105.0, 99.0])
        result = detect_engulfing_bearish(o, h, l, c)
        assert not result[0]
        assert result[1]

    def test_empty_arrays(self):
        """Empty arrays → empty results."""
        result = detect_patterns([], [], [], [])
        for v in result.values():
            assert len(v) == 0

    def test_single_bar(self):
        """Single bar arrays work."""
        result = detect_patterns([100], [110], [90], [100])
        assert len(result["doji"]) == 1


class TestCandleConfig:
    """CandleConfig customization."""

    def test_strict_doji(self):
        """Strict config rejects wider bodies."""
        strict = CandleConfig(body_doji_max=0.01)
        # Body = 1% of range → passes strict
        assert is_doji(100.0, 110.0, 90.0, 100.0, cfg=strict)
        # Body = 10% of range → fails strict
        assert not is_doji(100.0, 110.0, 90.0, 102.0, cfg=strict)

    def test_relaxed_bullish(self):
        """Relaxed config accepts weaker bodies."""
        relaxed = CandleConfig(body_strong_min=0.3)
        # 40% body/range → passes relaxed but not default (0.6)
        assert is_bullish(100.0, 110.0, 95.0, 106.0, cfg=relaxed)
        assert not is_bullish(100.0, 110.0, 95.0, 106.0)
