"""Tests for walk-forward ML pipeline orchestrator."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest

from src.ml.walk_forward import WalkForwardML, WalkForwardResult


def _make_data(n: int = 1000, seed: int = 42) -> pl.DataFrame:
    """Generate synthetic data with regime-switching trends."""
    np.random.seed(seed)
    timestamps = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(n)]

    close = np.zeros(n)
    close[0] = 250.0
    regime = 0
    for i in range(1, n):
        if np.random.random() < 0.02:
            regime = 1 - regime
        drift = 0.8 if regime == 0 else -0.8
        close[i] = close[i - 1] + drift + np.random.normal(0, 1.5)
    close = np.maximum(close, 10.0)

    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_ = (high + low) / 2
    volume = np.random.randint(5000, 100000, n)

    return pl.DataFrame({
        "timestamp": timestamps,
        "open": open_.tolist(),
        "high": high.tolist(),
        "low": low.tolist(),
        "close": close.tolist(),
        "volume": volume.tolist(),
    })


class TestWalkForwardML:
    @pytest.fixture(scope="class")
    def wf_result(self) -> WalkForwardResult:
        data = _make_data(1000, seed=42)
        wf = WalkForwardML(n_windows=3, train_ratio=0.7, gap_bars=1)
        return wf.run(data)

    def test_splits_data_correctly(self):
        wf = WalkForwardML(n_windows=5, train_ratio=0.7, gap_bars=1)
        splits = wf._create_splits(1000)
        assert len(splits) == 5

    def test_no_data_leakage(self):
        wf = WalkForwardML(n_windows=5, train_ratio=0.7, gap_bars=2)
        splits = wf._create_splits(1000)
        for train_start, train_end, test_start, test_end in splits:
            assert test_start > train_end, "Test must start after train + gap"
            assert test_start >= train_end + 2, "Gap of 2 bars required"

    def test_train_ratio(self):
        wf = WalkForwardML(n_windows=5, train_ratio=0.7, gap_bars=0)
        splits = wf._create_splits(1000)
        for train_start, train_end, test_start, test_end in splits:
            train_size = train_end - train_start
            total = test_end - train_start
            ratio = train_size / total
            assert abs(ratio - 0.7) < 0.05

    def test_returns_metrics(self, wf_result: WalkForwardResult):
        assert len(wf_result.window_metrics) > 0
        for wm in wf_result.window_metrics:
            assert wm.train_size > 0
            assert wm.test_size > 0

    def test_aggregate_metrics(self, wf_result: WalkForwardResult):
        assert isinstance(wf_result.aggregate_accuracy, float)
        assert isinstance(wf_result.aggregate_sharpe, float)

    def test_overfitting_detection(self, wf_result: WalkForwardResult):
        # overfitting_score = avg(train_sharpe) / avg(test_sharpe)
        # Can be any float: positive, negative, inf
        score = wf_result.overfitting_score
        assert isinstance(score, float)
        # Just verify it's computed (not NaN)
        import math
        assert not math.isnan(score)

    def test_short_data(self):
        data = _make_data(30)
        wf = WalkForwardML(n_windows=5, train_ratio=0.7)
        result = wf.run(data)
        # Should handle gracefully — may return empty result
        assert isinstance(result, WalkForwardResult)

    def test_predictions_length(self, wf_result: WalkForwardResult):
        total_oos = sum(wm.test_size for wm in wf_result.window_metrics)
        assert len(wf_result.oos_predictions) == total_oos

    def test_retrain_interval(self):
        wf = WalkForwardML(retrain_every=30)
        assert wf.retrain_every == 30

    def test_n_windows(self, wf_result: WalkForwardResult):
        assert wf_result.n_windows == 3

    def test_invalid_params(self):
        with pytest.raises(ValueError):
            WalkForwardML(n_windows=0)
        with pytest.raises(ValueError):
            WalkForwardML(train_ratio=1.5)
