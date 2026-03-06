"""Тесты конечного автомата диалога (FSM)."""
from __future__ import annotations

import pytest

from core.state_machine import (
    DialogEvent,
    DialogState,
    DialogStateMachine,
    InvalidTransitionError,
)


@pytest.fixture
def fsm():
    return DialogStateMachine("call-001")


# --- Базовые переходы ---


class TestBasicTransitions:
    def test_initial_state(self, fsm):
        """Начальное состояние — IDLE."""
        assert fsm.state == DialogState.IDLE
        assert fsm.call_id == "call-001"

    def test_incoming_call(self, fsm):
        """IDLE -> GREETING."""
        new_state = fsm.transition(DialogEvent.INCOMING_CALL)
        assert new_state == DialogState.GREETING

    def test_greeting_played(self, fsm):
        """GREETING -> LISTENING."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        new_state = fsm.transition(DialogEvent.GREETING_PLAYED)
        assert new_state == DialogState.LISTENING

    def test_speech_recognized(self, fsm):
        """LISTENING -> PROCESSING."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        new_state = fsm.transition(DialogEvent.SPEECH_RECOGNIZED)
        assert new_state == DialogState.PROCESSING

    def test_ai_respond(self, fsm):
        """PROCESSING -> RESPONDING."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        fsm.transition(DialogEvent.SPEECH_RECOGNIZED)
        new_state = fsm.transition(DialogEvent.AI_RESPOND)
        assert new_state == DialogState.RESPONDING

    def test_response_played(self, fsm):
        """RESPONDING -> LISTENING (цикл)."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        fsm.transition(DialogEvent.SPEECH_RECOGNIZED)
        fsm.transition(DialogEvent.AI_RESPOND)
        new_state = fsm.transition(DialogEvent.RESPONSE_PLAYED)
        assert new_state == DialogState.LISTENING


# --- Путь создания задачи ---


class TestTaskCreationPath:
    def test_full_happy_path(self, fsm):
        """Полный путь: IDLE -> ... -> COMPLETED."""
        fsm.transition(DialogEvent.INCOMING_CALL)  # GREETING
        fsm.transition(DialogEvent.GREETING_PLAYED)  # LISTENING
        fsm.transition(DialogEvent.SPEECH_RECOGNIZED)  # PROCESSING
        fsm.transition(DialogEvent.AI_CREATE_TASK)  # TASK_CREATING
        fsm.transition(DialogEvent.TASK_CREATED)  # CONFIRMING
        fsm.transition(DialogEvent.CLIENT_CONFIRMED)  # FAREWELL
        new_state = fsm.transition(DialogEvent.FAREWELL_PLAYED)  # COMPLETED
        assert new_state == DialogState.COMPLETED
        assert fsm.is_terminal

    def test_client_denied_returns_to_listening(self, fsm):
        """Клиент не подтвердил -> обратно к LISTENING."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        fsm.transition(DialogEvent.SPEECH_RECOGNIZED)
        fsm.transition(DialogEvent.AI_CREATE_TASK)
        fsm.transition(DialogEvent.TASK_CREATED)
        new_state = fsm.transition(DialogEvent.CLIENT_DENIED)
        assert new_state == DialogState.LISTENING


# --- Эскалация ---


class TestEscalation:
    def test_escalation_from_processing(self, fsm):
        """PROCESSING -> ESCALATING."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        fsm.transition(DialogEvent.SPEECH_RECOGNIZED)
        new_state = fsm.transition(DialogEvent.AI_ESCALATE)
        assert new_state == DialogState.ESCALATING

    def test_escalation_ends_with_call_ended(self, fsm):
        """ESCALATING -> COMPLETED."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        fsm.transition(DialogEvent.SPEECH_RECOGNIZED)
        fsm.transition(DialogEvent.AI_ESCALATE)
        new_state = fsm.transition(DialogEvent.CALL_ENDED)
        assert new_state == DialogState.COMPLETED


# --- Глобальные переходы ---


class TestGlobalTransitions:
    def test_call_ended_from_listening(self, fsm):
        """LISTENING + CALL_ENDED -> COMPLETED."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        new_state = fsm.transition(DialogEvent.CALL_ENDED)
        assert new_state == DialogState.COMPLETED

    def test_call_ended_from_greeting(self, fsm):
        """GREETING + CALL_ENDED -> COMPLETED."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        new_state = fsm.transition(DialogEvent.CALL_ENDED)
        assert new_state == DialogState.COMPLETED

    def test_error_from_listening(self, fsm):
        """LISTENING + ERROR -> ERROR."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        new_state = fsm.transition(DialogEvent.ERROR_OCCURRED)
        assert new_state == DialogState.ERROR

    def test_error_then_escalate(self, fsm):
        """ERROR -> ESCALATING."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        fsm.transition(DialogEvent.ERROR_OCCURRED)
        new_state = fsm.transition(DialogEvent.AI_ESCALATE)
        assert new_state == DialogState.ESCALATING


# --- Невозможные переходы ---


class TestInvalidTransitions:
    def test_invalid_transition_raises(self, fsm):
        """Невозможный переход -> исключение."""
        with pytest.raises(InvalidTransitionError):
            fsm.transition(DialogEvent.GREETING_PLAYED)

    def test_completed_state_is_terminal(self, fsm):
        """Из COMPLETED нельзя перейти."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        fsm.transition(DialogEvent.CALL_ENDED)
        assert fsm.is_terminal

        with pytest.raises(InvalidTransitionError):
            fsm.transition(DialogEvent.INCOMING_CALL)


# --- Утилиты ---


class TestFSMUtilities:
    def test_can_transition(self, fsm):
        """can_transition проверяет возможность перехода."""
        assert fsm.can_transition(DialogEvent.INCOMING_CALL) is True
        assert fsm.can_transition(DialogEvent.GREETING_PLAYED) is False

    def test_history(self, fsm):
        """История переходов записывается."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        assert len(fsm.history) == 2
        assert fsm.history[0].from_state == DialogState.IDLE
        assert fsm.history[0].to_state == DialogState.GREETING

    def test_to_dict(self, fsm):
        """Сериализация в dict."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        data = fsm.to_dict()
        assert data["call_id"] == "call-001"
        assert data["state"] == "greeting"
        assert len(data["history"]) == 1

    def test_from_dict(self, fsm):
        """Десериализация из dict."""
        fsm.transition(DialogEvent.INCOMING_CALL)
        fsm.transition(DialogEvent.GREETING_PLAYED)
        data = fsm.to_dict()

        restored = DialogStateMachine.from_dict(data)
        assert restored.state == DialogState.LISTENING
        assert restored.call_id == "call-001"
        assert len(restored.history) == 2

    def test_callbacks(self, fsm):
        """Callbacks вызываются при переходах."""
        entered = []
        exited = []

        fsm.on_enter(
            DialogState.GREETING,
            lambda f, e, t: entered.append((f, e, t)),
        )
        fsm.on_exit(
            DialogState.IDLE,
            lambda f, e, t: exited.append((f, e, t)),
        )

        fsm.transition(DialogEvent.INCOMING_CALL)

        assert len(entered) == 1
        assert entered[0][2] == DialogState.GREETING
        assert len(exited) == 1
        assert exited[0][0] == DialogState.IDLE
