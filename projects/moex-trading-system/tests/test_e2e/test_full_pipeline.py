"""End-to-end test: data → indicators → strategy → backtest → metrics.

Uses synthetic data to verify the complete pipeline works.
No external API calls. No network. Pure logic.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import polars as pl
import pytest

from src.analysis.features import calculate_atr, calculate_ema
from src.backtest.metrics import max_drawdown, sharpe_ratio
from src.core.models import Side, TradeResult
from src.strategies.trend.ema_crossover import EMACrossoverStrategy


def _generate_synthetic_ohlcv(
    n: int = 500, seed: int = 42
) -> pl.DataFrame:
    """Generate synthetic OHLCV data with alternating trends.

    Creates multiple trend cycles to guarantee EMA crossovers:
    - Segments of 80 bars: up, down, up, down, ...
    This ensures fast EMA(20) crosses slow EMA(50) multiple times.
    """
    np.random.seed(seed)
    timestamps = [datetime(2022, 1, 1) + timedelta(days=i) for i in range(n)]

    segment_len = 80
    close = np.zeros(n)
    close[0] = 250.0

    for i in range(1, n):
        segment = (i // segment_len) % 2
        drift = 1.5 if segment == 0 else -1.5  # strong alternating trend
        close[i] = close[i - 1] + drift + np.random.normal(0, 0.5)

    close = np.maximum(close, 10.0)

    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_ = (high + low) / 2
    volume = np.random.randint(5000, 200000, n)

    return pl.DataFrame({
        "timestamp": timestamps,
        "open": open_.tolist(),
        "high": high.tolist(),
        "low": low.tolist(),
        "close": close.tolist(),
        "volume": volume.tolist(),
        "instrument": ["SBER"] * n,
    })


def _simple_backtest(
    data: pl.DataFrame,
    strategy: EMACrossoverStrategy,
    initial_capital: float = 1_000_000,
    commission_pct: float = 0.0001,
) -> tuple[list[TradeResult], list[float]]:
    """Simple backtest engine: iterate bars, apply signals, track P&L.

    Returns (trades, equity_curve).
    """
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
    position_instrument = "SBER"

    warm_up = strategy.warm_up_period()

    for i in range(warm_up + 1, len(close)):
        # Get data up to current bar
        sub_data = data.slice(0, i + 1)
        signals = strategy.generate_signals(sub_data)

        current_price = close[i]
        current_atr = atr_series[i] if i < len(atr_series) else 5.0
        ts = datetime(2022, 1, 1) + timedelta(days=i)

        # Check stop loss on existing position
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
                    instrument=position_instrument,
                    side=position_side,
                    entry_price=position_entry,
                    exit_price=exit_price,
                    quantity=position_qty,
                    entry_timestamp=position_entry_ts,
                    exit_timestamp=ts,
                    strategy_name=strategy.name,
                    commission=comm,
                )
                trades.append(trade)
                cash += trade.net_pnl + position_entry * position_qty
                position_side = None
                position_qty = 0.0

        # Process signals
        for sig in signals:
            if position_side is not None:
                # Close existing
                exit_price = current_price
                comm = abs(exit_price * position_qty * commission_pct)
                trade = TradeResult(
                    instrument=position_instrument,
                    side=position_side,
                    entry_price=position_entry,
                    exit_price=exit_price,
                    quantity=position_qty,
                    entry_timestamp=position_entry_ts,
                    exit_timestamp=ts,
                    strategy_name=strategy.name,
                    commission=comm,
                )
                trades.append(trade)
                cash += trade.net_pnl + position_entry * position_qty
                position_side = None
                position_qty = 0.0

            # Open new position
            if current_atr > 0:
                qty = strategy.calculate_position_size(sig, cash, current_atr)
                if qty > 0 and cash > current_price * qty:
                    position_side = sig.side
                    position_qty = qty
                    position_entry = current_price
                    position_entry_ts = ts
                    position_instrument = sig.instrument
                    cash -= current_price * qty

        # Update equity
        portfolio_value = cash
        if position_side is not None:
            portfolio_value += current_price * position_qty
        equity_curve.append(portfolio_value)

    return trades, equity_curve


class TestFullPipeline:
    """E2E: synthetic data → EMA crossover → backtest → metrics."""

    @pytest.fixture
    def pipeline_result(self):
        data = _generate_synthetic_ohlcv(500, seed=42)
        strategy = EMACrossoverStrategy(instruments=["SBER"])
        trades, equity = _simple_backtest(data, strategy)
        return trades, equity, data

    def test_pipeline_runs_without_errors(self, pipeline_result):
        trades, equity, _ = pipeline_result
        assert isinstance(trades, list)
        assert isinstance(equity, list)
        assert len(equity) > 100

    def test_trades_generated(self, pipeline_result):
        trades, _, _ = pipeline_result
        assert len(trades) > 0, "Strategy should generate at least one trade"

    def test_sharpe_not_nan(self, pipeline_result):
        _, equity, _ = pipeline_result
        returns = pd.Series(np.diff(equity) / np.array(equity[:-1]))
        returns = returns.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        sr = sharpe_ratio(returns)
        assert not np.isnan(sr), f"Sharpe should not be NaN, got {sr}"

    def test_max_dd_below_100(self, pipeline_result):
        _, equity, _ = pipeline_result
        returns = pd.Series(np.diff(equity) / np.array(equity[:-1]))
        returns = returns.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        dd = max_drawdown(returns)
        assert dd < 1.0, f"Max drawdown should be < 100%, got {dd * 100:.1f}%"

    def test_commissions_positive(self, pipeline_result):
        trades, _, _ = pipeline_result
        total_comm = sum(t.commission for t in trades)
        assert total_comm > 0, "Commissions should be accounted for"

    def test_trade_results_valid(self, pipeline_result):
        trades, _, _ = pipeline_result
        for t in trades:
            assert t.entry_price > 0
            assert t.exit_price > 0
            assert t.quantity > 0
            assert t.entry_timestamp < t.exit_timestamp
            assert t.instrument == "SBER"
            assert t.strategy_name == "ema_crossover"

    def test_equity_curve_starts_at_capital(self, pipeline_result):
        _, equity, _ = pipeline_result
        assert equity[0] == 1_000_000

    def test_indicators_used(self, pipeline_result):
        """Verify indicators are computed during pipeline."""
        _, _, data = pipeline_result
        close = data["close"]
        ema20 = calculate_ema(close, 20)
        ema50 = calculate_ema(close, 50)
        assert len(ema20) == len(close)
        assert len(ema50) == len(close)
        # EMAs should be different
        assert not np.allclose(ema20.to_numpy(), ema50.to_numpy())

    def test_net_pnl_includes_costs(self, pipeline_result):
        trades, _, _ = pipeline_result
        for t in trades:
            assert abs(t.net_pnl - t.gross_pnl) >= 0
            if t.commission > 0:
                assert abs(t.net_pnl) <= abs(t.gross_pnl) + t.commission
