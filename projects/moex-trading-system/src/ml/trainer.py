"""ML model training for MOEX Trading System.

Trains LightGBM, XGBoost, and CatBoost classifiers for directional
prediction (up/down) using walk-forward methodology.

Public API:
    train_models(X_train, y_train) -> dict[str, Any]
        Train all three models and return fitted estimators.
"""
from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def train_models(
    X_train: list[dict[str, float]],
    y_train: list[int],
    lgbm_params: dict[str, Any] | None = None,
    xgb_params: dict[str, Any] | None = None,
    cat_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train LightGBM, XGBoost, and CatBoost on the same feature set.

    Parameters
    ----------
    X_train:
        List of feature dicts (one per sample).
    y_train:
        Binary target (1=up, 0=down).
    lgbm_params, xgb_params, cat_params:
        Optional hyperparameter overrides.

    Returns
    -------
    dict with keys: ``lgbm``, ``xgb``, ``catboost``, ``feature_names``.
    """
    try:
        import lightgbm as lgb
        import xgboost as xgb
        import catboost as cb
        import numpy as np
    except ImportError as e:
        logger.error("ML dependencies not installed: %s", e)
        return {}

    if len(X_train) < 50:
        logger.warning("Too few samples for training", n=len(X_train))
        return {}

    # Build numpy arrays
    feature_names = sorted(X_train[0].keys())
    X = np.array([[row.get(f, 0.0) for f in feature_names] for row in X_train])
    y = np.array(y_train)

    # Replace NaN/inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    models: dict[str, Any] = {"feature_names": feature_names}

    # --- LightGBM ---
    default_lgbm = {
        "objective": "binary",
        "metric": "binary_logloss",
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_samples": 20,
        "verbose": -1,
        "random_state": 42,
    }
    if lgbm_params:
        default_lgbm.update(lgbm_params)

    try:
        lgbm_model = lgb.LGBMClassifier(**default_lgbm)
        lgbm_model.fit(X, y)
        models["lgbm"] = lgbm_model
        logger.info("LightGBM trained", n_estimators=default_lgbm["n_estimators"])
    except Exception as e:
        logger.error("LightGBM training failed: %s", e)

    # --- XGBoost ---
    default_xgb = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
        "verbosity": 0,
        "random_state": 42,
    }
    if xgb_params:
        default_xgb.update(xgb_params)

    try:
        xgb_model = xgb.XGBClassifier(**default_xgb)
        xgb_model.fit(X, y)
        models["xgb"] = xgb_model
        logger.info("XGBoost trained", n_estimators=default_xgb["n_estimators"])
    except Exception as e:
        logger.error("XGBoost training failed: %s", e)

    # --- CatBoost ---
    default_cat = {
        "iterations": 200,
        "depth": 6,
        "learning_rate": 0.05,
        "loss_function": "Logloss",
        "verbose": 0,
        "random_seed": 42,
    }
    if cat_params:
        default_cat.update(cat_params)

    try:
        cat_model = cb.CatBoostClassifier(**default_cat)
        cat_model.fit(X, y)
        models["catboost"] = cat_model
        logger.info("CatBoost trained", iterations=default_cat["iterations"])
    except Exception as e:
        logger.error("CatBoost training failed: %s", e)

    return models
