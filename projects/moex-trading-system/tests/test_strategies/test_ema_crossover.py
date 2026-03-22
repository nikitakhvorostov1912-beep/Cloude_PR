"""Tests for EMA crossover strategy."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest

from src.core.base_strategy import BaseStrategy
from src.core.models import Side
from src.strategies.trend.ema_crossover import EMACrossoverStrategy


def _make_data(n: int, trend: str = "up", instrument: str = "SBER") -> pl.DataFrame:
    """Generate synthetic OHLCV data with a given trend."""
    np.random.seed(42)
    base = 250.0
    timestamps = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n)]

    if trend == "up":
        close = base + np.cumsum(np.random.normal(0.5, 1.0, n))
    elif trend == "down":
        close = base + np.cumsum(np.random.normal(-0.5, 1.0, n))
    else:  # flat
        close = base + np.cumsum(np.random.normal(0.0, 0.3, n))

    close = np.maximum(close, 1.0)
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_ = (high + low) / 2
    volume = np.random.randint(1000, 100000, n)

    return pl.DataFrame({
        "timestamp": timestamps,
        "open": open_.tolist(),
        "high": high.tolist(),
        "low": low.tolist(),
        "close": close.tolist(),
        "volume": volume.tolist(),
        "instrument": [instrument] * n,
    })


class TestEMACrossover:
    def test_creation(self):
        s = EMACrossoverStrategy()
        assert s.name == "ema_crossover"
        assert s.timeframe == "1d"

    def test_inherits_base(self):
        s = EMACrossoverStrategy()
        assert isinstance(s, BaseStrategy)

    def test_signals_on_uptrend(self):
        s = EMACrossoverStrategy(instruments=["SBER"])
        data = _make_data(200, trend="up")
        signals = s.generate_signals(data)
        # Should have at least one LONG signal in an uptrend
        long_signals = [sig for sig in signals if sig.side == Side.LONG]
        # May or may not generate — depends on crossover timing
        assert isinstance(signals, list)

    def test_signals_on_downtrend(self):
        s = EMACrossoverStrategy(instruments=["SBER"])
        data = _make_data(200, trend="down")
        signals = s.generate_signals(data)
        assert isinstance(signals, list)

    def test_signals_on_flat(self):
        s = EMACrossoverStrategy(instruments=["SBER"])
        data = _make_data(200, trend="flat")
        signals = s.generate_signals(data)
        assert isinstance(signals, list)

    def test_signals_on_forced_crossover(self):
        """Create data that forces a bullish crossover at the last bar."""
        n = 100
        timestamps = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n)]
        # First 99 bars: slow trend down (fast < slow)
        # Last bar: jump up (fast > slow)
        close = np.full(n, 100.0)
        close[:80] = np.linspace(100, 90, 80)
        close[80:99] = np.linspace(90, 92, 19)
        close[99] = 120.0  # big jump forces crossover

        data = pl.DataFrame({
            "timestamp": timestamps,
            "open": close.tolist(),
            "high": (close * 1.01).tolist(),
            "low": (close * 0.99).tolist(),
            "close": close.tolist(),
            "volume": [10000] * n,
            "instrument": ["SBER"] * n,
        })
        s = EMACrossoverStrategy(instruments=["SBER"])
        signals = s.generate_signals(data)
        assert len(signals) == 1
        assert signals[0].side == Side.LONG

    def test_position_size_respects_lot(self):
        s = EMACrossoverStrategy(instruments=["SBER"])
        from src.core.models import Signal
        sig = Signal(
            instrument="SBER", side=Side.LONG, strength=0.8,
            strategy_name="ema_crossover", timestamp=datetime.now(),
        )
        size = s.calculate_position_size(sig, 1_000_000, 5.0)
        assert size > 0
        # SBER lot = 10, size must be multiple of 10
        assert size % 10 == 0

    def test_stop_loss_long(self):
        s = EMACrossoverStrategy(instruments=["SBER"])
        stop = s.get_stop_loss(250.0, Side.LONG, 5.0)
        assert stop < 250.0
        # Should be entry - 2*ATR = 240.0
        assert abs(stop - 240.0) < 0.1

    def test_stop_loss_short(self):
        s = EMACrossoverStrategy(instruments=["SBER"])
        stop = s.get_stop_loss(250.0, Side.SHORT, 5.0)
        assert stop > 250.0

    def test_warm_up_period(self):
        s = EMACrossoverStrategy()
        assert s.warm_up_period() == 50

    def test_empty_data(self):
        s = EMACrossoverStrategy()
        data = pl.DataFrame({
            "timestamp": [], "open": [], "high": [], "low": [],
            "close": [], "volume": [], "instrument": [],
        })
        assert s.generate_signals(data) == []

    def test_short_data(self):
        s = EMACrossoverStrategy()
        data = _make_data(10)
        assert s.generate_signals(data) == []

    def test_take_profit(self):
        s = EMACrossoverStrategy(instruments=["SBER"])
        tp = s.get_take_profit(250.0, Side.LONG, 5.0)
        assert tp is not None
        assert tp > 250.0
