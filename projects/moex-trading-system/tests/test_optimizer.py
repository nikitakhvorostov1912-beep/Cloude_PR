"""Tests for src/backtest/optimizer.py — Optuna strategy optimizer."""
from __future__ import annotations

import math
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.optimizer import (
    HyperParam,
    OptimizerConfig,
    StrategyOptimizer,
    TrialResult,
    WalkForwardWindow,
    calculate_fitness,
    walk_forward_optimize,
)


# ---------------------------------------------------------------------------
# Fitness scoring tests
# ---------------------------------------------------------------------------


class TestCalculateFitness:
    def test_good_metrics(self):
        metrics = {"sharpe_ratio": 2.0, "total_trades": 50}
        score = calculate_fitness(metrics, objective="sharpe", optimal_total=100)
        assert 0 < score < 1

    def test_too_few_trades(self):
        metrics = {"sharpe_ratio": 3.0, "total_trades": 2}
        score = calculate_fitness(metrics, objective="sharpe", min_trades=5)
        assert score == 0.0001

    def test_negative_ratio(self):
        metrics = {"sharpe_ratio": -1.0, "total_trades": 50}
        assert calculate_fitness(metrics, objective="sharpe") == 0.0001

    def test_nan_ratio(self):
        metrics = {"sharpe_ratio": float("nan"), "total_trades": 50}
        assert calculate_fitness(metrics, objective="sharpe") == 0.0001

    def test_higher_trades_higher_score(self):
        """More trades (up to optimal) → higher total_effect_rate → higher score."""
        base = {"sharpe_ratio": 2.0}
        s10 = calculate_fitness({**base, "total_trades": 10}, optimal_total=100)
        s50 = calculate_fitness({**base, "total_trades": 50}, optimal_total=100)
        s100 = calculate_fitness({**base, "total_trades": 100}, optimal_total=100)
        assert s10 < s50 < s100

    def test_higher_ratio_higher_score(self):
        base = {"total_trades": 50}
        s1 = calculate_fitness({**base, "sharpe_ratio": 1.0})
        s3 = calculate_fitness({**base, "sharpe_ratio": 3.0})
        assert s1 < s3

    def test_all_objectives(self):
        metrics = {
            "sharpe_ratio": 1.5,
            "calmar_ratio": 5.0,
            "sortino_ratio": 3.0,
            "omega_ratio": 1.5,
            "serenity_index": 2.0,
            "smart_sharpe": 1.2,
            "smart_sortino": 2.5,
            "total_trades": 50,
        }
        for obj in ["sharpe", "calmar", "sortino", "omega", "serenity", "smart_sharpe", "smart_sortino"]:
            score = calculate_fitness(metrics, objective=obj)
            assert score > 0, f"Objective {obj} should produce positive score"

    def test_unknown_objective_raises(self):
        with pytest.raises(ValueError, match="Unknown objective"):
            calculate_fitness({"total_trades": 50}, objective="unknown")

    def test_score_capped_at_1(self):
        """Even with extreme values, score should not exceed 1."""
        metrics = {"sharpe_ratio": 100.0, "total_trades": 10000}
        score = calculate_fitness(metrics, optimal_total=100)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# Optimizer tests (with mock backtest)
# ---------------------------------------------------------------------------


def _mock_backtest_fn(hp: dict) -> dict:
    """Simple mock: higher rsi_period → better Sharpe (predictable for testing)."""
    period = hp.get("rsi_period", 14)
    sharpe = 0.5 + (period - 5) * 0.05  # 5→0.5, 50→2.75
    return {
        "sharpe_ratio": max(sharpe, -1),
        "total_trades": 30 + period,
        "net_profit_pct": sharpe * 10,
        "win_rate": 0.55,
    }


class TestStrategyOptimizer:
    def test_basic_optimization(self):
        config = OptimizerConfig(
            hyperparameters=[
                HyperParam(name="rsi_period", type="int", min=5, max=50, step=5),
            ],
            objective="sharpe",
            n_trials=20,
            optimal_total=80,
        )
        optimizer = StrategyOptimizer(config=config, train_backtest_fn=_mock_backtest_fn)
        results = optimizer.run()

        assert len(results) > 0
        best = results[0]
        assert best.fitness > 0
        assert "rsi_period" in best.params
        # Higher rsi_period should be preferred (higher Sharpe in our mock)
        assert best.params["rsi_period"] >= 20

    def test_with_test_backtest(self):
        config = OptimizerConfig(
            hyperparameters=[
                HyperParam(name="rsi_period", type="int", min=10, max=30),
            ],
            objective="sharpe",
            n_trials=10,
        )
        optimizer = StrategyOptimizer(
            config=config,
            train_backtest_fn=_mock_backtest_fn,
            test_backtest_fn=_mock_backtest_fn,  # same for test (simplified)
        )
        results = optimizer.run()

        assert len(results) > 0
        best = results[0]
        assert best.testing_metrics is not None
        assert "sharpe_ratio" in best.testing_metrics

    def test_best_params_property(self):
        config = OptimizerConfig(
            hyperparameters=[HyperParam(name="x", type="int", min=1, max=10)],
            n_trials=5,
        )
        optimizer = StrategyOptimizer(config=config, train_backtest_fn=_mock_backtest_fn)
        optimizer.run()
        assert "x" in optimizer.best_params
        assert optimizer.best_fitness > 0

    def test_float_and_categorical_params(self):
        config = OptimizerConfig(
            hyperparameters=[
                HyperParam(name="threshold", type="float", min=0.1, max=0.9, step=0.1),
                HyperParam(name="mode", type="categorical", options=["fast", "slow"]),
            ],
            n_trials=10,
        )

        def bt(hp):
            val = hp["threshold"] * (2 if hp["mode"] == "fast" else 1)
            return {"sharpe_ratio": val, "total_trades": 50}

        optimizer = StrategyOptimizer(config=config, train_backtest_fn=bt)
        results = optimizer.run()
        assert len(results) > 0

    def test_failing_backtest_handled(self):
        """Optimizer should handle backtest exceptions gracefully."""
        call_count = 0

        def failing_bt(hp):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise RuntimeError("Backtest crashed")
            return {"sharpe_ratio": 1.5, "total_trades": 30}

        config = OptimizerConfig(
            hyperparameters=[HyperParam(name="x", type="int", min=1, max=10)],
            n_trials=9,
        )
        optimizer = StrategyOptimizer(config=config, train_backtest_fn=failing_bt)
        results = optimizer.run()  # should not raise
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Walk-forward tests
# ---------------------------------------------------------------------------


class TestWalkForward:
    def test_basic_walk_forward(self):
        windows = [
            ("2023-01-01", "2023-06-30", "2023-07-01", "2023-09-30"),
            ("2023-04-01", "2023-09-30", "2023-10-01", "2023-12-31"),
        ]

        def bt_factory(start, end, hp):
            period = hp.get("rsi_period", 14)
            return {"sharpe_ratio": 1.0 + period * 0.02, "total_trades": 25}

        results = walk_forward_optimize(
            hyperparameters=[HyperParam(name="rsi_period", type="int", min=5, max=30)],
            windows=windows,
            backtest_factory=bt_factory,
            n_trials_per_window=10,
            optimal_total=30,
        )

        assert len(results) == 2
        for w in results:
            assert isinstance(w, WalkForwardWindow)
            assert w.train_fitness > 0
            assert "rsi_period" in w.best_params
