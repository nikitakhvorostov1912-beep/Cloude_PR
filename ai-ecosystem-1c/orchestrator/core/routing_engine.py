"""Routing engine — wraps deterministic rules + classifier agent."""

from __future__ import annotations

import logging
from typing import Optional

from agents.classifier.agent import ClassifierAgent
from agents.classifier.routing_rules import apply_deterministic_rules
from models.api.task import ClassificationResult

logger = logging.getLogger(__name__)


class RoutingEngine:
    """Central routing logic: rules → LLM → result.

    Orchestrates the two-phase classification and applies
    business rules for escalation and confidence thresholds.
    """

    def __init__(
        self,
        classifier: ClassifierAgent,
        *,
        escalation_threshold: float = 0.65,
        low_confidence_threshold: float = 0.80,
    ) -> None:
        self._classifier = classifier
        self._escalation_threshold = escalation_threshold
        self._low_confidence_threshold = low_confidence_threshold

    async def route(
        self,
        *,
        call_id: str,
        transcript: str,
        client_context: Optional[str] = None,
    ) -> RoutingDecision:
        """Classify and route a call.

        Returns a RoutingDecision with the classification and
        flags for escalation / low confidence.
        """
        classification = await self._classifier.classify(
            call_id=call_id,
            transcript=transcript,
            client_context=client_context,
        )

        needs_escalation = (
            classification.department_confidence < self._escalation_threshold
        )
        low_confidence = (
            classification.department_confidence < self._low_confidence_threshold
        )

        if needs_escalation:
            logger.warning(
                "call_id=%s below escalation threshold (%.2f < %.2f)",
                call_id,
                classification.department_confidence,
                self._escalation_threshold,
            )

        return RoutingDecision(
            classification=classification,
            needs_escalation=needs_escalation,
            low_confidence=low_confidence,
        )


class RoutingDecision:
    """Result of the routing engine with business-logic flags."""

    __slots__ = ("classification", "needs_escalation", "low_confidence")

    def __init__(
        self,
        *,
        classification: ClassificationResult,
        needs_escalation: bool,
        low_confidence: bool,
    ) -> None:
        self.classification = classification
        self.needs_escalation = needs_escalation
        self.low_confidence = low_confidence

    @property
    def should_create_task(self) -> bool:
        return not self.needs_escalation

    @property
    def warnings(self) -> list[str]:
        w = list(self.classification.warnings)
        if self.low_confidence:
            w.append("Низкая уверенность классификации — требуется проверка")
        if self.needs_escalation:
            w.append("Требуется эскалация на оператора")
        return w
