"""Deterministic routing rules — executed BEFORE LLM classification.

If a rule matches with high confidence, we skip the LLM entirely.
This saves latency and tokens for obvious cases.
"""

from __future__ import annotations

import re
from typing import Optional

from models.api.task import Department, Priority, RoutingResult, TaskType

# ──────────────────────────────────────────────────────────────────────
# Pattern sets for keyword matching
# ──────────────────────────────────────────────────────────────────────
_ERROR_PATTERNS = re.compile(
    r"(не\s*работает|ошибка|вылетает|зависает|не\s*открывается|"
    r"не\s*проводится|не\s*печатает|ошибку\s*выдаёт|ошибку\s*выдает|"
    r"падает|крашится|сломалось|глючит|баг)",
    re.IGNORECASE,
)

_CONSULT_PATTERNS = re.compile(
    r"(как\s*сделать|подскажите|где\s*найти|помогите\s*разобраться|"
    r"не\s*понимаю\s*как|вопрос\s*по|консультация|можно\s*ли|"
    r"расскажите|объясните)",
    re.IGNORECASE,
)

_FEATURE_PATTERNS = re.compile(
    r"(доработ|автоматизир|новый\s*отчёт|новый\s*отчет|"
    r"дополнительн|функционал|разработ|настро\w+\s*печатн|"
    r"внешн\w+\s*обработк|расшир)",
    re.IGNORECASE,
)

_UPDATE_PATTERNS = re.compile(
    r"(обновить|обновлен|перейти\s*на\s*нов|новая\s*версия|"
    r"апдейт|update|релиз|миграц)",
    re.IGNORECASE,
)

_PROJECT_PATTERNS = re.compile(
    r"(внедрени|внедрить|перенос\s*данных|интеграц|"
    r"подключ\w+\s*модул|запуск\s*проект|проект\s*внедрен)",
    re.IGNORECASE,
)

_CRITICAL_PATTERNS = re.compile(
    r"(не\s*могу\s*работать|всё\s*стоит|все\s*стоит|"
    r"зарплата\s*горит|бухгалтерия\s*стоит|отчётность\s*горит|"
    r"отчетность\s*горит|сдача\s*отчётов|сдача\s*отчетов|"
    r"блокирует\s*работу|парализован)",
    re.IGNORECASE,
)

_URGENT_PATTERNS = re.compile(
    r"(срочно|очень\s*важно|мешает\s*работать|критично|"
    r"горит|нужно\s*сегодня|не\s*терпит)",
    re.IGNORECASE,
)

_PRESALE_PATTERNS = re.compile(
    r"(сколько\s*стоит|цена|стоимость|купить|лицензи|"
    r"коммерческое\s*предложение|тариф|прайс|"
    r"хотим\s*подключить|новый\s*клиент|"
    r"рассмотреть\s*возможность)",
    re.IGNORECASE,
)

_SPECIALIST_PATTERNS = re.compile(
    r"(свяжите\s*(с|меня)|переведите\s*на|соедините\s*с|"
    r"хочу\s*поговорить\s*с|нужен\s*конкретный|"
    r"мо(й|им)\s*менеджер|мо(й|им)\s*специалист|мо(й|им)\s*программист)",
    re.IGNORECASE,
)

_ESCALATION_PATTERNS = re.compile(
    r"(оператор|человек|живой\s*человек|переведите|"
    r"хватит\s*бот|не\s*хочу\s*с\s*роботом|руководител)",
    re.IGNORECASE,
)


