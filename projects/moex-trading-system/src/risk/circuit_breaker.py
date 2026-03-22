"""Circuit breaker — wraps PortfolioCircuitBreaker with main.py-compatible API.

main.py uses: new_day(), check(), get_position_multiplier(), record_trade()
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from src.risk.portfolio_circuit_breaker import (
    CircuitBreakerState,
    PortfolioCircuitBreaker,
)


class CircuitState(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    HALTED = "halted"
    EMERGENCY = "emergency"


class CircuitBreaker:
    """Daily circuit breaker compatible with main.py TradingPipeline.

    Methods expected by main.py:
      new_day(equity) — reset daily counters
      check(equity) -> (CircuitState, reason)
      get_position_multiplier() -> float
      record_trade(pnl)
    """

    def __init__(
        self,
        max_daily_dd_pct: float = 0.05,
        max_total_dd_pct: float = 0.15,
    ):
        self._max_daily_dd = max_daily_dd_pct
        self._max_total_dd = max_total_dd_pct
        self._day_start_equity: float = 0.0
        self._peak_equity: float = 0.0
        self._daily_pnl: float = 0.0
        self._state = CircuitState.NORMAL
        self._trades_today: int = 0
        self._consecutive_losses: int = 0

    def new_day(self, equity: float) -> None:
        """Reset daily counters at start of trading day."""
        self._day_start_equity = equity
        if equity > self._peak_equity:
            self._peak_equity = equity
        self._daily_pnl = 0.0
        self._trades_today = 0
        self._state = CircuitState.NORMAL

    def check(self, equity: float) -> tuple[CircuitState, str]:
        """Check if circuit breaker should trigger.

        Returns (state, reason).
        """
        if self._day_start_equity <= 0:
            self._day_start_equity = equity
            self._peak_equity = equity
            return CircuitState.NORMAL, ""

        # Daily drawdown
        daily_dd = (self._day_start_equity - equity) / self._day_start_equity
        if daily_dd >= self._max_daily_dd:
            self._state = CircuitState.HALTED
            return CircuitState.HALTED, f"Daily DD {daily_dd:.1%} >= {self._max_daily_dd:.0%}"

        # Total drawdown from peak
        if self._peak_equity > 0:
            total_dd = (self._peak_equity - equity) / self._peak_equity
            if total_dd >= self._max_total_dd:
                self._state = CircuitState.EMERGENCY
                return CircuitState.EMERGENCY, f"Total DD {total_dd:.1%} >= {self._max_total_dd:.0%}"

        # Warning zone
        if daily_dd >= self._max_daily_dd * 0.7:
            self._state = CircuitState.WARNING
            return CircuitState.WARNING, f"Daily DD {daily_dd:.1%} approaching limit"

        self._state = CircuitState.NORMAL
        return CircuitState.NORMAL, ""

    def get_position_multiplier(self) -> float:
        """Position size multiplier based on current state."""
        if self._state == CircuitState.EMERGENCY:
            return 0.0
        if self._state == CircuitState.HALTED:
            return 0.0
        if self._state == CircuitState.WARNING:
            return 0.5
        return 1.0

    def record_trade(self, pnl: float) -> None:
        """Record a completed trade for daily tracking."""
        self._daily_pnl += pnl
        self._trades_today += 1
        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

    @property
    def is_triggered(self) -> bool:
        return self._state in (CircuitState.HALTED, CircuitState.EMERGENCY)

    @property
    def state(self) -> CircuitState:
        return self._state


__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerState",
    "PortfolioCircuitBreaker",
]
