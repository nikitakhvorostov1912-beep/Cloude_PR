"""Claude AI Agent — диалоговый агент с function calling.

Использует Anthropic SDK для ведения диалога с клиентом.
Вызывает функцию create_task когда собрал достаточно информации.

Модель: claude-sonnet-4-20250514
Макс. вопросов за диалог: 5
Порог уверенности: 0.65 (ниже -> уточнение)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import anthropic

from models.task import Classification
from prompts.agent_system import build_system_prompt

logger = logging.getLogger(__name__)


class AgentAction(StrEnum):
    """Действие агента после обработки ввода."""

    RESPOND = "respond"
    CREATE_TASK = "create_task"
    ESCALATE = "escalate"
    CLARIFY = "clarify"


@dataclass
class AgentResponse:
    """Ответ AI-агента."""

    action: AgentAction
    text: str
    classification: Classification | None = None
    needs_clarification: bool = False
    escalation_reason: str | None = None
    latency_ms: int = 0


@dataclass
class DialogContext:
    """Контекст диалога для AI-агента."""

    call_id: str
    client_info: dict = field(default_factory=dict)
    messages: list[dict[str, str]] = field(default_factory=list)
    questions_asked: int = 0
    max_questions: int = 5
    started_at: float = field(default_factory=time.time)


# Определение инструмента create_task для Claude
CREATE_TASK_TOOL = {
    "name": "create_task",
    "description": (
        "Создаёт задачу в 1С по результатам разговора с клиентом. "
        "Вызывай когда собрал достаточно информации: отдел, тип обращения, "
        "приоритет, описание проблемы."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "department": {
                "type": "string",
                "enum": [
                    "support",
                    "development",
                    "implementation",
                    "presale",
                    "specialist",
                ],
                "description": "Целевой отдел для маршрутизации",
            },
            "product": {
                "type": "string",
                "enum": [
                    "БП",
                    "КА",
                    "ЗУП",
                    "УТ",
                    "Розница",
                    "ERP",
                    "Кастомная",
                    "Неизвестно",
                ],
                "description": "Продукт 1С клиента",
            },
            "task_type": {
                "type": "string",
                "enum": ["error", "consult", "feature", "update", "project"],
                "description": "Тип обращения",
            },
            "priority": {
                "type": "string",
                "enum": ["critical", "high", "normal", "low"],
                "description": "Приоритет",
            },
            "summary": {
                "type": "string",
                "description": "Краткое описание (одна строка для карточки)",
            },
            "description": {
                "type": "string",
                "description": "Подробное описание проблемы словами клиента",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Уверенность в классификации (0.0-1.0)",
            },
        },
        "required": [
            "department",
            "product",
            "task_type",
            "priority",
            "summary",
            "description",
            "confidence",
        ],
    },
}

ESCALATE_TOOL = {
    "name": "escalate_to_operator",
    "description": (
        "Переводит звонок на живого оператора. Вызывай когда: "
        "клиент просит живого человека, не удаётся понять проблему "
        "после 2 уточнений, вопрос о ценах/договорах/скидках, "
        "производственная авария."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Причина эскалации",
            },
        },
        "required": ["reason"],
    },
}


class AIAgent:
    """Диалоговый AI-агент на базе Claude.

    Usage:
        agent = AIAgent(api_key="...", model="claude-sonnet-4-20250514")
        ctx = agent.create_context(call_id="call-001", client_info={...})
        response = await agent.process_input("У нас не проводятся документы", ctx)
        # response.action, response.text, response.classification
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
        temperature: float = 0.3,
        confidence_threshold: float = 0.65,
        max_questions: int = 5,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._confidence_threshold = confidence_threshold
        self._max_questions = max_questions

    def create_context(
        self, *, call_id: str, client_info: dict | None = None
    ) -> DialogContext:
        """Создаёт контекст нового диалога."""
        return DialogContext(
            call_id=call_id,
            client_info=client_info or {},
            max_questions=self._max_questions,
        )

    async def process_input(
        self,
        text: str,
        context: DialogContext,
        *,
        stt_confidence: float = 1.0,
    ) -> AgentResponse:
        """Обрабатывает пользовательский ввод и возвращает ответ.

        Args:
            text: Распознанный текст клиента.
            context: Контекст диалога.
            stt_confidence: Уверенность STT в распознавании.

        Returns:
            AgentResponse с действием и текстом ответа.
        """
        start_time = time.time()

        # Добавляем сообщение клиента в историю
        context.messages.append({"role": "user", "content": text})

        # Если STT уверенность низкая — просим повторить
        if stt_confidence < self._confidence_threshold:
            response = AgentResponse(
                action=AgentAction.CLARIFY,
                text="Извините, плохо расслышал. Можете повторить?",
                needs_clarification=True,
                latency_ms=int((time.time() - start_time) * 1000),
            )
            context.messages.append({"role": "assistant", "content": response.text})
            context.questions_asked += 1
            return response

        # Проверка лимита вопросов
        if context.questions_asked >= context.max_questions:
            return AgentResponse(
                action=AgentAction.ESCALATE,
                text=(
                    "Я задал уже достаточно вопросов. "
                    "Давайте я переведу вас на специалиста, "
                    "который сможет помочь более предметно."
                ),
                escalation_reason="max_questions_reached",
                latency_ms=int((time.time() - start_time) * 1000),
            )

        # Вызов Claude API
        system_prompt = build_system_prompt(context.client_info)

        try:
            api_response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system_prompt,
                tools=[CREATE_TASK_TOOL, ESCALATE_TOOL],
                messages=context.messages,
            )
        except anthropic.APIError:
            logger.exception("Ошибка Claude API")
            return AgentResponse(
                action=AgentAction.ESCALATE,
                text=(
                    "Произошла техническая ошибка. "
                    "Сейчас переведу вас на специалиста."
                ),
                escalation_reason="api_error",
                latency_ms=int((time.time() - start_time) * 1000),
            )

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Claude API: model=%s, latency=%dms, stop=%s",
            self._model,
            latency_ms,
            api_response.stop_reason,
        )

        return self._process_api_response(api_response, context, latency_ms)

    def _process_api_response(
        self,
        api_response: Any,
        context: DialogContext,
        latency_ms: int,
    ) -> AgentResponse:
        """Обрабатывает ответ Claude API."""
        text_parts: list[str] = []
        tool_use_block = None

        for block in api_response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_use_block = block

        response_text = " ".join(text_parts).strip()

        # Обработка вызова инструмента
        if tool_use_block is not None:
            if tool_use_block.name == "create_task":
                return self._handle_create_task(
                    tool_use_block.input,
                    response_text,
                    context,
                    latency_ms,
                )
            if tool_use_block.name == "escalate_to_operator":
                return self._handle_escalation(
                    tool_use_block.input,
                    response_text,
                    context,
                    latency_ms,
                )

        # Обычный текстовый ответ (вопрос/уточнение)
        if response_text:
            context.messages.append({"role": "assistant", "content": response_text})
            context.questions_asked += 1

        return AgentResponse(
            action=AgentAction.RESPOND,
            text=response_text or "Расскажите подробнее о вашей проблеме.",
            latency_ms=latency_ms,
        )

    def _handle_create_task(
        self,
        tool_input: dict,
        text: str,
        context: DialogContext,
        latency_ms: int,
    ) -> AgentResponse:
        """Обрабатывает вызов create_task от Claude."""
        logger.info("Claude вызвал create_task: %s", tool_input)

        try:
            classification = Classification(**tool_input)
        except Exception:
            logger.exception("Невалидная классификация от Claude")
            return AgentResponse(
                action=AgentAction.RESPOND,
                text="Давайте уточню: расскажите подробнее о вашей проблеме.",
                latency_ms=latency_ms,
            )

        # Проверка уверенности
        if classification.confidence < self._confidence_threshold:
            context.messages.append({"role": "assistant", "content": text})
            context.questions_asked += 1
            return AgentResponse(
                action=AgentAction.CLARIFY,
                text=(
                    text
                    or "Хочу уточнить, чтобы правильно зарегистрировать обращение. "
                    "Можете описать проблему подробнее?"
                ),
                classification=classification,
                needs_clarification=True,
                latency_ms=latency_ms,
            )

        # Уверенность достаточная — создаём задачу
        confirmation = (
            text
            or f"Понял, зарегистрирую обращение: {classification.summary}. "
            "Всё верно?"
        )
        context.messages.append({"role": "assistant", "content": confirmation})

        return AgentResponse(
            action=AgentAction.CREATE_TASK,
            text=confirmation,
            classification=classification,
            latency_ms=latency_ms,
        )

    def _handle_escalation(
        self,
        tool_input: dict,
        text: str,
        context: DialogContext,
        latency_ms: int,
    ) -> AgentResponse:
        """Обрабатывает вызов escalate_to_operator от Claude."""
        reason = tool_input.get("reason", "unknown")
        logger.info("Claude вызвал escalation: reason=%s", reason)

        escalation_text = (
            text
            or "Сейчас переведу вас на специалиста, который сможет помочь. "
            "Оставайтесь на линии."
        )
        context.messages.append({"role": "assistant", "content": escalation_text})

        return AgentResponse(
            action=AgentAction.ESCALATE,
            text=escalation_text,
            escalation_reason=reason,
            latency_ms=latency_ms,
        )
