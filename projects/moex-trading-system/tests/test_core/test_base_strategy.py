"""Tests for src/core/base_strategy.py and strategy_registry.py."""
from __future__ import annotations

from datetime import datetime

import polars as pl
import pytest

from src.core.base_strategy import BaseStrategy
from src.core.models import Side, Signal
from src.core.strategy_registry import StrategyRegistry


class DummyStrategy(BaseStrategy):
    """Concrete test implementation of BaseStrategy."""

    def __init__(self, **kwargs):
        super().__init__(name="dummy", **kwargs)
        self._params = {"fast": 10, "slow": 30}

    def generate_signals(self, data: pl.DataFrame) -> list[Signal]:
        if data.height == 0:
            return []
        return [
            Signal(
                instrument="SBER",
                side=Side.LONG,
                strength=0.7,
                strategy_name=self.name,
                timestamp=datetime.now(),
            )
        ]

    def calculate_position_size(
        self, signal: Signal, portfolio_value: float, atr: float
    ) -> float:
        risk_per_trade = 0.02
        risk_amount = portfolio_value * risk_per_trade
        return max(1.0, risk_amount / (atr * 2))

    def get_stop_loss(self, entry_price: float, side: Side, atr: float) -> float:
        if side == Side.LONG:
            return entry_price - 2 * atr
        return entry_price + 2 * atr

    def warm_up_period(self) -> int:
        return 30


class TestBaseStrategy:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BaseStrategy(name="abstract")  # type: ignore[abstract]

    def test_concrete_strategy(self):
        s = DummyStrategy()
        assert s.name == "dummy"
        assert s.timeframe == "1d"
        assert isinstance(s, BaseStrategy)

    def test_generate_signals_returns_list(self):
        s = DummyStrategy()
        df = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 1)],
            "open": [100.0], "high": [105.0], "low": [99.0],
            "close": [103.0], "volume": [1000],
        })
        signals = s.generate_signals(df)
        assert isinstance(signals, list)
        assert len(signals) == 1
        assert isinstance(signals[0], Signal)

    def test_position_size_positive(self):
        s = DummyStrategy()
        sig = Signal(
            instrument="SBER", side=Side.LONG, strength=0.8,
            strategy_name="dummy", timestamp=datetime.now(),
        )
        size = s.calculate_position_size(sig, 1_000_000, 5.0)
        assert size > 0

    def test_stop_loss_below_entry_long(self):
        s = DummyStrategy()
        stop = s.get_stop_loss(250.0, Side.LONG, 5.0)
        assert stop < 250.0

    def test_stop_loss_above_entry_short(self):
        s = DummyStrategy()
        stop = s.get_stop_loss(250.0, Side.SHORT, 5.0)
        assert stop > 250.0

    def test_get_params(self):
        s = DummyStrategy()
        params = s.get_params()
        assert isinstance(params, dict)
        assert "fast" in params
        assert params["fast"] == 10

    def test_set_params(self):
        s = DummyStrategy()
        s.set_params({"fast": 20, "slow": 50})
        assert s.get_params()["fast"] == 20
        assert s.get_params()["slow"] == 50

    def test_warm_up_period(self):
        s = DummyStrategy()
        assert s.warm_up_period() == 30
        assert isinstance(s.warm_up_period(), int)

    def test_repr(self):
        s = DummyStrategy()
        assert "DummyStrategy" in repr(s)
        assert "dummy" in repr(s)


class TestStrategyRegistry:
    def test_register_and_create(self):
        reg = StrategyRegistry()
        reg.register("dummy", DummyStrategy)
        s = reg.create("dummy")
        assert isinstance(s, DummyStrategy)

    def test_register_non_subclass(self):
        reg = StrategyRegistry()
        with pytest.raises(TypeError):
            reg.register("bad", dict)  # type: ignore[arg-type]

    def test_register_duplicate(self):
        reg = StrategyRegistry()
        reg.register("dummy", DummyStrategy)
        with pytest.raises(ValueError, match="already registered"):
            reg.register("dummy", DummyStrategy)

    def test_create_unknown(self):
        reg = StrategyRegistry()
        with pytest.raises(KeyError):
            reg.create("nonexistent")

    def test_list_strategies(self):
        reg = StrategyRegistry()
        reg.register("alpha", DummyStrategy)
        reg.register("beta", DummyStrategy)
        assert reg.list_strategies() == ["alpha", "beta"]

    def test_discover(self):
        reg = StrategyRegistry()
        reg.discover()
        assert "dummystrategy" in reg

    def test_len(self):
        reg = StrategyRegistry()
        assert len(reg) == 0
        reg.register("dummy", DummyStrategy)
        assert len(reg) == 1
