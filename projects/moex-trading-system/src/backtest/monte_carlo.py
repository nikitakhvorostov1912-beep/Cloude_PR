"""Monte Carlo simulation for strategy robustness testing.

Two modes:
1. Trade shuffling — reorder trades to test if performance depends on sequence
2. Equity noise — add Gaussian noise to daily returns to test sensitivity

Adapted from jesse-ai/jesse research/monte_carlo/ (MIT License) with:
- No Ray dependency — uses concurrent.futures for parallelism
- Standalone: works with plain lists of trades and equity curves
- Confidence intervals with statistical significance tests
- MOEX defaults (252 trading days)

Original: https://github.com/jesse-ai/jesse/blob/master/jesse/research/monte_carlo/
License: MIT (c) 2020 Jesse.Trade
"""
from __future__ import annotations

import logging
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_SEED = 42
_ANNUALIZATION_FACTOR = 252  # MOEX trading days


# ---------------------------------------------------------------------------
# Core: equity curve reconstruction from shuffled trades
# ---------------------------------------------------------------------------


def _reconstruct_equity(
    shuffled_pnls: list[float],
    starting_balance: float,
) -> list[float]:
    """Build equity curve by cumulatively adding PnLs to starting balance."""
    equity = [starting_balance]
    balance = starting_balance
    for pnl in shuffled_pnls:
        balance += pnl
        equity.append(balance)
    return equity


def _equity_metrics(equity: list[float]) -> dict[str, float]:
    """Calculate basic metrics from an equity curve."""
    if len(equity) < 2:
        return {"total_return": 0.0, "max_drawdown": 0.0, "sharpe_ratio": 0.0}

    start = equity[0]
    total_return = (equity[-1] - start) / start if start > 0 else 0.0

    # Max drawdown
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    # Sharpe from daily returns
    returns = []
    for i in range(1, len(equity)):
        if equity[i - 1] > 0:
            returns.append((equity[i] - equity[i - 1]) / equity[i - 1])
    if len(returns) > 1:
        arr = np.array(returns)
        std = float(arr.std(ddof=1))
        sharpe = (float(arr.mean()) / std * np.sqrt(_ANNUALIZATION_FACTOR)) if std > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "total_return": total_return,
        "max_drawdown": -max_dd,  # negative convention
        "sharpe_ratio": sharpe,
        "final_balance": equity[-1],
    }


# ---------------------------------------------------------------------------
# Single scenario workers (top-level for pickling)
# ---------------------------------------------------------------------------


def _run_trade_shuffle_scenario(args: tuple) -> dict[str, Any]:
    """Worker for trade-shuffle Monte Carlo (must be top-level for multiprocessing)."""
    pnls, starting_balance, seed = args
    rng = random.Random(seed)
    shuffled = pnls.copy()
    rng.shuffle(shuffled)
    equity = _reconstruct_equity(shuffled, starting_balance)
    metrics = _equity_metrics(equity)
    return metrics


def _run_noise_scenario(args: tuple) -> dict[str, Any]:
    """Worker for returns-noise Monte Carlo."""
    daily_returns, starting_balance, noise_std, seed = args
    rng = np.random.RandomState(seed)
    noise = rng.normal(0, noise_std, len(daily_returns))
    noisy_returns = np.array(daily_returns) + noise
    equity = [starting_balance]
    balance = starting_balance
    for r in noisy_returns:
        balance *= (1 + r)
        equity.append(balance)
    return _equity_metrics(equity)


# ---------------------------------------------------------------------------
# Confidence analysis
# ---------------------------------------------------------------------------


@dataclass
class ConfidenceInterval:
    """Confidence interval bounds for a metric."""
    lower: float
    upper: float


@dataclass
class MetricAnalysis:
    """Statistical analysis of a single metric across Monte Carlo scenarios."""
    original: float
    mean: float
    std: float
    min: float
    max: float
    percentile_5: float
    percentile_25: float
    median: float
    percentile_75: float
    percentile_95: float
    ci_90: ConfidenceInterval = field(default_factory=lambda: ConfidenceInterval(0, 0))
    ci_95: ConfidenceInterval = field(default_factory=lambda: ConfidenceInterval(0, 0))
    p_value: float = 0.0
    is_significant_5pct: bool = False
    is_significant_1pct: bool = False


