"""Telegram bot for trading alerts and manual control.

Alerts: signal generated, order filled, stop triggered,
circuit breaker activated, daily P&L report.

Commands: /status, /stop, /start, /positions, /pnl
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import structlog

from src.core.config import load_settings
from src.core.models import Portfolio, Position, Side, Signal, TradeResult

logger = structlog.get_logger(__name__)

MAX_MESSAGE_LENGTH = 4096  # Telegram limit


class TradingTelegramBot:
    """Telegram bot for trading alerts and control."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ):
        try:
            cfg = load_settings()
            self._token = bot_token or cfg.telegram.bot_token or ""
            self._chat_id = chat_id or cfg.telegram.chat_id or ""
        except FileNotFoundError:
            self._token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
            self._chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

        self._bot: Any = None
        self._trading_active = True

    @property
    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    @property
    def trading_active(self) -> bool:
        return self._trading_active

    async def start(self) -> None:
        """Initialize the bot (connect to Telegram API)."""
        if not self.is_configured:
            logger.warning("Telegram bot not configured — alerts disabled")
            return

        try:
            from telegram import Bot
            self._bot = Bot(token=self._token)
            logger.info("Telegram bot initialized")
        except ImportError:
            logger.error("python-telegram-bot not installed")
        except Exception as e:
            logger.error("Failed to start Telegram bot", error=str(e))

    async def send_message(self, text: str) -> bool:
        """Send a message to the configured chat.

        Returns True if sent successfully, False otherwise.
        """
        if not self._bot:
            logger.debug("Telegram bot not initialized, skipping message")
            return False

        # Truncate to Telegram limit
        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[:MAX_MESSAGE_LENGTH - 20] + "\n... (truncated)"

        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error("Failed to send Telegram message", error=str(e))
            return False

    # ── Alert formatters ────────────────────────────────────────

    @staticmethod
    def format_signal_message(signal: Signal) -> str:
        """Format a trading signal for Telegram."""
        emoji = "\U0001F7E2" if signal.side == Side.LONG else "\U0001F534"
        return (
            f"{emoji} <b>SIGNAL: {signal.instrument}</b>\n"
            f"Direction: {signal.side.value.upper()}\n"
            f"Strength: {signal.strength:.2f}\n"
            f"Confidence: {signal.confidence:.2f}\n"
            f"Strategy: {signal.strategy_name}\n"
            f"Time: {signal.timestamp.strftime('%H:%M:%S')}"
        )

    @staticmethod
    def format_trade_message(trade: TradeResult) -> str:
        """Format a completed trade for Telegram."""
        pnl_emoji = "\U0001F4B0" if trade.net_pnl >= 0 else "\U0001F4C9"
        return (
            f"{pnl_emoji} <b>TRADE: {trade.instrument}</b>\n"
            f"Side: {trade.side.value.upper()}\n"
            f"Entry: {trade.entry_price:.2f} → Exit: {trade.exit_price:.2f}\n"
            f"Qty: {trade.quantity:.0f}\n"
            f"Gross P&L: {trade.gross_pnl:+,.2f} RUB\n"
            f"Net P&L: {trade.net_pnl:+,.2f} RUB\n"
            f"Commission: {trade.commission:.2f}\n"
            f"Return: {trade.return_pct * 100:+.2f}%\n"
            f"Duration: {trade.duration / 3600:.1f}h"
        )

    @staticmethod
    def format_pnl_report(
        portfolio: Portfolio,
        daily_pnl: float,
        trades_today: list[TradeResult],
    ) -> str:
        """Format daily P&L report for Telegram."""
        pnl_emoji = "\U0001F4B0" if daily_pnl >= 0 else "\U0001F4C9"
        winning = sum(1 for t in trades_today if t.net_pnl > 0)
        losing = sum(1 for t in trades_today if t.net_pnl <= 0)

        return (
            f"{pnl_emoji} <b>DAILY P&L REPORT</b>\n"
            f"{'=' * 25}\n"
            f"Portfolio value: {portfolio.total_value:,.0f} RUB\n"
            f"Cash: {portfolio.cash:,.0f} RUB\n"
            f"Exposure: {portfolio.exposure * 100:.1f}%\n"
            f"Positions: {len(portfolio.positions)}\n"
            f"\nDaily P&L: {daily_pnl:+,.0f} RUB\n"
            f"Trades: {len(trades_today)} (W: {winning}, L: {losing})\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    @staticmethod
    def format_circuit_breaker_message(
        reason: str, drawdown_pct: float
    ) -> str:
        """Format circuit breaker alert."""
        return (
            f"\U0001F6A8 <b>CIRCUIT BREAKER ACTIVATED</b>\n"
            f"Reason: {reason}\n"
            f"Drawdown: {drawdown_pct * 100:.1f}%\n"
            f"Trading HALTED\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )

    # ── Command handlers ────────────────────────────────────────

    @staticmethod
    def parse_command(text: str) -> tuple[str, list[str]]:
        """Parse a Telegram command.

        Returns (command_name, args).
        """
        parts = text.strip().split()
        if not parts or not parts[0].startswith("/"):
            return "", []
        command = parts[0].lstrip("/").lower()
        args = parts[1:]
        return command, args

    def handle_command(self, command: str) -> str:
        """Handle a bot command and return response text."""
        handlers = {
            "status": self._cmd_status,
            "stop": self._cmd_stop,
            "start": self._cmd_start,
            "positions": self._cmd_positions,
            "pnl": self._cmd_pnl,
            "help": self._cmd_help,
        }
        handler = handlers.get(command)
        if handler:
            return handler()
        return f"Unknown command: /{command}\nType /help for available commands."

    def _cmd_status(self) -> str:
        status = "ACTIVE" if self._trading_active else "STOPPED"
        return f"Trading status: {status}"

    def _cmd_stop(self) -> str:
        self._trading_active = False
        return "\U0001F6D1 Trading STOPPED"

    def _cmd_start(self) -> str:
        self._trading_active = True
        return "\U0001F7E2 Trading RESUMED"

    def _cmd_positions(self) -> str:
        return "No positions (use with live portfolio)"

    def _cmd_pnl(self) -> str:
        return "No P&L data (use with live portfolio)"

    def _cmd_help(self) -> str:
        return (
            "<b>Available commands:</b>\n"
            "/status — Current trading status\n"
            "/stop — Stop trading\n"
            "/start — Resume trading\n"
            "/positions — List open positions\n"
            "/pnl — Show P&L report\n"
            "/help — This message"
        )
