"""Tests for multi-analyst signal synthesis framework."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.strategy.signal_synthesis import (
    Action, Analyst, AnalystOpinion, BullBearCase, Conviction,
    Decision, DecisionMemory, SignalSynthesizer,
)


# ===========================================================================
# Helper analyst functions
# ===========================================================================

def always_buy(data):
    return AnalystOpinion(Action.BUY, Conviction.STRONG, 0.8, "Trend up")

def always_sell(data):
    return AnalystOpinion(Action.SELL, Conviction.STRONG, -0.8, "Trend down")

def neutral(data):
    return AnalystOpinion(Action.HOLD, Conviction.NEUTRAL, 0.0, "No signal")

def weak_buy(data):
    return AnalystOpinion(Action.BUY, Conviction.WEAK, 0.3, "Slight uptrend")

def weak_sell(data):
    return AnalystOpinion(Action.SELL, Conviction.WEAK, -0.3, "Slight downtrend")

def error_analyst(data):
    raise RuntimeError("API timeout")

def dynamic_analyst(data):
    price = data.get("close", 100)
    sma = data.get("sma", 100)
    if price > sma * 1.02:
        return AnalystOpinion(Action.BUY, Conviction.MODERATE, 0.5, f"Price {price} > SMA {sma}")
    elif price < sma * 0.98:
        return AnalystOpinion(Action.SELL, Conviction.MODERATE, -0.5, f"Price {price} < SMA {sma}")
    return AnalystOpinion(Action.HOLD, Conviction.NEUTRAL, 0.0, "Near SMA")


# ===========================================================================
# Tests — 20
# ===========================================================================


class TestSignalSynthesizer:

    def test_unanimous_buy(self):
        """All analysts agree → BUY with high confidence."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("trend", always_buy, weight=2.0))
        synth.add_analyst(Analyst("momentum", always_buy, weight=1.0))
        synth.add_analyst(Analyst("volume", always_buy, weight=1.0))
        d = synth.decide({})
        assert d.action == Action.BUY
        assert d.confidence > 0.7
        assert d.score > 0.5

    def test_unanimous_sell(self):
        """All analysts agree → SELL."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("a", always_sell))
        synth.add_analyst(Analyst("b", always_sell))
        d = synth.decide({})
        assert d.action == Action.SELL
        assert d.score < -0.5

    def test_disagreement_hold(self):
        """Analysts disagree → low confidence → HOLD."""
        synth = SignalSynthesizer(min_confidence=0.5)
        synth.add_analyst(Analyst("bull", always_buy, weight=1.0))
        synth.add_analyst(Analyst("bear", always_sell, weight=1.0))
        d = synth.decide({})
        # Score near 0, confidence low
        assert abs(d.score) < 0.1
        assert d.action == Action.HOLD

    def test_weight_matters(self):
        """Heavy-weighted bull overrides light bear."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("heavy_bull", always_buy, weight=5.0))
        synth.add_analyst(Analyst("light_bear", always_sell, weight=1.0))
        d = synth.decide({})
        assert d.action == Action.BUY
        assert d.score > 0

    def test_neutral_zone(self):
        """Weak signals in neutral zone → HOLD."""
        synth = SignalSynthesizer(buy_threshold=0.3, sell_threshold=-0.3)
        synth.add_analyst(Analyst("weak", weak_buy))
        d = synth.decide({})
        # Score 0.3 = exactly at threshold
        assert d.action in (Action.BUY, Action.HOLD)

    def test_error_analyst_ignored(self):
        """Failed analyst gets neutral opinion, doesn't crash."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("good", always_buy))
        synth.add_analyst(Analyst("broken", error_analyst))
        d = synth.decide({})
        assert d.action == Action.BUY  # good analyst wins
        assert "Error" in d.opinions["broken"].reasoning

    def test_dynamic_analyst_with_data(self):
        """Analyst uses market_data to form opinion."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("dynamic", dynamic_analyst))
        d_bull = synth.decide({"close": 110, "sma": 100})
        assert d_bull.score > 0
        d_bear = synth.decide({"close": 90, "sma": 100})
        assert d_bear.score < 0

    def test_bull_bear_case(self):
        """Bull/bear breakdown populated correctly."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("bull1", always_buy))
        synth.add_analyst(Analyst("bear1", always_sell))
        synth.add_analyst(Analyst("neutral1", neutral))
        d = synth.decide({})
        bb = d.bull_bear
        assert "bull1" in bb.bull_analysts
        assert "bear1" in bb.bear_analysts
        assert "neutral1" in bb.neutral_analysts
        assert bb.bull_score > 0
        assert bb.bear_score > 0

    def test_strongest_bull_bear_reasons(self):
        """Strongest reason tracked."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("strong", always_buy))
        synth.add_analyst(Analyst("weak_b", weak_sell))
        d = synth.decide({})
        assert "strong" in d.bull_bear.strongest_bull
        assert "weak_b" in d.bull_bear.strongest_bear

    def test_decision_has_all_opinions(self):
        """All analyst opinions in audit trail."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("a", always_buy))
        synth.add_analyst(Analyst("b", always_sell))
        d = synth.decide({})
        assert "a" in d.opinions
        assert "b" in d.opinions
        assert d.opinions["a"].action == Action.BUY
        assert d.opinions["b"].action == Action.SELL

    def test_confidence_range(self):
        """Confidence always in [0, 1]."""
        for buy_fn in [always_buy, always_sell, neutral, weak_buy]:
            synth = SignalSynthesizer()
            synth.add_analyst(Analyst("a", buy_fn))
            synth.add_analyst(Analyst("b", always_sell))
            d = synth.decide({})
            assert 0.0 <= d.confidence <= 1.0

    def test_score_range(self):
        """Score always in [-1, 1]."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("a", always_buy, weight=10))
        synth.add_analyst(Analyst("b", always_sell, weight=1))
        d = synth.decide({})
        assert -1.0 <= d.score <= 1.0

    def test_single_analyst(self):
        """Works with just one analyst."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("solo", always_buy))
        d = synth.decide({})
        assert d.action == Action.BUY

    def test_no_analysts(self):
        """No analysts → HOLD with zero confidence."""
        synth = SignalSynthesizer()
        d = synth.decide({})
        assert d.action == Action.HOLD
        assert d.score == 0.0

    def test_reasoning_not_empty(self):
        """Decision always has reasoning."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("a", always_buy))
        d = synth.decide({})
        assert len(d.reasoning) > 0

    def test_record_outcome_correct(self):
        """Record correct buy decision."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("a", always_buy))
        d = synth.decide({})
        mem = synth.record_outcome(d, "SBER", pnl=500.0)
        assert mem.was_correct
        assert "Correct" in mem.lesson

    def test_record_outcome_wrong(self):
        """Record wrong buy decision (lost money)."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("a", always_buy))
        d = synth.decide({})
        mem = synth.record_outcome(d, "SBER", pnl=-200.0)
        assert not mem.was_correct
        assert "Wrong" in mem.lesson

    def test_win_rate(self):
        """Win rate calculated from memory."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("a", always_buy))
        d = synth.decide({})
        synth.record_outcome(d, "SBER", 100)
        synth.record_outcome(d, "GAZP", -50)
        synth.record_outcome(d, "LKOH", 200)
        assert abs(synth.win_rate - 2 / 3) < 0.01

    def test_category_field(self):
        """Analyst category stored."""
        a = Analyst("llm", always_buy, category="llm")
        assert a.category == "llm"

    def test_multiple_categories(self):
        """Mix of quant and LLM analysts."""
        synth = SignalSynthesizer()
        synth.add_analyst(Analyst("trend", always_buy, weight=2, category="quant"))
        synth.add_analyst(Analyst("news_llm", weak_sell, weight=1, category="llm"))
        d = synth.decide({})
        # Quant weighted 2x → BUY despite LLM sell
        assert d.action == Action.BUY
        assert "trend" in d.bull_bear.bull_analysts
        assert "news_llm" in d.bull_bear.bear_analysts
