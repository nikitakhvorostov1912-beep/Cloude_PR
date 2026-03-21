"""Tests for src/risk/rules.py — portfolio risk rules engine."""
from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.risk.rules import (
    ConcentrationRule,
    CurrencyClusterRule,
    DrawdownRule,
    FeeRatioRule,
    MinPositionsRule,
    PortfolioSnapshot,
    Position,
    RuleVerdict,
    RulesEngine,
    SectorClusterRule,
)


@pytest.fixture
def diversified_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        positions=[
            Position("SBER", 200_000, currency="RUB", sector="finance"),
            Position("GAZP", 180_000, currency="RUB", sector="energy"),
            Position("LKOH", 170_000, currency="RUB", sector="energy"),
            Position("YNDX", 150_000, currency="RUB", sector="tech"),
            Position("VTBR", 100_000, currency="RUB", sector="finance"),
            Position("MGNT", 100_000, currency="RUB", sector="retail"),
            Position("GMKN", 100_000, currency="USD", sector="metals"),
        ],
        total_value=1_000_000,
        current_drawdown=0.05,
        total_fees=5_000,
        total_invested=950_000,
    )


@pytest.fixture
def concentrated_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        positions=[
            Position("SBER", 700_000, currency="RUB", sector="finance"),
            Position("GAZP", 200_000, currency="RUB", sector="energy"),
            Position("LKOH", 100_000, currency="RUB", sector="energy"),
        ],
        total_value=1_000_000,
        current_drawdown=0.18,
        total_fees=30_000,
        total_invested=1_000_000,
    )


class TestConcentrationRule:
    def test_pass_diversified(self, diversified_portfolio):
        r = ConcentrationRule(max_weight=0.25).evaluate(diversified_portfolio)
        assert r.verdict == RuleVerdict.PASS

    def test_fail_concentrated(self, concentrated_portfolio):
        r = ConcentrationRule(max_weight=0.25).evaluate(concentrated_portfolio)
        assert r.verdict == RuleVerdict.FAIL
        assert "SBER" in r.message
        assert r.value == pytest.approx(0.7, rel=0.01)

    def test_warn_threshold(self, diversified_portfolio):
        r = ConcentrationRule(max_weight=0.25, warn_weight=0.15).evaluate(diversified_portfolio)
        assert r.verdict == RuleVerdict.WARN

    def test_empty_portfolio(self):
        r = ConcentrationRule().evaluate(PortfolioSnapshot(positions=[]))
        assert r.verdict == RuleVerdict.PASS


class TestCurrencyClusterRule:
    def test_pass_mostly_rub(self, diversified_portfolio):
        r = CurrencyClusterRule(max_weight=0.95).evaluate(diversified_portfolio)
        assert r.verdict == RuleVerdict.PASS

    def test_fail_too_much_rub(self, diversified_portfolio):
        r = CurrencyClusterRule(max_weight=0.50).evaluate(diversified_portfolio)
        assert r.verdict == RuleVerdict.FAIL
        assert "RUB" in r.message


class TestSectorClusterRule:
    def test_fail_energy_heavy(self):
        portfolio = PortfolioSnapshot(positions=[
            Position("GAZP", 400_000, sector="energy"),
            Position("LKOH", 350_000, sector="energy"),
            Position("SBER", 150_000, sector="finance"),
            Position("YNDX", 100_000, sector="tech"),
        ])
        r = SectorClusterRule(max_weight=0.40).evaluate(portfolio)
        assert r.verdict == RuleVerdict.FAIL
        assert "energy" in r.message

    def test_pass_balanced(self, diversified_portfolio):
        r = SectorClusterRule(max_weight=0.40).evaluate(diversified_portfolio)
        assert r.verdict == RuleVerdict.PASS


class TestDrawdownRule:
    def test_pass_low_dd(self, diversified_portfolio):
        r = DrawdownRule(max_dd=0.15).evaluate(diversified_portfolio)
        assert r.verdict == RuleVerdict.PASS

    def test_fail_high_dd(self, concentrated_portfolio):
        r = DrawdownRule(max_dd=0.15).evaluate(concentrated_portfolio)
        assert r.verdict == RuleVerdict.FAIL

    def test_warn_zone(self):
        p = PortfolioSnapshot(positions=[], current_drawdown=0.12)
        r = DrawdownRule(max_dd=0.15, warn_dd=0.10).evaluate(p)
        assert r.verdict == RuleVerdict.WARN


class TestFeeRatioRule:
    def test_pass_low_fees(self, diversified_portfolio):
        r = FeeRatioRule(max_ratio=0.02).evaluate(diversified_portfolio)
        assert r.verdict == RuleVerdict.PASS

    def test_fail_high_fees(self, concentrated_portfolio):
        r = FeeRatioRule(max_ratio=0.02).evaluate(concentrated_portfolio)
        assert r.verdict == RuleVerdict.FAIL


class TestMinPositionsRule:
    def test_pass_enough(self, diversified_portfolio):
        r = MinPositionsRule(min_count=5).evaluate(diversified_portfolio)
        assert r.verdict == RuleVerdict.PASS

    def test_warn_too_few(self, concentrated_portfolio):
        r = MinPositionsRule(min_count=5).evaluate(concentrated_portfolio)
        assert r.verdict == RuleVerdict.WARN


class TestRulesEngine:
    def test_all_pass_diversified(self, diversified_portfolio):
        # Default currency_cluster max=80%, but our portfolio is 90% RUB (realistic for MOEX)
        # Use MOEX-appropriate thresholds where RUB dominance is expected
        engine = RulesEngine([
            ConcentrationRule(max_weight=0.25),
            CurrencyClusterRule(max_weight=0.95),  # MOEX is RUB-dominated
            SectorClusterRule(max_weight=0.40),
            DrawdownRule(max_dd=0.15),
            FeeRatioRule(max_ratio=0.02),
            MinPositionsRule(min_count=5),
        ])
        results = engine.evaluate(diversified_portfolio)
        assert len(results) == 6
        assert engine.is_all_pass(results)
        assert not engine.has_failures(results)

    def test_has_failures_concentrated(self, concentrated_portfolio):
        engine = RulesEngine()
        results = engine.evaluate(concentrated_portfolio)
        assert engine.has_failures(results)

    def test_custom_rules(self, diversified_portfolio):
        engine = RulesEngine([ConcentrationRule(max_weight=0.10)])
        results = engine.evaluate(diversified_portfolio)
        assert len(results) == 1
        assert results[0].verdict == RuleVerdict.FAIL

    def test_format_report(self, diversified_portfolio):
        engine = RulesEngine()
        results = engine.evaluate(diversified_portfolio)
        report = engine.format_report(results)
        assert "RISK RULES REPORT" in report
        assert "pass" in report
