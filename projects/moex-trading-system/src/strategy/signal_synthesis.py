"""Multi-analyst signal synthesis framework for trading decisions.

Inspired by TauricResearch/TradingAgents (Apache 2.0) architecture.
Written from scratch. Works with BOTH quantitative signals AND LLM.

Architecture mirrors real trading firms:
  Analysts (quant indicators, ML models, LLM) → independent opinions
  Bull/Bear cases explicitly modeled
  Risk Judge weighs evidence → final BUY/HOLD/SELL + confidence

Two modes:
  1. Pure quant: analysts = indicator functions, no LLM needed
  2. Hybrid: some analysts are quant, some are LLM-powered

Usage (pure quant):
    from src.strategy.signal_synthesis import (
        SignalSynthesizer, Analyst, AnalystOpinion, Decision
    )

    synth = SignalSynthesizer()
    synth.add_analyst(Analyst("trend", trend_analyzer, weight=2.0))
    synth.add_analyst(Analyst("momentum", momentum_analyzer, weight=1.5))
    synth.add_analyst(Analyst("volume", volume_analyzer, weight=1.0))

    decision = synth.decide(market_data)
    print(decision.action, decision.confidence, decision.reasoning)

Usage (with LLM):
    synth.add_analyst(Analyst("llm_news", llm_news_analyzer, weight=1.0))
    decision = synth.decide(market_data)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Protocol


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Conviction(str, Enum):
    """Strength of analyst's opinion."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class AnalystOpinion:
    """One analyst's opinion on an instrument.

    Attributes:
        action: BUY/SELL/HOLD recommendation.
        conviction: Strength of the opinion.
        score: Numeric signal in [-1, +1]. -1 = strong sell, +1 = strong buy.
        reasoning: Human-readable explanation (for debugging/logging).
        metadata: Extra data (indicator values, LLM response, etc).
    """

    action: Action
    conviction: Conviction
    score: float  # [-1, +1]
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AnalystFn(Protocol):
    """Protocol for analyst functions.

    Takes market_data dict, returns AnalystOpinion.
    Can be a simple function or LLM call.
    """

    def __call__(self, market_data: dict[str, Any]) -> AnalystOpinion: ...


@dataclass
class Analyst:
    """Named analyst with weight.

    Attributes:
        name: Analyst identifier (e.g. "trend", "momentum", "llm_news").
        analyze: Callable that produces an AnalystOpinion.
        weight: Importance weight (default 1.0). Higher = more influence.
        category: "quant" | "ml" | "llm" | "fundamental".
    """

    name: str
    analyze: Callable[[dict[str, Any]], AnalystOpinion]
    weight: float = 1.0
    category: str = "quant"


@dataclass(frozen=True)
class BullBearCase:
    """Structured bull vs bear argument.

    Attributes:
        bull_score: Weighted sum of bullish opinions.
        bear_score: Weighted sum of bearish opinions.
        bull_analysts: Names of analysts recommending BUY.
        bear_analysts: Names of analysts recommending SELL.
        neutral_analysts: Names recommending HOLD.
        strongest_bull: Highest conviction bull reason.
        strongest_bear: Highest conviction bear reason.
    """

    bull_score: float
    bear_score: float
    bull_analysts: tuple[str, ...]
    bear_analysts: tuple[str, ...]
    neutral_analysts: tuple[str, ...]
    strongest_bull: str
    strongest_bear: str


@dataclass(frozen=True)
class Decision:
    """Final trading decision after synthesis.

    Attributes:
        action: BUY/SELL/HOLD.
        confidence: Confidence level [0, 1]. 0 = no confidence, 1 = certain.
        score: Weighted aggregate score [-1, +1].
        reasoning: Summary of why this decision was made.
        bull_bear: The bull/bear case breakdown.
        opinions: All analyst opinions for audit trail.
        timestamp: When the decision was made.
    """

    action: Action
    confidence: float
    score: float
    reasoning: str
    bull_bear: BullBearCase
    opinions: dict[str, AnalystOpinion]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class DecisionMemory:
    """Past decision with outcome — for learning from mistakes.

    Attributes:
        decision: The original decision.
        symbol: Instrument traded.
        outcome_pnl: Realized PnL from this decision.
        was_correct: Whether action direction was right.
        lesson: What to learn (auto-generated or manual).
    """

    decision: Decision
    symbol: str
    outcome_pnl: float = 0.0
    was_correct: bool = False
    lesson: str = ""


