"""ML prediction — generate probabilities from trained models.

Public API:
    predict(models, X) -> list[float]
        Returns P(up) for each sample using weighted ensemble.
"""
from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Ensemble weights (sum to 1.0)
ENSEMBLE_WEIGHTS: dict[str, float] = {
    "lgbm": 0.40,
    "xgb": 0.30,
    "catboost": 0.30,
}


def predict(
    models: dict[str, Any],
    X: list[dict[str, float]],
    weights: dict[str, float] | None = None,
) -> list[float]:
    """Generate ensemble P(up) predictions.

    Parameters
    ----------
    models:
        Dict with ``lgbm``, ``xgb``, ``catboost`` fitted models
        and ``feature_names`` list.
    X:
        Feature dicts for prediction.
    weights:
        Optional custom weights. Defaults to ENSEMBLE_WEIGHTS.

    Returns
    -------
    list[float]
        P(up) for each sample, range [0.0, 1.0].
    """
    try:
        import numpy as np
    except ImportError:
        return [0.5] * len(X)

    if not models or "feature_names" not in models:
        return [0.5] * len(X)

    weights = weights or ENSEMBLE_WEIGHTS
    feature_names = models["feature_names"]

    # Build numpy array
    X_arr = np.array([[row.get(f, 0.0) for f in feature_names] for row in X])
    X_arr = np.nan_to_num(X_arr, nan=0.0, posinf=0.0, neginf=0.0)

    n = len(X)
    ensemble_proba = np.zeros(n)
    total_weight = 0.0

    for model_name, weight in weights.items():
        model = models.get(model_name)
        if model is None:
            continue

        try:
            proba = model.predict_proba(X_arr)[:, 1]  # P(class=1) = P(up)
            ensemble_proba += proba * weight
            total_weight += weight
        except Exception as e:
            logger.warning("predict_failed", model=model_name, error=str(e))

    if total_weight > 0:
        ensemble_proba /= total_weight

    return ensemble_proba.tolist()


def predict_single(
    models: dict[str, Any],
    features: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Predict P(up) for a single sample.

    Returns
    -------
    float
        P(up) in [0.0, 1.0]. Returns 0.5 on error.
    """
    result = predict(models, [features], weights)
    return result[0] if result else 0.5
