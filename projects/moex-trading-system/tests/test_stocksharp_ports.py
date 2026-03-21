"""Tests for StockSharp-ported modules: quoting, commissions, protective."""
from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.execution.quoting import (
    ActionType, BestByPriceBehavior, BestByVolumeBehavior,
    LastTradeBehavior, LevelBehavior, LimitBehavior,
    MarketFollowBehavior, QuoteLevel, QuotingAction,
    QuotingEngine, QuotingInput, Side, TWAPBehavior, VWAPBehavior,
)
from src.backtest.commissions import (
    CommissionManager, FixedPerContractRule, FixedPerOrderRule,
    InstrumentTypeRule, MakerTakerRule, MinCommissionRule,
    PercentOfTurnoverRule, TurnoverTierRule, TradeInfo,
)
from src.risk.protective import (
    CloseReason, ProtectiveAction, ProtectiveConfig,
    ProtectiveController, Side as PSide,
)


# =========================================================================
# QUOTING ENGINE
# =========================================================================

class TestBestByPriceBehavior:
    def test_buy_uses_bid(self):
        b = BestByPriceBehavior()
        p = b.calculate_best_price(Side.BUY, 100.0, 101.0, None, None, [], [])
        assert p == 100.0

    def test_sell_uses_ask(self):
        b = BestByPriceBehavior()
        p = b.calculate_best_price(Side.SELL, 100.0, 101.0, None, None, [], [])
        assert p == 101.0

    def test_fallback_to_last_trade(self):
        b = BestByPriceBehavior()
        p = b.calculate_best_price(Side.BUY, None, None, 99.0, None, [], [])
        assert p == 99.0

    def test_requote_on_drift(self):
        b = BestByPriceBehavior(price_offset=0.5)
        assert b.need_requote(100.0, 10, 10, 100.3) is None  # within offset
        assert b.need_requote(100.0, 10, 10, 100.6) == 100.6  # beyond offset


class TestVWAPBehavior:
    def test_accumulates(self):
        v = VWAPBehavior()
        p1 = v.calculate_best_price(Side.BUY, None, None, 100.0, 50.0, [], [])
        assert p1 == 100.0
        p2 = v.calculate_best_price(Side.BUY, None, None, 102.0, 50.0, [], [])
        # VWAP = (100*50 + 102*50) / 100 = 101.0
        assert abs(p2 - 101.0) < 0.01


class TestTWAPBehavior:
    def test_time_gating(self):
        t = TWAPBehavior(interval_seconds=60)
        # First call — should trigger
        assert t.need_requote(None, None, 10, 100.0, current_time=1000) == 100.0
        # Within interval — should wait
        assert t.need_requote(100.0, 10, 10, 101.0, current_time=1030) is None
        # After interval — should trigger
        assert t.need_requote(100.0, 10, 10, 101.0, current_time=1061) == 101.0


class TestBestByVolumeBehavior:
    def test_finds_level(self):
        b = BestByVolumeBehavior(volume_threshold=150)
        bids = [QuoteLevel(100.0, 80), QuoteLevel(99.5, 100), QuoteLevel(99.0, 50)]
        p = b.calculate_best_price(Side.BUY, None, None, None, None, bids, [])
        assert p == 99.5  # cumulative 180 > 150 at second level


class TestLevelBehavior:
    def test_midpoint(self):
        b = LevelBehavior(min_level=0, max_level=2, price_step=0.5)
        bids = [QuoteLevel(100.0, 10), QuoteLevel(99.5, 20), QuoteLevel(99.0, 30)]
        p = b.calculate_best_price(Side.BUY, None, None, None, None, bids, [])
        assert p == 99.5  # midpoint of 100 and 99


