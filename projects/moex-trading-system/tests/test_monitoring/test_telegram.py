"""Tests for Telegram bot message formatting and commands."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.core.models import Portfolio, Position, Side, Signal, TradeResult
from src.monitoring.telegram_bot import MAX_MESSAGE_LENGTH, TradingTelegramBot

NOW = datetime(2024, 6, 15, 14, 30, 0)


@pytest.fixture
def bot():
    return TradingTelegramBot(bot_token="", chat_id="")


class TestTelegramBot:
    def test_format_signal_message(self, bot):
        sig = Signal(
            instrument="SBER", side=Side.LONG, strength=0.85,
            strategy_name="ema_crossover", timestamp=NOW, confidence=0.75,
        )
        msg = bot.format_signal_message(sig)
        assert "SBER" in msg
        assert "LONG" in msg
        assert "0.85" in msg
        assert "ema_crossover" in msg

    def test_format_trade_message(self, bot):
        trade = TradeResult(
            instrument="GAZP", side=Side.SHORT,
            entry_price=180.0, exit_price=170.0, quantity=100,
            entry_timestamp=NOW, exit_timestamp=NOW + timedelta(hours=3),
            strategy_name="ema_crossover", commission=3.6,
        )
        msg = bot.format_trade_message(trade)
        assert "GAZP" in msg
        assert "SHORT" in msg
        assert "180.00" in msg
        assert "170.00" in msg
        assert "P&L" in msg

    def test_format_pnl_report(self, bot):
        pos = Position(
            instrument="SBER", side=Side.LONG, quantity=100,
            entry_price=250.0, current_price=260.0,
        )
        portfolio = Portfolio(positions=[pos], cash=900_000)
        trades = [
            TradeResult(
                instrument="SBER", side=Side.LONG,
                entry_price=250.0, exit_price=260.0, quantity=50,
                entry_timestamp=NOW, exit_timestamp=NOW + timedelta(hours=1),
            ),
            TradeResult(
                instrument="GAZP", side=Side.LONG,
                entry_price=180.0, exit_price=175.0, quantity=100,
                entry_timestamp=NOW, exit_timestamp=NOW + timedelta(hours=2),
            ),
        ]
        msg = bot.format_pnl_report(portfolio, 5000.0, trades)
        assert "DAILY P&L" in msg
        assert "5,000" in msg
        assert "W: 1" in msg
        assert "L: 1" in msg

    def test_format_circuit_breaker(self, bot):
        msg = bot.format_circuit_breaker_message("Daily drawdown exceeded", 0.055)
        assert "CIRCUIT BREAKER" in msg
        assert "5.5%" in msg

    def test_command_parsing(self, bot):
        cmd, args = bot.parse_command("/status")
        assert cmd == "status"
        assert args == []

        cmd, args = bot.parse_command("/stop now")
        assert cmd == "stop"
        assert args == ["now"]

        cmd, args = bot.parse_command("not a command")
        assert cmd == ""

    def test_no_token_graceful(self, bot):
        assert not bot.is_configured

    def test_message_length(self, bot):
        # All formatted messages should be under 4096
        sig = Signal(
            instrument="SBER", side=Side.LONG, strength=0.5,
            strategy_name="test", timestamp=NOW,
        )
        msg = bot.format_signal_message(sig)
        assert len(msg) < MAX_MESSAGE_LENGTH

    def test_stop_start_commands(self, bot):
        assert bot.trading_active
        response = bot.handle_command("stop")
        assert "STOPPED" in response
        assert not bot.trading_active

        response = bot.handle_command("start")
        assert "RESUMED" in response
        assert bot.trading_active

    def test_help_command(self, bot):
        msg = bot.handle_command("help")
        assert "/status" in msg
        assert "/stop" in msg
        assert "/start" in msg

    def test_unknown_command(self, bot):
        msg = bot.handle_command("unknown")
        assert "Unknown command" in msg