# ──────────────────────────────────────────────────────────────────────
# Main routing function
# ──────────────────────────────────────────────────────────────────────
def apply_deterministic_rules(transcript: str) -> Optional[RoutingResult]:
    """Try to classify the call using keyword rules.

    Returns RoutingResult if a rule matched with sufficient confidence,
    or None if the transcript should be sent to LLM.
    """
    text = transcript.lower()

    # 1. Escalation request — always honor
    if _ESCALATION_PATTERNS.search(text):
        return RoutingResult(
            department=Department.SUPPORT,
            confidence=0.95,
            rule="escalation_request",
        )

    # 2. Specific specialist request
    if _SPECIALIST_PATTERNS.search(text):
        return RoutingResult(
            department=Department.SPECIALIST,
            confidence=0.90,
            rule="specialist_request",
        )

    # 3. Pre-sale / commercial
    if _PRESALE_PATTERNS.search(text):
        return RoutingResult(
            department=Department.PRESALE,
            task_type=TaskType.CONSULT,
            priority=Priority.NORMAL,
            confidence=0.85,
            rule="presale_keywords",
        )

    # 4. Determine task type
    task_type = _detect_task_type(text)
    if task_type is None:
        return None  # Ambiguous — send to LLM

    # 5. Determine priority
    priority = _detect_priority(text)

    # 6. Map task type → department
    department = _task_type_to_department(task_type)

    # 7. Calculate confidence based on pattern match strength
    confidence = _calculate_confidence(text, task_type)
    if confidence < 0.70:
        return None  # Not confident enough — send to LLM

    return RoutingResult(
        department=department,
        task_type=task_type,
        priority=priority,
        confidence=confidence,
        rule=f"deterministic_{task_type.value}",
    )


def _detect_task_type(text: str) -> Optional[TaskType]:
    """Detect task type from transcript keywords."""
    scores: dict[TaskType, int] = {}

    if _ERROR_PATTERNS.search(text):
        scores[TaskType.ERROR] = len(_ERROR_PATTERNS.findall(text))
    if _CONSULT_PATTERNS.search(text):
        scores[TaskType.CONSULT] = len(_CONSULT_PATTERNS.findall(text))
    if _FEATURE_PATTERNS.search(text):
        scores[TaskType.FEATURE] = len(_FEATURE_PATTERNS.findall(text))
    if _UPDATE_PATTERNS.search(text):
        scores[TaskType.UPDATE] = len(_UPDATE_PATTERNS.findall(text))
    if _PROJECT_PATTERNS.search(text):
        scores[TaskType.PROJECT] = len(_PROJECT_PATTERNS.findall(text))

    if not scores:
        return None

    # Return the type with most keyword matches
    return max(scores, key=lambda k: scores[k])


def _detect_priority(text: str) -> Priority:
    """Detect priority from transcript keywords."""
    if _CRITICAL_PATTERNS.search(text):
        return Priority.CRITICAL
    if _URGENT_PATTERNS.search(text):
        return Priority.HIGH
    return Priority.NORMAL


def _task_type_to_department(task_type: TaskType) -> Department:
    """Map task type to the most likely department."""
    mapping = {
        TaskType.ERROR: Department.SUPPORT,
        TaskType.CONSULT: Department.SUPPORT,
        TaskType.FEATURE: Department.DEVELOPMENT,
        TaskType.UPDATE: Department.IMPLEMENTATION,
        TaskType.PROJECT: Department.IMPLEMENTATION,
    }
    return mapping.get(task_type, Department.SUPPORT)


def _calculate_confidence(text: str, task_type: TaskType) -> float:
    """Calculate confidence based on pattern match density."""
    pattern_map = {
        TaskType.ERROR: _ERROR_PATTERNS,
        TaskType.CONSULT: _CONSULT_PATTERNS,
        TaskType.FEATURE: _FEATURE_PATTERNS,
        TaskType.UPDATE: _UPDATE_PATTERNS,
        TaskType.PROJECT: _PROJECT_PATTERNS,
    }
    pattern = pattern_map.get(task_type)
    if pattern is None:
        return 0.5

    matches = len(pattern.findall(text))
    word_count = len(text.split())

    # Base confidence + density bonus
    base = 0.70
    density_bonus = min(matches / max(word_count / 20, 1), 0.25)
    return min(base + density_bonus, 0.95)
