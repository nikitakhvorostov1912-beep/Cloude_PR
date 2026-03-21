"""Tests for src/backtest/metrics.py — comprehensive performance metrics."""
from __future__ import annotations

import math
import sys
import os

import numpy as np
import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtest.metrics import (
    TradeMetrics,
    autocorr_penalty,
    cagr,
    calculate_trade_metrics,
    calmar_ratio,
    conditional_value_at_risk,
    format_metrics,
    max_drawdown,
    max_underwater_period,
    omega_ratio,
    serenity_index,
    sharpe_ratio,
    sortino_ratio,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def flat_returns() -> pd.Series:
    """Returns that are always zero — no movement."""
    idx = pd.date_range("2024-01-02", periods=100, freq="B")
    return pd.Series(0.0, index=idx)


@pytest.fixture
def positive_returns() -> pd.Series:
    """Steady 0.1% daily gain."""
    idx = pd.date_range("2024-01-02", periods=252, freq="B")
    return pd.Series(0.001, index=idx)


@pytest.fixture
def mixed_returns() -> pd.Series:
    """Alternating +1% / -0.5% returns."""
    idx = pd.date_range("2024-01-02", periods=100, freq="B")
    vals = [0.01 if i % 2 == 0 else -0.005 for i in range(100)]
    return pd.Series(vals, index=idx)


@pytest.fixture
def sample_trades() -> list[dict]:
    """10 trades with known PnL distribution."""
    return [
        {"pnl": 5000, "direction": "long", "fee": 50, "holding_period": 3},
        {"pnl": -2000, "direction": "long", "fee": 50, "holding_period": 2},
        {"pnl": 3000, "direction": "short", "fee": 50, "holding_period": 5},
        {"pnl": -1000, "direction": "long", "fee": 50, "holding_period": 1},
        {"pnl": 8000, "direction": "short", "fee": 50, "holding_period": 7},
        {"pnl": -3000, "direction": "long", "fee": 50, "holding_period": 2},
        {"pnl": 4000, "direction": "long", "fee": 50, "holding_period": 4},
        {"pnl": 2000, "direction": "short", "fee": 50, "holding_period": 3},
        {"pnl": -500, "direction": "long", "fee": 50, "holding_period": 1},
        {"pnl": 6000, "direction": "long", "fee": 50, "holding_period": 6},
    ]


@pytest.fixture
def sample_daily_balance() -> list[float]:
    """Growing balance with a drawdown in the middle."""
    np.random.seed(42)
    balance = [1_000_000.0]
    for _ in range(251):
        change = np.random.normal(500, 3000)
        balance.append(max(balance[-1] + change, 100_000))
    return balance


# ---------------------------------------------------------------------------
# Return-level metric tests
# ---------------------------------------------------------------------------


class TestSharpeRatio:
    def test_zero_returns(self, flat_returns):
        assert sharpe_ratio(flat_returns) == 0.0

    def test_positive_returns(self, positive_returns):
        sr = sharpe_ratio(positive_returns, periods=252)
        # Constant 0.1% daily → std ≈ 0 but not exactly 0 due to float precision
        # Sharpe is extremely high (effectively infinite) for constant positive returns
        assert sr > 0

    def test_mixed_returns_positive(self, mixed_returns):
        sr = sharpe_ratio(mixed_returns, periods=252)
        assert sr > 0  # net positive returns

    def test_smart_sharpe_lower_than_regular(self, mixed_returns):
        regular = sharpe_ratio(mixed_returns, periods=252, smart=False)
        smart = sharpe_ratio(mixed_returns, periods=252, smart=True)
        # Smart Sharpe should be <= regular (autocorr penalty >= 1)
        assert smart <= regular + 1e-10

    def test_accepts_dataframe(self, mixed_returns):
        df = mixed_returns.to_frame("ret")
        sr = sharpe_ratio(df, periods=252)
        assert isinstance(sr, float)


class TestSortinoRatio:
    def test_zero_returns(self, flat_returns):
        assert sortino_ratio(flat_returns) == 0.0

    def test_all_positive_returns_is_inf(self, positive_returns):
        sr = sortino_ratio(positive_returns, periods=252)
        assert sr == float("inf")  # no downside → inf

    def test_mixed_positive(self, mixed_returns):
        sr = sortino_ratio(mixed_returns, periods=252)
        assert sr > 0

    def test_sortino_greater_than_sharpe(self, mixed_returns):
        """Sortino should be >= Sharpe when there are fewer down days."""
        sr = sharpe_ratio(mixed_returns, periods=252)
        so = sortino_ratio(mixed_returns, periods=252)
        assert so >= sr


class TestCalmarRatio:
    def test_no_drawdown(self, positive_returns):
        # Constant positive returns → no drawdown → calmar=0 (div by zero guard)
        cr = calmar_ratio(positive_returns)
        # max_dd is 0 for constant positive → calmar returns 0
        assert cr == 0.0

    def test_mixed_returns(self, mixed_returns):
        cr = calmar_ratio(mixed_returns)
        assert isinstance(cr, float)


class TestOmegaRatio:
    def test_mixed_returns(self, mixed_returns):
        omega = omega_ratio(mixed_returns, periods=252)
        assert omega > 1.0  # net positive → omega > 1

    def test_short_series(self):
        idx = pd.date_range("2024-01-02", periods=1, freq="B")
        ret = pd.Series([0.01], index=idx)
        assert omega_ratio(ret) == 0.0


class TestMaxDrawdown:
    def test_no_drawdown(self, positive_returns):
        dd = max_drawdown(positive_returns)
        assert dd == 0.0  # constant positive → no drawdown

    def test_known_drawdown(self):
        """Drawdown from -20% return followed by +50% recovery."""
        idx = pd.date_range("2024-01-02", periods=4, freq="B")
        # cumulative: 1.0 → 0.8 → 1.2 → 1.1 → dd at 0.8 is -20%
        ret = pd.Series([-0.2, 0.5, -0.083], index=idx[:3])
        dd = max_drawdown(ret)
        assert dd < -0.05  # there is a meaningful drawdown


class TestMaxUnderwaterPeriod:
    def test_no_drawdown(self):
        balance = [100, 110, 120, 130]
        assert max_underwater_period(balance) == 0

    def test_known_underwater(self):
        balance = [100, 90, 85, 88, 95, 100, 110]
        # Peak at 100 (idx 0), recovery at 100 (idx 5)
        # Underwater from idx 1 to idx 4 (idx 5 recovers) → 4 days below peak
        # max_underwater counts from peak_idx to current, recovery resets
        assert max_underwater_period(balance) == 4

    def test_short_series(self):
        assert max_underwater_period([100]) == 0


class TestCVaR:
    def test_known_values(self):
        idx = pd.date_range("2024-01-02", periods=100, freq="B")
        np.random.seed(42)
        ret = pd.Series(np.random.normal(0.001, 0.02, 100), index=idx)
        cvar = conditional_value_at_risk(ret, confidence=0.95)
        assert cvar < 0  # CVaR should be negative (it's a loss measure)

    def test_short_series(self):
        idx = pd.date_range("2024-01-02", periods=1, freq="B")
        ret = pd.Series([0.01], index=idx)
        assert conditional_value_at_risk(ret) == 0.0


class TestCAGR:
    def test_known_cagr(self):
        """1% daily for 252 days ≈ ~1152% annual."""
        idx = pd.date_range("2024-01-02", periods=252, freq="B")
        ret = pd.Series(0.01, index=idx)
        c = cagr(ret, periods=252)
        assert c > 1.0  # > 100% annual


class TestAutocorrPenalty:
    def test_random_returns(self):
        np.random.seed(42)
        ret = pd.Series(np.random.normal(0, 0.01, 100))
        p = autocorr_penalty(ret)
        assert p >= 1.0  # penalty is always >= 1

    def test_short_series(self):
        ret = pd.Series([0.01, 0.02])
        assert autocorr_penalty(ret) >= 1.0


# ---------------------------------------------------------------------------
# Trade-level metrics tests
# ---------------------------------------------------------------------------


class TestCalculateTradeMetrics:
    def test_basic_metrics(self, sample_trades, sample_daily_balance):
        m = calculate_trade_metrics(
            trades=sample_trades,
            daily_balance=sample_daily_balance,
            starting_balance=1_000_000,
        )
        assert m.total_trades == 10
        assert m.total_winning == 6
        assert m.total_losing == 4
        assert abs(m.win_rate - 0.6) < 0.01
        assert m.net_profit == 21500  # sum of all PnLs
        assert m.gross_profit == 28000
        assert m.gross_loss == -6500
        assert m.profit_factor == pytest.approx(28000 / 6500, rel=0.01)

    def test_empty_trades(self):
        m = calculate_trade_metrics(
            trades=[], daily_balance=[1_000_000], starting_balance=1_000_000
        )
        assert m.total_trades == 0
        assert m.win_rate == 0.0

    def test_all_winners(self):
        trades = [
            {"pnl": 1000, "direction": "long", "fee": 10, "holding_period": 2}
            for _ in range(5)
        ]
        balance = [1_000_000 + i * 1000 for i in range(6)]
        m = calculate_trade_metrics(trades, balance, 1_000_000)
        assert m.win_rate == 1.0
        assert m.total_losing == 0
        assert m.losing_streak == 0

    def test_all_losers(self):
        trades = [
            {"pnl": -1000, "direction": "short", "fee": 10, "holding_period": 1}
            for _ in range(5)
        ]
        balance = [1_000_000 - i * 1000 for i in range(6)]
        m = calculate_trade_metrics(trades, balance, 1_000_000)
        assert m.win_rate == 0.0
        assert m.winning_streak == 0
        assert m.losing_streak == 5

    def test_long_short_breakdown(self, sample_trades, sample_daily_balance):
        m = calculate_trade_metrics(sample_trades, sample_daily_balance, 1_000_000)
        assert m.longs_count == 7
        assert m.shorts_count == 3
        assert m.win_rate_shorts > 0  # all 3 shorts are winners

    def test_streaks(self):
        trades = [
            {"pnl": 100, "direction": "long", "fee": 1, "holding_period": 1},
            {"pnl": 200, "direction": "long", "fee": 1, "holding_period": 1},
            {"pnl": 300, "direction": "long", "fee": 1, "holding_period": 1},
            {"pnl": -100, "direction": "long", "fee": 1, "holding_period": 1},
            {"pnl": -200, "direction": "long", "fee": 1, "holding_period": 1},
        ]
        balance = [100_000] * 6
        m = calculate_trade_metrics(trades, balance, 100_000)
        assert m.winning_streak == 3
        assert m.losing_streak == 2


class TestFormatMetrics:
    def test_produces_string(self, sample_trades, sample_daily_balance):
        m = calculate_trade_metrics(sample_trades, sample_daily_balance, 1_000_000)
        report = format_metrics(m)
        assert "PERFORMANCE REPORT" in report
        assert "Sharpe" in report
        assert "Sortino" in report
        assert "Omega" in report
        assert "Serenity" in report
        assert "CVaR" in report
        assert "Smart Sharpe" in report
