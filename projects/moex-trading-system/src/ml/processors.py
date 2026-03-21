"""Cross-sectional and robust data processors for ML pipeline.

Inspired by Microsoft Qlib data/dataset/processor.py (MIT License).
Written from scratch. Critical for proper ML feature engineering.

Key insight: features should be normalized CROSS-SECTIONALLY (across
all stocks at same date), not HISTORICALLY (across time for one stock).
This prevents look-ahead bias in live trading.

Usage:
    from src.ml.processors import cs_rank_norm, robust_zscore, cs_zscore

    # Normalize features across all stocks for each date
    normalized = cs_rank_norm(features_df)
    robust = robust_zscore(features_df, clip=3.0)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def cs_rank_norm(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Cross-Sectional Rank Normalization.

    For each date, ranks all stocks by feature value, then maps
    rank percentile to pseudo-normal: (rank_pct - 0.5) * 3.46

    3.46 ≈ 2 * Φ⁻¹(0.9999) ensures 99.99% of values in [-1.73, 1.73].

    This eliminates outliers and makes features comparable across dates.
    Essential for ML models that assume similar feature distributions.

    Args:
        df: DataFrame with DatetimeIndex and stock features as columns,
            OR MultiIndex (date, stock) with feature columns.
        columns: Columns to normalize (None = all numeric).

    Returns:
        Normalized DataFrame (same shape).
    """
    result = df.copy()
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()

    if isinstance(df.index, pd.MultiIndex):
        # MultiIndex: group by first level (date)
        for col in cols:
            ranked = df.groupby(level=0)[col].rank(pct=True)
            result[col] = (ranked - 0.5) * 3.46
    else:
        # Each row is a date, each column is a stock
        for col in cols:
            result[col] = (df[col].rank(pct=True) - 0.5) * 3.46

    return result


def cs_zscore(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Cross-Sectional Z-Score Normalization.

    For each date, normalizes features across all stocks:
    z = (x - mean_across_stocks) / std_across_stocks

    Unlike historical zscore (which uses past data), this uses
    CURRENT cross-section — no look-ahead bias.

    Args:
        df: DataFrame. If MultiIndex (date, stock), groups by date.
        columns: Columns to normalize.

    Returns:
        Normalized DataFrame.
    """
    result = df.copy()
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()

    if isinstance(df.index, pd.MultiIndex):
        for col in cols:
            grouped = df.groupby(level=0)[col]
            mean = grouped.transform("mean")
            std = grouped.transform("std")
            std = std.replace(0, 1.0)
            result[col] = (df[col] - mean) / std
    else:
        for col in cols:
            mean = df[col].mean()
            std = df[col].std()
            if std == 0:
                std = 1.0
            result[col] = (df[col] - mean) / std

    return result


def robust_zscore(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    clip_value: float = 3.0,
) -> pd.DataFrame:
    """Robust Z-Score using MAD (Median Absolute Deviation).

    More robust to outliers than standard zscore:
    z = (x - median) / (MAD * 1.4826)

    1.4826 = 1/Φ⁻¹(0.75) — makes MAD equivalent to σ for normal data.
    Clipping to [-clip, +clip] prevents extreme values.

    Critical for MOEX: stocks hitting ±20% limit-up/down create
    extreme outliers that corrupt standard zscore.

    Args:
        df: DataFrame with numeric features.
        columns: Columns to normalize.
        clip_value: Clip bounds (default ±3.0).

    Returns:
        Normalized and clipped DataFrame.
    """
    result = df.copy()
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()

    for col in cols:
        median = df[col].median()
        mad = (df[col] - median).abs().median()
        scale = mad * 1.4826
        if scale < 1e-10:
            scale = 1.0
        z = (df[col] - median) / scale
        result[col] = z.clip(-clip_value, clip_value)

    return result


def cs_fillna(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "mean",
) -> pd.DataFrame:
    """Cross-Sectional NaN filling.

    Fills NaN with the cross-sectional statistic (mean/median) for each date.
    Better than ffill for panel data — uses current market info, not stale.

    Args:
        df: DataFrame with MultiIndex (date, stock).
        columns: Columns to fill.
        method: "mean" or "median".
    """
    result = df.copy()
    cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()

    if isinstance(df.index, pd.MultiIndex):
        for col in cols:
            if method == "median":
                fill = df.groupby(level=0)[col].transform("median")
            else:
                fill = df.groupby(level=0)[col].transform("mean")
            result[col] = df[col].fillna(fill)
    else:
        for col in cols:
            fill = df[col].median() if method == "median" else df[col].mean()
            result[col] = df[col].fillna(fill)

    return result


def rolling_slope(
    series: pd.Series | np.ndarray,
    window: int = 20,
) -> np.ndarray:
    """Rolling linear regression slope.

    Formula: β = (N·Σ(i·x_i) − Σi·Σx_i) / (N·Σi² − (Σi)²)

    Measures the trend strength and direction over a window.
    Positive = uptrend, negative = downtrend.

    Args:
        series: Price or feature series.
        window: Rolling window size.

    Returns:
        Array of slope values.
    """
    arr = np.asarray(series, dtype=np.float64)
    n = len(arr)
    result = np.zeros(n)

    indices = np.arange(window, dtype=np.float64)
    sum_i = indices.sum()
    sum_i2 = (indices ** 2).sum()
    denom = window * sum_i2 - sum_i ** 2

    if denom == 0:
        return result

    for t in range(window - 1, n):
        x = arr[t - window + 1:t + 1]
        sum_x = x.sum()
        sum_ix = (indices * x).sum()
        result[t] = (window * sum_ix - sum_i * sum_x) / denom

    return result


def rolling_rsquare(
    series: pd.Series | np.ndarray,
    window: int = 20,
) -> np.ndarray:
    """Rolling R² of linear regression on time index.

    R² near 1.0 = strong linear trend.
    R² near 0.0 = no linear trend (random walk or mean-reverting).

    Args:
        series: Price or feature series.
        window: Rolling window size.

    Returns:
        Array of R² values in [0, 1].
    """
    arr = np.asarray(series, dtype=np.float64)
    n = len(arr)
    result = np.zeros(n)

    indices = np.arange(window, dtype=np.float64)
    sum_i = indices.sum()
    sum_i2 = (indices ** 2).sum()
    denom = window * sum_i2 - sum_i ** 2

    if denom == 0:
        return result

    for t in range(window - 1, n):
        x = arr[t - window + 1:t + 1]
        mean_x = x.mean()
        ss_tot = ((x - mean_x) ** 2).sum()
        if ss_tot == 0:
            result[t] = 0.0
            continue
        sum_x = x.sum()
        sum_ix = (indices * x).sum()
        slope = (window * sum_ix - sum_i * sum_x) / denom
        intercept = (sum_x - slope * sum_i) / window
        fitted = intercept + slope * indices
        ss_res = ((x - fitted) ** 2).sum()
        result[t] = max(0.0, 1.0 - ss_res / ss_tot)

    return result
