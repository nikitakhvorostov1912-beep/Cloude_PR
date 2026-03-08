"""Tests for DialogueManager FSM."""

from __future__ import annotations

import pytest

from agents.voice_agent.dialogue_manager import DialogState, DialogueManager


class TestDialogueManager:
    """Test dialog state machine transitions and context."""

    def test_initial_state_is_greeting(self) -> None:
        mgr = DialogueManager("call-001")
        assert mgr.state == DialogState.GREETING

    def test_valid_transition_greeting_to_listening(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.transition(DialogState.LISTENING)
        assert mgr.state == DialogState.LISTENING

    def test_invalid_transition_raises(self) -> None:
        mgr = DialogueManager("call-001")
        with pytest.raises(ValueError, match="Invalid transition"):
            mgr.transition(DialogState.CLASSIFYING)

    def test_listening_to_clarifying(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.transition(DialogState.LISTENING)
        mgr.transition(DialogState.CLARIFYING)
        assert mgr.state == DialogState.CLARIFYING

    def test_listening_to_escalated(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.transition(DialogState.LISTENING)
        mgr.transition(DialogState.ESCALATED)
        assert mgr.state == DialogState.ESCALATED

    def test_full_happy_path(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.transition(DialogState.LISTENING)
        mgr.transition(DialogState.CLARIFYING)
        mgr.transition(DialogState.CLASSIFYING)
        mgr.transition(DialogState.CREATING_TASK)
        mgr.transition(DialogState.FAREWELL)
        mgr.transition(DialogState.CLOSED)
        assert mgr.state == DialogState.CLOSED
        assert not mgr.is_active

    def test_is_active(self) -> None:
        mgr = DialogueManager("call-001")
        assert mgr.is_active
        mgr.transition(DialogState.LISTENING)
        assert mgr.is_active

    def test_add_messages(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.add_user_message("Здравствуйте")
        mgr.add_assistant_message("Чем помочь?")
        assert len(mgr.context.messages) == 2
        assert mgr.context.messages[0]["role"] == "user"
        assert mgr.context.messages[1]["role"] == "assistant"

    def test_transcript_parts(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.add_user_message("Помогите")
        mgr.add_assistant_message("Конечно")
        transcript = mgr.context.full_transcript
        assert "Клиент: Помогите" in transcript
        assert "Оператор: Конечно" in transcript

    def test_questions_counter(self) -> None:
        mgr = DialogueManager("call-001", max_questions=3)
        assert mgr.context.can_ask_more
        mgr.increment_questions()
        mgr.increment_questions()
        assert mgr.context.can_ask_more
        mgr.increment_questions()
        assert not mgr.context.can_ask_more

    def test_set_client_info(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.set_client_info(name="Иванов", phone="+74951234567", product="БП")
        assert mgr.context.client_name == "Иванов"
        assert mgr.context.client_phone == "+74951234567"
        assert mgr.context.product == "БП"

    def test_set_classification(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.set_classification({"department": "support"})
        assert mgr.context.classification == {"department": "support"}

    def test_set_task_number(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.set_task_number("SAK-1234")
        assert mgr.context.task_number == "SAK-1234"

    def test_set_escalation(self) -> None:
        mgr = DialogueManager("call-001")
        mgr.set_escalation("Клиент просит оператора")
        assert mgr.context.escalation_reason == "Клиент просит оператора"
