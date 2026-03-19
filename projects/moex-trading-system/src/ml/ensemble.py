"""ML Ensemble orchestration — train, predict, score.

Combines trainer and predictor into a single high-level API.

Public API:
    MLEnsemble.train(candles, ta_features, macro, sentiment)
    MLEnsemble.predict(features) -> float (ml_score 0-100)
    MLEnsemble.feature_importance() -> dict[str, float]
"""
from __future__ import annotations

from typing import Any

import structlog

from src.ml.features import compute_target, prepare_features
from src.ml.predictor import predict_single
from src.ml.trainer import train_models

logger = structlog.get_logger(__name__)


class MLEnsemble:
    """High-level ML ensemble for directional prediction."""

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._is_trained: bool = False

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def train(
        self,
        candles: list[dict[str, Any]],
        ta_features: list[dict[str, Any]],
        macro: dict[str, float] | None = None,
        sentiment: float = 0.0,
        horizon: int = 1,
    ) -> bool:
        """Train the ensemble on historical data.

        Parameters
        ----------
        candles:
            OHLCV bars.
        ta_features:
            TA indicator values per bar.
        macro:
            Macro indicators.
        sentiment:
            Daily sentiment score.
        horizon:
            Prediction horizon in bars.

        Returns
        -------
        bool
            True if training succeeded.
        """
        if len(candles) < 100:
            logger.warning("Not enough data for ML training", n=len(candles))
            return False

        # Prepare features
        X = prepare_features(candles, ta_features, macro, sentiment)
        y = compute_target(candles, horizon=horizon)

        # Align lengths (ta_features may be shorter than candles)
        min_len = min(len(X), len(y))
        X = X[:min_len]
        y = y[:min_len]

        # Remove last `horizon` rows (unknown target)
        X = X[:-horizon]
        y = y[:-horizon]

        if len(X) < 50:
            logger.warning("Not enough aligned samples", n=len(X))
            return False

        # Train
        self._models = train_models(X, y)
        self._is_trained = bool(self._models.get("lgbm") or self._models.get("xgb"))

        if self._is_trained:
            logger.info("MLEnsemble trained", n_samples=len(X))

        return self._is_trained

    def predict_score(self, features: dict[str, float]) -> float:
        """Predict ml_score (0-100) for a single sample.

        Parameters
        ----------
        features:
            Feature dict from prepare_features().

        Returns
        -------
        float
            Score 0-100 where 100 = strong BUY signal, 0 = strong SELL.
            50 = neutral / not trained.
        """
        if not self._is_trained:
            return 50.0

        p_up = predict_single(self._models, features)
        return round(p_up * 100, 2)

    def feature_importance(self, top_n: int = 20) -> dict[str, float]:
        """Get top feature importances from LightGBM model.

        Returns
        -------
        dict[str, float]
            Feature name -> importance (normalized to sum=1).
        """
        model = self._models.get("lgbm")
        if model is None:
            return {}

        try:
            importances = model.feature_importances_
            names = self._models.get("feature_names", [])

            pairs = sorted(
                zip(names, importances),
                key=lambda x: x[1],
                reverse=True,
            )[:top_n]

            total = sum(v for _, v in pairs) or 1.0
            return {name: round(imp / total, 4) for name, imp in pairs}
        except Exception as e:
            logger.warning("feature_importance_error", error=str(e))
            return {}
