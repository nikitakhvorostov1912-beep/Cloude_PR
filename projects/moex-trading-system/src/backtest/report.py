"""Backtest reporting — metrics calculation and overfitting detection."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backtest.engine import BacktestResult


def calculate_metrics(
    equity_curve: list[float],
    trades: list[dict],
    risk_free_rate: float = 0.19,
) -> "BacktestResult":
    """
    Compute full set of performance metrics from equity curve and trade log.

    Args:
        equity_curve: Daily equity values (starting from initial capital).
        trades: List of trade dicts with keys: pnl, direction, entry, exit, etc.
        risk_free_rate: Annual risk-free rate (CBR key rate, default 19%).

    Returns:
        BacktestResult populated with all metrics.
    """
    from src.backtest.engine import BacktestResult  # avoid circular import at module load

    if len(equity_curve) < 2:
        return BacktestResult(equity_curve=equity_curve, trades=trades)

    initial = equity_curve[0]
    final = equity_curve[-1]
    n_days = len(equity_curve) - 1

    # --- Returns ---
    total_return = (final - initial) / initial if initial > 0 else 0.0
    years = n_days / 252.0
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    # --- Daily returns ---
    daily_returns = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] > 0
    ]

    if not daily_returns:
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            equity_curve=equity_curve,
            trades=trades,
        )

    avg_daily = sum(daily_returns) / len(daily_returns)
    daily_rf = risk_free_rate / 252.0

    # Sharpe
    excess = [r - daily_rf for r in daily_returns]
    excess_mean = sum(excess) / len(excess)
    variance = sum((r - excess_mean) ** 2 for r in excess) / max(len(excess) - 1, 1)
    std_dev = math.sqrt(variance)
    sharpe = (excess_mean / std_dev * math.sqrt(252)) if std_dev > 0 else 0.0

    # Sortino — downside deviation only
    downside = [r - daily_rf for r in daily_returns if r < daily_rf]
    if downside:
        ds_var = sum(d**2 for d in downside) / max(len(downside) - 1, 1)
        ds_std = math.sqrt(ds_var)
        sortino = (excess_mean * math.sqrt(252)) / ds_std if ds_std > 0 else 0.0
    else:
        sortino = float("inf") if excess_mean > 0 else 0.0

    # Max drawdown
    max_dd = 0.0
    peak = equity_curve[0]
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    calmar = annual_return / max_dd if max_dd > 0 else 0.0

    # Trade statistics
    total_trades = len(trades)
    if total_trades > 0:
        pnls = [t.get("pnl", 0.0) for t in trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]

        win_rate = len(winners) / total_trades
        avg_trade_pnl = sum(pnls) / total_trades

        gross_profit = sum(winners)
        gross_loss = abs(sum(losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Max consecutive losses
        max_cons = 0
        current_cons = 0
        for p in pnls:
            if p < 0:
                current_cons += 1
                max_cons = max(max_cons, current_cons)
            else:
                current_cons = 0
    else:
        win_rate = 0.0
        avg_trade_pnl = 0.0
        profit_factor = 0.0
        max_cons = 0

    # Recovery factor = total_return / max_drawdown
    recovery = total_return / max_dd if max_dd > 0 else 0.0

    # Time in market — fraction of days with an open position
    days_in_market = sum(1 for t in trades if t.get("holding_days", 0) > 0)
    time_in_market_pct = days_in_market / n_days if n_days > 0 else 0.0

    return BacktestResult(
        total_return=total_return,
        annual_return=annual_return,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_dd,
        calmar_ratio=calmar,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=total_trades,
        avg_trade_pnl=avg_trade_pnl,
        max_consecutive_losses=max_cons,
        recovery_factor=recovery,
        time_in_market_pct=time_in_market_pct,
        equity_curve=equity_curve,
        trades=trades,
    )


def check_overfitting(
    in_sample_sharpe: float,
    out_of_sample_sharpe: float,
    num_parameters: int,
    num_backtests: int,
) -> dict[str, bool | float]:
    """
    Heuristic overfitting checks for walk-forward results.

    Rules:
    1. IS/OOS Sharpe ratio > 2.0  → likely overfit
    2. IS Sharpe > 3.0 → suspiciously high
    3. OOS Sharpe < 0 → strategy fails out-of-sample
    4. num_backtests > 100 → data-snooping bias risk

    Returns:
        Dict with boolean flags and computed ratios.
    """
    is_oos_ratio = (
        in_sample_sharpe / out_of_sample_sharpe
        if out_of_sample_sharpe != 0
        else float("inf")
    )

    overfit_ratio = is_oos_ratio > 2.0
    suspiciously_high = in_sample_sharpe > 3.0
    fails_oos = out_of_sample_sharpe < 0.0
    data_snooping_risk = num_backtests > 100

    # Deflated Sharpe ratio estimate (Haircut Sharpe)
    # Simple approximation: haircut = 1 - sqrt(log(n) / sharpe)
    haircut_adj = math.log(max(num_backtests, 1))
    deflated_sharpe = in_sample_sharpe - math.sqrt(haircut_adj) if in_sample_sharpe > 0 else in_sample_sharpe

    # Parameter inflation penalty
    param_penalty = num_parameters / max(num_backtests, 1)

    return {
        "is_overfit": overfit_ratio or fails_oos,
        "overfit_ratio": overfit_ratio,
        "suspiciously_high_is_sharpe": suspiciously_high,
        "fails_out_of_sample": fails_oos,
        "data_snooping_risk": data_snooping_risk,
        "is_oos_ratio": round(is_oos_ratio, 3),
        "deflated_sharpe": round(deflated_sharpe, 3),
        "parameter_inflation": round(param_penalty, 4),
        "in_sample_sharpe": round(in_sample_sharpe, 3),
        "out_of_sample_sharpe": round(out_of_sample_sharpe, 3),
    }


def generate_report(result: "BacktestResult") -> str:
    """Format BacktestResult into human-readable text report."""
    lines = [
        "=" * 60,
        "  BACKTEST REPORT",
        "=" * 60,
        f"  Total Return       : {result.total_return:>+.2%}",
        f"  Annual Return      : {result.annual_return:>+.2%}",
        f"  Sharpe Ratio       : {result.sharpe_ratio:>.3f}",
        f"  Sortino Ratio      : {result.sortino_ratio:>.3f}",
        f"  Calmar Ratio       : {result.calmar_ratio:>.3f}",
        f"  Max Drawdown       : {result.max_drawdown:>.2%}",
        f"  Recovery Factor    : {result.recovery_factor:>.3f}",
        "-" * 60,
        f"  Total Trades       : {result.total_trades}",
        f"  Win Rate           : {result.win_rate:>.2%}",
        f"  Avg Trade P&L      : {result.avg_trade_pnl:>+.2f} ₽",
        f"  Profit Factor      : {result.profit_factor:>.3f}",
        f"  Max Consec. Losses : {result.max_consecutive_losses}",
        f"  Time in Market     : {result.time_in_market_pct:>.2%}",
        "=" * 60,
    ]
    return "\n".join(lines)


def generate_html_report(
    equity_curve: list[float],
    benchmark_curve: list[float] | None = None,
    output_path: str = "data/backtest_report.html",
    title: str = "MOEX Trading System",
) -> str:
    """Generate a QuantStats HTML tear sheet from equity curve.

    Parameters
    ----------
    equity_curve:
        Daily portfolio equity values.
    benchmark_curve:
        Optional IMOEX equity curve for comparison.
    output_path:
        Where to save the HTML report.
    title:
        Report title.

    Returns
    -------
    str
        Path to the generated HTML file.
    """
    try:
        import pandas as pd
        import quantstats as qs
    except ImportError:
        return ""

    returns = pd.Series(equity_curve).pct_change().dropna()
    returns.index = pd.date_range(end="2026-01-01", periods=len(returns), freq="B")

    benchmark = None
    if benchmark_curve and len(benchmark_curve) > 1:
        benchmark = pd.Series(benchmark_curve).pct_change().dropna()
        benchmark.index = returns.index[: len(benchmark)]

    qs.reports.html(returns, benchmark=benchmark, output=output_path, title=title)
    return output_path
