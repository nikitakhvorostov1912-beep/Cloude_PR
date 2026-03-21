"""Tests for src/indicators/utils.py — strategy utility functions."""
from __future__ import annotations

import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.indicators.utils import (
    barssince,
    cross,
    crossover,
    crossunder,
    highest,
    lowest,
    quantile_rank,
)


class TestCrossover:
    def test_golden_cross(self):
        fast = [9, 10, 11, 12]  # was below, now above
        slow = [10, 10, 10, 10]
        # At bar -2: fast=11 > slow=10, bar -3: fast=10 == slow=10
        # Actually: bar[-2]=11, bar[-1]=12, slow[-2]=10, slow[-1]=10
        assert crossover([8, 9, 11], [10, 10, 10])

    def test_no_cross(self):
        assert not crossover([5, 6, 7], [10, 10, 10])

    def test_scalar_threshold(self):
        assert crossover([49, 51], 50)

    def test_short_series(self):
        assert not crossover([10], [5])

    def test_equal_no_cross(self):
        assert not crossover([10, 10], [10, 10])


class TestCrossunder:
    def test_death_cross(self):
        assert crossunder([11, 9], [10, 10])

    def test_no_crossunder(self):
        assert not crossunder([5, 6], [10, 10])


class TestCross:
    def test_either_direction(self):
        assert cross([9, 11], [10, 10])   # above
        assert cross([11, 9], [10, 10])   # below
        assert not cross([5, 6], [10, 10])  # neither


class TestBarsSince:
    def test_recent_true(self):
        cond = [False, True, False, False]
        assert barssince(cond) == 2  # 2 bars ago

    def test_last_bar_true(self):
        cond = [False, False, True]
        assert barssince(cond) == 0

    def test_never_true(self):
        cond = [False, False, False]
        assert barssince(cond) == -1

    def test_custom_default(self):
        cond = [False]
        assert barssince(cond, default=999) == 999


class TestQuantileRank:
    def test_highest_value(self):
        series = [1, 2, 3, 4, 100]
        rank = quantile_rank(series)
        assert rank == 1.0  # 100 is above all prior values

    def test_lowest_value(self):
        series = [10, 20, 30, 1]
        rank = quantile_rank(series)
        assert rank == 0.0

    def test_median_value(self):
        series = list(range(1, 11)) + [5]  # [1..10, 5]
        rank = quantile_rank(series)
        # 5 is below 5 values (6,7,8,9,10) and above 4 (1,2,3,4)
        assert 0.3 < rank < 0.5

    def test_lookback(self):
        series = [100, 1, 2, 3, 50]
        rank = quantile_rank(series, lookback=3)
        # Last 3: [2, 3, 50], last=50, prior=[2,3] → 100% above
        assert rank == 1.0

    def test_short_series(self):
        assert quantile_rank([5]) == 0.5


class TestHighestLowest:
    def test_highest(self):
        assert highest([10, 20, 15, 5, 25], 3) == 25

    def test_lowest(self):
        assert lowest([10, 20, 15, 5, 25], 3) == 5

    def test_period_larger_than_data(self):
        assert highest([10, 20], 5) == 20
        assert lowest([10, 20], 5) == 10

    def test_with_nan(self):
        assert highest([10, np.nan, 20], 3) == 20
        assert lowest([10, np.nan, 20], 3) == 10