@dataclass
class MonteCarloResult:
    """Full Monte Carlo simulation result."""
    n_scenarios: int
    mode: str  # "trade_shuffle" or "returns_noise"
    original_metrics: dict[str, float]
    analysis: dict[str, MetricAnalysis]
    scenario_metrics: list[dict[str, float]] = field(default_factory=list)


def _analyze_metric(
    name: str,
    original_value: float,
    simulated_values: np.ndarray,
    higher_is_better: bool = True,
) -> MetricAnalysis:
    """Compute percentiles, CI, and p-value for one metric."""
    if len(simulated_values) == 0:
        return MetricAnalysis(original=original_value, mean=0, std=0, min=0, max=0,
                              percentile_5=0, percentile_25=0, median=0,
                              percentile_75=0, percentile_95=0)

    if higher_is_better:
        p_value = float(np.sum(simulated_values >= original_value) / len(simulated_values))
    else:
        p_value = float(np.sum(simulated_values <= original_value) / len(simulated_values))

    return MetricAnalysis(
        original=original_value,
        mean=float(np.mean(simulated_values)),
        std=float(np.std(simulated_values)),
        min=float(np.min(simulated_values)),
        max=float(np.max(simulated_values)),
        percentile_5=float(np.percentile(simulated_values, 5)),
        percentile_25=float(np.percentile(simulated_values, 25)),
        median=float(np.percentile(simulated_values, 50)),
        percentile_75=float(np.percentile(simulated_values, 75)),
        percentile_95=float(np.percentile(simulated_values, 95)),
        ci_90=ConfidenceInterval(
            lower=float(np.percentile(simulated_values, 5)),
            upper=float(np.percentile(simulated_values, 95)),
        ),
        ci_95=ConfidenceInterval(
            lower=float(np.percentile(simulated_values, 2.5)),
            upper=float(np.percentile(simulated_values, 97.5)),
        ),
        p_value=p_value,
        is_significant_5pct=p_value < 0.05,
        is_significant_1pct=p_value < 0.01,
    )


def _build_analysis(
    original_metrics: dict[str, float],
    all_scenario_metrics: list[dict[str, float]],
) -> dict[str, MetricAnalysis]:
    """Build MetricAnalysis for each metric key present in scenarios."""
    analysis: dict[str, MetricAnalysis] = {}
    metric_keys = ["total_return", "max_drawdown", "sharpe_ratio"]

    for key in metric_keys:
        values = np.array([s[key] for s in all_scenario_metrics if key in s])
        if len(values) == 0:
            continue
        higher_is_better = key != "max_drawdown"
        analysis[key] = _analyze_metric(
            key,
            original_metrics.get(key, 0.0),
            values,
            higher_is_better=higher_is_better,
        )
    return analysis


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def monte_carlo_trades(
    trades: list[dict[str, Any]],
    starting_balance: float,
    n_scenarios: int = 1000,
    max_workers: int | None = None,
    seed: int = _BASE_SEED,
) -> MonteCarloResult:
    """Monte Carlo via trade-order shuffling.

    Tests whether strategy performance depends on the specific sequence of trades.
    If results are similar regardless of order → strategy is robust.
    If results vary wildly → performance may be an artifact of trade ordering.

    Args:
        trades: List of trade dicts, each must have 'pnl' key.
        starting_balance: Initial portfolio value.
        n_scenarios: Number of shuffle scenarios to run.
        max_workers: Max parallel processes (None = CPU count).
        seed: Base random seed for reproducibility.

    Returns:
        MonteCarloResult with analysis per metric.
    """
    pnls = [t.get("pnl", 0.0) for t in trades]
    if not pnls:
        raise ValueError("No trades provided for Monte Carlo simulation.")

    # Original metrics
    original_equity = _reconstruct_equity(pnls, starting_balance)
    original_metrics = _equity_metrics(original_equity)

    # Run scenarios
    args_list = [(pnls, starting_balance, seed + i) for i in range(n_scenarios)]

    all_results: list[dict[str, float]] = []
    workers = max_workers or min(n_scenarios, 4)

    if workers <= 1 or n_scenarios <= 50:
        # Sequential for small jobs
        all_results = [_run_trade_shuffle_scenario(a) for a in args_list]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run_trade_shuffle_scenario, a): i for i, a in enumerate(args_list)}
            for future in as_completed(futures):
                try:
                    all_results.append(future.result())
                except Exception as e:
                    logger.warning("Scenario %d failed: %s", futures[future], e)

    analysis = _build_analysis(original_metrics, all_results)

    return MonteCarloResult(
        n_scenarios=len(all_results),
        mode="trade_shuffle",
        original_metrics=original_metrics,
        analysis=analysis,
        scenario_metrics=all_results,
    )


