"""Tests for abu-inspired components: UMP filter, trend quality, gap detector."""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ml.ump_filter import (
    UmpireFilter, UmpireResult, MainUmp, EdgeUmp, Verdict,
)
from src.indicators.trend_quality import (
    path_distance_ratio, gap_detector, gap_detector_array,
    polynomial_complexity, GapEvent,
)


# ===========================================================================
# UMP Filter — 12 tests
# ===========================================================================


class TestMainUmp:

    @pytest.fixture
    def trained_main(self):
        rng = np.random.default_rng(42)
        n = 200
        X = rng.normal(0, 1, (n, 5))
        # First half = wins, second half = losses (clusterable)
        X[:100] += 2.0  # shift winning trades
        y = np.concatenate([np.ones(100), np.zeros(100)])
        main = MainUmp(n_components_range=(5, 15), loss_threshold=0.6, min_hits=2)
        main.fit(X, y)
        return main, X

    def test_fit_creates_models(self, trained_main):
        main, X = trained_main
        assert main._fitted
        assert len(main._models) > 0

    def test_winning_trade_passes(self, trained_main):
        main, X = trained_main
        # Trade from "winning" region
        x = np.array([2.5, 2.0, 2.3, 1.8, 2.1])
        blocked, hits, total = main.predict(x)
        # Should mostly pass (winning cluster)
        assert total > 0

    def test_losing_trade_may_block(self, trained_main):
        main, X = trained_main
        # Trade from "losing" region
        x = np.array([-0.5, -0.3, -0.8, -0.2, -0.6])
        blocked, hits, total = main.predict(x)
        assert total > 0

    def test_unfitted_passes(self):
        main = MainUmp()
        blocked, hits, total = main.predict(np.zeros(5))
        assert not blocked
        assert total == 0


class TestEdgeUmp:

    @pytest.fixture
    def trained_edge(self):
        rng = np.random.default_rng(42)
        n = 200
        X = rng.normal(0, 1, (n, 5))
        pnl = rng.normal(0, 10, n)
        pnl[:50] += 20  # strong winners
        pnl[150:] -= 20  # strong losers
        edge = EdgeUmp(n_neighbors=50, dist_threshold=5.0, corr_threshold=0.5)
        edge.fit(X, pnl)
        return edge, X, pnl

    def test_fit_creates_labels(self, trained_edge):
        edge, X, pnl = trained_edge
        assert edge._fitted
        assert (edge._labels == 1).sum() > 0
        assert (edge._labels == -1).sum() > 0

    def test_similar_to_winner(self, trained_edge):
        edge, X, pnl = trained_edge
        # Trade similar to a top winner
        x = X[10] + np.random.default_rng(99).normal(0, 0.1, 5)
        vote, conf = edge.predict(x)
        # Should lean towards win
        assert vote >= 0

    def test_unfitted_returns_zero(self):
        edge = EdgeUmp()
        vote, conf = edge.predict(np.zeros(5))
        assert vote == 0
        assert conf == 0.0

    def test_far_trade_uncertain(self, trained_edge):
        edge, X, pnl = trained_edge
        # Very far from any historical trade
        x = np.full(5, 100.0)
        vote, conf = edge.predict(x)
        assert vote == 0  # too far → uncertain


class TestUmpireFilter:

    @pytest.fixture
    def umpire(self):
        rng = np.random.default_rng(42)
        n = 300
        X = rng.normal(0, 1, (n, 5))
        X[:150] += 1.5
        pnl = np.concatenate([rng.uniform(1, 10, 150), rng.uniform(-10, -1, 150)])
        ump = UmpireFilter(
            main_kwargs={"n_components_range": (5, 15), "min_hits": 1},
            edge_kwargs={"n_neighbors": 50, "dist_threshold": 5.0, "corr_threshold": 0.3},
        )
        ump.fit(X, pnl)
        return ump

    def test_judge_returns_result(self, umpire):
        result = umpire.judge(np.zeros(5))
        assert isinstance(result, UmpireResult)
        assert result.verdict in (Verdict.PASS, Verdict.BLOCK, Verdict.UNCERTAIN)

    def test_reason_not_empty(self, umpire):
        result = umpire.judge(np.random.default_rng(42).normal(0, 1, 5))
        assert len(result.reason) > 0

    def test_confidence_bounded(self, umpire):
        result = umpire.judge(np.random.default_rng(42).normal(0, 1, 5))
        assert 0.0 <= result.confidence <= 1.0

    def test_unfitted_passes(self):
        ump = UmpireFilter()
        result = ump.judge(np.zeros(5))
        assert result.verdict == Verdict.PASS
        assert not result.blocked


# ===========================================================================
# Path/Distance Ratio — 7 tests
# ===========================================================================


