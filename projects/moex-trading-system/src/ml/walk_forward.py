"""Walk-forward ML pipeline orchestrator.

Cycle: train(window_N) → predict(window_N+1) → shift → retrain → ...
Connects trainer, predictor, processors, label_generators, and metrics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
import structlog

from src.analysis.features import calculate_all_features
from src.ml.predictor import predict
from src.ml.trainer import train_models

logger = structlog.get_logger(__name__)


@dataclass
class WindowMetrics:
    """Metrics for a single walk-forward window."""

    window_id: int
    train_size: int
    test_size: int
    train_accuracy: float = 0.0
    test_accuracy: float = 0.0
    train_sharpe: float = 0.0
    test_sharpe: float = 0.0
    predictions: list[float] = field(default_factory=list)
    actuals: list[int] = field(default_factory=list)


@dataclass
class WalkForwardResult:
    """Aggregated walk-forward results."""

    window_metrics: list[WindowMetrics] = field(default_factory=list)
    oos_predictions: list[float] = field(default_factory=list)
    oos_actuals: list[int] = field(default_factory=list)
    aggregate_sharpe: float = 0.0
    aggregate_accuracy: float = 0.0
    overfitting_score: float = 0.0
    n_windows: int = 0


class WalkForwardML:
    """Walk-forward ML pipeline.

    Args:
        n_windows: Number of rolling windows.
        train_ratio: Fraction of each window used for training.
        gap_bars: Gap between train and test to prevent leakage.
        retrain_every: Retrain model every N bars in test window.
        label_fn: Function to generate labels from close prices.
    """

    def __init__(
        self,
        n_windows: int = 5,
        train_ratio: float = 0.70,
        gap_bars: int = 1,
        retrain_every: int = 60,
        label_fn: Any = None,
    ):
        if n_windows < 1:
            raise ValueError("n_windows must be >= 1")
        if not 0 < train_ratio < 1:
            raise ValueError("train_ratio must be between 0 and 1")

        self.n_windows = n_windows
        self.train_ratio = train_ratio
        self.gap_bars = gap_bars
        self.retrain_every = retrain_every
        self.label_fn = label_fn or self._default_labels

    def run(self, data: pl.DataFrame) -> WalkForwardResult:
        """Run walk-forward ML pipeline.

        Args:
            data: Raw OHLCV DataFrame.

        Returns:
            WalkForwardResult with per-window and aggregate metrics.
        """
        # Feature engineering
        enriched = calculate_all_features(data)
        close = data["close"].to_numpy()

        # Generate labels
        labels = self.label_fn(close)

        # Add labels
        enriched = enriched.with_columns(pl.Series("_label", labels))

        # Get feature columns
        feature_cols = [
            c for c in enriched.columns
            if c not in ("timestamp", "open", "high", "low", "close", "volume", "instrument", "_label")
        ]

        # Drop nulls
        clean = enriched.drop_nulls()
        if clean.height < 100:
            logger.warning("Too few clean rows for walk-forward", rows=clean.height)
            return WalkForwardResult()

        # Split into windows
        splits = self._create_splits(clean.height)

        result = WalkForwardResult(n_windows=len(splits))
        all_train_sharpes: list[float] = []
        all_test_sharpes: list[float] = []

        for win_id, (train_start, train_end, test_start, test_end) in enumerate(splits):
            train_df = clean.slice(train_start, train_end - train_start)
            test_df = clean.slice(test_start, test_end - test_start)

            if train_df.height < 50 or test_df.height < 10:
                logger.debug("Window too small, skipping", window=win_id)
                continue

            # Extract features and labels
            X_train = train_df.select(feature_cols).to_dicts()
            y_train = train_df["_label"].to_list()
            X_test = test_df.select(feature_cols).to_dicts()
            y_test = test_df["_label"].to_list()

            # Train
            models = train_models(X_train, y_train)
            if not models:
                logger.warning("Training failed", window=win_id)
                continue

            # Predict
            train_preds = predict(models, X_train)
            test_preds = predict(models, X_test)

            # Compute accuracies
            train_acc = self._accuracy(train_preds, y_train)
            test_acc = self._accuracy(test_preds, y_test)

            # Compute Sharpe-like metric from predictions
            train_sharpe = self._prediction_sharpe(train_preds, y_train)
            test_sharpe = self._prediction_sharpe(test_preds, y_test)

            wm = WindowMetrics(
                window_id=win_id,
                train_size=train_df.height,
                test_size=test_df.height,
                train_accuracy=train_acc,
                test_accuracy=test_acc,
                train_sharpe=train_sharpe,
                test_sharpe=test_sharpe,
                predictions=test_preds,
                actuals=y_test,
            )
            result.window_metrics.append(wm)
            result.oos_predictions.extend(test_preds)
            result.oos_actuals.extend(y_test)
            all_train_sharpes.append(train_sharpe)
            all_test_sharpes.append(test_sharpe)

            logger.info(
                "Window complete",
                window=win_id,
                train_acc=f"{train_acc:.3f}",
                test_acc=f"{test_acc:.3f}",
                train_sharpe=f"{train_sharpe:.3f}",
                test_sharpe=f"{test_sharpe:.3f}",
            )

        # Aggregate metrics
        if result.oos_predictions:
            result.aggregate_accuracy = self._accuracy(
                result.oos_predictions, result.oos_actuals
            )

        if all_test_sharpes:
            result.aggregate_sharpe = float(np.mean(all_test_sharpes))

        if all_train_sharpes and all_test_sharpes:
            avg_train = float(np.mean(all_train_sharpes))
            avg_test = float(np.mean(all_test_sharpes))
            if avg_test != 0:
                result.overfitting_score = avg_train / avg_test
            else:
                result.overfitting_score = float("inf") if avg_train > 0 else 0.0

        return result

    def _create_splits(
        self, total_rows: int
    ) -> list[tuple[int, int, int, int]]:
        """Create train/test split indices for each window.

        Returns list of (train_start, train_end, test_start, test_end).
        """
        window_size = total_rows // self.n_windows
        splits: list[tuple[int, int, int, int]] = []

        for i in range(self.n_windows):
            win_start = i * window_size
            win_end = min((i + 1) * window_size, total_rows)
            actual_size = win_end - win_start

            train_size = int(actual_size * self.train_ratio)
            train_start = win_start
            train_end = win_start + train_size
            test_start = train_end + self.gap_bars
            test_end = win_end

            if test_start >= test_end:
                continue

            splits.append((train_start, train_end, test_start, test_end))

        return splits

    @staticmethod
    def _default_labels(close: np.ndarray) -> list[int]:
        """Generate simple next-bar direction labels."""
        labels = []
        for i in range(len(close) - 1):
            labels.append(1 if close[i + 1] > close[i] else 0)
        labels.append(0)
        return labels

    @staticmethod
    def _accuracy(predictions: list[float], actuals: list[int]) -> float:
        """Compute directional accuracy."""
        if not predictions or not actuals:
            return 0.0
        correct = sum(
            1 for p, a in zip(predictions, actuals)
            if (p > 0.5 and a == 1) or (p <= 0.5 and a == 0)
        )
        return correct / len(actuals)

    @staticmethod
    def _prediction_sharpe(
        predictions: list[float], actuals: list[int]
    ) -> float:
        """Compute Sharpe-like metric from prediction returns."""
        if not predictions or not actuals:
            return 0.0
        returns = []
        for p, a in zip(predictions, actuals):
            direction = 1.0 if p > 0.5 else -1.0
            actual_return = 0.01 if a == 1 else -0.01
            returns.append(direction * actual_return)

        arr = np.array(returns)
        if arr.std() == 0:
            return 0.0
        return float(arr.mean() / arr.std() * np.sqrt(252))
