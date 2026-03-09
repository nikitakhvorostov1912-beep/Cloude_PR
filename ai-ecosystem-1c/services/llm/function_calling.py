"""Tool schemas for Claude function calling.

Defines the exact tool specifications from the master prompt:
- create_task: create a task in Sakura CRM
- escalate_to_operator: hand off to a human specialist
"""

from __future__ import annotations

from typing import Any

from models.api.task import Department, Priority, Product, TaskType

# ──────────────────────────────────────────────────────────────────────
# Tool: create_task
# ──────────────────────────────────────────────────────────────────────
CREATE_TASK_TOOL: dict[str, Any] = {
    "name": "create_task",
    "description": (
        "Создать задачу в CRM Сакура по результатам классификации звонка. "
        "Вызывается когда собрано достаточно информации для маршрутизации."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "department": {
                "type": "string",
                "enum": [d.value for d in Department],
                "description": "Целевой отдел для задачи",
            },
            "task_type": {
                "type": "string",
                "enum": [t.value for t in TaskType],
                "description": "Тип задачи: error, consult, feature, update, project",
            },
            "priority": {
                "type": "string",
                "enum": [p.value for p in Priority],
                "description": "Приоритет: critical, high, normal, low",
            },
            "product": {
                "type": "string",
                "enum": [p.value for p in Product],
                "description": "Продукт 1С (если определён)",
            },
            "title": {
                "type": "string",
                "description": "Краткий заголовок задачи (до 200 символов)",
            },
            "description": {
                "type": "string",
                "description": (
                    "Подробное описание проблемы с ключевыми фразами клиента, "
                    "шагами воспроизведения и контекстом"
                ),
            },
            "reasoning": {
                "type": "string",
                "description": "Обоснование выбора отдела и приоритета",
            },
        },
        "required": [
            "department",
            "task_type",
            "priority",
            "title",
            "description",
            "reasoning",
        ],
    },
}

# ──────────────────────────────────────────────────────────────────────
# Tool: escalate_to_operator
# ──────────────────────────────────────────────────────────────────────
ESCALATE_TOOL: dict[str, Any] = {
    "name": "escalate_to_operator",
    "description": (
        "Эскалировать звонок живому оператору. Используется когда AI "
        "не может уверенно классифицировать обращение или клиент настаивает "
        "на разговоре с человеком."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Причина эскалации",
            },
            "department_hint": {
                "type": "string",
                "enum": [d.value for d in Department],
                "description": "Предполагаемый отдел (если есть догадка)",
            },
            "priority": {
                "type": "string",
                "enum": [p.value for p in Priority],
                "description": "Рекомендуемый приоритет",
            },
            "context_summary": {
                "type": "string",
                "description": (
                    "Краткое описание того, что удалось узнать от клиента "
                    "до момента эскалации"
                ),
            },
        },
        "required": ["reason", "context_summary"],
    },
}


# ──────────────────────────────────────────────────────────────────────
# Helper: get all tools for a given agent type
# ──────────────────────────────────────────────────────────────────────
def get_classifier_tools() -> list[dict[str, Any]]:
    """Tools available to the classifier agent."""
    return [CREATE_TASK_TOOL, ESCALATE_TOOL]


def get_voice_tools() -> list[dict[str, Any]]:
    """Tools available to the voice agent (dialog phase)."""
    return [CREATE_TASK_TOOL, ESCALATE_TOOL]
