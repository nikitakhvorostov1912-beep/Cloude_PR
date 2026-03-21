"""Portfolio-level circuit breaker — liquidate all on drawdown threshold.

Inspired by QuantConnect LEAN MaximumDrawdownPercentPortfolio (Apache 2.0).
Written from scratch in Python.

Two modes:
- Trailing: DD measured from portfolio equity peak (tightens as profits grow).
- Static: DD measured from initial capital (fixed reference).

Usage:
    cb = PortfolioCircuitBreaker(max_dd_pct=0.15, trailing=True)
    cb.update(equity=110_000)  # new peak
    cb.update(equity=95_000)   # DD = (110-95)/110 = 13.6% → still OK
    cb.update(equity=93_000)   # DD = (110-93)/110 = 15.5% → TRIGGERED
    assert cb.is_triggered
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CircuitBreakerState:
    """Current state of the circuit breaker.

    Attributes:
        is_triggered: True if DD threshold exceeded.
        current_dd_pct: Current drawdown as fraction (0.15 = 15%).
        peak_equity: Highest equity observed (trailing mode).
        reference_equity: Reference for DD calc (peak or initial).
        trigger_count: How many times CB has been triggered.
        last_trigger_time: When last triggered.
    """

    is_triggered: bool = False
    current_dd_pct: float = 0.0
    peak_equity: float = 0.0
    reference_equity: float = 0.0
    trigger_count: int = 0
    last_trigger_time: datetime | None = None


class PortfolioCircuitBreaker:
    """Portfolio-level drawdown circuit breaker.

    When portfolio equity drops by max_dd_pct from reference,
    the breaker triggers. Strategies should liquidate all positions.

    In trailing mode, the reference is the equity peak (tightens
    as profits grow). In static mode, the reference is initial capital.

    Args:
        max_dd_pct: Maximum drawdown as fraction (0.15 = 15%).
        trailing: If True, reference = equity peak. If False, reference = initial.
        cooldown_bars: Bars to wait after trigger before re-enabling (default 0).
    """

    def __init__(
        self,
        max_dd_pct: float = 0.15,
        trailing: bool = True,
        cooldown_bars: int = 0,
    ) -> None:
        if not 0 < max_dd_pct < 1:
            raise ValueError(f"max_dd_pct must be in (0, 1), got {max_dd_pct}")
        self._max_dd_pct = max_dd_pct
        self._trailing = trailing
        self._cooldown_bars = cooldown_bars
        self._peak_equity: float = 0.0
        self._initial_equity: float = 0.0
        self._is_triggered: bool = False
        self._trigger_count: int = 0
        self._last_trigger_time: datetime | None = None
        self._bars_since_trigger: int = 0
        self._initialized: bool = False

    @property
    def is_triggered(self) -> bool:
        return self._is_triggered

    @property
    def state(self) -> CircuitBreakerState:
        ref = self._peak_equity if self._trailing else self._initial_equity
        dd = (ref - self._peak_equity) / ref if ref > 0 else 0.0
        if self._trailing:
            dd = max(0.0, dd)
        return CircuitBreakerState(
            is_triggered=self._is_triggered,
            current_dd_pct=self._current_dd,
            peak_equity=self._peak_equity,
            reference_equity=ref,
            trigger_count=self._trigger_count,
            last_trigger_time=self._last_trigger_time,
        )

    @property
    def _current_dd(self) -> float:
        ref = self._peak_equity if self._trailing else self._initial_equity
        if ref <= 0:
            return 0.0
        return 0.0  # placeholder, computed in update

    def update(
        self,
        equity: float,
        timestamp: datetime | None = None,
    ) -> bool:
        """Update with current portfolio equity.

        Args:
            equity: Current total portfolio equity.
            timestamp: Optional timestamp for logging.

        Returns:
            True if circuit breaker just triggered on this update.
        """
        if not self._initialized:
            self._initial_equity = equity
            self._peak_equity = equity
            self._initialized = True
            return False

        # Update peak
        if equity > self._peak_equity:
            self._peak_equity = equity

        # Cooldown handling
        if self._is_triggered:
            self._bars_since_trigger += 1
            if self._bars_since_trigger > self._cooldown_bars:
                self._is_triggered = False
                self._bars_since_trigger = 0
                # Reset peak for trailing mode after recovery
                if self._trailing:
                    self._peak_equity = equity
            return False

        # Calculate drawdown
        reference = self._peak_equity if self._trailing else self._initial_equity
        if reference <= 0:
            return False

        dd_pct = (reference - equity) / reference

        if dd_pct >= self._max_dd_pct:
            self._is_triggered = True
            self._trigger_count += 1
            self._last_trigger_time = timestamp or datetime.now()
            self._bars_since_trigger = 0
            return True

        return False

    def reset(self, new_equity: float | None = None) -> None:
        """Reset the circuit breaker state."""
        self._is_triggered = False
        self._bars_since_trigger = 0
        if new_equity is not None:
            self._peak_equity = new_equity
            self._initial_equity = new_equity
            self._initialized = True
        else:
            self._initialized = False
            self._peak_equity = 0.0
            self._initial_equity = 0.0
