"""Flexible commission rules engine for backtesting.

Ported from StockSharp CommissionRule architecture (Apache 2.0) to Python.
Supports MOEX-specific commission models:
- Percentage of turnover (equities: ~0.01%)
- Fixed per contract (futures: ~2 RUB)
- Tiered by volume / turnover thresholds
- Per-order and per-trade rules

Usage:
    manager = CommissionManager([
        PercentOfTurnoverRule(0.0001),       # 0.01% of turnover
        FixedPerContractRule(2.0),            # 2 RUB per futures contract
        MinCommissionRule(min_value=0.01),    # minimum 1 kopek
    ])
    fee = manager.calculate(price=280.5, volume=10, instrument_type="equity")
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

@dataclass
class TradeInfo:
    """Minimal trade/order info for commission calculation."""
    price: float
    volume: float
    instrument_type: str = "equity"   # equity, futures, options, fx
    symbol: str = ""
    board: str = ""                   # TQBR, FORTS, etc.
    is_maker: bool = False            # maker vs taker


class CommissionRule(ABC):
    """Abstract commission calculation rule."""

    @abstractmethod
    def calculate(self, trade: TradeInfo) -> float | None:
        """Calculate commission for a trade. Returns None if rule doesn't apply."""
        ...

    def reset(self) -> None:
        """Reset accumulated state (for stateful rules like turnover)."""
        pass


# ---------------------------------------------------------------------------
# Concrete rules
# ---------------------------------------------------------------------------

class PercentOfTurnoverRule(CommissionRule):
    """Commission as percentage of trade turnover (price × volume).

    MOEX equities: ~0.01% (0.0001)
    """

    def __init__(self, rate: float = 0.0001):
        self.rate = rate

    def calculate(self, trade: TradeInfo) -> float | None:
        return trade.price * trade.volume * self.rate


class FixedPerContractRule(CommissionRule):
    """Fixed amount per contract/lot.

    MOEX futures: ~2 RUB per contract
    """

    def __init__(self, per_contract: float = 2.0):
        self.per_contract = per_contract

    def calculate(self, trade: TradeInfo) -> float | None:
        return trade.volume * self.per_contract


class FixedPerOrderRule(CommissionRule):
    """Fixed amount per order regardless of volume."""

    def __init__(self, per_order: float = 1.0):
        self.per_order = per_order

    def calculate(self, trade: TradeInfo) -> float | None:
        return self.per_order


class InstrumentTypeRule(CommissionRule):
    """Route to different rules based on instrument type."""

    def __init__(self, rules: dict[str, CommissionRule]):
        self.rules = rules

    def calculate(self, trade: TradeInfo) -> float | None:
        rule = self.rules.get(trade.instrument_type)
        if rule:
            return rule.calculate(trade)
        return None


class TurnoverTierRule(CommissionRule):
    """Tiered commission based on cumulative daily turnover.

    Lower rates after reaching turnover thresholds.
    """

    def __init__(self, tiers: list[tuple[float, float]]):
        """
        Args:
            tiers: List of (turnover_threshold, rate) sorted ascending.
                   e.g. [(0, 0.0003), (1_000_000, 0.0002), (10_000_000, 0.0001)]
        """
        self.tiers = sorted(tiers, key=lambda t: t[0])
        self._cumulative_turnover: float = 0.0

    def calculate(self, trade: TradeInfo) -> float | None:
        turnover = trade.price * trade.volume
        self._cumulative_turnover += turnover

        rate = self.tiers[0][1]
        for threshold, tier_rate in self.tiers:
            if self._cumulative_turnover >= threshold:
                rate = tier_rate
        return turnover * rate

    def reset(self) -> None:
        self._cumulative_turnover = 0.0


class MakerTakerRule(CommissionRule):
    """Different rates for maker vs taker orders."""

    def __init__(self, maker_rate: float = 0.00005, taker_rate: float = 0.0001):
        self.maker_rate = maker_rate
        self.taker_rate = taker_rate

    def calculate(self, trade: TradeInfo) -> float | None:
        rate = self.maker_rate if trade.is_maker else self.taker_rate
        return trade.price * trade.volume * rate


class MinCommissionRule(CommissionRule):
    """Ensures minimum commission per trade."""

    def __init__(self, inner: CommissionRule | None = None, min_value: float = 0.01):
        self.inner = inner
        self.min_value = min_value

    def calculate(self, trade: TradeInfo) -> float | None:
        if self.inner:
            result = self.inner.calculate(trade)
            if result is not None:
                return max(result, self.min_value)
        return self.min_value


class SymbolOverrideRule(CommissionRule):
    """Override commission for specific symbols."""

    def __init__(self, overrides: dict[str, CommissionRule], default: CommissionRule | None = None):
        self.overrides = overrides
        self.default = default

    def calculate(self, trade: TradeInfo) -> float | None:
        rule = self.overrides.get(trade.symbol, self.default)
        if rule:
            return rule.calculate(trade)
        return None


# ---------------------------------------------------------------------------
# Commission Manager
# ---------------------------------------------------------------------------

class CommissionManager:
    """Aggregates multiple commission rules.

    Rules are evaluated in order. First non-None result is used.
    Or use mode='sum' to sum all applicable rules.
    """

    def __init__(self, rules: list[CommissionRule], mode: str = "first"):
        """
        Args:
            rules: Commission rules to apply.
            mode: 'first' = use first matching rule, 'sum' = sum all rules.
        """
        self.rules = rules
        self.mode = mode

    def calculate(self, price: float, volume: float, instrument_type: str = "equity",
                  symbol: str = "", board: str = "", is_maker: bool = False) -> float:
        """Calculate commission for a trade.

        Returns:
            Commission amount (always >= 0).
        """
        trade = TradeInfo(price, volume, instrument_type, symbol, board, is_maker)

        if self.mode == "sum":
            total = 0.0
            for rule in self.rules:
                result = rule.calculate(trade)
                if result is not None:
                    total += result
            return total

        for rule in self.rules:
            result = rule.calculate(trade)
            if result is not None:
                return result
        return 0.0

    def reset(self) -> None:
        """Reset all stateful rules (call at start of each trading day)."""
        for rule in self.rules:
            rule.reset()

    @staticmethod
    def moex_default() -> CommissionManager:
        """Pre-configured MOEX commission model."""
        return CommissionManager(
            rules=[
                InstrumentTypeRule({
                    "equity": PercentOfTurnoverRule(0.0001),      # 0.01%
                    "futures": FixedPerContractRule(2.0),          # 2 RUB
                    "options": FixedPerContractRule(2.0),          # 2 RUB
                    "fx": PercentOfTurnoverRule(0.00003),         # 0.003%
                }),
            ],
            mode="first",
        )
