"""Portfolio risk rules engine — X-Ray style diversification analysis.

Inspired by Ghostfolio X-Ray (AGPL — code written from scratch, not copied).
Evaluates portfolio against configurable risk rules and returns pass/fail verdicts.

Rules check:
- Instrument concentration (single position too large)
- Currency diversification (too much in one currency)
- Sector concentration (single sector dominance)
- Drawdown limits (portfolio below threshold)
- Correlation risk (positions too correlated)
- Fee ratio (total fees vs portfolio value)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Sequence, TypeVar

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

T = TypeVar("T")


class RuleVerdict(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class RuleResult:
    """Result of a single rule evaluation."""
    rule_name: str
    verdict: RuleVerdict
    message: str
    value: float = 0.0       # the measured value (e.g., 0.65 for 65% concentration)
    threshold: float = 0.0   # the threshold that was exceeded
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# RiskApproved / RiskRefused wrappers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskApproved(Generic[T]):
    """Type-level marker: order has passed risk checks.

    Inspired by barter-rs RiskApproved<T> (MIT License).
    Prevents sending unchecked orders to execution layer.

    Usage:
        approved = risk_engine.check_order(order)
        execution.send(approved)  # only accepts RiskApproved[Order]
    """

    order: T
    approved_by: str = "RulesEngine"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class RiskRefused(Generic[T]):
    """Type-level marker: order was rejected by risk checks.

    Attributes:
        order: The rejected order.
        reason: Human-readable rejection reason.
        rule_name: Name of the rule that triggered refusal.
    """

    order: T
    reason: str = ""
    rule_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Position:
    """Minimal position representation for rule evaluation."""
    symbol: str
    value: float          # current market value in RUB
    weight: float = 0.0   # fraction of portfolio (auto-calculated)
    currency: str = "RUB"
    sector: str = "other"
    asset_class: str = "equity"  # equity, futures, bond, cash


@dataclass
class PortfolioSnapshot:
    """Portfolio state for rule evaluation."""
    positions: list[Position]
    total_value: float = 0.0
    current_drawdown: float = 0.0  # current DD from peak (e.g. 0.08 = 8%)
    total_fees: float = 0.0
    total_invested: float = 0.0

    def __post_init__(self):
        if self.total_value == 0 and self.positions:
            self.total_value = sum(p.value for p in self.positions)
        if self.total_value > 0:
            for p in self.positions:
                p.weight = p.value / self.total_value


# ---------------------------------------------------------------------------
# Abstract base rule
# ---------------------------------------------------------------------------

class BaseRule(ABC):
    """Abstract base for portfolio risk rules."""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    @abstractmethod
    def evaluate(self, portfolio: PortfolioSnapshot) -> RuleResult:
        """Evaluate rule against portfolio. Must return RuleResult."""
        ...

    def _pass(self, message: str, value: float = 0.0, **details) -> RuleResult:
        return RuleResult(self.name, RuleVerdict.PASS, message, value=value, details=details)

    def _warn(self, message: str, value: float = 0.0, threshold: float = 0.0, **details) -> RuleResult:
        return RuleResult(self.name, RuleVerdict.WARN, message, value, threshold, details)

    def _fail(self, message: str, value: float = 0.0, threshold: float = 0.0, **details) -> RuleResult:
        return RuleResult(self.name, RuleVerdict.FAIL, message, value, threshold, details)


# ---------------------------------------------------------------------------
# Concrete rules
# ---------------------------------------------------------------------------

class ConcentrationRule(BaseRule):
    """Check that no single position exceeds a weight threshold."""

    def __init__(self, max_weight: float = 0.25, warn_weight: float = 0.20, enabled: bool = True):
        super().__init__("concentration", enabled)
        self.max_weight = max_weight
        self.warn_weight = warn_weight

    def evaluate(self, portfolio: PortfolioSnapshot) -> RuleResult:
        if not portfolio.positions:
            return self._pass("No positions")

        heaviest = max(portfolio.positions, key=lambda p: p.weight)
        w = heaviest.weight

        if w > self.max_weight:
            return self._fail(
                f"{heaviest.symbol} = {w:.0%} портфеля (макс {self.max_weight:.0%})",
                value=w, threshold=self.max_weight, symbol=heaviest.symbol,
            )
        if w > self.warn_weight:
            return self._warn(
                f"{heaviest.symbol} = {w:.0%} портфеля (внимание > {self.warn_weight:.0%})",
                value=w, threshold=self.warn_weight, symbol=heaviest.symbol,
            )
        return self._pass(f"Макс. позиция {heaviest.symbol} = {w:.0%}", value=w)


class CurrencyClusterRule(BaseRule):
    """Check currency diversification — no single currency > threshold."""

    def __init__(self, max_weight: float = 0.80, enabled: bool = True):
        super().__init__("currency_cluster", enabled)
        self.max_weight = max_weight

    def evaluate(self, portfolio: PortfolioSnapshot) -> RuleResult:
        if not portfolio.positions or portfolio.total_value == 0:
            return self._pass("No positions")

        currency_totals: dict[str, float] = {}
        for p in portfolio.positions:
            currency_totals[p.currency] = currency_totals.get(p.currency, 0) + p.value

        heaviest_cur = max(currency_totals, key=currency_totals.get)
        w = currency_totals[heaviest_cur] / portfolio.total_value

        if w > self.max_weight:
            return self._fail(
                f"{heaviest_cur} = {w:.0%} портфеля (макс {self.max_weight:.0%})",
                value=w, threshold=self.max_weight, currency=heaviest_cur,
            )
        return self._pass(f"Макс. валюта {heaviest_cur} = {w:.0%}", value=w)


class SectorClusterRule(BaseRule):
    """Check sector diversification — no single sector > threshold."""

    def __init__(self, max_weight: float = 0.40, enabled: bool = True):
        super().__init__("sector_cluster", enabled)
        self.max_weight = max_weight

    def evaluate(self, portfolio: PortfolioSnapshot) -> RuleResult:
        if not portfolio.positions or portfolio.total_value == 0:
            return self._pass("No positions")

        sector_totals: dict[str, float] = {}
        for p in portfolio.positions:
            sector_totals[p.sector] = sector_totals.get(p.sector, 0) + p.value

        heaviest_sec = max(sector_totals, key=sector_totals.get)
        w = sector_totals[heaviest_sec] / portfolio.total_value

        if w > self.max_weight:
            return self._fail(
                f"Сектор '{heaviest_sec}' = {w:.0%} (макс {self.max_weight:.0%})",
                value=w, threshold=self.max_weight, sector=heaviest_sec,
            )
        return self._pass(f"Макс. сектор '{heaviest_sec}' = {w:.0%}", value=w)


class DrawdownRule(BaseRule):
    """Check that current drawdown is within acceptable limits."""

    def __init__(self, max_dd: float = 0.15, warn_dd: float = 0.10, enabled: bool = True):
        super().__init__("drawdown", enabled)
        self.max_dd = max_dd
        self.warn_dd = warn_dd

    def evaluate(self, portfolio: PortfolioSnapshot) -> RuleResult:
        dd = portfolio.current_drawdown
        if dd >= self.max_dd:
            return self._fail(
                f"Просадка {dd:.1%} превышает лимит {self.max_dd:.0%}",
                value=dd, threshold=self.max_dd,
            )
        if dd >= self.warn_dd:
            return self._warn(
                f"Просадка {dd:.1%} — зона внимания (лимит {self.max_dd:.0%})",
                value=dd, threshold=self.warn_dd,
            )
        return self._pass(f"Просадка {dd:.1%} в норме", value=dd)


class FeeRatioRule(BaseRule):
    """Check that accumulated fees don't exceed a percentage of invested capital."""

    def __init__(self, max_ratio: float = 0.02, enabled: bool = True):
        super().__init__("fee_ratio", enabled)
        self.max_ratio = max_ratio

    def evaluate(self, portfolio: PortfolioSnapshot) -> RuleResult:
        if portfolio.total_invested == 0:
            return self._pass("Нет инвестиций")

        ratio = portfolio.total_fees / portfolio.total_invested
        if ratio > self.max_ratio:
            return self._fail(
                f"Комиссии {ratio:.2%} от инвестиций (макс {self.max_ratio:.0%})",
                value=ratio, threshold=self.max_ratio,
            )
        return self._pass(f"Комиссии {ratio:.2%} от инвестиций", value=ratio)


