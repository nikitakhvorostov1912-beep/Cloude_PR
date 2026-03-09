"""Finite State Machine for voice dialog lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional


class DialogState(StrEnum):
    """Dialog FSM states."""

    GREETING = "greeting"
    LISTENING = "listening"
    CLARIFYING = "clarifying"
    CLASSIFYING = "classifying"
    CREATING_TASK = "creating_task"
    ESCALATED = "escalated"
    FAREWELL = "farewell"
    CLOSED = "closed"


@dataclass
class DialogContext:
    """Mutable context accumulated during the dialog."""

    call_id: str
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    product: Optional[str] = None

    messages: list[dict[str, Any]] = field(default_factory=list)
    questions_asked: int = 0
    max_questions: int = 5

    transcript_parts: list[str] = field(default_factory=list)
    key_phrases: list[str] = field(default_factory=list)

    classification: Optional[dict[str, Any]] = None
    task_number: Optional[str] = None
    escalation_reason: Optional[str] = None

    @property
    def full_transcript(self) -> str:
        return "\n".join(self.transcript_parts)

    @property
    def can_ask_more(self) -> bool:
        return self.questions_asked < self.max_questions


class DialogueManager:
    """Manages dialog state transitions and context accumulation."""

    def __init__(self, call_id: str, *, max_questions: int = 5) -> None:
        self._state = DialogState.GREETING
        self._context = DialogContext(call_id=call_id, max_questions=max_questions)
        self._transitions: dict[DialogState, set[DialogState]] = {
            DialogState.GREETING: {DialogState.LISTENING},
            DialogState.LISTENING: {
                DialogState.CLARIFYING,
                DialogState.CLASSIFYING,
                DialogState.ESCALATED,
            },
            DialogState.CLARIFYING: {
                DialogState.LISTENING,
                DialogState.CLASSIFYING,
                DialogState.ESCALATED,
            },
            DialogState.CLASSIFYING: {
                DialogState.CREATING_TASK,
                DialogState.ESCALATED,
            },
            DialogState.CREATING_TASK: {DialogState.FAREWELL},
            DialogState.ESCALATED: {DialogState.FAREWELL, DialogState.CLOSED},
            DialogState.FAREWELL: {DialogState.CLOSED},
            DialogState.CLOSED: set(),
        }

    @property
    def state(self) -> DialogState:
        return self._state

    @property
    def context(self) -> DialogContext:
        return self._context

    @property
    def is_active(self) -> bool:
        return self._state not in (DialogState.CLOSED, DialogState.FAREWELL)

    def transition(self, target: DialogState) -> None:
        """Move to a new state if the transition is valid."""
        valid = self._transitions.get(self._state, set())
        if target not in valid:
            raise ValueError(
                f"Invalid transition: {self._state} → {target}. "
                f"Valid targets: {valid}"
            )
        self._state = target

    def add_user_message(self, text: str) -> None:
        """Record a user (client) utterance."""
        self._context.messages.append({"role": "user", "content": text})
        self._context.transcript_parts.append(f"Клиент: {text}")

    def add_assistant_message(self, text: str) -> None:
        """Record an assistant (AI) response."""
        self._context.messages.append({"role": "assistant", "content": text})
        self._context.transcript_parts.append(f"Оператор: {text}")

    def increment_questions(self) -> None:
        """Track that a clarification question was asked."""
        self._context.questions_asked += 1

    def set_client_info(
        self,
        *,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        product: Optional[str] = None,
    ) -> None:
        """Update client identification info."""
        if name is not None:
            self._context.client_name = name
        if phone is not None:
            self._context.client_phone = phone
        if product is not None:
            self._context.product = product

    def set_classification(self, classification: dict[str, Any]) -> None:
        self._context.classification = classification

    def set_task_number(self, task_number: str) -> None:
        self._context.task_number = task_number

    def set_escalation(self, reason: str) -> None:
        self._context.escalation_reason = reason
