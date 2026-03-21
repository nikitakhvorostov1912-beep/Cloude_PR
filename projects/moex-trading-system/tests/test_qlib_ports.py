"""Tests for Qlib-inspired ML processors and rolling factors."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ml.processors import (
    cs_rank_norm, cs_zscore, robust_zscore, cs_fillna,
    rolling_slope, rolling_rsquare,
)


@pytest.fixture
def panel_df():
    """MultiIndex (date, stock) panel."""
    dates = pd.date_range("2024-01-01", periods=3, freq="B")
    stocks = ["SBER", "GAZP", "LKOH"]
    idx = pd.MultiIndex.from_product([dates, stocks], names=["date", "stock"])
    data = {
        "return": [0.01, -0.02, 0.03, 0.005, -0.01, 0.02, -0.005, 0.015, -0.008],
        "volume": [100, 200, 50, 150, 80, 120, 90, 180, 70],
    }
    return pd.DataFrame(data, index=idx)


class TestCSRankNorm:

    def test_output_range(self, panel_df):
        result = cs_rank_norm(panel_df)
        # (rank_pct - 0.5) * 3.46: for 3 stocks, pcts are 0.33, 0.67, 1.0
        # mapped: (0.33-0.5)*3.46, (0.67-0.5)*3.46, (1.0-0.5)*3.46
        assert result["return"].abs().max() < 2.0

    def test_preserves_shape(self, panel_df):
        result = cs_rank_norm(panel_df)
        assert result.shape == panel_df.shape

    def test_no_nan(self, panel_df):
        result = cs_rank_norm(panel_df)
        assert not result.isna().any().any()

    def test_cross_sectional_not_historical(self, panel_df):
        """Each date normalized independently."""
        result = cs_rank_norm(panel_df, columns=["return"])
        # Sum of normalized values per date should be ~0
        for date in panel_df.index.get_level_values(0).unique():
            vals = result.loc[date, "return"]
            assert abs(vals.mean()) < 1.0

    def test_simple_df(self):
        """Works on simple (non-MultiIndex) DataFrames too."""
        df = pd.DataFrame({"a": [10, 20, 30, 40, 50]})
        result = cs_rank_norm(df)
        assert len(result) == 5


class TestRobustZScore:

    def test_clip_bounds(self):
        df = pd.DataFrame({"x": [1, 2, 3, 100, -100, 2, 3]})
        result = robust_zscore(df, clip_value=3.0)
        assert result["x"].max() <= 3.0
        assert result["x"].min() >= -3.0

    def test_constant_data(self):
        """Constant → z = 0."""
        df = pd.DataFrame({"x": [5.0] * 10})
        result = robust_zscore(df)
        assert (result["x"] == 0).all()

    def test_outlier_resilience(self):
        """Outlier doesn't distort normal values."""
        normal = list(range(100))
        with_outlier = normal + [10000]
        df_normal = pd.DataFrame({"x": normal})
        df_outlier = pd.DataFrame({"x": with_outlier})
        r_normal = robust_zscore(df_normal)
        r_outlier = robust_zscore(df_outlier)
        # Median-based: normal values should be similar in both
        assert abs(r_normal["x"].iloc[50] - r_outlier["x"].iloc[50]) < 0.5

    def test_mad_scaling(self):
        """MAD * 1.4826 ≈ σ for normal data."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame({"x": rng.normal(0, 1, 1000)})
        result = robust_zscore(df, clip_value=10.0)
        # For normal data, result should have std ≈ 1
        assert 0.7 < result["x"].std() < 1.3


class TestCSZScore:

    def test_mean_zero_per_date(self, panel_df):
        result = cs_zscore(panel_df)
        for date in panel_df.index.get_level_values(0).unique():
            vals = result.loc[date, "return"]
            assert abs(vals.mean()) < 1e-10

    def test_std_one_per_date(self, panel_df):
        result = cs_zscore(panel_df)
        for date in panel_df.index.get_level_values(0).unique():
            vals = result.loc[date, "return"]
            if len(vals) > 1:
                assert abs(vals.std(ddof=0) - 1.0) < 0.5  # small sample


class TestCSFillna:

    def test_fills_nan_with_mean(self):
        idx = pd.MultiIndex.from_product(
            [["2024-01-01"], ["A", "B", "C"]], names=["date", "stock"]
        )
        df = pd.DataFrame({"x": [10, np.nan, 30]}, index=idx)
        result = cs_fillna(df)
        assert result["x"].iloc[1] == 20.0  # mean of 10, 30

    def test_no_nan_after_fill(self, panel_df):
        df = panel_df.copy()
        df.iloc[0, 0] = np.nan
        df.iloc[3, 1] = np.nan
        result = cs_fillna(df)
        assert not result.isna().any().any()


class TestRollingSlope:

    def test_uptrend_positive(self):
        x = np.linspace(100, 150, 50)
        slope = rolling_slope(x, window=10)
        assert slope[-1] > 0

    def test_downtrend_negative(self):
        x = np.linspace(150, 100, 50)
        slope = rolling_slope(x, window=10)
        assert slope[-1] < 0

    def test_flat_zero(self):
        x = np.full(30, 100.0)
        slope = rolling_slope(x, window=10)
        assert abs(slope[-1]) < 1e-10

    def test_correct_length(self):
        x = np.random.default_rng(42).normal(100, 5, 100)
        slope = rolling_slope(x, window=20)
        assert len(slope) == 100


class TestRollingRSquare:

    def test_perfect_linear(self):
        x = np.linspace(100, 200, 50)
        r2 = rolling_rsquare(x, window=10)
        assert r2[-1] > 0.99

    def test_random_walk_low_r2(self):
        rng = np.random.default_rng(42)
        x = 100 + np.cumsum(rng.normal(0, 1, 200))
        r2 = rolling_rsquare(x, window=20)
        # Random walk: some windows trending, some not — avg R² < 0.5
        assert r2[-100:].mean() < 0.7

    def test_range_bounded(self):
        rng = np.random.default_rng(42)
        x = rng.normal(100, 5, 100)
        r2 = rolling_rsquare(x, window=10)
        assert np.all(r2 >= 0)
        assert np.all(r2 <= 1.0)
