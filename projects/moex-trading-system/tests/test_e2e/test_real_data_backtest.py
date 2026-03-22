"""Backtest on real SBER data (2023-2024).

Requires data/history/SBER.parquet to exist.
Run scripts/download_history.py first if not present.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import pytest

from src.analysis.features import calculate_atr, calculate_ema
from src.backtest.metrics import max_drawdown, sharpe_ratio
from src.core.models import Side, TradeResult
from src.strategies.trend.ema_crossover import EMACrossoverStrategy

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "history" / "SBER.parquet"
data_exists = DATA_FILE.exists()


def _backtest_on_data(
    data: pl.DataFrame,
    strategy: EMACrossoverStrategy,
    initial_capital: float = 1_000_000,
    commission_pct: float = 0.0001,
) -> tuple[list[TradeResult], list[float]]:
    """Simple backtest engine for real data."""
    close = data["close"].to_numpy()
    high = data["high"].to_numpy()
    low = data["low"].to_numpy()

    atr_series = calculate_atr(
        pl.Series("high", high), pl.Series("low", low), pl.Series("close", close)
    ).to_numpy()

    trades: list[TradeResult] = []
    equity_curve: list[float] = [initial_capital]

    cash = initial_capital
    position_side: Side | None = None
    position_qty = 0.0
    position_entry = 0.0
    position_entry_ts = datetime.now()

    warm_up = strategy.warm_up_period()

    timestamps = data["timestamp"].to_list()

    for i in range(warm_up + 1, len(close)):
        sub_data = data.slice(0, i + 1)
        signals = strategy.generate_signals(sub_data)

        current_price = close[i]
        current_atr = atr_series[i] if i < len(atr_series) else 5.0
        ts = timestamps[i]
        if not isinstance(ts, datetime):
            ts = datetime.now()

        # Check stop loss
        if position_side is not None and current_atr > 0:
            stop = strategy.get_stop_loss(position_entry, position_side, current_atr)
            hit_stop = (
                (position_side == Side.LONG and low[i] <= stop) or
                (position_side == Side.SHORT and high[i] >= stop)
            )
            if hit_stop:
                exit_price = stop
                comm = abs(exit_price * position_qty * commission_pct)
                trade = TradeResult(
                    instrument="SBER", side=position_side,
                    entry_price=position_entry, exit_price=exit_price,
                    quantity=position_qty,
                    entry_timestamp=position_entry_ts, exit_timestamp=ts,
                    strategy_name=strategy.name, commission=comm,
                )
                trades.append(trade)
                cash += trade.net_pnl + position_entry * position_qty
                position_side = None
                position_qty = 0.0

        for sig in signals:
            if position_side is not None:
                exit_price = current_price
                comm = abs(exit_price * position_qty * commission_pct)
                trade = TradeResult(
                    instrument="SBER", side=position_side,
                    entry_price=position_entry, exit_price=exit_price,
                    quantity=position_qty,
                    entry_timestamp=position_entry_ts, exit_timestamp=ts,
                    strategy_name=strategy.name, commission=comm,
                )
                trades.append(trade)
                cash += trade.net_pnl + position_entry * position_qty
                position_side = None
                position_qty = 0.0

            if current_atr > 0:
                qty = strategy.calculate_position_size(sig, cash, current_atr)
                if qty > 0 and cash > current_price * qty:
                    position_side = sig.side
                    position_qty = qty
                    position_entry = current_price
                    position_entry_ts = ts
                    cash -= current_price * qty

        portfolio_value = cash
        if position_side is not None:
            portfolio_value += current_price * position_qty
        equity_curve.append(portfolio_value)

    return trades, equity_curve


@pytest.mark.skipif(not data_exists, reason="SBER.parquet not found, run download_history.py first")
class TestRealDataBacktest:
    @pytest.fixture(scope="class")
    def backtest_result(self):
        data = pl.read_parquet(DATA_FILE)
        strategy = EMACrossoverStrategy(instruments=["SBER"])
        trades, equity = _backtest_on_data(data, strategy)
        return trades, equity, data

    def test_data_loaded(self, backtest_result):
        _, _, data = backtest_result
        assert data.height > 100

    def test_trades_generated(self, backtest_result):
        trades, _, _ = backtest_result
        assert len(trades) > 0

    def test_sharpe_not_nan(self, backtest_result):
        _, equity, _ = backtest_result
        returns = pd.Series(np.diff(equity) / np.array(equity[:-1]))
        returns = returns.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        sr = sharpe_ratio(returns)
        assert not np.isnan(sr)

    def test_max_dd_below_50(self, backtest_result):
        _, equity, _ = backtest_result
        returns = pd.Series(np.diff(equity) / np.array(equity[:-1]))
        returns = returns.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        dd = max_drawdown(returns)
        assert dd < 0.5, f"Max DD = {dd * 100:.1f}% — too high"

    def test_buy_and_hold_comparison(self, backtest_result):
        trades, equity, data = backtest_result
        close = data["close"].to_numpy()

        # Buy & hold return
        bh_return = (close[-1] - close[0]) / close[0]

        # Strategy return
        strat_return = (equity[-1] - equity[0]) / equity[0]

        # Just verify both are computed
        print(f"  Buy & Hold SBER: {bh_return * 100:.1f}%")
        print(f"  EMA Crossover:   {strat_return * 100:.1f}%")
        print(f"  Trades: {len(trades)}")

        assert isinstance(bh_return, float)
        assert isinstance(strat_return, float)

    def test_commissions_accounted(self, backtest_result):
        trades, _, _ = backtest_result
        total_comm = sum(t.commission for t in trades)
        assert total_comm > 0
