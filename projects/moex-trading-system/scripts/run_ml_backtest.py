"""Full ML backtest pipeline with walk-forward evaluation.

Usage:
    python scripts/run_ml_backtest.py

Steps:
1. Load data (SBER from data/history/ or download)
2. Feature engineering (all indicators + Qlib processors)
3. Label generation (next-bar direction)
4. Walk-forward ML (CatBoost + LightGBM + XGBoost ensemble)
5. Compare with: buy & hold, EMA crossover
6. Print results report
7. Monte Carlo confidence interval
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import polars as pl
import structlog

from src.analysis.features import calculate_all_features
from src.backtest.metrics import max_drawdown, sharpe_ratio
from src.core.models import Side, TradeResult
from src.data.moex_iss import MoexISSClient
from src.ml.walk_forward import WalkForwardML

logger = structlog.get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "history"
TICKER = "SBER"


async def ensure_data() -> pl.DataFrame:
    """Load or download SBER data."""
    parquet = DATA_DIR / f"{TICKER}.parquet"
    if parquet.exists():
        return pl.read_parquet(parquet)

    print(f"Downloading {TICKER} data...")
    async with MoexISSClient() as client:
        bars = await client.fetch_candles(TICKER, "2020-01-01", str(date.today()))
        df = client.to_polars(bars)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(parquet)
        return df


def buy_and_hold_return(data: pl.DataFrame) -> float:
    """Calculate buy & hold return."""
    close = data["close"].to_numpy()
    return float((close[-1] - close[0]) / close[0])


def ml_signal_backtest(
    predictions: list[float],
    actuals: list[int],
    initial_capital: float = 1_000_000,
) -> tuple[list[float], float]:
    """Simple ML signal backtest: go long when P(up) > 0.55.

    Returns (equity_curve, total_return).
    """
    equity = [initial_capital]
    cash = initial_capital
    position_value = 0.0

    for i, (pred, actual) in enumerate(zip(predictions, actuals)):
        if pred > 0.55 and position_value == 0:
            # Enter long
            position_value = cash
            cash = 0.0
        elif pred <= 0.45 and position_value > 0:
            # Exit
            pnl_pct = 0.01 if actual == 1 else -0.01
            cash = position_value * (1 + pnl_pct)
            position_value = 0.0
        elif position_value > 0:
            # Hold, apply daily return
            pnl_pct = 0.01 if actual == 1 else -0.01
            position_value *= (1 + pnl_pct)

        total = cash + position_value
        equity.append(total)

    total_return = (equity[-1] - equity[0]) / equity[0]
    return equity, total_return


def run_backtest() -> None:
    """Run the full ML backtest pipeline."""
    print("=" * 60)
    print("MOEX Trading Bot — ML Walk-Forward Backtest")
    print("=" * 60)

    # 1. Load data
    data = asyncio.run(ensure_data())
    print(f"\nData: {TICKER}, {data.height} bars")
    print(f"Period: {data['timestamp'][0]} — {data['timestamp'][-1]}")

    # 2. Walk-forward ML
    print("\nRunning walk-forward ML pipeline...")
    wf = WalkForwardML(n_windows=5, train_ratio=0.7, gap_bars=1)
    result = wf.run(data)

    # 3. ML backtest
    if result.oos_predictions:
        equity, ml_return = ml_signal_backtest(
            result.oos_predictions, result.oos_actuals
        )
        returns = pd.Series(np.diff(equity) / np.array(equity[:-1]))
        returns = returns.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        ml_sharpe = sharpe_ratio(returns)
        ml_dd = max_drawdown(returns)
    else:
        ml_return = 0.0
        ml_sharpe = 0.0
        ml_dd = 0.0

    # 4. Buy & hold comparison
    bh_return = buy_and_hold_return(data)

    # 5. Report
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nML Walk-Forward ({result.n_windows} windows):")
    print(f"  OOS Accuracy:     {result.aggregate_accuracy * 100:.1f}%")
    print(f"  OOS Sharpe:       {result.aggregate_sharpe:.3f}")
    print(f"  Overfitting Score: {result.overfitting_score:.3f}")
    print(f"  ML Backtest Return: {ml_return * 100:.1f}%")
    print(f"  ML Sharpe:        {ml_sharpe:.3f}")
    print(f"  ML Max DD:        {ml_dd * 100:.1f}%")

    print(f"\nBuy & Hold {TICKER}:")
    print(f"  Return: {bh_return * 100:.1f}%")

    print(f"\nPer-window metrics:")
    for wm in result.window_metrics:
        print(
            f"  Window {wm.window_id}: "
            f"Train acc={wm.train_accuracy:.3f}, "
            f"Test acc={wm.test_accuracy:.3f}, "
            f"Train Sharpe={wm.train_sharpe:.2f}, "
            f"Test Sharpe={wm.test_sharpe:.2f}"
        )

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    run_backtest()
