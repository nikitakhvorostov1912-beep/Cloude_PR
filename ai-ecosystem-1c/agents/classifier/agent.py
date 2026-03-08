"""Classifier agent — two-phase classification: deterministic rules → LLM.

Phase 1: Apply keyword-based routing rules (fast, no API cost).
Phase 2: If rules don't match or have low confidence, use Claude LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.classifier.prompts import build_classifier_system_prompt
from agents.classifier.routing_rules import apply_deterministic_rules
from models.api.task import (
    ClassificationResult,
    Department,
    Priority,
    Product,
    TaskType,
)
from services.llm.claude_client import ClaudeClient
from services.llm.function_calling import get_classifier_tools

logger = logging.getLogger(__name__)


class ClassifierAgent(BaseAgent):
    """Two-phase classifier: deterministic rules first, then LLM fallback."""

    def __init__(self, llm: ClaudeClient) -> None:
        super().__init__(name="classifier", max_retries=2)
        self._llm = llm

    async def classify(
        self,
        *,
        call_id: str,
        transcript: str,
        client_context: Optional[str] = None,
    ) -> ClassificationResult:
        """Classify a call transcript.

        Returns ClassificationResult with the classification and routing info.
        """
        return await self.execute_with_retry(
            call_id=call_id,
            transcript=transcript,
            client_context=client_context,
        )

    async def _execute(self, *, call_id: str, **kwargs: Any) -> ClassificationResult:
        transcript: str = kwargs["transcript"]
        client_context: Optional[str] = kwargs.get("client_context")

        # Phase 1: Deterministic rules
        rule_result = apply_deterministic_rules(transcript)
        if rule_result is not None and rule_result.confidence >= 0.80:
            logger.info(
                "call_id=%s deterministic_rule=%s confidence=%.2f",
                call_id,
                rule_result.rule,
                rule_result.confidence,
            )
            return ClassificationResult(
                department=rule_result.department,
                department_confidence=rule_result.confidence,
                department_reason=f"Детерминированное правило: {rule_result.rule}",
                task_type=rule_result.task_type or TaskType.CONSULT,
                task_type_confidence=rule_result.confidence,
                priority=rule_result.priority or Priority.NORMAL,
                priority_confidence=rule_result.confidence * 0.9,
                priority_reason="Определено по ключевым словам",
                description=transcript[:500],
                summary=transcript[:200],
                used_deterministic_rule=rule_result.rule,
            )

        # Phase 2: LLM classification
        logger.info("call_id=%s routing to LLM classifier", call_id)
        return await self._classify_with_llm(
            call_id=call_id,
            transcript=transcript,
            client_context=client_context,
        )

    async def _classify_with_llm(
        self,
        *,
        call_id: str,
        transcript: str,
        client_context: Optional[str] = None,
    ) -> ClassificationResult:
        """Use Claude to classify the transcript via function calling."""
        system = build_classifier_system_prompt(client_context=client_context)

        response = await self._llm.classify(
            system=system,
            transcript=transcript,
            client_context=client_context,
            tools=get_classifier_tools(),
        )

        self._metrics.total_tokens += response.total_tokens

        if not response.has_tool_calls:
            logger.warning(
                "call_id=%s LLM did not call any tool, text=%s",
                call_id,
                response.text[:200],
            )
            return self._fallback_classification(transcript, response.text)

        tool = response.tool_calls[0]
        if tool["name"] == "escalate_to_operator":
            return self._escalation_classification(tool["input"])

        if tool["name"] == "create_task":
            return self._parse_tool_result(tool["input"], response)

        logger.warning("call_id=%s unknown tool: %s", call_id, tool["name"])
        return self._fallback_classification(transcript, response.text)

    def _parse_tool_result(
        self,
        tool_input: dict[str, Any],
        response: Any,
    ) -> ClassificationResult:
        """Parse create_task tool call into ClassificationResult."""
        department = Department(tool_input.get("department", "support"))
        task_type = TaskType(tool_input.get("task_type", "consult"))
        priority = Priority(tool_input.get("priority", "normal"))

        product_raw = tool_input.get("product")
        product = None
        if product_raw:
            try:
                product = Product(product_raw)
            except ValueError:
                product = Product.UNKNOWN

        return ClassificationResult(
            department=department,
            department_confidence=0.85,
            department_reason=tool_input.get("reasoning", "Классификация через LLM"),
            task_type=task_type,
            task_type_confidence=0.80,
            priority=priority,
            priority_confidence=0.80,
            priority_reason=tool_input.get("reasoning", ""),
            product=product,
            product_confidence=0.75 if product else 0.0,
            description=tool_input.get("description", ""),
            summary=tool_input.get("title", "")[:500],
            reasoning=tool_input.get("reasoning", ""),
            llm_model=response.model,
            tokens_used=response.total_tokens,
        )

    def _escalation_classification(
        self,
        tool_input: dict[str, Any],
    ) -> ClassificationResult:
        """Build a classification for escalation cases."""
        dept_hint = tool_input.get("department_hint", "support")
        try:
            department = Department(dept_hint)
        except ValueError:
            department = Department.SUPPORT

        priority_raw = tool_input.get("priority", "normal")
        try:
            priority = Priority(priority_raw)
        except ValueError:
            priority = Priority.NORMAL

        return ClassificationResult(
            department=department,
            department_confidence=0.40,
            department_reason=f"Эскалация: {tool_input.get('reason', 'не указано')}",
            task_type=TaskType.CONSULT,
            task_type_confidence=0.30,
            priority=priority,
            priority_confidence=0.50,
            priority_reason="Требуется ручная обработка",
            description=tool_input.get("context_summary", ""),
            summary="Эскалация на оператора",
            reasoning=tool_input.get("reason", ""),
            warnings=["Требуется ручная классификация"],
        )

    @staticmethod
    def _fallback_classification(
        transcript: str,
        llm_text: str,
    ) -> ClassificationResult:
        """Last resort: return low-confidence classification."""
        return ClassificationResult(
            department=Department.SUPPORT,
            department_confidence=0.30,
            department_reason="Не удалось классифицировать автоматически",
            task_type=TaskType.CONSULT,
            task_type_confidence=0.30,
            priority=Priority.NORMAL,
            priority_confidence=0.50,
            priority_reason="Приоритет по умолчанию",
            description=transcript[:500],
            summary=llm_text[:200] if llm_text else transcript[:200],
            reasoning="Fallback: LLM не вызвал инструмент классификации",
            warnings=["Низкая уверенность", "Требуется ручная проверка"],
        )
