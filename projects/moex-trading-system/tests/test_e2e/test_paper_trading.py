"""Tests for paper trading runner."""
from __future__ import annotations

from datetime import datetime, time

import pytest

from scripts.paper_trading import PaperTradingRunner


class TestPaperTrading:
    @pytest.fixture
    def runner(self):
        return PaperTradingRunner(
            poll_interval_sec=1,
            instruments=["SBER"],
        )

    def test_creates_loop(self, runner):
        assert runner is not None
        assert not runner.is_running
        assert runner._instruments == ["SBER"]

    def test_clearing_check(self, runner):
        """Should detect clearing sessions."""
        # 14:00-14:05 is clearing
        clearing_time = datetime(2024, 6, 15, 14, 2, 0)
        assert runner.is_clearing_time(clearing_time)

        # 12:00 is not clearing
        normal_time = datetime(2024, 6, 15, 12, 0, 0)
        assert not runner.is_clearing_time(normal_time)

        # 18:50 is clearing_2
        clearing_2 = datetime(2024, 6, 15, 18, 50, 0)
        assert runner.is_clearing_time(clearing_2)

    def test_session_end(self, runner):
        """Should close positions before 18:30."""
        before_close = datetime(2024, 6, 15, 18, 0, 0)
        assert not runner.should_close_positions(before_close)

        after_close = datetime(2024, 6, 15, 18, 35, 0)
        assert runner.should_close_positions(after_close)

    def test_circuit_breaker(self, runner):
        """Triggers when daily DD > 5%."""
        runner._start_equity = 1_000_000
        # 4% DD — no trigger
        assert not runner.check_circuit_breaker(960_000)
        # 6% DD — trigger
        assert runner.check_circuit_breaker(940_000)
        assert runner._circuit_breaker_triggered

    def test_graceful_shutdown(self, runner):
        """Stop method sets flags correctly."""
        runner._running = True
        runner.stop()
        assert not runner.is_running
        assert runner._shutdown_event.is_set()

    def test_trading_hours(self, runner):
        """Trading hours 10:00-18:40."""
        trading = datetime(2024, 6, 15, 14, 0, 0)
        assert runner.is_trading_hours(trading)

        before = datetime(2024, 6, 15, 9, 30, 0)
        assert not runner.is_trading_hours(before)

        after = datetime(2024, 6, 15, 19, 0, 0)
        assert not runner.is_trading_hours(after)

    def test_parse_time(self):
        t = PaperTradingRunner._parse_time("14:05")
        assert t == time(14, 5)
