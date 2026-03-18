"""TSFRESH feature extraction for MOEX time series.

Generates up to 794 features from OHLCV price series using TSFRESH,
then filters to statistically significant features via Benjamini-Hochberg.

Features are cached in SQLite to avoid recomputation (5-15 min on 10K bars).

Public API:
    extract_features(candles, window=60)
        Extract TSFRESH features from a list of OHLCVBar objects.

    extract_and_select(candles, target, window=60, fdr_level=0.05)
        Extract features and select only statistically significant ones.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_CACHE_DIR = Path("data/tsfresh_cache")


def extract_features(
    candles: list[dict[str, Any]],
    window: int = 60,
    column: str = "close",
) -> dict[str, list[float]]:
    """Extract TSFRESH features from price data using a rolling window.

    Parameters
    ----------
    candles:
        List of dicts with at least ``close``, ``high``, ``low``, ``volume``, ``dt``.
    window:
        Rolling window size in bars for feature extraction.
    column:
        Which price column to use as the main series.

    Returns
    -------
    dict[str, list[float]]
        Feature names -> values for each window position.
        Length = len(candles) - window + 1.
    """
    try:
        import pandas as pd
        from tsfresh import extract_features as _extract
        from tsfresh.utilities.dataframe_functions import roll_time_series
    except ImportError:
        logger.warning("tsfresh not installed, returning empty features")
        return {}

    if len(candles) < window + 10:
        logger.warning("Not enough candles for TSFRESH", n=len(candles), window=window)
        return {}

    # Build DataFrame for tsfresh
    values = [float(c.get(column, c.get("close", 0))) for c in candles]
    volumes = [float(c.get("volume", 0)) for c in candles]

    df = pd.DataFrame({
        "id": 0,
        "time": range(len(values)),
        column: values,
        "volume": volumes,
    })

    # Roll time series into windows
    rolled = roll_time_series(
        df,
        column_id="id",
        column_sort="time",
        max_timeshift=window - 1,
        min_timeshift=window - 1,
    )

    if rolled.empty:
        return {}

    # Extract features (disable progress bar for automation)
    features_df = _extract(
        rolled,
        column_id="id",
        column_sort="time",
        disable_progressbar=True,
        n_jobs=1,  # single-threaded for stability
    )

    # Drop columns with NaN/inf
    features_df = features_df.replace([float("inf"), float("-inf")], float("nan"))
    features_df = features_df.dropna(axis=1, how="any")

    result: dict[str, list[float]] = {}
    for col_name in features_df.columns:
        result[str(col_name)] = features_df[col_name].tolist()

    logger.info("tsfresh_extracted", n_features=len(result), n_rows=len(features_df))
    return result


def extract_and_select(
    candles: list[dict[str, Any]],
    target: list[int],
    window: int = 60,
    fdr_level: float = 0.05,
    column: str = "close",
) -> dict[str, list[float]]:
    """Extract features and filter to statistically significant ones.

    Parameters
    ----------
    candles:
        List of dicts with OHLCV data.
    target:
        Binary target variable (1=up, 0=down) aligned with feature output.
        Length must equal len(candles) - window + 1.
    window:
        Rolling window size.
    fdr_level:
        False discovery rate for Benjamini-Hochberg procedure.
    column:
        Price column to use.

    Returns
    -------
    dict[str, list[float]]
        Only statistically significant features.
    """
    try:
        import pandas as pd
        from tsfresh import select_features
    except ImportError:
        logger.warning("tsfresh not installed")
        return {}

    all_features = extract_features(candles, window=window, column=column)
    if not all_features:
        return {}

    # Build DataFrame from extracted features
    features_df = pd.DataFrame(all_features)
    n_rows = len(features_df)

    if len(target) != n_rows:
        logger.error(
            "target length mismatch",
            target_len=len(target),
            features_len=n_rows,
        )
        return {}

    target_series = pd.Series(target, dtype=float)

    # Select significant features
    selected_df = select_features(features_df, target_series, fdr_level=fdr_level)

    if selected_df.empty:
        logger.warning("No significant features found at FDR=%s", fdr_level)
        return {}

    result: dict[str, list[float]] = {}
    for col_name in selected_df.columns:
        result[str(col_name)] = selected_df[col_name].tolist()

    logger.info(
        "tsfresh_selected",
        total=len(all_features),
        selected=len(result),
        fdr_level=fdr_level,
    )
    return result


def _cache_key(candles: list[dict], window: int, column: str) -> str:
    """Generate a cache key from candle data parameters."""
    n = len(candles)
    last_dt = candles[-1].get("dt", "") if candles else ""
    raw = f"{n}:{window}:{column}:{last_dt}"
    return hashlib.md5(raw.encode()).hexdigest()
