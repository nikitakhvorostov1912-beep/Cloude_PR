"""Конечный автомат (FSM) для управления диалогом.

States: IDLE -> GREETING -> LISTENING -> PROCESSING -> RESPONDING ->
        TASK_CREATING -> CONFIRMING -> FAREWELL -> COMPLETED
        Также: ESCALATING, ERROR

Персистентность через Redis (опционально).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DialogState(StrEnum):
    """Состояния диалога."""

    IDLE = "idle"
    GREETING = "greeting"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    TASK_CREATING = "task_creating"
    CONFIRMING = "confirming"
    FAREWELL = "farewell"
    COMPLETED = "completed"
    ESCALATING = "escalating"
    ERROR = "error"


class DialogEvent(StrEnum):
    """События, инициирующие переходы."""

    INCOMING_CALL = "incoming_call"
    GREETING_PLAYED = "greeting_played"
    SPEECH_RECOGNIZED = "speech_recognized"
    AI_RESPOND = "ai_respond"
    RESPONSE_PLAYED = "response_played"
    AI_CREATE_TASK = "ai_create_task"
    TASK_CREATED = "task_created"
    CLIENT_CONFIRMED = "client_confirmed"
    CLIENT_DENIED = "client_denied"
    AI_ESCALATE = "ai_escalate"
    FAREWELL_PLAYED = "farewell_played"
    CALL_ENDED = "call_ended"
    ERROR_OCCURRED = "error_occurred"
    TIMEOUT = "timeout"


# Таблица переходов: (текущее_состояние, событие) -> новое_состояние
TRANSITIONS: dict[tuple[DialogState, DialogEvent], DialogState] = {
    # Начало
    (DialogState.IDLE, DialogEvent.INCOMING_CALL): DialogState.GREETING,
    # Приветствие
    (DialogState.GREETING, DialogEvent.GREETING_PLAYED): DialogState.LISTENING,
    # Слушаем клиента
    (DialogState.LISTENING, DialogEvent.SPEECH_RECOGNIZED): DialogState.PROCESSING,
    (DialogState.LISTENING, DialogEvent.TIMEOUT): DialogState.RESPONDING,
    # Обработка AI
    (DialogState.PROCESSING, DialogEvent.AI_RESPOND): DialogState.RESPONDING,
    (DialogState.PROCESSING, DialogEvent.AI_CREATE_TASK): DialogState.TASK_CREATING,
    (DialogState.PROCESSING, DialogEvent.AI_ESCALATE): DialogState.ESCALATING,
    # Озвучиваем ответ
    (DialogState.RESPONDING, DialogEvent.RESPONSE_PLAYED): DialogState.LISTENING,
    # Создание задачи
    (DialogState.TASK_CREATING, DialogEvent.TASK_CREATED): DialogState.CONFIRMING,
    (DialogState.TASK_CREATING, DialogEvent.ERROR_OCCURRED): DialogState.ERROR,
    # Подтверждение
    (DialogState.CONFIRMING, DialogEvent.CLIENT_CONFIRMED): DialogState.FAREWELL,
    (DialogState.CONFIRMING, DialogEvent.CLIENT_DENIED): DialogState.LISTENING,
    (DialogState.CONFIRMING, DialogEvent.GREETING_PLAYED): DialogState.FAREWELL,
    # Прощание
    (DialogState.FAREWELL, DialogEvent.FAREWELL_PLAYED): DialogState.COMPLETED,
    # Эскалация
    (DialogState.ESCALATING, DialogEvent.CALL_ENDED): DialogState.COMPLETED,
    # Ошибка
    (DialogState.ERROR, DialogEvent.AI_ESCALATE): DialogState.ESCALATING,
    (DialogState.ERROR, DialogEvent.CALL_ENDED): DialogState.COMPLETED,
    # Глобальные переходы (из любого состояния)
    # Обрабатываются отдельно в transition()
}

# Состояния, из которых можно завершить по CALL_ENDED
CALL_ENDED_STATES = {
    DialogState.LISTENING,
    DialogState.PROCESSING,
    DialogState.RESPONDING,
    DialogState.GREETING,
    DialogState.CONFIRMING,
    DialogState.FAREWELL,
}


@dataclass
class TransitionRecord:
    """Запись о переходе состояния."""

    from_state: DialogState
    event: DialogEvent
    to_state: DialogState
    timestamp: float = field(default_factory=time.time)


Callback = Callable[[DialogState, DialogEvent, DialogState], Any]


class DialogStateMachine:
    """Конечный автомат диалога.

    Usage:
        fsm = DialogStateMachine(call_id="call-001")
        new_state = fsm.transition(DialogEvent.INCOMING_CALL)
        # new_state == DialogState.GREETING
    """

    def __init__(
        self,
        call_id: str,
        *,
        initial_state: DialogState = DialogState.IDLE,
    ) -> None:
        self._call_id = call_id
        self._state = initial_state
        self._history: list[TransitionRecord] = []
        self._on_enter: dict[DialogState, list[Callback]] = {}
        self._on_exit: dict[DialogState, list[Callback]] = {}
        self._on_any_transition: list[Callback] = []

    @property
    def state(self) -> DialogState:
        return self._state

    @property
    def call_id(self) -> str:
        return self._call_id

    @property
    def history(self) -> list[TransitionRecord]:
        return list(self._history)

    @property
    def is_terminal(self) -> bool:
        """Диалог завершён."""
        return self._state == DialogState.COMPLETED

    def transition(self, event: DialogEvent) -> DialogState:
        """Выполняет переход по событию.

        Args:
            event: Событие, инициирующее переход.

        Returns:
            Новое состояние.

        Raises:
            InvalidTransitionError: Если переход невозможен.
        """
        old_state = self._state

        # Глобальный CALL_ENDED
        if event == DialogEvent.CALL_ENDED and old_state in CALL_ENDED_STATES:
            new_state = DialogState.COMPLETED
        # Глобальный ERROR_OCCURRED
        elif event == DialogEvent.ERROR_OCCURRED and old_state not in {
            DialogState.COMPLETED,
            DialogState.ERROR,
        }:
            new_state = DialogState.ERROR
        else:
            key = (old_state, event)
            if key not in TRANSITIONS:
                raise InvalidTransitionError(
                    f"Невозможный переход: {old_state} + {event}"
                )
            new_state = TRANSITIONS[key]

        # Выполнение перехода
        record = TransitionRecord(
            from_state=old_state, event=event, to_state=new_state
        )
        self._history.append(record)

        logger.debug(
            "FSM [%s]: %s --%s--> %s",
            self._call_id,
            old_state,
            event,
            new_state,
        )

        # Callbacks
        self._fire_exit(old_state, event, new_state)
        self._state = new_state
        self._fire_enter(new_state, event, old_state)
        self._fire_any(old_state, event, new_state)

        return new_state

    def can_transition(self, event: DialogEvent) -> bool:
        """Проверяет возможность перехода."""
        if event == DialogEvent.CALL_ENDED and self._state in CALL_ENDED_STATES:
            return True
        if event == DialogEvent.ERROR_OCCURRED and self._state not in {
            DialogState.COMPLETED,
            DialogState.ERROR,
        }:
            return True
        return (self._state, event) in TRANSITIONS

    def on_enter(self, state: DialogState, callback: Callback) -> None:
        """Регистрирует callback при входе в состояние."""
        self._on_enter.setdefault(state, []).append(callback)

    def on_exit(self, state: DialogState, callback: Callback) -> None:
        """Регистрирует callback при выходе из состояния."""
        self._on_exit.setdefault(state, []).append(callback)

    def on_any_transition(self, callback: Callback) -> None:
        """Регистрирует callback на любой переход."""
        self._on_any_transition.append(callback)

    def _fire_enter(
        self, state: DialogState, event: DialogEvent, from_state: DialogState
    ) -> None:
        for cb in self._on_enter.get(state, []):
            try:
                cb(from_state, event, state)
            except Exception:
                logger.exception("Ошибка в on_enter callback для %s", state)

    def _fire_exit(
        self, state: DialogState, event: DialogEvent, to_state: DialogState
    ) -> None:
        for cb in self._on_exit.get(state, []):
            try:
                cb(state, event, to_state)
            except Exception:
                logger.exception("Ошибка в on_exit callback для %s", state)

    def _fire_any(
        self, from_state: DialogState, event: DialogEvent, to_state: DialogState
    ) -> None:
        for cb in self._on_any_transition:
            try:
                cb(from_state, event, to_state)
            except Exception:
                logger.exception("Ошибка в on_any_transition callback")

    def to_dict(self) -> dict:
        """Сериализация для Redis."""
        return {
            "call_id": self._call_id,
            "state": self._state.value,
            "history": [
                {
                    "from": r.from_state.value,
                    "event": r.event.value,
                    "to": r.to_state.value,
                    "ts": r.timestamp,
                }
                for r in self._history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> DialogStateMachine:
        """Десериализация из Redis."""
        fsm = cls(
            call_id=data["call_id"],
            initial_state=DialogState(data["state"]),
        )
        for h in data.get("history", []):
            fsm._history.append(
                TransitionRecord(
                    from_state=DialogState(h["from"]),
                    event=DialogEvent(h["event"]),
                    to_state=DialogState(h["to"]),
                    timestamp=h["ts"],
                )
            )
        return fsm


class InvalidTransitionError(Exception):
    """Невозможный переход состояния."""
