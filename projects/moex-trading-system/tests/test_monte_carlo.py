"""Tests for src/backtest/monte_carlo.py — Monte Carlo robustness simulation."""
from __future__ import annotations

import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.monte_carlo import (
    MonteCarloResult,
    format_monte_carlo,
    monte_carlo_returns_noise,
    monte_carlo_trades,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_trades() -> list[dict]:
    """20 trades with mixed PnL."""
    rng = np.random.RandomState(42)
    return [
        {"pnl": float(rng.normal(500, 2000)), "direction": "long", "fee": 50}
        for _ in range(20)
    ]


@pytest.fixture
def sample_balance() -> list[float]:
    """Daily balance over ~1 year with realistic noise."""
    rng = np.random.RandomState(42)
    balance = [1_000_000.0]
    for _ in range(251):
        daily_return = rng.normal(0.0003, 0.015)
        balance.append(balance[-1] * (1 + daily_return))
    return balance


# ---------------------------------------------------------------------------
# Trade shuffle tests
# ---------------------------------------------------------------------------


class TestMonteCarloTrades:
    def test_basic_run(self, sample_trades):
        result = monte_carlo_trades(
            trades=sample_trades,
            starting_balance=1_000_000,
            n_scenarios=50,
            max_workers=1,
        )
        assert isinstance(result, MonteCarloResult)
        assert result.mode == "trade_shuffle"
        assert result.n_scenarios == 50
        assert "total_return" in result.analysis
        assert "max_drawdown" in result.analysis
        assert "sharpe_ratio" in result.analysis

    def test_reproducible_with_seed(self, sample_trades):
        r1 = monte_carlo_trades(sample_trades, 1_000_000, n_scenarios=20, seed=123, max_workers=1)
        r2 = monte_carlo_trades(sample_trades, 1_000_000, n_scenarios=20, seed=123, max_workers=1)
        # Same seed → same scenario metrics
        assert len(r1.scenario_metrics) == len(r2.scenario_metrics)
        for m1, m2 in zip(r1.scenario_metrics, r2.scenario_metrics):
            assert abs(m1["total_return"] - m2["total_return"]) < 1e-10

    def test_different_seed_gives_different_paths(self, sample_trades):
        r1 = monte_carlo_trades(sample_trades, 1_000_000, n_scenarios=20, seed=1, max_workers=1)
        r2 = monte_carlo_trades(sample_trades, 1_000_000, n_scenarios=20, seed=999, max_workers=1)
        # Total return is invariant (sum of PnLs doesn't change with shuffle)
        # But max drawdown depends on ORDER → should differ between seeds
        dd1 = [m["max_drawdown"] for m in r1.scenario_metrics]
        dd2 = [m["max_drawdown"] for m in r2.scenario_metrics]
        assert dd1 != dd2

    def test_original_metrics_present(self, sample_trades):
        result = monte_carlo_trades(sample_trades, 1_000_000, n_scenarios=10, max_workers=1)
        assert "total_return" in result.original_metrics
        assert "max_drawdown" in result.original_metrics
        assert "sharpe_ratio" in result.original_metrics

    def test_percentiles_ordered(self, sample_trades):
        result = monte_carlo_trades(sample_trades, 1_000_000, n_scenarios=100, max_workers=1)
        for name, a in result.analysis.items():
            assert a.percentile_5 <= a.median <= a.percentile_95, f"{name} percentiles out of order"

    def test_confidence_intervals(self, sample_trades):
        result = monte_carlo_trades(sample_trades, 1_000_000, n_scenarios=100, max_workers=1)
        for name, a in result.analysis.items():
            assert a.ci_95.lower <= a.ci_95.upper
            assert a.ci_90.lower <= a.ci_90.upper
            # 95% CI should be wider than 90%
            assert a.ci_95.upper - a.ci_95.lower >= a.ci_90.upper - a.ci_90.lower - 1e-10

    def test_empty_trades_raises(self):
        with pytest.raises(ValueError, match="No trades"):
            monte_carlo_trades([], 1_000_000, n_scenarios=10)

    def test_all_winning_trades(self):
        trades = [{"pnl": 1000} for _ in range(10)]
        result = monte_carlo_trades(trades, 100_000, n_scenarios=20, max_workers=1)
        # All scenarios should have same total return (shuffling winners = same result)
        returns = [m["total_return"] for m in result.scenario_metrics]
        assert all(abs(r - returns[0]) < 1e-10 for r in returns)


# ---------------------------------------------------------------------------
# Returns noise tests
# ---------------------------------------------------------------------------


class TestMonteCarloReturnsNoise:
    def test_basic_run(self, sample_balance):
        result = monte_carlo_returns_noise(
            daily_balance=sample_balance,
            noise_std=0.002,
            n_scenarios=50,
            max_workers=1,
        )
        assert isinstance(result, MonteCarloResult)
        assert result.mode == "returns_noise"
        assert result.n_scenarios == 50
        assert "total_return" in result.analysis

    def test_higher_noise_more_variance(self, sample_balance):
        r_low = monte_carlo_returns_noise(sample_balance, noise_std=0.001, n_scenarios=100, max_workers=1)
        r_high = monte_carlo_returns_noise(sample_balance, noise_std=0.01, n_scenarios=100, max_workers=1)
        # Higher noise → more variance in total returns
        std_low = r_low.analysis["total_return"].std
        std_high = r_high.analysis["total_return"].std
        assert std_high > std_low

    def test_short_balance_raises(self):
        with pytest.raises(ValueError, match="at least 3"):
            monte_carlo_returns_noise([100_000, 101_000], noise_std=0.01)

    def test_p_values_between_0_and_1(self, sample_balance):
        result = monte_carlo_returns_noise(sample_balance, n_scenarios=50, max_workers=1)
        for name, a in result.analysis.items():
            assert 0.0 <= a.p_value <= 1.0, f"{name} p_value out of range"


# ---------------------------------------------------------------------------
# Formatting tests
# ---------------------------------------------------------------------------


class TestFormatMonteCarlo:
    def test_format_trade_shuffle(self, sample_trades):
        result = monte_carlo_trades(sample_trades, 1_000_000, n_scenarios=20, max_workers=1)
        report = format_monte_carlo(result)
        assert "TRADE SHUFFLE" in report
        assert "Scenarios: 20" in report
        assert "Total Return" in report
        assert "Sharpe" in report
        assert "p-value" in report

    def test_format_noise(self, sample_balance):
        result = monte_carlo_returns_noise(sample_balance, n_scenarios=20, max_workers=1)
        report = format_monte_carlo(result)
        assert "RETURNS NOISE" in report
