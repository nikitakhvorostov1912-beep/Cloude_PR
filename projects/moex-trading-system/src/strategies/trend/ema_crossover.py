"""EMA Crossover trend-following strategy.

Reference implementation of BaseStrategy.
Fast EMA(20) crosses above slow EMA(50) → LONG.
Fast EMA(20) crosses below slow EMA(50) → SHORT.
Position sizing: 2% risk per trade via ATR.
Stop-loss: 2 × ATR from entry.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
import polars as pl

from src.analysis.features import calculate_atr, calculate_ema
from src.core.base_strategy import BaseStrategy
from src.core.config import load_settings
from src.core.models import Side, Signal


class EMACrossoverStrategy(BaseStrategy):
    """EMA crossover trend strategy."""

    def __init__(
        self,
        instruments: list[str] | None = None,
        fast_period: int = 20,
        slow_period: int = 50,
        risk_per_trade: float = 0.02,
        atr_multiplier: float = 2.0,
        atr_period: int = 14,
    ):
        super().__init__(
            name="ema_crossover",
            timeframe="1d",
            instruments=instruments or ["SBER"],
        )
        self._params = {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "risk_per_trade": risk_per_trade,
            "atr_multiplier": atr_multiplier,
            "atr_period": atr_period,
        }

    @property
    def fast_period(self) -> int:
        return self._params["fast_period"]

    @property
    def slow_period(self) -> int:
        return self._params["slow_period"]

    @property
    def risk_per_trade(self) -> float:
        return self._params["risk_per_trade"]

    @property
    def atr_multiplier(self) -> float:
        return self._params["atr_multiplier"]

    def generate_signals(self, data: pl.DataFrame) -> list[Signal]:
        """Generate signals from EMA crossover.

        Returns LONG when fast EMA crosses above slow EMA,
        SHORT when fast EMA crosses below slow EMA.
        """
        if data.height < self.warm_up_period():
            return []

        close = data["close"]
        ema_fast = calculate_ema(close, self.fast_period).to_numpy()
        ema_slow = calculate_ema(close, self.slow_period).to_numpy()

        signals: list[Signal] = []

        # Check last two bars for crossover
        idx = data.height - 1
        prev = idx - 1

        if prev < self.slow_period:
            return []

        fast_above_now = ema_fast[idx] > ema_slow[idx]
        fast_above_prev = ema_fast[prev] > ema_slow[prev]

        # Determine instrument name
        instrument = self.instruments[0] if self.instruments else "UNKNOWN"
        if "instrument" in data.columns:
            instrument = str(data["instrument"][idx])

        # Get timestamp
        ts = datetime.now()
        if "timestamp" in data.columns:
            ts_val = data["timestamp"][idx]
            if isinstance(ts_val, datetime):
                ts = ts_val

        # Crossover detection
        if fast_above_now and not fast_above_prev:
            # Bullish crossover
            diff = abs(ema_fast[idx] - ema_slow[idx])
            spread = abs(ema_slow[idx]) if ema_slow[idx] != 0 else 1.0
            strength = min(1.0, diff / spread * 10)
            signals.append(Signal(
                instrument=instrument,
                side=Side.LONG,
                strength=strength,
                strategy_name=self.name,
                timestamp=ts,
                confidence=0.6,
            ))
        elif not fast_above_now and fast_above_prev:
            # Bearish crossover
            diff = abs(ema_fast[idx] - ema_slow[idx])
            spread = abs(ema_slow[idx]) if ema_slow[idx] != 0 else 1.0
            strength = min(1.0, diff / spread * 10)
            signals.append(Signal(
                instrument=instrument,
                side=Side.SHORT,
                strength=strength,
                strategy_name=self.name,
                timestamp=ts,
                confidence=0.6,
            ))

        return signals

    def calculate_position_size(
        self, signal: Signal, portfolio_value: float, atr: float
    ) -> float:
        """Calculate position size using ATR-based risk sizing.

        Risk = 2% of portfolio per trade.
        Size = risk_amount / (atr_multiplier * atr).
        Rounded down to lot size.
        """
        if atr <= 0 or portfolio_value <= 0:
            return 0.0

        risk_amount = portfolio_value * self.risk_per_trade
        raw_size = risk_amount / (self.atr_multiplier * atr)

        # Round to lot size
        lot_size = self._get_lot_size(signal.instrument)
        lots = max(1, int(raw_size / lot_size))
        return float(lots * lot_size)

    def get_stop_loss(self, entry_price: float, side: Side, atr: float) -> float:
        """Stop-loss at 2 × ATR from entry, rounded to price step."""
        offset = self.atr_multiplier * atr
        if side == Side.LONG:
            raw = entry_price - offset
        else:
            raw = entry_price + offset

        step = self._get_price_step(
            self.instruments[0] if self.instruments else "SBER"
        )
        return self._round_to_step(raw, step)

    def get_take_profit(
        self, entry_price: float, side: Side, atr: float
    ) -> float | None:
        """Take profit at 3 × ATR from entry."""
        offset = 3.0 * atr
        if side == Side.LONG:
            raw = entry_price + offset
        else:
            raw = entry_price - offset

        step = self._get_price_step(
            self.instruments[0] if self.instruments else "SBER"
        )
        return self._round_to_step(raw, step)

    def warm_up_period(self) -> int:
        return self.slow_period

    def _get_lot_size(self, instrument: str) -> int:
        """Get lot size from config, fallback to 1."""
        try:
            cfg = load_settings()
            info = cfg.get_instrument_info(instrument)
            return info.lot
        except (FileNotFoundError, KeyError):
            return 1

    def _get_price_step(self, instrument: str) -> float:
        """Get price step from config, fallback to 0.01."""
        try:
            cfg = load_settings()
            info = cfg.get_instrument_info(instrument)
            return info.step
        except (FileNotFoundError, KeyError):
            return 0.01

    @staticmethod
    def _round_to_step(price: float, step: float) -> float:
        """Round price to nearest valid step."""
        if step <= 0:
            return price
        return round(round(price / step) * step, 10)