class TestQuotingEngine:
    def test_register_new_order(self):
        engine = QuotingEngine(
            behavior=BestByPriceBehavior(),
            side=Side.BUY, total_volume=100,
            max_order_volume=20, price_step=0.01,
        )
        action = engine.process(QuotingInput(
            best_bid=280.50, best_ask=280.60,
        ))
        assert action.action == ActionType.REGISTER
        assert action.volume == 20  # max_order_volume
        assert action.price == 280.50

    def test_finish_on_complete(self):
        engine = QuotingEngine(
            behavior=BestByPriceBehavior(),
            side=Side.BUY, total_volume=10,
        )
        engine.on_fill(10)
        action = engine.process(QuotingInput(best_bid=100))
        assert action.action == ActionType.FINISH

    def test_timeout(self):
        engine = QuotingEngine(
            behavior=BestByPriceBehavior(),
            side=Side.BUY, total_volume=100,
            timeout=60, start_time=1000,
        )
        action = engine.process(QuotingInput(best_bid=100, current_time=1061))
        assert action.action == ActionType.FINISH
        assert "Timeout" in action.reason

    def test_cancel_on_price_change(self):
        engine = QuotingEngine(
            behavior=BestByPriceBehavior(price_offset=0.5),
            side=Side.BUY, total_volume=100,
        )
        action = engine.process(QuotingInput(
            best_bid=280.50, current_order_price=279.00,
            current_order_volume=20,
        ))
        assert action.action == ActionType.CANCEL

    def test_price_step_rounding(self):
        engine = QuotingEngine(
            behavior=LimitBehavior(limit_price=100.123),
            side=Side.BUY, total_volume=10, price_step=0.05,
        )
        action = engine.process(QuotingInput())
        assert abs(action.price - 100.10) < 0.001  # rounded to 0.05 step


# =========================================================================
# COMMISSION RULES
# =========================================================================

class TestPercentOfTurnover:
    def test_basic(self):
        r = PercentOfTurnoverRule(0.0001)
        fee = r.calculate(TradeInfo(price=280.0, volume=100))
        assert abs(fee - 2.80) < 0.01  # 280 * 100 * 0.0001


class TestFixedPerContract:
    def test_futures(self):
        r = FixedPerContractRule(2.0)
        fee = r.calculate(TradeInfo(price=100000, volume=5))
        assert fee == 10.0


class TestTurnoverTier:
    def test_tier_progression(self):
        r = TurnoverTierRule([(0, 0.0003), (1_000_000, 0.0001)])
        # First trade: turnover 500K → rate 0.0003
        fee1 = r.calculate(TradeInfo(price=500, volume=1000))
        assert abs(fee1 - 500_000 * 0.0003) < 0.01
        # Second trade: cumulative 1M → rate drops to 0.0001
        fee2 = r.calculate(TradeInfo(price=500, volume=1000))
        assert abs(fee2 - 500_000 * 0.0001) < 0.01

    def test_reset(self):
        r = TurnoverTierRule([(0, 0.0003), (1_000_000, 0.0001)])
        r.calculate(TradeInfo(price=500, volume=2000))
        r.reset()
        assert r._cumulative_turnover == 0.0


class TestMakerTaker:
    def test_maker_cheaper(self):
        r = MakerTakerRule(maker_rate=0.00005, taker_rate=0.0001)
        maker_fee = r.calculate(TradeInfo(price=100, volume=10, is_maker=True))
        taker_fee = r.calculate(TradeInfo(price=100, volume=10, is_maker=False))
        assert maker_fee < taker_fee


class TestInstrumentTypeRule:
    def test_routes(self):
        r = InstrumentTypeRule({
            "equity": PercentOfTurnoverRule(0.0001),
            "futures": FixedPerContractRule(2.0),
        })
        eq_fee = r.calculate(TradeInfo(price=280, volume=100, instrument_type="equity"))
        fu_fee = r.calculate(TradeInfo(price=100000, volume=5, instrument_type="futures"))
        assert abs(eq_fee - 2.80) < 0.01
        assert fu_fee == 10.0


