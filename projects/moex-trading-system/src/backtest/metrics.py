"""Comprehensive performance metrics for backtesting and strategy evaluation.

Adapted from jesse-ai/jesse (MIT License) with MOEX-specific adjustments:
- Default periods=252 (MOEX trading days vs 365 for crypto)
- Added Profit Factor, Recovery Factor
- Smart Sharpe/Sortino with autocorrelation penalty
- Standalone: no jesse dependencies

Original: https://github.com/jesse-ai/jesse/blob/master/jesse/services/metrics.py
License: MIT (c) 2020 Jesse.Trade
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MOEX_TRADING_DAYS = 252
"""Number of trading days per year on Moscow Exchange."""

CBR_KEY_RATE = 0.19
"""Central Bank of Russia key rate (annual), used as default risk-free rate."""


# ---------------------------------------------------------------------------
# Return-level metrics
# ---------------------------------------------------------------------------


def _prepare_returns(
    returns: pd.Series | pd.DataFrame,
    rf: float = 0.0,
    periods: int = MOEX_TRADING_DAYS,
) -> pd.Series:
    """Convert returns to Series and subtract risk-free rate."""
    if isinstance(returns, pd.DataFrame):
        returns = returns.iloc[:, 0]
    returns = returns.dropna()
    if rf != 0:
        returns = returns - (rf / periods)
    return returns


def autocorr_penalty(returns: pd.Series) -> float:
    """Autocorrelation penalty for Smart Sharpe/Sortino.

    Serial correlation in returns understates true volatility.
    This factor inflates the denominator to compensate.
    """
    num = len(returns)
    if num < 3:
        return 1.0
    coef = abs(np.corrcoef(returns.values[:-1], returns.values[1:])[0, 1])
    if np.isnan(coef):
        return 1.0
    corr = [((num - x) / num) * coef ** x for x in range(1, num)]
    return float(np.sqrt(1 + 2 * np.sum(corr)))


def sharpe_ratio(
    returns: pd.Series | pd.DataFrame,
    rf: float = 0.0,
    periods: int = MOEX_TRADING_DAYS,
    annualize: bool = True,
    smart: bool = False,
) -> float:
    """Sharpe ratio — excess return per unit of total risk."""
    ret = _prepare_returns(returns, rf, periods)
    if len(ret) < 2:
        return 0.0
    divisor = float(ret.std(ddof=1))
    if divisor == 0:
        return 0.0
    if smart:
        divisor *= autocorr_penalty(ret)
    res = float(ret.mean()) / divisor
    if annualize:
        res *= math.sqrt(periods)
    return float(res)


def sortino_ratio(
    returns: pd.Series | pd.DataFrame,
    rf: float = 0.0,
    periods: int = MOEX_TRADING_DAYS,
    annualize: bool = True,
    smart: bool = False,
) -> float:
    """Sortino ratio — excess return per unit of downside risk only."""
    ret = _prepare_returns(returns, rf, periods)
    if len(ret) < 2:
        return 0.0
    downside = float(np.sqrt((ret[ret < 0] ** 2).sum() / len(ret)))
    if downside == 0:
        return float("inf") if float(ret.mean()) > 0 else 0.0
    if smart:
        downside *= autocorr_penalty(ret)
    res = float(ret.mean()) / downside
    if annualize:
        res *= math.sqrt(periods)
    return float(res)


def calmar_ratio(
    returns: pd.Series | pd.DataFrame,
    periods: int = MOEX_TRADING_DAYS,
) -> float:
    """Calmar ratio — CAGR divided by max drawdown."""
    ret = _prepare_returns(returns)
    if len(ret) < 2:
        return 0.0
    cagr_val = cagr(returns, periods=periods)
    max_dd = abs(max_drawdown(returns))
    return cagr_val / max_dd if max_dd != 0 else 0.0


def omega_ratio(
    returns: pd.Series | pd.DataFrame,
    rf: float = 0.0,
    required_return: float = 0.0,
    periods: int = MOEX_TRADING_DAYS,
) -> float:
    """Omega ratio — probability-weighted gain/loss above threshold."""
    ret = _prepare_returns(returns, rf, periods)
    if len(ret) < 2:
        return 0.0
    if periods == 1:
        threshold = required_return
    else:
        threshold = (1 + required_return) ** (1.0 / periods) - 1
    excess = ret - threshold
    numer = float(excess[excess > 0].sum())
    denom = float(-excess[excess < 0].sum())
    return numer / denom if denom > 0 else float("nan")


def serenity_index(
    returns: pd.Series | pd.DataFrame,
    rf: float = 0.0,
) -> float:
    """Serenity index — risk-adjusted return using Ulcer Index and CVaR."""
    ret = _prepare_returns(returns)
    if len(ret) < 2:
        return 0.0
    dd = _to_drawdown_series(ret)
    ui = ulcer_index(ret)
    if ui == 0:
        return 0.0
    cvar = conditional_value_at_risk(dd)
    std = float(ret.std())
    if std == 0:
        return 0.0
    pitfall = -cvar / std
    if pitfall == 0:
        return 0.0
    return float((ret.sum() - rf) / (ui * pitfall))


def ulcer_index(returns: pd.Series) -> float:
    """Ulcer index — root mean square of drawdowns (downside risk measure)."""
    dd = _to_drawdown_series(returns)
    n = len(returns)
    if n <= 1:
        return 0.0
    return float(np.sqrt((dd ** 2).sum() / (n - 1)))


def _to_drawdown_series(returns: pd.Series) -> pd.Series:
    """Convert returns to drawdown series."""
    prices = (1 + returns).cumprod()
    dd = prices / np.maximum.accumulate(prices) - 1.0
    return dd.replace([np.inf, -np.inf, -0], 0)


def conditional_value_at_risk(
    returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """CVaR (Expected Shortfall) — average loss beyond VaR threshold."""
    if len(returns) < 2:
        return 0.0
    sorted_ret = np.sort(returns.values)
    index = int((1 - confidence) * len(sorted_ret))
    if index == 0:
        return float(sorted_ret[0]) if len(sorted_ret) > 0 else 0.0
    c_var = float(sorted_ret[:index].mean())
    return c_var if not np.isnan(c_var) else 0.0


# ---------------------------------------------------------------------------
# Portfolio-level metrics
# ---------------------------------------------------------------------------


def max_drawdown(returns: pd.Series | pd.DataFrame) -> float:
    """Maximum drawdown as a negative fraction (e.g. -0.15 = -15%)."""
    ret = _prepare_returns(returns)
    if len(ret) < 2:
        return 0.0
    prices = (ret + 1).cumprod()
    result = float((prices / prices.expanding(min_periods=1).max()).min() - 1)
    return result


def max_underwater_period(daily_balance: Sequence[float]) -> int:
    """Max days from peak to recovery (longest drawdown duration)."""
    if len(daily_balance) < 2:
        return 0
    max_period = 0
    current_peak = daily_balance[0]
    peak_idx = 0
    for i in range(1, len(daily_balance)):
        if daily_balance[i] >= current_peak:
            current_peak = daily_balance[i]
            peak_idx = i
        else:
            underwater = i - peak_idx
            if underwater > max_period:
                max_period = underwater
    return max_period


def cagr(
    returns: pd.Series | pd.DataFrame,
    rf: float = 0.0,
    periods: int = MOEX_TRADING_DAYS,
) -> float:
    """Compound Annual Growth Rate."""
    ret = _prepare_returns(returns, rf)
    if len(ret) < 2:
        return 0.0
    last_value = float((1 + ret).prod())
    days = (ret.index[-1] - ret.index[0]).days
    years = days / 365.0
    if years == 0:
        return 0.0
    ratio = np.clip(last_value, 1e-10, 1e10)
    with np.errstate(over="ignore", under="ignore"):
        result = float(ratio ** (1 / years) - 1)
    return result


# ---------------------------------------------------------------------------
# Trade-level metrics
# ---------------------------------------------------------------------------


def _streak_analysis(pnls: np.ndarray) -> tuple[int, int, int]:
    """Compute winning streak, losing streak, and current streak from PnL array."""
    if len(pnls) == 0:
        return 0, 0, 0
    pos = np.clip(pnls, 0, 1).astype(bool).cumsum()
    neg = np.clip(pnls, -1, 0).astype(bool).cumsum()
    streaks = np.where(
        pnls >= 0,
        pos - np.maximum.accumulate(np.where(pnls <= 0, pos, 0)),
        -neg + np.maximum.accumulate(np.where(pnls >= 0, neg, 0)),
    )
    winning_streak = int(max(streaks.max(), 0))
    losing_streak = int(0 if streaks.min() > 0 else abs(streaks.min()))
    current = int(streaks[-1])
    return winning_streak, losing_streak, current


@dataclass
class TradeMetrics:
    """Complete trade-level and portfolio-level metrics."""

    # Portfolio metrics
    starting_balance: float = 0.0
    finishing_balance: float = 0.0
    total_return: float = 0.0
    annual_return: float = 0.0
    net_profit: float = 0.0
    net_profit_pct: float = 0.0

    # Risk-adjusted ratios
    sharpe_ratio: float = 0.0
    smart_sharpe: float = 0.0
    sortino_ratio: float = 0.0
    smart_sortino: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    serenity_index: float = 0.0

    # Drawdown
    max_drawdown: float = 0.0
    max_underwater_period: int = 0

    # Risk
    cvar_95: float = 0.0

    # Trade stats
    total_trades: int = 0
    total_winning: int = 0
    total_losing: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    recovery_factor: float = 0.0
    expectancy: float = 0.0
    expectancy_pct: float = 0.0

    # Averages
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_win_loss_ratio: float = 0.0
    avg_holding_period: float = 0.0

    # Extremes
    largest_win: float = 0.0
    largest_loss: float = 0.0
    winning_streak: int = 0
    losing_streak: int = 0
    current_streak: int = 0

    # Breakdown
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    total_fees: float = 0.0

    # Long/short split
    longs_count: int = 0
    shorts_count: int = 0
    win_rate_longs: float = 0.0
    win_rate_shorts: float = 0.0


def calculate_trade_metrics(
    trades: list[dict],
    daily_balance: list[float],
    starting_balance: float,
    risk_free_rate: float = CBR_KEY_RATE,
    periods: int = MOEX_TRADING_DAYS,
    start_date: str | None = None,
) -> TradeMetrics:
    """Calculate comprehensive metrics from trade list and daily balance.

    Args:
        trades: List of dicts with keys: pnl, direction (long/short),
                fee, holding_period (days).
        daily_balance: Daily portfolio equity values.
        starting_balance: Initial capital.
        risk_free_rate: Annual risk-free rate (default: CBR key rate 19%).
        periods: Trading days per year (default: 252 for MOEX).
        start_date: ISO date string for index (e.g. "2024-01-10").

    Returns:
        TradeMetrics dataclass with all computed values.
    """
    m = TradeMetrics(starting_balance=starting_balance)

    if not trades:
        return m

    # --- Trade-level ---
    pnls = np.array([t.get("pnl", 0.0) for t in trades], dtype=float)
    directions = [t.get("direction", "long") for t in trades]
    fees = np.array([t.get("fee", 0.0) for t in trades], dtype=float)
    holdings = np.array([t.get("holding_period", 0.0) for t in trades], dtype=float)

    m.total_trades = len(pnls)
    m.total_winning = int((pnls > 0).sum())
    m.total_losing = int((pnls < 0).sum())
    m.win_rate = m.total_winning / m.total_trades if m.total_trades > 0 else 0.0

    m.gross_profit = float(pnls[pnls > 0].sum())
    m.gross_loss = float(pnls[pnls < 0].sum())
    m.total_fees = float(fees.sum())
    m.net_profit = float(pnls.sum())
    m.net_profit_pct = (m.net_profit / starting_balance * 100) if starting_balance > 0 else 0.0
    m.finishing_balance = starting_balance + m.net_profit

    m.profit_factor = (
        m.gross_profit / abs(m.gross_loss) if m.gross_loss != 0 else float("inf")
    )

    # Averages
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    m.avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
    m.avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 0.0
    m.avg_win_loss_ratio = m.avg_win / m.avg_loss if m.avg_loss > 0 else 0.0
    m.avg_holding_period = float(holdings.mean()) if len(holdings) > 0 else 0.0

    # Expectancy
    m.expectancy = m.avg_win * m.win_rate - m.avg_loss * (1 - m.win_rate)
    m.expectancy_pct = (m.expectancy / starting_balance * 100) if starting_balance > 0 else 0.0

    # Extremes
    m.largest_win = float(pnls.max()) if len(pnls) > 0 else 0.0
    m.largest_loss = float(pnls.min()) if len(pnls) > 0 else 0.0

    # Streaks
    m.winning_streak, m.losing_streak, m.current_streak = _streak_analysis(pnls)

    # Long/short breakdown
    dir_arr = np.array(directions)
    long_mask = dir_arr == "long"
    short_mask = dir_arr == "short"
    m.longs_count = int(long_mask.sum())
    m.shorts_count = int(short_mask.sum())

    long_wins = ((pnls > 0) & long_mask).sum()
    long_total = long_mask.sum()
    m.win_rate_longs = float(long_wins / long_total) if long_total > 0 else 0.0

    short_wins = ((pnls > 0) & short_mask).sum()
    short_total = short_mask.sum()
    m.win_rate_shorts = float(short_wins / short_total) if short_total > 0 else 0.0

    # --- Portfolio-level (from daily balance) ---
    if len(daily_balance) < 2:
        return m

    if start_date:
        date_index = pd.date_range(start=start_date, periods=len(daily_balance), freq="B")
    else:
        date_index = pd.date_range(end="2026-01-01", periods=len(daily_balance), freq="B")

    daily_ret = pd.Series(daily_balance, index=date_index).pct_change(1).dropna()

    if len(daily_ret) < 2:
        return m

    m.total_return = (daily_balance[-1] - daily_balance[0]) / daily_balance[0] if daily_balance[0] > 0 else 0.0
    m.annual_return = cagr(daily_ret, periods=periods) * 100
    m.max_drawdown = max_drawdown(daily_ret) * 100
    m.max_underwater_period = max_underwater_period(daily_balance)

    m.recovery_factor = (
        m.total_return / abs(m.max_drawdown / 100) if m.max_drawdown != 0 else 0.0
    )

    m.sharpe_ratio = sharpe_ratio(daily_ret, periods=periods)
    m.smart_sharpe = sharpe_ratio(daily_ret, periods=periods, smart=True)
    m.sortino_ratio = sortino_ratio(daily_ret, periods=periods)
    m.smart_sortino = sortino_ratio(daily_ret, periods=periods, smart=True)
    m.calmar_ratio = calmar_ratio(daily_ret, periods=periods)
    m.omega_ratio = omega_ratio(daily_ret, periods=periods)
    m.serenity_index = serenity_index(daily_ret)
    m.cvar_95 = conditional_value_at_risk(daily_ret, confidence=0.95)

    return m


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_metrics(m: TradeMetrics) -> str:
    """Format TradeMetrics into a human-readable report string."""
    dd_pct = abs(m.max_drawdown)
    lines = [
        "=" * 64,
        "  PERFORMANCE REPORT (MOEX)",
        "=" * 64,
        f"  Starting Balance   : {m.starting_balance:>14,.0f} RUB",
        f"  Finishing Balance  : {m.finishing_balance:>14,.0f} RUB",
        f"  Net Profit         : {m.net_profit:>+14,.0f} RUB ({m.net_profit_pct:>+.2f}%)",
        f"  Annual Return      : {m.annual_return:>+.2f}%",
        "-" * 64,
        "  RISK-ADJUSTED RATIOS",
        "-" * 64,
        f"  Sharpe Ratio       : {m.sharpe_ratio:>.3f}",
        f"  Smart Sharpe       : {m.smart_sharpe:>.3f}",
        f"  Sortino Ratio      : {m.sortino_ratio:>.3f}",
        f"  Smart Sortino      : {m.smart_sortino:>.3f}",
        f"  Calmar Ratio       : {m.calmar_ratio:>.3f}",
        f"  Omega Ratio        : {m.omega_ratio:>.3f}",
        f"  Serenity Index     : {m.serenity_index:>.3f}",
        "-" * 64,
        "  RISK",
        "-" * 64,
        f"  Max Drawdown       : {dd_pct:>.2f}%",
        f"  Max Underwater     : {m.max_underwater_period} days",
        f"  CVaR (95%)         : {m.cvar_95:>.4f}",
        f"  Recovery Factor    : {m.recovery_factor:>.3f}",
        "-" * 64,
        "  TRADES",
        "-" * 64,
        f"  Total Trades       : {m.total_trades}",
        f"  Win Rate           : {m.win_rate:>.2%}",
        f"  Profit Factor      : {m.profit_factor:>.3f}",
        f"  Expectancy         : {m.expectancy:>+,.0f} RUB/trade",
        f"  Avg Win            : {m.avg_win:>+,.0f} RUB",
        f"  Avg Loss           : {-m.avg_loss:>+,.0f} RUB",
        f"  Win/Loss Ratio     : {m.avg_win_loss_ratio:>.3f}",
        f"  Avg Holding        : {m.avg_holding_period:>.1f} days",
        f"  Largest Win        : {m.largest_win:>+,.0f} RUB",
        f"  Largest Loss       : {m.largest_loss:>+,.0f} RUB",
        f"  Winning Streak     : {m.winning_streak}",
        f"  Losing Streak      : {m.losing_streak}",
        f"  Total Fees         : {m.total_fees:>,.0f} RUB",
    ]

    if m.longs_count + m.shorts_count > 0:
        lines += [
            "-" * 64,
            "  LONG / SHORT",
            "-" * 64,
            f"  Longs              : {m.longs_count} ({m.win_rate_longs:.0%} win)",
            f"  Shorts             : {m.shorts_count} ({m.win_rate_shorts:.0%} win)",
        ]

    lines.append("=" * 64)
    return "\n".join(lines)
