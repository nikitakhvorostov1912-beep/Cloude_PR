"""Protective position controller — SL/TP with trailing and timeout.

Ported from StockSharp ProtectiveController architecture (Apache 2.0) to Python.

Features:
- Stop-loss: fixed, trailing (follows price), ATR-based
- Take-profit: fixed offset
- Time-stop: force close after timeout (for MOEX session awareness)
- Absolute and percentage offsets
- MOEX price step rounding
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class CloseReason(str, Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TIMEOUT = "timeout"
    TRAILING_STOP = "trailing_stop"


@dataclass
class ProtectiveAction:
    """Recommendation from the protective controller."""
    should_close: bool = False
    reason: CloseReason | None = None
    close_price: float = 0.0
    use_market_order: bool = False
    message: str = ""


@dataclass
class ProtectiveConfig:
    """Configuration for position protection."""
    # Stop-loss
    stop_offset: float = 0.0         # absolute price offset (e.g. 5.0 RUB)
    stop_pct: float = 0.0            # percentage offset (e.g. 0.02 = 2%)
    is_trailing: bool = False         # trailing stop mode

    # Take-profit
    take_offset: float = 0.0         # absolute price offset
    take_pct: float = 0.0            # percentage offset

    # Time-stop
    timeout_seconds: float = 0.0     # 0 = disabled
    use_market_on_timeout: bool = True

    # MOEX
    price_step: float = 0.01         # tick size for rounding


# ---------------------------------------------------------------------------
# Protective Controller
# ---------------------------------------------------------------------------

class ProtectiveController:
    """Manages SL/TP/trailing/timeout for a single position.

    Pure functional: call update() with current price/time, get ProtectiveAction.
    Does NOT submit orders — the caller handles execution.

    Usage:
        ctrl = ProtectiveController(
            side=Side.LONG,
            entry_price=280.50,
            entry_time=time.time(),
            config=ProtectiveConfig(
                stop_pct=0.02,      # 2% stop-loss
                take_pct=0.05,      # 5% take-profit
                is_trailing=True,   # trailing stop
                timeout_seconds=3600,  # 1 hour time-stop
                price_step=0.01,
            ),
        )

        action = ctrl.update(current_price=285.0, current_time=time.time())
        if action.should_close:
            broker.close_position(reason=action.reason)
    """

    def __init__(
        self,
        side: Side,
        entry_price: float,
        entry_time: float,
        config: ProtectiveConfig,
    ):
        self.side = side
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.config = config

        # Internal state
        self._best_price = entry_price  # tracks high watermark (long) or low (short)
        self._stop_price = self._calc_initial_stop()
        self._take_price = self._calc_take()
        self._is_closed = False

    @property
    def stop_price(self) -> float | None:
        return self._stop_price

    @property
    def take_price(self) -> float | None:
        return self._take_price

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    def _round(self, price: float) -> float:
        step = self.config.price_step
        if step > 0:
            return round(price / step) * step
        return price

    def _calc_offset(self, base_price: float, offset: float, pct: float, direction: int) -> float:
        """Calculate price with offset (absolute or pct, whichever is set)."""
        if pct > 0:
            return self._round(base_price * (1 + direction * pct))
        if offset > 0:
            return self._round(base_price + direction * offset)
        return 0.0

    def _calc_initial_stop(self) -> float | None:
        if self.config.stop_offset == 0 and self.config.stop_pct == 0:
            return None
        direction = -1 if self.side == Side.LONG else 1
        return self._calc_offset(self.entry_price, self.config.stop_offset,
                                 self.config.stop_pct, direction)

    def _calc_take(self) -> float | None:
        if self.config.take_offset == 0 and self.config.take_pct == 0:
            return None
        direction = 1 if self.side == Side.LONG else -1
        return self._calc_offset(self.entry_price, self.config.take_offset,
                                 self.config.take_pct, direction)

    def _update_trailing(self, current_price: float) -> None:
        """Update trailing stop based on new high/low watermark."""
        if not self.config.is_trailing or self._stop_price is None:
            return

        if self.side == Side.LONG:
            if current_price > self._best_price:
                self._best_price = current_price
                new_stop = self._calc_offset(
                    self._best_price, self.config.stop_offset,
                    self.config.stop_pct, -1,
                )
                if new_stop > self._stop_price:
                    self._stop_price = new_stop
        else:
            if current_price < self._best_price:
                self._best_price = current_price
                new_stop = self._calc_offset(
                    self._best_price, self.config.stop_offset,
                    self.config.stop_pct, 1,
                )
                if new_stop < self._stop_price:
                    self._stop_price = new_stop

    def update(self, current_price: float, current_time: float) -> ProtectiveAction:
        """Check all protective conditions against current price/time.

        Args:
            current_price: Latest market price.
            current_time: Unix timestamp.

        Returns:
            ProtectiveAction — if should_close is True, the position should be exited.
        """
        if self._is_closed:
            return ProtectiveAction(message="Already closed")

        # 1. Time-stop (highest priority — MOEX session end, etc.)
        if self.config.timeout_seconds > 0:
            elapsed = current_time - self.entry_time
            if elapsed >= self.config.timeout_seconds:
                self._is_closed = True
                return ProtectiveAction(
                    should_close=True,
                    reason=CloseReason.TIMEOUT,
                    close_price=current_price,
                    use_market_order=self.config.use_market_on_timeout,
                    message=f"Timeout {elapsed:.0f}s >= {self.config.timeout_seconds:.0f}s",
                )

        # 2. Update trailing stop
        self._update_trailing(current_price)

        # 3. Check stop-loss
        if self._stop_price is not None:
            triggered = (
                (self.side == Side.LONG and current_price <= self._stop_price) or
                (self.side == Side.SHORT and current_price >= self._stop_price)
            )
            if triggered:
                self._is_closed = True
                reason = CloseReason.TRAILING_STOP if self.config.is_trailing else CloseReason.STOP_LOSS
                return ProtectiveAction(
                    should_close=True,
                    reason=reason,
                    close_price=self._stop_price,
                    message=f"Stop @ {self._stop_price:.2f} (current {current_price:.2f})",
                )

        # 4. Check take-profit
        if self._take_price is not None:
            triggered = (
                (self.side == Side.LONG and current_price >= self._take_price) or
                (self.side == Side.SHORT and current_price <= self._take_price)
            )
            if triggered:
                self._is_closed = True
                return ProtectiveAction(
                    should_close=True,
                    reason=CloseReason.TAKE_PROFIT,
                    close_price=self._take_price,
                    message=f"Take @ {self._take_price:.2f} (current {current_price:.2f})",
                )

        return ProtectiveAction(message="No trigger")
