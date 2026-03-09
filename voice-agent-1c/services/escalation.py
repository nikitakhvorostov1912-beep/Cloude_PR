"""Логика эскалации звонка.

Дерево принятия решений: нужно ли переводить на живого оператора.
Причины: CLIENT_REQUESTED, LOW_CONFIDENCE, SENSITIVE_TOPIC,
         MAX_QUESTIONS, CLIENT_FRUSTRATED, SYSTEM_ERROR.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class EscalationReason(StrEnum):
    """Причины эскалации."""

    CLIENT_REQUESTED = "client_requested"
    LOW_CONFIDENCE = "low_confidence"
    SENSITIVE_TOPIC = "sensitive_topic"
    MAX_QUESTIONS = "max_questions"
    CLIENT_FRUSTRATED = "client_frustrated"
    SYSTEM_ERROR = "system_error"
    PRODUCTION_OUTAGE = "production_outage"


@dataclass
class EscalationDecision:
    """Решение об эскалации."""

    should_escalate: bool
    reason: EscalationReason | None = None
    details: str = ""


# Ключевые слова для обнаружения
OPERATOR_KEYWORDS = [
    "оператор",
    "живой человек",
    "человек",
    "специалист",
    "позовите",
    "переведите",
    "хочу поговорить",
    "настоящего",
]

FRUSTRATION_KEYWORDS = [
    "бред",
    "ерунда",
    "чушь",
    "тупой",
    "бот",
    "робот",
    "достал",
    "надоел",
    "безобразие",
    "безответственность",
    "жалоб",  # жалоба, жалобу, жалобы
    "начальник",
    "руководител",  # руководитель, руководителя
]

SENSITIVE_KEYWORDS = [
    "денег",
    "деньг",  # деньги, денег
    "оплат",  # оплата, оплату
    "счёт",
    "счет",
    "договор",
    "контракт",
    "скидк",  # скидка, скидку
    "цена",
    "цену",
    "стоимост",  # стоимость, стоимости
    "тариф",
    "возврат",
    "суд",
    "юрист",
    "претензи",  # претензия, претензию
]

OUTAGE_KEYWORDS = [
    "встала работа",
    "ничего не работает",
    "всё встало",
    "все встало",
    "не можем работать",
    "авария",
    "сбой полный",
    "база не открывается",
    "сервер упал",
    "полный стоп",
]


def _text_contains_any(text: str, keywords: list[str]) -> str | None:
    """Проверяет наличие ключевых слов в тексте."""
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            return kw
    return None


class EscalationService:
    """Сервис оценки необходимости эскалации.

    Usage:
        service = EscalationService()
        decision = service.evaluate(
            text="Позовите живого человека!",
            ai_confidence=0.9,
            questions_asked=2,
            max_questions=5,
        )
        if decision.should_escalate:
            # перевод на оператора
    """

    def evaluate(
        self,
        text: str,
        *,
        ai_confidence: float = 1.0,
        questions_asked: int = 0,
        max_questions: int = 5,
        consecutive_low_confidence: int = 0,
    ) -> EscalationDecision:
        """Оценивает необходимость эскалации.

        Проверяет в порядке приоритета:
        1. Клиент просит оператора
        2. Производственная авария
        3. Фрустрация клиента
        4. Чувствительная тема (деньги, юриспруденция)
        5. Низкая уверенность AI (2+ раза подряд)
        6. Превышен лимит вопросов
        """
        # 1. Клиент просит оператора
        kw = _text_contains_any(text, OPERATOR_KEYWORDS)
        if kw:
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.CLIENT_REQUESTED,
                details=f"Клиент запросил оператора: '{kw}'",
            )

        # 2. Производственная авария
        kw = _text_contains_any(text, OUTAGE_KEYWORDS)
        if kw:
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.PRODUCTION_OUTAGE,
                details=f"Производственная авария: '{kw}'",
            )

        # 3. Фрустрация
        kw = _text_contains_any(text, FRUSTRATION_KEYWORDS)
        if kw:
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.CLIENT_FRUSTRATED,
                details=f"Клиент раздражён: '{kw}'",
            )

        # 4. Чувствительная тема
        kw = _text_contains_any(text, SENSITIVE_KEYWORDS)
        if kw:
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.SENSITIVE_TOPIC,
                details=f"Чувствительная тема: '{kw}'",
            )

        # 5. Низкая уверенность AI (2+ раза подряд)
        if consecutive_low_confidence >= 2:
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.LOW_CONFIDENCE,
                details=f"Низкая уверенность AI {consecutive_low_confidence} раз подряд",
            )

        # 6. Превышен лимит вопросов
        if questions_asked >= max_questions:
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.MAX_QUESTIONS,
                details=f"Задано {questions_asked}/{max_questions} вопросов",
            )

        return EscalationDecision(should_escalate=False)
