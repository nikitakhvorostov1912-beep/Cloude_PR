"""VectorBT-based backtesting engine for mass parameter optimization.

1000x faster than event-driven backtesting for grid search.
Complements the walk-forward engine (engine.py) for research.

Public API:
    grid_search_rsi(closes, rsi_periods, entry_thresholds, exit_thresholds)
    grid_search_ema_crossover(closes, fast_periods, slow_periods)
    optimize_pre_score_threshold(closes, signals, thresholds)
"""
from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def grid_search_rsi(
    closes: list[float],
    rsi_periods: list[int] | None = None,
    entry_thresholds: list[float] | None = None,
    exit_thresholds: list[float] | None = None,
    initial_capital: float = 1_000_000,
    commission_pct: float = 0.05,
) -> dict[str, Any]:
    """Grid search RSI strategy parameters using VectorBT.

    Parameters
    ----------
    closes:
        Historical close prices.
    rsi_periods:
        RSI periods to test. Default: [7, 10, 14, 21].
    entry_thresholds:
        RSI values for entry. Default: [25, 30, 35, 40].
    exit_thresholds:
        RSI values for exit. Default: [65, 70, 75, 80].
    initial_capital:
        Starting capital.
    commission_pct:
        Commission as percentage.

    Returns
    -------
    dict with: best_params, best_sharpe, all_results (DataFrame), heatmap_data.
    """
    try:
        import numpy as np
        import pandas as pd
        import vectorbt as vbt
    except ImportError:
        logger.error("vectorbt not installed")
        return {"error": "vectorbt not installed"}

    rsi_periods = rsi_periods or [7, 10, 14, 21]
    entry_thresholds = entry_thresholds or [25, 30, 35, 40]
    exit_thresholds = exit_thresholds or [65, 70, 75, 80]

    close_series = pd.Series(closes, dtype=float)

    results: list[dict[str, Any]] = []
    best_sharpe = -999.0
    best_params: dict[str, Any] = {}

    for period in rsi_periods:
        rsi = vbt.RSI.run(close_series, window=period).rsi

        for entry_th in entry_thresholds:
            for exit_th in exit_thresholds:
                if entry_th >= exit_th:
                    continue

                entries = rsi.vbt.crossed_below(entry_th)
                exits = rsi.vbt.crossed_above(exit_th)

                pf = vbt.Portfolio.from_signals(
                    close_series,
                    entries=entries,
                    exits=exits,
                    init_cash=initial_capital,
                    fees=commission_pct / 100,
                    freq="1D",
                )

                sharpe = float(pf.sharpe_ratio())
                total_return = float(pf.total_return())
                max_dd = float(pf.max_drawdown())
                n_trades = int(pf.trades.count())

                params = {
                    "rsi_period": period,
                    "entry_threshold": entry_th,
                    "exit_threshold": exit_th,
                }

                results.append({
                    **params,
                    "sharpe": round(sharpe, 4),
                    "total_return": round(total_return, 4),
                    "max_drawdown": round(max_dd, 4),
                    "n_trades": n_trades,
                })

                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = params

    logger.info(
        "vbt_grid_search_rsi",
        combinations=len(results),
        best_sharpe=round(best_sharpe, 4),
        best_params=best_params,
    )

    return {
        "best_params": best_params,
        "best_sharpe": round(best_sharpe, 4),
        "all_results": results,
        "total_combinations": len(results),
    }


def grid_search_ema_crossover(
    closes: list[float],
    fast_periods: list[int] | None = None,
    slow_periods: list[int] | None = None,
    initial_capital: float = 1_000_000,
    commission_pct: float = 0.05,
) -> dict[str, Any]:
    """Grid search EMA crossover parameters.

    Parameters
    ----------
    closes:
        Historical close prices.
    fast_periods:
        Fast EMA periods. Default: [5, 10, 15, 20].
    slow_periods:
        Slow EMA periods. Default: [30, 50, 100, 200].

    Returns
    -------
    dict with best_params, best_sharpe, all_results.
    """
    try:
        import pandas as pd
        import vectorbt as vbt
    except ImportError:
        logger.error("vectorbt not installed")
        return {"error": "vectorbt not installed"}

    fast_periods = fast_periods or [5, 10, 15, 20]
    slow_periods = slow_periods or [30, 50, 100, 200]

    close_series = pd.Series(closes, dtype=float)

    results: list[dict[str, Any]] = []
    best_sharpe = -999.0
    best_params: dict[str, Any] = {}

    for fast in fast_periods:
        for slow in slow_periods:
            if fast >= slow:
                continue

            fast_ema = vbt.MA.run(close_series, window=fast, ewm=True).ma
            slow_ema = vbt.MA.run(close_series, window=slow, ewm=True).ma

            entries = fast_ema.vbt.crossed_above(slow_ema)
            exits = fast_ema.vbt.crossed_below(slow_ema)

            pf = vbt.Portfolio.from_signals(
                close_series,
                entries=entries,
                exits=exits,
                init_cash=initial_capital,
                fees=commission_pct / 100,
                freq="1D",
            )

            sharpe = float(pf.sharpe_ratio())
            total_return = float(pf.total_return())
            max_dd = float(pf.max_drawdown())
            n_trades = int(pf.trades.count())

            params = {"fast_ema": fast, "slow_ema": slow}
            results.append({
                **params,
                "sharpe": round(sharpe, 4),
                "total_return": round(total_return, 4),
                "max_drawdown": round(max_dd, 4),
                "n_trades": n_trades,
            })

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params

    logger.info(
        "vbt_grid_search_ema",
        combinations=len(results),
        best_sharpe=round(best_sharpe, 4),
        best_params=best_params,
    )

    return {
        "best_params": best_params,
        "best_sharpe": round(best_sharpe, 4),
        "all_results": results,
        "total_combinations": len(results),
    }