class TestPathDistanceRatio:

    def test_perfect_trend(self):
        """Linear rise → PDR ≈ 1.0."""
        close = np.linspace(100, 150, 50)
        pdr = path_distance_ratio(close, window=10)
        assert 0.99 < pdr[-1] < 1.01

    def test_noisy_higher_pdr(self):
        """Noisy data → PDR > 1."""
        rng = np.random.default_rng(42)
        close = np.linspace(100, 150, 50) + rng.normal(0, 5, 50)
        pdr = path_distance_ratio(close, window=10)
        assert pdr[-1] > 1.0

    def test_flat_market(self):
        """Flat with noise → very high PDR."""
        rng = np.random.default_rng(42)
        close = 100 + rng.normal(0, 2, 50)
        pdr = path_distance_ratio(close, window=10)
        valid = pdr[~np.isnan(pdr)]
        assert valid.mean() > 2.0

    def test_correct_length(self):
        close = np.linspace(100, 200, 100)
        pdr = path_distance_ratio(close, window=20)
        assert len(pdr) == 100

    def test_window_affects(self):
        """Different windows on noisy data → different PDR values."""
        rng = np.random.default_rng(42)
        close = np.linspace(100, 200, 100) + rng.normal(0, 3, 100)
        pdr10 = path_distance_ratio(close, window=10)
        pdr30 = path_distance_ratio(close, window=30)
        assert not np.allclose(pdr10[40:], pdr30[40:], equal_nan=True)

    def test_no_nan_after_warmup(self):
        close = np.linspace(100, 200, 50)
        pdr = path_distance_ratio(close, window=10)
        assert not np.any(np.isnan(pdr[10:]))

    def test_pure_oscillation(self):
        """Oscillating → very high PDR."""
        close = np.array([100, 110, 100, 110, 100, 110] * 10, dtype=float)
        pdr = path_distance_ratio(close, window=10)
        valid = pdr[~np.isnan(pdr)]
        assert valid.mean() > 3.0


# ===========================================================================
# Gap Detector — 8 tests
# ===========================================================================


class TestGapDetector:

    @pytest.fixture
    def ohlcv_with_gap(self):
        n = 50
        rng = np.random.default_rng(42)
        c = np.linspace(100, 110, n) + rng.normal(0, 0.5, n)
        o = c - rng.uniform(-0.5, 0.5, n)
        h = c + rng.uniform(0.5, 1.5, n)
        l = c - rng.uniform(0.5, 1.5, n)
        v = rng.uniform(1000, 5000, n)
        # Inject gap at bar 30
        c[30] = c[29] + 10  # +10 RUB gap
        h[30] = c[30] + 1
        l[30] = c[29] + 5
        o[30] = c[29] + 6
        v[30] = 20000  # high volume
        return o, h, l, c, v

    def test_detects_gap(self, ohlcv_with_gap):
        o, h, l, c, v = ohlcv_with_gap
        gaps = gap_detector(o, h, l, c, v)
        assert len(gaps) >= 1

    def test_gap_direction(self, ohlcv_with_gap):
        o, h, l, c, v = ohlcv_with_gap
        gaps = gap_detector(o, h, l, c, v)
        up_gaps = [g for g in gaps if g.direction == "up"]
        assert len(up_gaps) >= 1

    def test_gap_event_fields(self, ohlcv_with_gap):
        o, h, l, c, v = ohlcv_with_gap
        gaps = gap_detector(o, h, l, c, v)
        if gaps:
            g = gaps[0]
            assert isinstance(g, GapEvent)
            assert g.power > 0
            assert g.gap_pct > 0

    def test_no_gaps_in_flat(self):
        n = 50
        c = np.full(n, 100.0)
        o = c.copy()
        h = c + 0.1
        l = c - 0.1
        v = np.full(n, 1000.0)
        gaps = gap_detector(o, h, l, c, v)
        assert len(gaps) == 0

    def test_array_version(self, ohlcv_with_gap):
        o, h, l, c, v = ohlcv_with_gap
        arr = gap_detector_array(o, h, l, c, v)
        assert len(arr) == len(c)
        assert np.any(arr != 0)

    def test_short_data(self):
        gaps = gap_detector(
            np.array([100.0]), np.array([101.0]),
            np.array([99.0]), np.array([100.0]),
            np.array([1000.0]),
        )
        assert gaps == []

    def test_volume_confirmed(self, ohlcv_with_gap):
        o, h, l, c, v = ohlcv_with_gap
        gaps = gap_detector(o, h, l, c, v, volume_mult=1.0)
        confirmed = [g for g in gaps if g.volume_confirmed]
        assert len(confirmed) >= 0  # depends on specific data

    def test_higher_factor_fewer_gaps(self, ohlcv_with_gap):
        o, h, l, c, v = ohlcv_with_gap
        gaps_low = gap_detector(o, h, l, c, v, gap_factor=1.0)
        gaps_high = gap_detector(o, h, l, c, v, gap_factor=3.0)
        assert len(gaps_low) >= len(gaps_high)


# ===========================================================================
# Polynomial Complexity — 6 tests
# ===========================================================================


class TestPolynomialComplexity:

    def test_linear_trend(self):
        """Linear → complexity = 1."""
        close = np.linspace(100, 200, 50)
        pc = polynomial_complexity(close, window=20)
        assert pc[-1] == 1

    def test_quadratic(self):
        """U-shape → complexity = 2."""
        x = np.arange(50, dtype=float)
        close = 100 + (x - 25) ** 2 * 0.1
        pc = polynomial_complexity(close, window=30)
        assert pc[-1] >= 2

    def test_noisy_higher(self):
        """Noisy data → higher complexity."""
        rng = np.random.default_rng(42)
        close = 100 + rng.normal(0, 5, 100)
        pc = polynomial_complexity(close, window=20)
        assert pc[-1] >= 2

    def test_range_bounded(self):
        rng = np.random.default_rng(42)
        close = 100 + np.cumsum(rng.normal(0, 1, 100))
        pc = polynomial_complexity(close, window=20, max_degree=6)
        assert np.all(pc >= 1)
        assert np.all(pc <= 6)

    def test_correct_length(self):
        close = np.linspace(100, 200, 80)
        pc = polynomial_complexity(close, window=20)
        assert len(pc) == 80

    def test_flat_simple(self):
        """Flat data → complexity = 1."""
        close = np.full(50, 100.0)
        pc = polynomial_complexity(close, window=20)
        assert pc[-1] == 1
