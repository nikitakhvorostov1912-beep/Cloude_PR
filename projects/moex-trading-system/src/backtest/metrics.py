"""Comprehensive performance metrics for backtesting and strategy evaluation.

Adapted from jesse-ai/jesse (MIT License) with MOEX-specific adjustments:
- Default periods=252 (MOEX trading days vs 365 for crypto)
- Added Profit Factor, Recovery Factor
- Smart Sharpe/Sortino with autocorrelation penalty
- Standalone: no jesse dependencies

Additional metrics inspired by pybroker concepts (written from scratch):
- BCa Bootstrap Confidence Intervals (bias-corrected accelerated)
- MAE/MFE Trade Quality (max adverse/favorable excursion)
- Equity R², Relative Entropy, Ulcer Performance Index

Original: https://github.com/jesse-ai/jesse/blob/master/jesse/services/metrics.py
License: MIT (c) 2020 Jesse.Trade
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, NamedTuple, Sequence

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MOEX_TRADING_DAYS = 252
"""Number of trading days per year on Moscow Exchange."""

CBR_KEY_RATE = 0.19
"""Central Bank of Russia key rate (annual), used as default risk-free rate."""

_DEFAULT_N_BOOT = 10_000
"""Default number of bootstrap resamples."""

_DEFAULT_BOOT_SAMPLE_SIZE = 1_000
"""Default sample size per bootstrap resample."""


# ---------------------------------------------------------------------------
# BCa Bootstrap Confidence Intervals
# ---------------------------------------------------------------------------


class BootstrapCI(NamedTuple):
    """Confidence interval from BCa bootstrap.

    Attributes:
        low: Lower bound of the interval.
        high: Upper bound of the interval.
        level: Confidence level (e.g. 0.95).
        point_estimate: Point estimate of the statistic.
    """

    low: float
    high: float
    level: float
    point_estimate: float


@dataclass(frozen=True)
class BootstrapResult:
    """Full bootstrap result with multiple confidence levels.

    Attributes:
        ci_90: 90% confidence interval.
        ci_95: 95% confidence interval.
        ci_975: 97.5% confidence interval.
        point_estimate: Point estimate of the statistic.
        n_samples: Number of bootstrap resamples used.
    """

    ci_90: BootstrapCI
    ci_95: BootstrapCI
    ci_975: BootstrapCI
    point_estimate: float
    n_samples: int


def _jackknife_acceleration(data: np.ndarray, stat_fn: Callable) -> float:
    """Compute jackknife acceleration factor for BCa.

    Leave-one-out jackknife estimates how the statistic is influenced
    by each data point — skewed influence = biased bootstrap distribution.
    """
    n = len(data)
    if n < 3:
        return 0.0
    jk_values = np.empty(n)
    for i in range(n):
        subset = np.concatenate([data[:i], data[i + 1:]])
        jk_values[i] = stat_fn(subset)
    jk_mean = jk_values.mean()
    diffs = jk_mean - jk_values
    numer = (diffs ** 3).sum()
    denom = (diffs ** 2).sum()
    if denom == 0:
        return 0.0
    return float(numer / (6.0 * denom ** 1.5))


def bca_bootstrap(
    data: np.ndarray,
    stat_fn: Callable[[np.ndarray], float],
    n_boot: int = _DEFAULT_N_BOOT,
    sample_size: int | None = None,
    rng: np.random.Generator | None = None,
) -> BootstrapResult:
    """Bias-corrected and accelerated (BCa) bootstrap confidence intervals.

    BCa corrects two problems with naive percentile bootstrap:
    1. Bias: the bootstrap distribution median != the point estimate
    2. Skewness: the bootstrap distribution is asymmetric

    Args:
        data: 1D array of observations.
        stat_fn: Function mapping array → scalar statistic.
        n_boot: Number of bootstrap resamples.
        sample_size: Size of each resample (default: len(data)).
        rng: NumPy random generator for reproducibility.

    Returns:
        BootstrapResult with 90%, 95%, 97.5% confidence intervals.
    """
    data = np.asarray(data, dtype=np.float64)
    n = len(data)
    if n == 0:
        empty_ci = BootstrapCI(0.0, 0.0, 0.0, 0.0)
        return BootstrapResult(empty_ci, empty_ci, empty_ci, 0.0, 0)

    if rng is None:
        rng = np.random.default_rng()

    if sample_size is None:
        sample_size = n

    sample_size = min(sample_size, n)
    point_est = float(stat_fn(data))

    # Generate bootstrap distribution
    boot_stats = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=sample_size)
        boot_stats[i] = stat_fn(data[idx])

    boot_stats.sort()

    # Bias correction: z0 = Φ⁻¹(proportion of bootstrap < point estimate)
    prop_below = np.mean(boot_stats < point_est)
    prop_below = np.clip(prop_below, 1e-10, 1 - 1e-10)
    z0 = float(scipy_stats.norm.ppf(prop_below))

    # Acceleration via jackknife
    a = _jackknife_acceleration(data, stat_fn)

    def _bca_quantile(alpha: float) -> float:
        """Compute BCa-adjusted quantile."""
        z_alpha = float(scipy_stats.norm.ppf(alpha))
        numerator = z0 + z_alpha
        denominator = 1.0 - a * numerator
        if abs(denominator) < 1e-10:
            denominator = 1e-10
        adjusted_z = z0 + numerator / denominator
        adjusted_p = float(scipy_stats.norm.cdf(adjusted_z))
        adjusted_p = np.clip(adjusted_p, 0.0, 1.0)
        idx = int(adjusted_p * (n_boot - 1))
        idx = np.clip(idx, 0, n_boot - 1)
        return float(boot_stats[idx])

    ci_90 = BootstrapCI(_bca_quantile(0.05), _bca_quantile(0.95), 0.90, point_est)
    ci_95 = BootstrapCI(_bca_quantile(0.025), _bca_quantile(0.975), 0.95, point_est)
    ci_975 = BootstrapCI(_bca_quantile(0.0125), _bca_quantile(0.9875), 0.975, point_est)

    return BootstrapResult(
        ci_90=ci_90, ci_95=ci_95, ci_975=ci_975,
        point_estimate=point_est, n_samples=n_boot,
    )


def bootstrap_metrics(
    daily_returns: pd.Series | np.ndarray,
    n_boot: int = _DEFAULT_N_BOOT,
    periods: int = MOEX_TRADING_DAYS,
    rng: np.random.Generator | None = None,
) -> dict[str, BootstrapResult]:
    """Bootstrap CI for key performance metrics.

    Computes BCa bootstrap for Sharpe, Sortino, Profit Factor, Max DD.

    Args:
        daily_returns: Series of daily returns.
        n_boot: Number of bootstrap resamples.
        periods: Trading days per year.
        rng: Random generator.

    Returns:
        Dict mapping metric name → BootstrapResult.
    """
    arr = np.asarray(daily_returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        empty_ci = BootstrapCI(0.0, 0.0, 0.0, 0.0)
        empty_br = BootstrapResult(empty_ci, empty_ci, empty_ci, 0.0, 0)
        return {
            "sharpe": empty_br, "sortino": empty_br,
            "profit_factor": empty_br, "max_drawdown": empty_br,
        }

    def _sharpe(x: np.ndarray) -> float:
        if len(x) < 2 or x.std(ddof=1) == 0:
            return 0.0
        return float(x.mean() / x.std(ddof=1) * np.sqrt(periods))

    def _sortino(x: np.ndarray) -> float:
        if len(x) < 2:
            return 0.0
        downside = x[x < 0]
        if len(downside) == 0 or downside.std(ddof=1) == 0:
            return 0.0
        return float(x.mean() / downside.std(ddof=1) * np.sqrt(periods))

    def _profit_factor(x: np.ndarray) -> float:
        gains = x[x > 0].sum()
        losses_abs = abs(x[x < 0].sum())
        if losses_abs == 0:
            return float("inf") if gains > 0 else 0.0
        return float(gains / losses_abs)

    def _max_dd(x: np.ndarray) -> float:
        if len(x) == 0:
            return 0.0
        cumulative = np.cumprod(1 + x)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())

    return {
        "sharpe": bca_bootstrap(arr, _sharpe, n_boot=n_boot, rng=rng),
        "sortino": bca_bootstrap(arr, _sortino, n_boot=n_boot, rng=rng),
        "profit_factor": bca_bootstrap(arr, _profit_factor, n_boot=n_boot, rng=rng),
        "max_drawdown": bca_bootstrap(arr, _max_dd, n_boot=n_boot, rng=rng),
    }


# ---------------------------------------------------------------------------
# MAE / MFE (Max Adverse / Favorable Excursion)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeExcursion:
    """MAE/MFE for a single trade.

    Attributes:
        mae: Max adverse excursion (worst drawdown from entry, always >= 0).
        mfe: Max favorable excursion (best paper profit from entry, always >= 0).
        mae_pct: MAE as percentage of entry price.
        mfe_pct: MFE as percentage of entry price.
    """

    mae: float
    mfe: float
    mae_pct: float
    mfe_pct: float


@dataclass(frozen=True)
class MAEMFESummary:
    """Aggregate MAE/MFE statistics across trades.

    Attributes:
        avg_mae: Average MAE across trades.
        avg_mfe: Average MFE across trades.
        avg_mae_pct: Average MAE %.
        avg_mfe_pct: Average MFE %.
        mfe_mae_ratio: Ratio of avg MFE to avg MAE (>2 = good entries).
        edge_ratio: (avg_mfe - avg_mae) / avg_mae — positive = entries have edge.
        trades: Per-trade excursion details.
    """

    avg_mae: float
    avg_mfe: float
    avg_mae_pct: float
    avg_mfe_pct: float
    mfe_mae_ratio: float
    edge_ratio: float
    trades: tuple[TradeExcursion, ...]


def compute_mae_mfe(
    trades: list[dict],
    price_history: pd.DataFrame | None = None,
) -> MAEMFESummary:
    """Compute MAE/MFE for each trade.

    Each trade dict must have:
        - entry_price: float
        - direction: "long" or "short"
        - high_prices: list[float] — high prices during the trade
        - low_prices: list[float] — low prices during the trade

    If price_history is provided and trades have entry_bar/exit_bar,
    the high/low prices are extracted automatically.

    Args:
        trades: List of trade dicts.
        price_history: Optional DataFrame with 'high', 'low' columns.

    Returns:
        MAEMFESummary with per-trade and aggregate excursions.
    """
    if not trades:
        return MAEMFESummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ())

    excursions: list[TradeExcursion] = []

    for trade in trades:
        entry_price = float(trade.get("entry_price", 0.0))
        direction = trade.get("direction", "long")

        if entry_price <= 0:
            excursions.append(TradeExcursion(0.0, 0.0, 0.0, 0.0))
            continue

        # Get high/low arrays for the trade duration
        if price_history is not None and "entry_bar" in trade and "exit_bar" in trade:
            start = int(trade["entry_bar"])
            end = int(trade["exit_bar"]) + 1
            highs = price_history["high"].iloc[start:end].values.astype(float)
            lows = price_history["low"].iloc[start:end].values.astype(float)
        else:
            highs = np.array(trade.get("high_prices", [entry_price]), dtype=float)
            lows = np.array(trade.get("low_prices", [entry_price]), dtype=float)

        if len(highs) == 0 or len(lows) == 0:
            excursions.append(TradeExcursion(0.0, 0.0, 0.0, 0.0))
            continue

        if direction == "long":
            # Long: MAE = entry - min(low), MFE = max(high) - entry
            mae = max(entry_price - float(lows.min()), 0.0)
            mfe = max(float(highs.max()) - entry_price, 0.0)
        else:
            # Short: MAE = max(high) - entry, MFE = entry - min(low)
            mae = max(float(highs.max()) - entry_price, 0.0)
            mfe = max(entry_price - float(lows.min()), 0.0)

        mae_pct = (mae / entry_price) * 100
        mfe_pct = (mfe / entry_price) * 100
        excursions.append(TradeExcursion(mae, mfe, mae_pct, mfe_pct))

    if not excursions:
        return MAEMFESummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ())

    avg_mae = float(np.mean([e.mae for e in excursions]))
    avg_mfe = float(np.mean([e.mfe for e in excursions]))
    avg_mae_pct = float(np.mean([e.mae_pct for e in excursions]))
    avg_mfe_pct = float(np.mean([e.mfe_pct for e in excursions]))
    if avg_mae > 0:
        mfe_mae_ratio = avg_mfe / avg_mae
    elif avg_mfe > 0:
        mfe_mae_ratio = float("inf")
    else:
        mfe_mae_ratio = 0.0
    edge_ratio = (avg_mfe - avg_mae) / avg_mae if avg_mae > 0 else 0.0

    return MAEMFESummary(
        avg_mae=avg_mae,
        avg_mfe=avg_mfe,
        avg_mae_pct=avg_mae_pct,
        avg_mfe_pct=avg_mfe_pct,
        mfe_mae_ratio=mfe_mae_ratio,
        edge_ratio=edge_ratio,
        trades=tuple(excursions),
    )


# ---------------------------------------------------------------------------
# Equity R², Relative Entropy, Ulcer Performance Index
# ---------------------------------------------------------------------------


def equity_r_squared(equity_curve: Sequence[float] | np.ndarray) -> float:
    """R² of linear regression on equity curve.

    1.0 = perfectly linear equity growth (ideal).
    0.0 = no trend.
    Negative = equity curve worse than flat line.

    Useful for screening: strategies with R² > 0.9 have consistent growth.
    """
    equity = np.asarray(equity_curve, dtype=np.float64)
    n = len(equity)
    if n < 3:
        return 0.0
    x = np.arange(n, dtype=np.float64)
    ss_tot = np.sum((equity - equity.mean()) ** 2)
    if ss_tot == 0:
        return 0.0
    # Linear regression: y = a + b*x
    x_mean = x.mean()
    b = np.sum((x - x_mean) * (equity - equity.mean())) / np.sum((x - x_mean) ** 2)
    a = equity.mean() - b * x_mean
    fitted = a + b * x
    ss_res = np.sum((equity - fitted) ** 2)
    return float(1.0 - ss_res / ss_tot)


def relative_entropy(returns: np.ndarray | pd.Series, n_bins: int = 20) -> float:
    """Normalized Shannon entropy of return distribution.

    Range [0, 1]: 0 = all returns in one bin (concentrated), 1 = uniform.
    High entropy = diverse, unpredictable returns.
    Low entropy = clustered, predictable returns.

    Args:
        returns: Array of returns.
        n_bins: Number of histogram bins.
    """
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2 or n_bins < 2:
        return 0.0
    counts, _ = np.histogram(arr, bins=n_bins)
    total = counts.sum()
    if total == 0:
        return 0.0
    probs = counts / total
    probs = probs[probs > 0]
    entropy = -np.sum(probs * np.log(probs))
    max_entropy = np.log(n_bins)
    if max_entropy == 0:
        return 0.0
    return float(entropy / max_entropy)


def ulcer_performance_index(
    equity_curve: Sequence[float] | np.ndarray,
    periods: int = MOEX_TRADING_DAYS,
) -> float:
    """Ulcer Performance Index — risk-adjusted return using Ulcer Index.

    UPI = annualized_return / ulcer_index

    Better than Sharpe for strategies with rare deep drawdowns because
    Ulcer Index penalizes duration AND depth of drawdowns, not just
    return volatility.

    Args:
        equity_curve: Daily portfolio equity values.
        periods: Trading days per year.

    Returns:
        UPI value. Higher is better.
    """
    equity = np.asarray(equity_curve, dtype=np.float64)
    n = len(equity)
    if n < 3 or equity[0] <= 0:
        return 0.0

    # Annualized return
    total_return = equity[-1] / equity[0]
    if total_return <= 0:
        return 0.0
    years = n / periods
    if years <= 0:
        return 0.0
    ann_return = total_return ** (1.0 / years) - 1.0

    # Ulcer Index
    running_max = np.maximum.accumulate(equity)
    pct_drawdown = ((equity - running_max) / running_max) * 100
    ulcer = float(np.sqrt(np.mean(pct_drawdown ** 2)))

    if ulcer == 0:
        return float("inf") if ann_return > 0 else 0.0
    return float(ann_return / (ulcer / 100))


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
# CAPM & system quality metrics (inspired by backtesting.py — written from scratch)
# ---------------------------------------------------------------------------


def alpha_beta(
    equity_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> tuple[float, float]:
    """Jensen Alpha and Beta from CAPM model.

    Alpha = R_portfolio - Rf - Beta * (R_market - Rf)
    Beta = Cov(R_p, R_m) / Var(R_m)

    Args:
        equity_returns: Daily portfolio returns.
        benchmark_returns: Daily benchmark (e.g. IMOEX) returns.
        risk_free_rate: Annual risk-free rate.

    Returns:
        (alpha, beta) tuple. Alpha is total (not annualized).
    """
    if len(equity_returns) < 2 or len(benchmark_returns) < 2:
        return 0.0, 0.0

    # Align lengths
    n = min(len(equity_returns), len(benchmark_returns))
    eq = equity_returns.values[-n:]
    bm = benchmark_returns.values[-n:]

    # Convert to log returns for proper CAPM
    eq_log = np.log1p(eq)
    bm_log = np.log1p(bm)

    if len(eq_log) < 2:
        return 0.0, 0.0

    cov_matrix = np.cov(eq_log, bm_log)
    var_market = cov_matrix[1, 1]
    beta = float(cov_matrix[0, 1] / var_market) if var_market > 0 else 0.0

    total_eq_return = float(np.expm1(eq_log.sum()))
    total_bm_return = float(np.expm1(bm_log.sum()))

    alpha = total_eq_return - risk_free_rate - beta * (total_bm_return - risk_free_rate)
    return float(alpha), float(beta)


def sqn(pnls: np.ndarray) -> float:
    """System Quality Number — measures trading system quality.

    SQN = sqrt(N) * mean(PnL) / std(PnL)
    Interpretation: < 1.6 poor, 1.6-2.0 below avg, 2.0-2.5 avg,
                    2.5-3.0 good, 3.0-5.0 excellent, 5.0-7.0 superb, > 7.0 holy grail
    """
    if len(pnls) < 2:
        return 0.0
    std = float(np.std(pnls, ddof=1))
    if std == 0:
        return 0.0
    return float(np.sqrt(len(pnls)) * np.mean(pnls) / std)


def kelly_criterion(win_rate: float, avg_win_loss_ratio: float) -> float:
    """Kelly Criterion — optimal fraction of capital to risk per trade.

    Kelly = W - (1-W) / R
    where W = win rate, R = avg_win / avg_loss

    Returns value in [0, 1]. Negative means don't trade.
    """
    if avg_win_loss_ratio <= 0:
        return 0.0
    k = win_rate - (1 - win_rate) / avg_win_loss_ratio
    return max(0.0, float(k))


def geometric_mean(returns: np.ndarray) -> float:
    """Geometric mean of returns — correct compounding measure.

    More accurate than arithmetic mean for multiplicative returns.
    """
    if len(returns) == 0:
        return 0.0
    returns_plus_one = returns + 1.0
    if np.any(returns_plus_one <= 0):
        return 0.0
    return float(np.exp(np.log(returns_plus_one).mean()) - 1)


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

    # CAPM
    alpha: float = 0.0          # Jensen Alpha (excess return over CAPM)
    beta: float = 0.0           # market sensitivity

    # System quality
    sqn: float = 0.0            # System Quality Number
    kelly_criterion: float = 0.0  # optimal position fraction
    geometric_mean_return: float = 0.0  # per-trade geometric mean

    # Exposure
    exposure_time_pct: float = 0.0   # % of bars with open position
    buy_and_hold_return: float = 0.0  # passive B&H return for comparison

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

    # MAE/MFE (trade quality)
    avg_mae: float = 0.0           # avg max adverse excursion (RUB)
    avg_mfe: float = 0.0           # avg max favorable excursion (RUB)
    avg_mae_pct: float = 0.0       # avg MAE as % of entry
    avg_mfe_pct: float = 0.0       # avg MFE as % of entry
    mfe_mae_ratio: float = 0.0     # MFE/MAE ratio (>2 = good entries)

    # Equity quality
    equity_r2: float = 0.0         # R² of equity curve (1.0 = perfect)
    return_entropy: float = 0.0    # normalized Shannon entropy of returns
    ulcer_perf_index: float = 0.0  # UPI = ann_return / ulcer_index


def calculate_trade_metrics(
    trades: list[dict],
    daily_balance: list[float],
    starting_balance: float,
    risk_free_rate: float = CBR_KEY_RATE,
    periods: int = MOEX_TRADING_DAYS,
    start_date: str | None = None,
    benchmark_balance: list[float] | None = None,
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
        benchmark_balance: Optional daily benchmark equity (e.g. IMOEX) for Alpha/Beta.

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

    # Alpha / Beta (CAPM) — requires benchmark
    if benchmark_balance and len(benchmark_balance) >= len(daily_balance):
        bm_series = pd.Series(benchmark_balance[:len(daily_balance)], index=date_index)
        bm_ret = bm_series.pct_change(1).dropna()
        if len(bm_ret) >= 2 and len(daily_ret) >= 2:
            m.alpha, m.beta = alpha_beta(daily_ret, bm_ret, risk_free_rate)

    # System quality (from PnLs)
    m.sqn = sqn(pnls)
    m.kelly_criterion = kelly_criterion(m.win_rate, m.avg_win_loss_ratio)

    # Geometric mean of per-trade returns (% of starting balance)
    trade_returns = pnls / starting_balance if starting_balance > 0 else pnls
    m.geometric_mean_return = geometric_mean(trade_returns)

    # Buy & Hold return (first balance → last balance without trading)
    m.buy_and_hold_return = m.total_return * 100  # same as total_return in pct

    # Equity quality metrics
    equity_arr = np.array(daily_balance, dtype=float)
    m.equity_r2 = equity_r_squared(equity_arr)
    m.return_entropy = relative_entropy(daily_ret.values)
    m.ulcer_perf_index = ulcer_performance_index(equity_arr, periods=periods)

    # MAE/MFE (if trades provide entry_price and high/low prices)
    has_excursion_data = any(
        "entry_price" in t and ("high_prices" in t or "entry_bar" in t)
        for t in trades
    )
    if has_excursion_data:
        mae_mfe = compute_mae_mfe(trades)
        m.avg_mae = mae_mfe.avg_mae
        m.avg_mfe = mae_mfe.avg_mfe
        m.avg_mae_pct = mae_mfe.avg_mae_pct
        m.avg_mfe_pct = mae_mfe.avg_mfe_pct
        m.mfe_mae_ratio = mae_mfe.mfe_mae_ratio

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
        "  CAPM & SYSTEM QUALITY",
        "-" * 64,
        f"  Alpha (Jensen)     : {m.alpha:>+.3f}",
        f"  Beta               : {m.beta:>.3f}",
        f"  SQN                : {m.sqn:>.3f}",
        f"  Kelly Criterion    : {m.kelly_criterion:>.3f}",
        f"  Geo. Mean Return   : {m.geometric_mean_return:>+.4f}",
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

    # Equity quality
    lines += [
        "-" * 64,
        "  EQUITY QUALITY",
        "-" * 64,
        f"  Equity R²          : {m.equity_r2:>.4f}",
        f"  Return Entropy     : {m.return_entropy:>.4f}",
        f"  Ulcer Perf. Index  : {m.ulcer_perf_index:>.3f}",
    ]

    # MAE/MFE (if available)
    if m.avg_mae > 0 or m.avg_mfe > 0:
        lines += [
            "-" * 64,
            "  TRADE QUALITY (MAE/MFE)",
            "-" * 64,
            f"  Avg MAE            : {m.avg_mae:>,.0f} RUB ({m.avg_mae_pct:>.2f}%)",
            f"  Avg MFE            : {m.avg_mfe:>,.0f} RUB ({m.avg_mfe_pct:>.2f}%)",
            f"  MFE/MAE Ratio      : {m.mfe_mae_ratio:>.3f}",
        ]

    lines.append("=" * 64)
    return "\n".join(lines)
