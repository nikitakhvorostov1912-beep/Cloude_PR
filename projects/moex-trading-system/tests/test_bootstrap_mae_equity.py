"""Tests for BCa Bootstrap, MAE/MFE, Equity R², Relative Entropy, UPI.

New metrics inspired by pybroker concepts, written from scratch.
Tests verify correctness against known values and edge cases.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.metrics import (
    BootstrapCI,
    BootstrapResult,
    MAEMFESummary,
    TradeExcursion,
    TradeMetrics,
    bca_bootstrap,
    bootstrap_metrics,
    calculate_trade_metrics,
    compute_mae_mfe,
    equity_r_squared,
    format_metrics,
    relative_entropy,
    ulcer_performance_index,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def rng() -> np.random.Generator:
    """Reproducible random generator."""
    return np.random.default_rng(42)


@pytest.fixture
def normal_data(rng: np.random.Generator) -> np.ndarray:
    """1000 samples from N(10, 2)."""
    return rng.normal(loc=10.0, scale=2.0, size=1000)


@pytest.fixture
def trending_equity() -> np.ndarray:
    """Perfectly linear growing equity."""
    return np.linspace(100_000, 200_000, 252)


@pytest.fixture
def noisy_equity(rng: np.random.Generator) -> np.ndarray:
    """Linear trend + noise."""
    trend = np.linspace(100_000, 150_000, 252)
    noise = rng.normal(0, 2000, size=252)
    return trend + noise


@pytest.fixture
def long_trades() -> list[dict]:
    """Sample long trades with high/low prices for MAE/MFE."""
    return [
        {
            "pnl": 500,
            "direction": "long",
            "fee": 10,
            "holding_period": 5,
            "entry_price": 300.0,
            "high_prices": [302.0, 310.0, 308.0, 305.0, 303.0],
            "low_prices": [298.0, 295.0, 300.0, 301.0, 302.0],
        },
        {
            "pnl": -200,
            "direction": "long",
            "fee": 10,
            "holding_period": 3,
            "entry_price": 250.0,
            "high_prices": [252.0, 248.0, 245.0],
            "low_prices": [247.0, 240.0, 243.0],
        },
        {
            "pnl": 1000,
            "direction": "long",
            "fee": 10,
            "holding_period": 10,
            "entry_price": 150.0,
            "high_prices": [155.0, 160.0, 165.0, 170.0, 168.0, 167.0, 166.0, 165.0, 164.0, 163.0],
            "low_prices": [148.0, 149.0, 150.0, 155.0, 160.0, 158.0, 157.0, 156.0, 155.0, 162.0],
        },
    ]


@pytest.fixture
def short_trades() -> list[dict]:
    """Sample short trades with high/low prices for MAE/MFE."""
    return [
        {
            "pnl": 300,
            "direction": "short",
            "fee": 10,
            "holding_period": 4,
            "entry_price": 500.0,
            "high_prices": [502.0, 498.0, 495.0, 490.0],
            "low_prices": [498.0, 490.0, 488.0, 487.0],
        },
    ]


# ===========================================================================
# BCa Bootstrap — 10 tests
# ===========================================================================


class TestBcaBootstrap:
    """BCa Bootstrap Confidence Intervals."""

    def test_returns_bootstrap_result(self, normal_data: np.ndarray, rng: np.random.Generator):
        """bca_bootstrap returns BootstrapResult with correct structure."""
        result = bca_bootstrap(normal_data, np.mean, n_boot=500, rng=rng)
        assert isinstance(result, BootstrapResult)
        assert isinstance(result.ci_90, BootstrapCI)
        assert isinstance(result.ci_95, BootstrapCI)
        assert isinstance(result.ci_975, BootstrapCI)
        assert result.n_samples == 500

    def test_ci_ordering(self, normal_data: np.ndarray, rng: np.random.Generator):
        """Wider confidence levels have wider intervals."""
        result = bca_bootstrap(normal_data, np.mean, n_boot=2000, rng=rng)
        # 97.5% CI should be wider than 95%, which should be wider than 90%
        width_90 = result.ci_90.high - result.ci_90.low
        width_95 = result.ci_95.high - result.ci_95.low
        width_975 = result.ci_975.high - result.ci_975.low
        assert width_90 <= width_95 + 0.5  # allow small tolerance
        assert width_95 <= width_975 + 0.5

    def test_ci_covers_true_mean(self, rng: np.random.Generator):
        """95% CI should cover true mean of N(10, 2) with high probability."""
        true_mean = 10.0
        covered = 0
        n_trials = 20
        for seed in range(n_trials):
            data = np.random.default_rng(seed + 100).normal(10.0, 2.0, size=200)
            result = bca_bootstrap(data, np.mean, n_boot=1000, rng=np.random.default_rng(seed))
            if result.ci_95.low <= true_mean <= result.ci_95.high:
                covered += 1
        # Expect >= 80% coverage (relaxed due to small n_trials)
        assert covered >= 14, f"Coverage {covered}/{n_trials} too low"

    def test_point_estimate_correct(self, normal_data: np.ndarray, rng: np.random.Generator):
        """Point estimate should equal stat_fn applied to full data."""
        result = bca_bootstrap(normal_data, np.mean, n_boot=100, rng=rng)
        assert abs(result.point_estimate - float(normal_data.mean())) < 1e-10

    def test_empty_data(self):
        """Empty array returns zero bootstrap result."""
        result = bca_bootstrap(np.array([]), np.mean)
        assert result.point_estimate == 0.0
        assert result.n_samples == 0
        assert result.ci_95.low == 0.0
        assert result.ci_95.high == 0.0

    def test_single_element(self, rng: np.random.Generator):
        """Single element: CI degenerates to point."""
        result = bca_bootstrap(np.array([5.0]), np.mean, n_boot=100, rng=rng)
        assert result.point_estimate == 5.0

    def test_constant_data(self, rng: np.random.Generator):
        """All same values: CI should be very tight."""
        data = np.full(100, 7.0)
        result = bca_bootstrap(data, np.mean, n_boot=500, rng=rng)
        assert abs(result.ci_95.low - 7.0) < 0.01
        assert abs(result.ci_95.high - 7.0) < 0.01

    def test_custom_stat_fn(self, normal_data: np.ndarray, rng: np.random.Generator):
        """Works with custom statistic function (median)."""
        result = bca_bootstrap(normal_data, np.median, n_boot=500, rng=rng)
        assert abs(result.point_estimate - float(np.median(normal_data))) < 1e-10
        assert result.ci_95.low < result.point_estimate < result.ci_95.high

    def test_sample_size_smaller_than_data(self, normal_data: np.ndarray, rng: np.random.Generator):
        """Custom sample_size works correctly."""
        result = bca_bootstrap(normal_data, np.mean, n_boot=200, sample_size=50, rng=rng)
        assert isinstance(result, BootstrapResult)
        # Wider CI because smaller samples
        full = bca_bootstrap(normal_data, np.mean, n_boot=200, rng=np.random.default_rng(42))
        assert result.ci_95.high - result.ci_95.low > 0

    def test_reproducibility(self, normal_data: np.ndarray):
        """Same seed produces same result."""
        r1 = bca_bootstrap(normal_data, np.mean, n_boot=100, rng=np.random.default_rng(99))
        r2 = bca_bootstrap(normal_data, np.mean, n_boot=100, rng=np.random.default_rng(99))
        assert r1.ci_95.low == r2.ci_95.low
        assert r1.ci_95.high == r2.ci_95.high


class TestBootstrapMetrics:
    """bootstrap_metrics convenience function."""

    def test_returns_dict_with_four_metrics(self, rng: np.random.Generator):
        """Returns dict with sharpe, sortino, profit_factor, max_drawdown."""
        returns = rng.normal(0.001, 0.02, size=252)
        result = bootstrap_metrics(returns, n_boot=200, rng=rng)
        assert set(result.keys()) == {"sharpe", "sortino", "profit_factor", "max_drawdown"}
        for v in result.values():
            assert isinstance(v, BootstrapResult)

    def test_empty_returns(self):
        """Empty returns array returns zeroed results."""
        result = bootstrap_metrics(np.array([]), n_boot=100)
        for v in result.values():
            assert v.point_estimate == 0.0

    def test_short_returns(self, rng: np.random.Generator):
        """Very short series (2 values) still works."""
        result = bootstrap_metrics(np.array([0.01, -0.005]), n_boot=100, rng=rng)
        assert isinstance(result["sharpe"], BootstrapResult)


# ===========================================================================
# MAE / MFE — 10 tests
# ===========================================================================


class TestMAEMFE:
    """MAE/MFE Trade Quality metrics."""

    def test_long_trade_mae(self, long_trades: list[dict]):
        """MAE for long = entry - min(lows)."""
        result = compute_mae_mfe(long_trades[:1])
        # Trade 1: entry=300, min low=295 → MAE=5
        assert abs(result.avg_mae - 5.0) < 0.01

    def test_long_trade_mfe(self, long_trades: list[dict]):
        """MFE for long = max(highs) - entry."""
        result = compute_mae_mfe(long_trades[:1])
        # Trade 1: entry=300, max high=310 → MFE=10
        assert abs(result.avg_mfe - 10.0) < 0.01

    def test_short_trade_mae(self, short_trades: list[dict]):
        """MAE for short = max(highs) - entry."""
        result = compute_mae_mfe(short_trades)
        # entry=500, max high=502 → MAE=2
        assert abs(result.avg_mae - 2.0) < 0.01

    def test_short_trade_mfe(self, short_trades: list[dict]):
        """MFE for short = entry - min(lows)."""
        result = compute_mae_mfe(short_trades)
        # entry=500, min low=487 → MFE=13
        assert abs(result.avg_mfe - 13.0) < 0.01

    def test_mfe_mae_ratio(self, long_trades: list[dict]):
        """MFE/MAE ratio computed correctly across trades."""
        result = compute_mae_mfe(long_trades)
        assert result.mfe_mae_ratio > 0
        expected_ratio = result.avg_mfe / result.avg_mae if result.avg_mae > 0 else 0
        assert abs(result.mfe_mae_ratio - expected_ratio) < 0.01

    def test_empty_trades(self):
        """No trades → zero summary."""
        result = compute_mae_mfe([])
        assert result.avg_mae == 0.0
        assert result.avg_mfe == 0.0
        assert result.mfe_mae_ratio == 0.0
        assert len(result.trades) == 0

    def test_zero_entry_price(self):
        """Entry price zero → zero excursions (no division by zero)."""
        trades = [{"entry_price": 0.0, "direction": "long", "high_prices": [10], "low_prices": [5]}]
        result = compute_mae_mfe(trades)
        assert result.avg_mae == 0.0

    def test_single_bar_trade(self):
        """Trade with single bar — MAE/MFE from that bar."""
        trades = [{
            "entry_price": 100.0,
            "direction": "long",
            "high_prices": [105.0],
            "low_prices": [98.0],
        }]
        result = compute_mae_mfe(trades)
        assert abs(result.avg_mae - 2.0) < 0.01  # 100 - 98
        assert abs(result.avg_mfe - 5.0) < 0.01  # 105 - 100

    def test_pct_values(self, long_trades: list[dict]):
        """Percentage values are computed correctly."""
        result = compute_mae_mfe(long_trades[:1])
        # MAE=5, entry=300 → 1.67%
        assert abs(result.avg_mae_pct - (5.0 / 300.0 * 100)) < 0.01

    def test_multiple_trades_aggregation(self, long_trades: list[dict]):
        """Multiple trades aggregate correctly."""
        result = compute_mae_mfe(long_trades)
        assert len(result.trades) == 3
        # Verify avg is mean of individual values
        individual_maes = [t.mae for t in result.trades]
        assert abs(result.avg_mae - float(np.mean(individual_maes))) < 0.01

    def test_edge_ratio(self, long_trades: list[dict]):
        """Edge ratio = (avg_mfe - avg_mae) / avg_mae."""
        result = compute_mae_mfe(long_trades)
        if result.avg_mae > 0:
            expected = (result.avg_mfe - result.avg_mae) / result.avg_mae
            assert abs(result.edge_ratio - expected) < 0.01


# ===========================================================================
# Equity R² — 7 tests
# ===========================================================================


class TestEquityRSquared:
    """Equity R² — goodness of fit to linear growth."""

    def test_perfect_linear(self, trending_equity: np.ndarray):
        """Perfectly linear equity → R² = 1.0."""
        r2 = equity_r_squared(trending_equity)
        assert abs(r2 - 1.0) < 1e-10

    def test_flat_equity(self):
        """Flat equity → R² = 0 (no variance to explain)."""
        r2 = equity_r_squared(np.full(100, 100_000.0))
        assert r2 == 0.0

    def test_noisy_linear(self, noisy_equity: np.ndarray):
        """Noisy linear trend → 0 < R² < 1."""
        r2 = equity_r_squared(noisy_equity)
        assert 0.5 < r2 < 1.0

    def test_random_walk(self, rng: np.random.Generator):
        """Random walk (no trend) → R² near 0."""
        walk = np.cumsum(rng.normal(0, 1, 1000)) + 100_000
        r2 = equity_r_squared(walk)
        # Could be any value, but generally low for true random walk
        assert -0.5 < r2 < 0.8

    def test_short_series(self):
        """Less than 3 points → 0."""
        assert equity_r_squared([100, 200]) == 0.0
        assert equity_r_squared([]) == 0.0

    def test_decreasing_equity(self):
        """Steadily decreasing equity still has high R²."""
        equity = np.linspace(200_000, 50_000, 100)
        r2 = equity_r_squared(equity)
        assert abs(r2 - 1.0) < 1e-10  # perfect linear, just downward

    def test_parabolic_equity(self):
        """Parabolic curve has lower R² than linear."""
        x = np.arange(100, dtype=float)
        equity = 100_000 + x ** 2
        r2 = equity_r_squared(equity)
        # Parabola isn't perfectly linear
        assert 0.7 < r2 < 1.0


# ===========================================================================
# Relative Entropy — 7 tests
# ===========================================================================


class TestRelativeEntropy:
    """Relative Entropy — diversity of return distribution."""

    def test_uniform_returns(self):
        """Uniformly distributed returns → entropy near 1.0."""
        returns = np.linspace(-0.05, 0.05, 10_000)
        h = relative_entropy(returns, n_bins=20)
        assert 0.9 < h <= 1.0

    def test_concentrated_returns(self):
        """All same values → entropy 0 (one bin has all mass)."""
        returns = np.full(100, 0.01)
        h = relative_entropy(returns, n_bins=20)
        assert h < 0.15

    def test_bimodal_returns(self):
        """Two clusters → intermediate entropy."""
        returns = np.concatenate([np.full(500, -0.02), np.full(500, 0.02)])
        h = relative_entropy(returns, n_bins=20)
        assert 0.05 < h < 0.8

    def test_empty_returns(self):
        """Empty array → 0."""
        assert relative_entropy(np.array([])) == 0.0

    def test_single_return(self):
        """Single value → 0 (need ≥ 2)."""
        assert relative_entropy(np.array([0.01])) == 0.0

    def test_nan_handling(self):
        """NaN values are dropped."""
        returns = np.array([0.01, np.nan, 0.02, 0.03, np.nan, -0.01] * 100)
        h = relative_entropy(returns, n_bins=10)
        assert 0.0 < h <= 1.0

    def test_range_bounded(self, rng: np.random.Generator):
        """Entropy always in [0, 1]."""
        returns = rng.normal(0, 0.02, 1000)
        h = relative_entropy(returns)
        assert 0.0 <= h <= 1.0


# ===========================================================================
# Ulcer Performance Index — 7 tests
# ===========================================================================


class TestUlcerPerformanceIndex:
    """Ulcer Performance Index — risk-adjusted return via Ulcer Index."""

    def test_perfect_growth(self, trending_equity: np.ndarray):
        """Linear growth with no drawdown → UPI = inf."""
        upi = ulcer_performance_index(trending_equity)
        assert upi == float("inf") or upi > 100  # no drawdown

    def test_flat_equity(self):
        """Flat equity → UPI = 0 (no return)."""
        equity = np.full(252, 100_000.0)
        upi = ulcer_performance_index(equity)
        assert upi == 0.0

    def test_declining_equity(self):
        """Declining equity → UPI negative or zero."""
        equity = np.linspace(100_000, 50_000, 252)
        upi = ulcer_performance_index(equity)
        assert upi < 0

    def test_positive_upi_for_growth_with_dd(self, noisy_equity: np.ndarray):
        """Growing equity with noise → positive UPI."""
        upi = ulcer_performance_index(noisy_equity)
        assert upi > 0

    def test_short_equity(self):
        """Less than 3 points → 0."""
        assert ulcer_performance_index([100, 200]) == 0.0

    def test_zero_start(self):
        """Zero starting equity → 0 (avoid division by zero)."""
        assert ulcer_performance_index([0, 100, 200]) == 0.0

    def test_higher_upi_is_better(self, rng: np.random.Generator):
        """Strategy with less drawdown has higher UPI."""
        # Smooth growth
        equity_smooth = np.linspace(100_000, 150_000, 252) + rng.normal(0, 100, 252)
        # Volatile growth to same endpoint
        equity_volatile = np.linspace(100_000, 150_000, 252) + rng.normal(0, 5000, 252)
        upi_smooth = ulcer_performance_index(equity_smooth)
        upi_volatile = ulcer_performance_index(equity_volatile)
        assert upi_smooth > upi_volatile


# ===========================================================================
# Integration with TradeMetrics — 5 tests
# ===========================================================================


class TestIntegration:
    """New metrics integrate correctly with calculate_trade_metrics."""

    def _make_daily_balance(self, n: int = 252, start: float = 100_000, end: float = 130_000) -> list[float]:
        """Generate linear daily balance."""
        return list(np.linspace(start, end, n))

    def _make_trades(self) -> list[dict]:
        return [
            {"pnl": 5000, "direction": "long", "fee": 50, "holding_period": 10,
             "entry_price": 300, "high_prices": [310, 315, 308], "low_prices": [295, 298, 300]},
            {"pnl": -2000, "direction": "long", "fee": 50, "holding_period": 5,
             "entry_price": 250, "high_prices": [252, 248], "low_prices": [240, 245]},
            {"pnl": 3000, "direction": "short", "fee": 50, "holding_period": 7,
             "entry_price": 500, "high_prices": [505, 498], "low_prices": [490, 488]},
        ]

    def test_equity_r2_in_trade_metrics(self):
        """calculate_trade_metrics populates equity_r2."""
        trades = [{"pnl": 100, "direction": "long", "fee": 1, "holding_period": 1}]
        balance = self._make_daily_balance()
        m = calculate_trade_metrics(trades, balance, 100_000)
        assert m.equity_r2 > 0.9  # linear balance → high R²

    def test_entropy_in_trade_metrics(self):
        """calculate_trade_metrics populates return_entropy."""
        trades = [{"pnl": 100, "direction": "long", "fee": 1, "holding_period": 1}]
        balance = self._make_daily_balance()
        m = calculate_trade_metrics(trades, balance, 100_000)
        assert 0.0 <= m.return_entropy <= 1.0

    def test_upi_in_trade_metrics(self):
        """calculate_trade_metrics populates ulcer_perf_index."""
        trades = [{"pnl": 100, "direction": "long", "fee": 1, "holding_period": 1}]
        balance = self._make_daily_balance()
        m = calculate_trade_metrics(trades, balance, 100_000)
        assert m.ulcer_perf_index != 0.0

    def test_mae_mfe_in_trade_metrics(self):
        """calculate_trade_metrics populates MAE/MFE when data available."""
        trades = self._make_trades()
        balance = self._make_daily_balance()
        m = calculate_trade_metrics(trades, balance, 100_000)
        assert m.avg_mae > 0
        assert m.avg_mfe > 0
        assert m.mfe_mae_ratio > 0

    def test_format_includes_new_sections(self):
        """format_metrics includes Equity Quality and MAE/MFE sections."""
        trades = self._make_trades()
        balance = self._make_daily_balance()
        m = calculate_trade_metrics(trades, balance, 100_000)
        report = format_metrics(m)
        assert "EQUITY QUALITY" in report
        assert "Equity R²" in report
        assert "Return Entropy" in report
        assert "Ulcer Perf" in report
        assert "TRADE QUALITY" in report
        assert "MAE" in report
        assert "MFE" in report
