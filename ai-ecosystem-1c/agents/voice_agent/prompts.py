"""Dynamic prompt builder for the voice agent.

Generates the system prompt from the master prompt specification:
- Greeting → client identification → problem clarification → classification.
"""

from __future__ import annotations

from typing import Optional


def build_voice_system_prompt(
    *,
    client_name: Optional[str] = None,
    product: Optional[str] = None,
    has_active_tasks: bool = False,
    max_questions: int = 5,
) -> str:
    """Build the voice agent system prompt with dynamic context injection."""

    context_block = ""
    if client_name:
        context_parts = [f"Имя клиента: {client_name}"]
        if product:
            context_parts.append(f"Продукт: {product}")
        if has_active_tasks:
            context_parts.append("У клиента есть активные задачи")
        context_block = (
            "\n\n<client_context>\n"
            + "\n".join(context_parts)
            + "\n</client_context>"
        )

    return f"""Ты — AI-помощник на первой линии технической поддержки франчайзи 1С.

## Твоя задача
Провести диалог с клиентом, собрать информацию о проблеме и классифицировать обращение
для маршрутизации в нужный отдел.

## Правила диалога
1. Будь вежлив и профессионален
2. Задавай уточняющие вопросы по одному (максимум {max_questions} вопросов)
3. Используй простой язык, избегай технического жаргона
4. Если клиент раздражён — прояви эмпатию, не спорь
5. Если клиент просит оператора — немедленно эскалируй

## Что нужно выяснить
- Суть проблемы (ошибка, консультация, доработка, обновление)
- Какой продукт 1С (БП, КА, ЗУП, УТ, Розница, ERP, кастомная)
- Критичность (блокирует работу или нет)
- Текст ошибки / код ошибки (если есть)

## Когда создавать задачу
Создай задачу через create_task когда:
- Собрано достаточно информации (минимум: суть + продукт)
- ИЛИ задано {max_questions} вопросов
- ИЛИ клиент повторяет одно и то же

## Когда эскалировать
Используй escalate_to_operator когда:
- Клиент прямо просит оператора / человека
- Проблема слишком сложная или нетипичная
- Клиент агрессивен или раздражён
- Уверенность в классификации < 65%

## Формат ответа
Отвечай ТОЛЬКО текстом для озвучивания (TTS). Без markdown, без спецсимволов.
Ответ должен быть коротким (1-3 предложения).{context_block}"""


def build_greeting(client_name: Optional[str] = None) -> str:
    """Generate initial greeting text for TTS."""
    if client_name:
        return (
            f"Здравствуйте, {client_name}. "
            "Вы позвонили в службу технической поддержки. "
            "Чем могу помочь?"
        )
    return (
        "Здравствуйте! "
        "Вы позвонили в службу технической поддержки. "
        "Чем могу помочь?"
    )


def build_clarification_prompt(question_number: int, max_questions: int) -> str:
    """Generate a reminder about remaining questions."""
    remaining = max_questions - question_number
    if remaining <= 1:
        return (
            "Это последний уточняющий вопрос. После него необходимо "
            "классифицировать обращение и создать задачу."
        )
    return f"Осталось уточняющих вопросов: {remaining}."
