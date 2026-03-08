"""Тесты AI Agent (Claude function calling)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ai_agent import (
    AgentAction,
    AgentResponse,
    AIAgent,
    DialogContext,
)


@pytest.fixture
def ai_agent():
    return AIAgent(
        api_key="test_key",
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        temperature=0.3,
        confidence_threshold=0.65,
        max_questions=5,
    )


@pytest.fixture
def dialog_context(ai_agent):
    return ai_agent.create_context(
        call_id="call-001",
        client_info={
            "found": True,
            "name": "ООО Ромашка",
            "product": "КА",
            "assigned_specialist": "Иванов Иван",
        },
    )


def _mock_text_response(text: str):
    """Создаёт мок ответа Claude с текстом."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    return response


def _mock_tool_response(tool_name: str, tool_input: dict, text: str = ""):
    """Создаёт мок ответа Claude с вызовом инструмента."""
    blocks = []
    if text:
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text
        blocks.append(text_block)

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input
    blocks.append(tool_block)

    response = MagicMock()
    response.content = blocks
    response.stop_reason = "tool_use"
    return response


# --- Контекст ---


class TestDialogContext:
    def test_create_context(self, ai_agent):
        """Контекст создаётся с правильными значениями."""
        ctx = ai_agent.create_context(
            call_id="call-001",
            client_info={"name": "Тест"},
        )
        assert ctx.call_id == "call-001"
        assert ctx.client_info == {"name": "Тест"}
        assert ctx.messages == []
        assert ctx.questions_asked == 0
        assert ctx.max_questions == 5

    def test_create_context_defaults(self, ai_agent):
        """Контекст без client_info."""
        ctx = ai_agent.create_context(call_id="call-002")
        assert ctx.client_info == {}


# --- Обработка ввода ---


class TestProcessInput:
    @pytest.mark.asyncio
    async def test_text_response(self, ai_agent, dialog_context):
        """Claude отвечает текстом -> RESPOND."""
        mock_response = _mock_text_response("Расскажите подробнее о проблеме.")

        with patch.object(
            ai_agent._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await ai_agent.process_input(
                "У нас проблема с документами", dialog_context
            )

        assert result.action == AgentAction.RESPOND
        assert "подробнее" in result.text
        assert result.classification is None

    @pytest.mark.asyncio
    async def test_low_stt_confidence_clarify(self, ai_agent, dialog_context):
        """Низкая уверенность STT -> CLARIFY."""
        result = await ai_agent.process_input(
            "мрмрмр", dialog_context, stt_confidence=0.3
        )

        assert result.action == AgentAction.CLARIFY
        assert result.needs_clarification is True
        assert "повторить" in result.text.lower()

    @pytest.mark.asyncio
    async def test_max_questions_escalate(self, ai_agent, dialog_context):
        """Превышен лимит вопросов -> ESCALATE."""
        dialog_context.questions_asked = 5

        result = await ai_agent.process_input(
            "Ещё один вопрос", dialog_context
        )

        assert result.action == AgentAction.ESCALATE
        assert result.escalation_reason == "max_questions_reached"
        assert "специалиста" in result.text.lower()

    @pytest.mark.asyncio
    async def test_messages_history_updated(self, ai_agent, dialog_context):
        """Сообщения добавляются в историю."""
        mock_response = _mock_text_response("Понял")

        with patch.object(
            ai_agent._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            await ai_agent.process_input("Привет", dialog_context)

        assert len(dialog_context.messages) == 2  # user + assistant
        assert dialog_context.messages[0]["role"] == "user"
        assert dialog_context.messages[0]["content"] == "Привет"

    @pytest.mark.asyncio
    async def test_questions_counter_increments(self, ai_agent, dialog_context):
        """Счётчик вопросов увеличивается."""
        mock_response = _mock_text_response("Какой продукт?")

        with patch.object(
            ai_agent._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            await ai_agent.process_input("Привет", dialog_context)

        assert dialog_context.questions_asked == 1


# --- Function Calling ---


class TestFunctionCalling:
    @pytest.mark.asyncio
    async def test_create_task_high_confidence(self, ai_agent, dialog_context):
        """Claude вызывает create_task с высокой уверенностью -> CREATE_TASK."""
        mock_response = _mock_tool_response(
            "create_task",
            {
                "department": "support",
                "product": "КА",
                "task_type": "error",
                "priority": "critical",
                "summary": "Не проводятся документы",
                "description": "С утра не проводятся документы в 1С КА",
                "confidence": 0.92,
            },
            text="Зарегистрирую обращение.",
        )

        with patch.object(
            ai_agent._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await ai_agent.process_input(
                "Документы не проводятся с утра!", dialog_context
            )

        assert result.action == AgentAction.CREATE_TASK
        assert result.classification is not None
        assert result.classification.department == "support"
        assert result.classification.priority == "critical"
        assert result.classification.confidence == 0.92

    @pytest.mark.asyncio
    async def test_create_task_low_confidence(self, ai_agent, dialog_context):
        """Claude вызывает create_task с низкой уверенностью -> CLARIFY."""
        mock_response = _mock_tool_response(
            "create_task",
            {
                "department": "support",
                "product": "Неизвестно",
                "task_type": "error",
                "priority": "normal",
                "summary": "Какая-то проблема",
                "description": "Непонятная проблема",
                "confidence": 0.4,
            },
            text="Хочу уточнить.",
        )

        with patch.object(
            ai_agent._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await ai_agent.process_input(
                "Что-то не работает", dialog_context
            )

        assert result.action == AgentAction.CLARIFY
        assert result.needs_clarification is True
        assert result.classification is not None
        assert result.classification.confidence == 0.4

    @pytest.mark.asyncio
    async def test_escalate_tool(self, ai_agent, dialog_context):
        """Claude вызывает escalate_to_operator -> ESCALATE."""
        mock_response = _mock_tool_response(
            "escalate_to_operator",
            {"reason": "Клиент просит живого человека"},
            text="Переведу на специалиста.",
        )

        with patch.object(
            ai_agent._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await ai_agent.process_input(
                "Позовите живого человека!", dialog_context
            )

        assert result.action == AgentAction.ESCALATE
        assert result.escalation_reason == "Клиент просит живого человека"

    @pytest.mark.asyncio
    async def test_invalid_classification_fallback(self, ai_agent, dialog_context):
        """Невалидная классификация -> fallback RESPOND."""
        mock_response = _mock_tool_response(
            "create_task",
            {"invalid_field": "bad"},
        )

        with patch.object(
            ai_agent._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await ai_agent.process_input(
                "Проблема", dialog_context
            )

        assert result.action == AgentAction.RESPOND
        assert "подробнее" in result.text.lower()


# --- API ошибки ---


class TestAPIErrors:
    @pytest.mark.asyncio
    async def test_api_error_escalates(self, ai_agent, dialog_context):
        """Ошибка API -> ESCALATE."""
        import anthropic

        with patch.object(
            ai_agent._client.messages,
            "create",
            new=AsyncMock(side_effect=anthropic.APIError(
                message="test error",
                request=MagicMock(),
                body=None,
            )),
        ):
            result = await ai_agent.process_input(
                "Привет", dialog_context
            )

        assert result.action == AgentAction.ESCALATE
        assert result.escalation_reason == "api_error"

    @pytest.mark.asyncio
    async def test_latency_tracked(self, ai_agent, dialog_context):
        """Латентность отслеживается."""
        mock_response = _mock_text_response("OK")

        with patch.object(
            ai_agent._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await ai_agent.process_input("Test", dialog_context)

        assert result.latency_ms >= 0
