"""Abstract base class for all trading strategies.

Every strategy in src/strategies/ MUST inherit from this class.
This ensures uniform interface for backtesting, optimization, and live trading.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import polars as pl

from src.core.models import Side, Signal


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(
        self,
        name: str,
        timeframe: str = "1d",
        instruments: list[str] | None = None,
    ):
        self.name = name
        self.timeframe = timeframe
        self.instruments = instruments or []
        self._params: dict[str, Any] = {}

    @abstractmethod
    def generate_signals(self, data: pl.DataFrame) -> list[Signal]:
        """Generate trading signals from market data.

        Args:
            data: DataFrame with columns: timestamp, open, high, low, close, volume.
                  May contain additional indicator columns.

        Returns:
            List of Signal objects. Empty list = no signal.
        """
        ...

    @abstractmethod
    def calculate_position_size(
        self, signal: Signal, portfolio_value: float, atr: float
    ) -> float:
        """Calculate position size in units (shares/contracts).

        Args:
            signal: The signal to size.
            portfolio_value: Current portfolio value in RUB.
            atr: Current ATR for the instrument.

        Returns:
            Number of units to trade. Must respect lot size.
        """
        ...

    @abstractmethod
    def get_stop_loss(self, entry_price: float, side: Side, atr: float) -> float:
        """Calculate stop-loss price.

        Args:
            entry_price: Entry price.
            side: LONG or SHORT.
            atr: Current ATR.

        Returns:
            Stop-loss price. For LONG: below entry. For SHORT: above entry.
        """
        ...

    def get_take_profit(
        self, entry_price: float, side: Side, atr: float
    ) -> float | None:
        """Calculate take-profit price. Optional — returns None by default."""
        return None

    def on_bar(self, bar: dict) -> list[Signal]:
        """Process a single bar in real-time mode. Override for live trading."""
        return []

    def get_params(self) -> dict[str, Any]:
        """Return current strategy parameters for optimization."""
        return self._params.copy()

    def set_params(self, params: dict[str, Any]) -> None:
        """Set strategy parameters (used by optimizer)."""
        self._params.update(params)

    def warm_up_period(self) -> int:
        """Number of bars needed before strategy can generate signals."""
        return 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', tf='{self.timeframe}')"