class TestCommissionManager:
    def test_moex_default(self):
        mgr = CommissionManager.moex_default()
        eq = mgr.calculate(price=280, volume=100, instrument_type="equity")
        fu = mgr.calculate(price=100000, volume=5, instrument_type="futures")
        assert abs(eq - 2.80) < 0.01
        assert fu == 10.0

    def test_sum_mode(self):
        mgr = CommissionManager(
            [PercentOfTurnoverRule(0.0001), FixedPerOrderRule(1.0)],
            mode="sum",
        )
        fee = mgr.calculate(price=100, volume=10)
        assert abs(fee - (0.10 + 1.0)) < 0.01


# =========================================================================
# PROTECTIVE CONTROLLER
# =========================================================================

class TestProtectiveStopLoss:
    def test_fixed_stop_long(self):
        ctrl = ProtectiveController(
            side=PSide.LONG, entry_price=280.0, entry_time=1000,
            config=ProtectiveConfig(stop_offset=5.0),
        )
        assert ctrl.stop_price == 275.0
        action = ctrl.update(276.0, 1010)
        assert not action.should_close
        action = ctrl.update(274.0, 1020)
        assert action.should_close
        assert action.reason == CloseReason.STOP_LOSS

    def test_pct_stop_short(self):
        ctrl = ProtectiveController(
            side=PSide.SHORT, entry_price=100.0, entry_time=1000,
            config=ProtectiveConfig(stop_pct=0.03),
        )
        assert abs(ctrl.stop_price - 103.0) < 0.01
        action = ctrl.update(103.5, 1010)
        assert action.should_close

    def test_trailing_stop_long(self):
        ctrl = ProtectiveController(
            side=PSide.LONG, entry_price=100.0, entry_time=1000,
            config=ProtectiveConfig(stop_pct=0.05, is_trailing=True),
        )
        assert abs(ctrl.stop_price - 95.0) < 0.01
        # Price rises to 110 → stop trails to 104.5
        ctrl.update(110.0, 1010)
        assert abs(ctrl.stop_price - 104.5) < 0.01
        # Price drops to 105 → stop stays
        ctrl.update(105.0, 1020)
        assert abs(ctrl.stop_price - 104.5) < 0.01
        # Price drops to 104 → triggered
        action = ctrl.update(104.0, 1030)
        assert action.should_close
        assert action.reason == CloseReason.TRAILING_STOP


class TestProtectiveTakeProfit:
    def test_take_long(self):
        ctrl = ProtectiveController(
            side=PSide.LONG, entry_price=100.0, entry_time=1000,
            config=ProtectiveConfig(take_pct=0.10),
        )
        assert abs(ctrl.take_price - 110.0) < 0.01
        action = ctrl.update(111.0, 1010)
        assert action.should_close
        assert action.reason == CloseReason.TAKE_PROFIT


class TestProtectiveTimeout:
    def test_time_stop(self):
        ctrl = ProtectiveController(
            side=PSide.LONG, entry_price=100.0, entry_time=1000,
            config=ProtectiveConfig(timeout_seconds=300),
        )
        action = ctrl.update(100.0, 1200)
        assert not action.should_close
        action = ctrl.update(100.0, 1301)
        assert action.should_close
        assert action.reason == CloseReason.TIMEOUT
        assert action.use_market_order

    def test_already_closed(self):
        ctrl = ProtectiveController(
            side=PSide.LONG, entry_price=100.0, entry_time=1000,
            config=ProtectiveConfig(stop_offset=5.0),
        )
        ctrl.update(94.0, 1010)  # triggers stop
        action = ctrl.update(90.0, 1020)  # already closed
        assert not action.should_close
        assert "Already closed" in action.message


class TestProtectivePriceStep:
    def test_rounding(self):
        ctrl = ProtectiveController(
            side=PSide.LONG, entry_price=100.0, entry_time=1000,
            config=ProtectiveConfig(stop_offset=3.33, price_step=1.0),
        )
        # 100 - 3.33 = 96.67 → rounded to 97.0
        assert ctrl.stop_price == 97.0
