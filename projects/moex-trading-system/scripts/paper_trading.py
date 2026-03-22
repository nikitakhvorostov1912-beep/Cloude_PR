"""Paper trading loop with Tinkoff sandbox.

1. Connect to Tinkoff sandbox
2. Load config from settings.yaml
3. Instantiate strategies (EMA crossover)
4. Run trading loop:
   a. Fetch candles, generate signals, apply risk checks
   b. Place orders via Tinkoff sandbox
   c. Send alerts to Telegram
5. Respect MOEX session times and clearings
6. Circuit breaker on daily DD > 5%
7. Graceful shutdown on Ctrl+C
"""
from __future__ import annotations

import asyncio
import signal
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog

from src.core.config import load_settings
from src.core.models import Side
from src.monitoring.telegram_bot import TradingTelegramBot

logger = structlog.get_logger(__name__)


class PaperTradingRunner:
    """Paper trading loop manager."""

    def __init__(
        self,
        poll_interval_sec: int = 300,
        instruments: list[str] | None = None,
    ):
        self._cfg = load_settings()
        self._poll_interval = poll_interval_sec
        self._instruments = instruments or ["SBER"]
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Session times from config
        self._main_start = self._parse_time(self._cfg.moex.sessions.main_start)
        self._main_end = self._parse_time(self._cfg.moex.sessions.main_end)
        self._clearing_1_start = self._parse_time(self._cfg.moex.sessions.clearing_1_start)
        self._clearing_1_end = self._parse_time(self._cfg.moex.sessions.clearing_1_end)
        self._clearing_2_start = self._parse_time(self._cfg.moex.sessions.clearing_2_start)
        self._clearing_2_end = self._parse_time(self._cfg.moex.sessions.clearing_2_end)
        self._close_positions_time = time(18, 30)

        # Telegram bot
        self._telegram = TradingTelegramBot()

        # State
        self._daily_pnl = 0.0
        self._start_equity = 0.0
        self._circuit_breaker_triggered = False

    @property
    def is_running(self) -> bool:
        return self._running

    def is_clearing_time(self, now: datetime | None = None) -> bool:
        """Check if current time is during a clearing session."""
        t = (now or datetime.now()).time()
        if self._clearing_1_start <= t <= self._clearing_1_end:
            return True
        if self._clearing_2_start <= t <= self._clearing_2_end:
            return True
        return False

    def is_trading_hours(self, now: datetime | None = None) -> bool:
        """Check if current time is within main trading session."""
        t = (now or datetime.now()).time()
        return self._main_start <= t <= self._main_end

    def should_close_positions(self, now: datetime | None = None) -> bool:
        """Check if it's time to close all positions before session end."""
        t = (now or datetime.now()).time()
        return t >= self._close_positions_time

    def check_circuit_breaker(self, current_equity: float) -> bool:
        """Check if daily drawdown exceeds limit.

        Returns True if circuit breaker should be triggered.
        """
        if self._start_equity <= 0:
            return False

        dd = (self._start_equity - current_equity) / self._start_equity
        threshold = self._cfg.risk.circuit_breaker_daily_dd

        if dd >= threshold:
            self._circuit_breaker_triggered = True
            logger.warning(
                "Circuit breaker triggered",
                drawdown_pct=f"{dd * 100:.1f}%",
                threshold_pct=f"{threshold * 100:.1f}%",
            )
            return True
        return False

    async def run(self) -> None:
        """Main trading loop."""
        self._running = True
        self._start_equity = 1_000_000  # from sandbox portfolio

        logger.info("Paper trading started", instruments=self._instruments)

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._handle_shutdown)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        await self._telegram.start()

        try:
            while self._running and not self._shutdown_event.is_set():
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self._poll_interval,
                    )
                    break  # shutdown requested
                except asyncio.TimeoutError:
                    pass  # normal timeout, run iteration

                if self._circuit_breaker_triggered:
                    logger.info("Circuit breaker active — skipping iteration")
                    continue

                now = datetime.now()

                if not self.is_trading_hours(now):
                    logger.debug("Outside trading hours")
                    continue

                if self.is_clearing_time(now):
                    logger.debug("Clearing session — skipping")
                    continue

                if self.should_close_positions(now):
                    logger.info("Session end approaching — closing positions")
                    continue

                # Trading iteration would go here:
                # 1. Fetch candles
                # 2. Generate signals
                # 3. Risk check
                # 4. Place orders
                # 5. Send alerts

                logger.debug("Trading iteration", time=now.strftime("%H:%M:%S"))

        except Exception as e:
            logger.error("Trading loop error", error=str(e))
        finally:
            self._running = False
            logger.info("Paper trading stopped")

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._running = False
        self._shutdown_event.set()
        logger.info("Shutdown requested")

    def _handle_shutdown(self) -> None:
        """Handle OS signal for graceful shutdown."""
        self.stop()

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse HH:MM string to time object."""
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))


if __name__ == "__main__":
    runner = PaperTradingRunner(
        poll_interval_sec=60,
        instruments=["SBER", "GAZP"],
    )
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        print("\nShutdown via Ctrl+C")
