"""End-to-end test: data → features → labels → train → predict → backtest.

Uses synthetic data to verify the complete ML pipeline works.
No external API calls. No network.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import polars as pl
import pytest

from src.analysis.features import calculate_all_features
from src.backtest.metrics import max_drawdown, sharpe_ratio
from src.ml.label_generators import generate_highlow_labels
from src.ml.predictor import predict
from src.ml.trainer import train_models


def _generate_ml_data(n: int = 1000, seed: int = 123) -> pl.DataFrame:
    """Generate synthetic OHLCV data for ML pipeline.

    Creates trending data with regime changes to give ML something to learn.
    """
    np.random.seed(seed)
    timestamps = [datetime(2020, 1, 1) + timedelta(days=i) for i in range(n)]

    # Create regime-switching data
    close = np.zeros(n)
    close[0] = 250.0
    regime = 0  # 0=up, 1=down
    for i in range(1, n):
        if np.random.random() < 0.01:  # 1% chance of regime switch
            regime = 1 - regime
        drift = 0.5 if regime == 0 else -0.5
        close[i] = close[i - 1] + drift + np.random.normal(0, 2.0)
    close = np.maximum(close, 10.0)

    high = close * (1 + np.abs(np.random.normal(0, 0.015, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.015, n)))
    open_ = close + np.random.normal(0, 0.5, n)
    open_ = np.clip(open_, low, high)
    volume = np.random.randint(10000, 500000, n)

    return pl.DataFrame({
        "timestamp": timestamps,
        "open": open_.tolist(),
        "high": high.tolist(),
        "low": low.tolist(),
        "close": close.tolist(),
        "volume": volume.tolist(),
    })


class TestMLPipeline:
    """E2E: synthetic data → features → labels → train → predict → metrics."""

    @pytest.fixture(scope="class")
    def ml_result(self):
        """Run the full ML pipeline once for all tests in this class."""
        # 1. Generate data
        data = _generate_ml_data(1000, seed=123)
        assert data.height == 1000

        # 2. Feature engineering
        enriched = calculate_all_features(data)
        assert enriched.width > data.width  # features added

        # 3. Label generation (simple: next bar direction)
        close = data["close"].to_numpy()
        labels = []
        for i in range(len(close) - 1):
            labels.append(1 if close[i + 1] > close[i] else 0)
        labels.append(0)  # last bar has no future

        # 4. Build feature matrix (drop NaN rows from indicators)
        feature_cols = [c for c in enriched.columns if c not in (
            "timestamp", "open", "high", "low", "close", "volume", "instrument",
        )]

        # Drop rows with NaN
        enriched_with_labels = enriched.with_columns(
            pl.Series("label", labels)
        )
        enriched_clean = enriched_with_labels.drop_nulls()

        if enriched_clean.height < 200:
            pytest.skip("Not enough clean data for ML pipeline")

        # Split train/test (70/30)
        split_idx = int(enriched_clean.height * 0.7)
        train_df = enriched_clean.slice(0, split_idx)
        test_df = enriched_clean.slice(split_idx)

        # Convert to list[dict] format expected by trainer
        X_train = train_df.select(feature_cols).to_dicts()
        y_train = train_df["label"].to_list()
        X_test = test_df.select(feature_cols).to_dicts()
        y_test = test_df["label"].to_list()

        # 5. Train models
        models = train_models(X_train, y_train)

        # 6. Predict
        predictions = predict(models, X_test)

        return {
            "data": data,
            "enriched": enriched,
            "models": models,
            "predictions": predictions,
            "y_test": y_test,
            "X_train_len": len(X_train),
            "X_test_len": len(X_test),
            "feature_cols": feature_cols,
        }

    def test_pipeline_no_crash(self, ml_result):
        """Pipeline runs end-to-end without errors."""
        assert ml_result["models"] is not None
        assert len(ml_result["predictions"]) > 0

    def test_features_generated(self, ml_result):
        """Feature engineering adds columns."""
        assert ml_result["enriched"].width > 6  # more than OHLCV

    def test_models_trained(self, ml_result):
        """All three models are trained."""
        models = ml_result["models"]
        assert isinstance(models, dict)
        assert len(models) > 0

    def test_predictions_length(self, ml_result):
        """Predictions match test set length."""
        assert len(ml_result["predictions"]) == ml_result["X_test_len"]

    def test_predictions_bounded(self, ml_result):
        """Predictions are probabilities in [0, 1]."""
        for p in ml_result["predictions"]:
            assert 0.0 <= p <= 1.0, f"Prediction {p} out of [0, 1]"

    def test_train_test_split_sizes(self, ml_result):
        """Train and test sets have reasonable sizes."""
        assert ml_result["X_train_len"] > 100
        assert ml_result["X_test_len"] > 50

    def test_feature_count(self, ml_result):
        """Multiple features generated."""
        assert len(ml_result["feature_cols"]) >= 5

    def test_predictions_not_constant(self, ml_result):
        """Predictions vary (model learned something)."""
        preds = ml_result["predictions"]
        assert len(set(round(p, 2) for p in preds)) > 1, "All predictions identical"

    def test_simple_backtest_from_predictions(self, ml_result):
        """Convert predictions to trades and compute basic metrics."""
        preds = ml_result["predictions"]
        y_test = ml_result["y_test"]

        # Simple PnL: go long when P(up) > 0.55, else flat
        returns = []
        for i in range(len(preds) - 1):
            if preds[i] > 0.55:
                ret = 0.01 if y_test[i] == 1 else -0.01  # simplified
                returns.append(ret)
            else:
                returns.append(0.0)

        returns_series = pd.Series(returns)
        sr = sharpe_ratio(returns_series)
        dd = max_drawdown(returns_series)
        # Just verify they compute without error
        assert not np.isnan(sr) or len(returns) < 5
        assert dd <= 1.0