def monte_carlo_returns_noise(
    daily_balance: Sequence[float],
    noise_std: float = 0.002,
    n_scenarios: int = 1000,
    max_workers: int | None = None,
    seed: int = _BASE_SEED,
) -> MonteCarloResult:
    """Monte Carlo via Gaussian noise on daily returns.

    Tests strategy sensitivity to small changes in market data.
    Adds random noise to each day's return, simulating market uncertainty.

    Args:
        daily_balance: Daily portfolio equity values.
        noise_std: Standard deviation of Gaussian noise added to returns (default 0.2%).
        n_scenarios: Number of noise scenarios.
        max_workers: Max parallel processes.
        seed: Base random seed.

    Returns:
        MonteCarloResult with analysis per metric.
    """
    if len(daily_balance) < 3:
        raise ValueError("Need at least 3 daily balance values.")

    starting_balance = daily_balance[0]
    daily_returns = [
        (daily_balance[i] - daily_balance[i - 1]) / daily_balance[i - 1]
        for i in range(1, len(daily_balance))
        if daily_balance[i - 1] > 0
    ]

    original_metrics = _equity_metrics(list(daily_balance))

    args_list = [(daily_returns, starting_balance, noise_std, seed + i) for i in range(n_scenarios)]

    all_results: list[dict[str, float]] = []
    workers = max_workers or min(n_scenarios, 4)

    if workers <= 1 or n_scenarios <= 50:
        all_results = [_run_noise_scenario(a) for a in args_list]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run_noise_scenario, a): i for i, a in enumerate(args_list)}
            for future in as_completed(futures):
                try:
                    all_results.append(future.result())
                except Exception as e:
                    logger.warning("Noise scenario %d failed: %s", futures[future], e)

    analysis = _build_analysis(original_metrics, all_results)

    return MonteCarloResult(
        n_scenarios=len(all_results),
        mode="returns_noise",
        original_metrics=original_metrics,
        analysis=analysis,
        scenario_metrics=all_results,
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_monte_carlo(result: MonteCarloResult) -> str:
    """Format Monte Carlo results into a human-readable report."""
    mode_label = {
        "trade_shuffle": "TRADE SHUFFLE (order independence test)",
        "returns_noise": "RETURNS NOISE (market sensitivity test)",
    }.get(result.mode, result.mode)

    lines = [
        "=" * 64,
        f"  MONTE CARLO: {mode_label}",
        f"  Scenarios: {result.n_scenarios}",
        "=" * 64,
        "",
        f"  {'Metric':<20} {'Original':>10} {'5th%':>10} {'Median':>10} {'95th%':>10} {'p-value':>8}",
        "  " + "-" * 68,
    ]

    for name, a in result.analysis.items():
        display = name.replace("_", " ").title()
        is_pct = name in ("total_return", "max_drawdown")
        fmt = lambda v: f"{v * 100:>+.1f}%" if is_pct else f"{v:>.3f}"

        sig = ""
        if a.is_significant_1pct:
            sig = "**"
        elif a.is_significant_5pct:
            sig = "*"

        lines.append(
            f"  {display:<20} {fmt(a.original):>10} {fmt(a.percentile_5):>10} "
            f"{fmt(a.median):>10} {fmt(a.percentile_95):>10} {a.p_value:>7.3f}{sig}"
        )

    lines += [
        "",
        "  * p < 0.05  ** p < 0.01",
        "  Low p-value = original result is unusual (potentially overfit)",
        "=" * 64,
    ]
    return "\n".join(lines)