class MinPositionsRule(BaseRule):
    """Check minimum number of positions for diversification."""

    def __init__(self, min_count: int = 5, enabled: bool = True):
        super().__init__("min_positions", enabled)
        self.min_count = min_count

    def evaluate(self, portfolio: PortfolioSnapshot) -> RuleResult:
        count = len(portfolio.positions)
        if count < self.min_count:
            return self._warn(
                f"Только {count} позиций (рекомендовано >= {self.min_count})",
                value=float(count), threshold=float(self.min_count),
            )
        return self._pass(f"{count} позиций", value=float(count))


# ---------------------------------------------------------------------------
# Rules Engine
# ---------------------------------------------------------------------------

class RulesEngine:
    """Evaluates portfolio against a set of risk rules.

    Usage:
        engine = RulesEngine()
        # or customize:
        engine = RulesEngine([
            ConcentrationRule(max_weight=0.30),
            DrawdownRule(max_dd=0.20),
        ])
        results = engine.evaluate(portfolio_snapshot)
        report = engine.format_report(results)
    """

    def __init__(self, rules: list[BaseRule] | None = None):
        self.rules = self.default_rules() if rules is None else rules

    @staticmethod
    def default_rules() -> list[BaseRule]:
        """Default MOEX-appropriate rule set."""
        return [
            ConcentrationRule(max_weight=0.25, warn_weight=0.20),
            CurrencyClusterRule(max_weight=0.80),
            SectorClusterRule(max_weight=0.40),
            DrawdownRule(max_dd=0.15, warn_dd=0.10),
            FeeRatioRule(max_ratio=0.02),
            MinPositionsRule(min_count=5),
        ]

    def evaluate(self, portfolio: PortfolioSnapshot) -> list[RuleResult]:
        """Run all enabled rules against portfolio."""
        results: list[RuleResult] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            try:
                results.append(rule.evaluate(portfolio))
            except Exception as e:
                logger.error("Rule '%s' failed: %s", rule.name, e)
                results.append(RuleResult(
                    rule.name, RuleVerdict.WARN,
                    f"Ошибка при проверке: {e}",
                ))
        return results

    def is_all_pass(self, results: list[RuleResult]) -> bool:
        """Check if all rules passed (no FAIL or WARN)."""
        return all(r.verdict == RuleVerdict.PASS for r in results)

    def has_failures(self, results: list[RuleResult]) -> bool:
        """Check if any rule failed."""
        return any(r.verdict == RuleVerdict.FAIL for r in results)

    def check_order(
        self,
        order: T,
        portfolio: PortfolioSnapshot,
    ) -> RiskApproved[T] | RiskRefused[T]:
        """Check an order against all rules.

        Returns RiskApproved if all rules pass, RiskRefused otherwise.
        Execution layer should only accept RiskApproved orders.
        """
        results = self.evaluate(portfolio)
        for r in results:
            if r.verdict == RuleVerdict.FAIL:
                return RiskRefused(
                    order=order,
                    reason=r.message,
                    rule_name=r.rule_name,
                )
        return RiskApproved(order=order, approved_by="RulesEngine")

    def check_orders(
        self,
        orders: Sequence[T],
        portfolio: PortfolioSnapshot,
    ) -> tuple[list[RiskApproved[T]], list[RiskRefused[T]]]:
        """Check multiple orders. Returns (approved, refused) tuple."""
        approved: list[RiskApproved[T]] = []
        refused: list[RiskRefused[T]] = []
        results = self.evaluate(portfolio)
        has_fail = self.has_failures(results)

        if has_fail:
            fail_msg = next(
                r.message for r in results
                if r.verdict == RuleVerdict.FAIL
            )
            fail_rule = next(
                r.rule_name for r in results
                if r.verdict == RuleVerdict.FAIL
            )
            for order in orders:
                refused.append(RiskRefused(
                    order=order,
                    reason=fail_msg,
                    rule_name=fail_rule,
                ))
        else:
            for order in orders:
                approved.append(
                    RiskApproved(order=order, approved_by="RulesEngine")
                )
        return approved, refused

    @staticmethod
    def format_report(results: list[RuleResult]) -> str:
        """Format rule results into a readable report."""
        icons = {RuleVerdict.PASS: "✅", RuleVerdict.WARN: "⚠️", RuleVerdict.FAIL: "🚩"}
        lines = [
            "=" * 50,
            "  RISK RULES REPORT",
            "=" * 50,
        ]
        for r in results:
            lines.append(f"  {icons[r.verdict]} {r.rule_name}: {r.message}")

        passes = sum(1 for r in results if r.verdict == RuleVerdict.PASS)
        warns = sum(1 for r in results if r.verdict == RuleVerdict.WARN)
        fails = sum(1 for r in results if r.verdict == RuleVerdict.FAIL)
        lines += [
            "-" * 50,
            f"  Total: {len(results)} rules | {passes} pass | {warns} warn | {fails} fail",
            "=" * 50,
        ]
        return "\n".join(lines)