class SignalSynthesizer:
    """Multi-analyst signal synthesis engine.

    Collects opinions from multiple analysts (quant + optional LLM),
    builds bull/bear cases, and produces a weighted consensus decision.

    The synthesizer does NOT call a LLM itself — analysts may or may
    not use LLMs internally. The synthesis is pure math.

    Args:
        buy_threshold: Minimum score to trigger BUY (default 0.2).
        sell_threshold: Minimum negative score to trigger SELL (default -0.2).
        min_confidence: Minimum confidence to act (below → HOLD).
    """

    def __init__(
        self,
        buy_threshold: float = 0.2,
        sell_threshold: float = -0.2,
        min_confidence: float = 0.3,
    ) -> None:
        self._analysts: list[Analyst] = []
        self._buy_threshold = buy_threshold
        self._sell_threshold = sell_threshold
        self._min_confidence = min_confidence
        self._memory: list[DecisionMemory] = []

    def add_analyst(self, analyst: Analyst) -> None:
        """Register an analyst."""
        self._analysts.append(analyst)

    @property
    def analysts(self) -> list[str]:
        return [a.name for a in self._analysts]

    def decide(self, market_data: dict[str, Any]) -> Decision:
        """Run all analysts and synthesize a decision.

        Args:
            market_data: Dict with whatever data analysts need
                (prices, indicators, news, etc).

        Returns:
            Decision with action, confidence, reasoning.
        """
        # 1. Collect opinions
        opinions: dict[str, AnalystOpinion] = {}
        for analyst in self._analysts:
            try:
                opinion = analyst.analyze(market_data)
                opinions[analyst.name] = opinion
            except Exception as e:
                # Failed analyst → neutral opinion
                opinions[analyst.name] = AnalystOpinion(
                    action=Action.HOLD,
                    conviction=Conviction.NEUTRAL,
                    score=0.0,
                    reasoning=f"Error: {e}",
                )

        # 2. Build bull/bear case
        bull_bear = self._build_bull_bear(opinions)

        # 3. Calculate weighted score
        total_weight = sum(a.weight for a in self._analysts)
        if total_weight == 0:
            total_weight = 1.0

        weighted_score = sum(
            opinions[a.name].score * a.weight
            for a in self._analysts
        ) / total_weight

        # 4. Calculate confidence
        # High confidence when analysts AGREE, low when they DISAGREE
        scores = [opinions[a.name].score for a in self._analysts]
        if len(scores) > 1:
            import numpy as np
            score_std = float(np.std(scores))
            # Confidence = 1 - normalized disagreement
            max_std = 1.0  # max possible std for [-1, 1] range
            agreement = 1.0 - min(score_std / max_std, 1.0)
            # Also factor in absolute signal strength
            strength = min(abs(weighted_score) / 0.5, 1.0)
            confidence = agreement * 0.6 + strength * 0.4
        else:
            confidence = abs(weighted_score)

        confidence = max(0.0, min(1.0, confidence))

        # 5. Make decision
        if confidence < self._min_confidence:
            action = Action.HOLD
            reasoning = (
                f"Confidence too low ({confidence:.2f} < {self._min_confidence}). "
                f"Score={weighted_score:+.3f}. Analysts disagree."
            )
        elif weighted_score >= self._buy_threshold:
            action = Action.BUY
            reasoning = (
                f"BUY signal: score={weighted_score:+.3f}, "
                f"confidence={confidence:.2f}. "
                f"Bulls: {', '.join(bull_bear.bull_analysts)}. "
                f"Strongest: {bull_bear.strongest_bull}"
            )
        elif weighted_score <= self._sell_threshold:
            action = Action.SELL
            reasoning = (
                f"SELL signal: score={weighted_score:+.3f}, "
                f"confidence={confidence:.2f}. "
                f"Bears: {', '.join(bull_bear.bear_analysts)}. "
                f"Strongest: {bull_bear.strongest_bear}"
            )
        else:
            action = Action.HOLD
            reasoning = (
                f"HOLD: score={weighted_score:+.3f} in neutral zone "
                f"[{self._sell_threshold}, {self._buy_threshold}]."
            )

        return Decision(
            action=action,
            confidence=round(confidence, 4),
            score=round(weighted_score, 4),
            reasoning=reasoning,
            bull_bear=bull_bear,
            opinions=opinions,
        )

    def _build_bull_bear(
        self, opinions: dict[str, AnalystOpinion],
    ) -> BullBearCase:
        """Structure opinions into bull vs bear cases."""
        bulls: list[str] = []
        bears: list[str] = []
        neutrals: list[str] = []
        bull_score = 0.0
        bear_score = 0.0
        best_bull_reason = ""
        best_bear_reason = ""
        best_bull_score = 0.0
        best_bear_score = 0.0

        for analyst in self._analysts:
            op = opinions.get(analyst.name)
            if op is None:
                continue
            if op.score > 0:
                bulls.append(analyst.name)
                bull_score += op.score * analyst.weight
                if op.score > best_bull_score:
                    best_bull_score = op.score
                    best_bull_reason = f"{analyst.name}: {op.reasoning}"
            elif op.score < 0:
                bears.append(analyst.name)
                bear_score += abs(op.score) * analyst.weight
                if abs(op.score) > best_bear_score:
                    best_bear_score = abs(op.score)
                    best_bear_reason = f"{analyst.name}: {op.reasoning}"
            else:
                neutrals.append(analyst.name)

        return BullBearCase(
            bull_score=round(bull_score, 4),
            bear_score=round(bear_score, 4),
            bull_analysts=tuple(bulls),
            bear_analysts=tuple(bears),
            neutral_analysts=tuple(neutrals),
            strongest_bull=best_bull_reason or "none",
            strongest_bear=best_bear_reason or "none",
        )

    def record_outcome(
        self,
        decision: Decision,
        symbol: str,
        pnl: float,
    ) -> DecisionMemory:
        """Record past decision outcome for learning.

        Args:
            decision: The decision that was made.
            symbol: Instrument traded.
            pnl: Realized PnL.

        Returns:
            DecisionMemory for reflection.
        """
        was_correct = (
            (decision.action == Action.BUY and pnl > 0)
            or (decision.action == Action.SELL and pnl > 0)
            or (decision.action == Action.HOLD and abs(pnl) < 0.01)
        )
        lesson = (
            f"{'Correct' if was_correct else 'Wrong'} {decision.action.value} "
            f"on {symbol}: PnL={pnl:+.2f}. "
            f"Score was {decision.score:+.3f}, confidence {decision.confidence:.2f}."
        )
        mem = DecisionMemory(
            decision=decision,
            symbol=symbol,
            outcome_pnl=pnl,
            was_correct=was_correct,
            lesson=lesson,
        )
        self._memory.append(mem)
        return mem

    @property
    def memory(self) -> list[DecisionMemory]:
        return list(self._memory)

    @property
    def win_rate(self) -> float:
        """Win rate of past decisions."""
        if not self._memory:
            return 0.0
        correct = sum(1 for m in self._memory if m.was_correct)
        return correct / len(self._memory)
