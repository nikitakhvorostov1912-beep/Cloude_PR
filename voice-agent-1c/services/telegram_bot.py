"""Telegram уведомления для Voice Agent.

Отправляет уведомления специалистам через Telegram Bot API.
Использует httpx вместо aiogram для минимизации зависимостей (без polling).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


@dataclass
class TelegramConfig:
    """Настройки Telegram бота."""

    bot_token: str
    support_chat_id: str
    admin_chat_id: str = ""


# Emoji-маркеры приоритета
PRIORITY_EMOJI = {
    "critical": "\U0001f534",  # 🔴
    "high": "\U0001f7e0",  # 🟠
    "normal": "\U0001f7e2",  # 🟢
    "low": "\u26aa",  # ⚪
}

TASK_TYPE_LABELS = {
    "error": "Ошибка/сбой",
    "consult": "Консультация",
    "feature": "Доработка",
    "update": "Обновление",
    "project": "Проект",
}


class TelegramNotifier:
    """Отправка уведомлений через Telegram Bot API.

    Usage:
        notifier = TelegramNotifier(config=TelegramConfig(...))
        await notifier.notify_new_task(task_data)
    """

    def __init__(self, config: TelegramConfig) -> None:
        self._config = config
        self._api_url = TELEGRAM_API_URL.format(token=config.bot_token)

    async def notify_new_task(
        self,
        *,
        task_number: str,
        client_name: str,
        task_type: str,
        priority: str,
        summary: str,
        department: str,
        assigned_to: str | None = None,
        call_duration: int | None = None,
        chat_id: str | None = None,
    ) -> bool:
        """Уведомление о новой задаче."""
        emoji = PRIORITY_EMOJI.get(priority, "\u2753")
        type_label = TASK_TYPE_LABELS.get(task_type, task_type)

        lines = [
            f"{emoji} <b>Новая задача #{task_number}</b>",
            "",
            f"\U0001f464 Клиент: {client_name}",
            f"\U0001f4cb Тип: {type_label}",
            f"\U0001f6a8 Приоритет: {priority.upper()}",
            f"\U0001f3e2 Отдел: {department}",
            "",
            f"\U0001f4dd {summary}",
        ]

        if assigned_to:
            lines.append(f"\n\U0001f464 Назначена: {assigned_to}")

        if call_duration:
            minutes = call_duration // 60
            seconds = call_duration % 60
            lines.append(f"\n\u23f1 Длительность звонка: {minutes}:{seconds:02d}")

        text = "\n".join(lines)
        target = chat_id or self._config.support_chat_id
        return await self._send_message(target, text)

    async def notify_escalation(
        self,
        *,
        call_id: str,
        caller_number: str,
        reason: str,
        client_name: str | None = None,
        chat_id: str | None = None,
    ) -> bool:
        """Алерт об эскалации звонка."""
        lines = [
            "\U0001f6a8\U0001f6a8 <b>ЭСКАЛАЦИЯ</b> \U0001f6a8\U0001f6a8",
            "",
            f"\U0001f4de Звонок: {call_id}",
            f"\U0001f4f1 Номер: {caller_number}",
        ]

        if client_name:
            lines.append(f"\U0001f464 Клиент: {client_name}")

        lines.extend([
            "",
            f"\U0001f4ac Причина: {reason}",
            "",
            "\u26a0\ufe0f Требуется ручная обработка",
        ])

        text = "\n".join(lines)
        target = chat_id or self._config.admin_chat_id or self._config.support_chat_id
        return await self._send_message(target, text)

    async def notify_missed_call(
        self,
        *,
        caller_number: str,
        client_name: str | None = None,
        next_working_time: str | None = None,
        chat_id: str | None = None,
    ) -> bool:
        """Уведомление о пропущенном звонке (нерабочее время)."""
        lines = [
            "\U0001f319 <b>Пропущенный звонок (нерабочее время)</b>",
            "",
            f"\U0001f4f1 Номер: {caller_number}",
        ]

        if client_name:
            lines.append(f"\U0001f464 Клиент: {client_name}")

        if next_working_time:
            lines.append(f"\n\u23f0 Следующее рабочее время: {next_working_time}")

        lines.append("\n\u260e\ufe0f Требуется обратный звонок")

        text = "\n".join(lines)
        target = chat_id or self._config.support_chat_id
        return await self._send_message(target, text)

    async def _send_message(self, chat_id: str, text: str) -> bool:
        """Отправляет сообщение через Telegram Bot API."""
        if not self._config.bot_token:
            logger.warning("Telegram bot_token не настроен, сообщение не отправлено")
            return False

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self._api_url, json=payload)
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    logger.info("Telegram сообщение отправлено в чат %s", chat_id)
                    return True
                else:
                    logger.error(
                        "Telegram API ошибка: %s",
                        result.get("description", "unknown"),
                    )
                    return False

        except httpx.HTTPError:
            logger.exception("Ошибка отправки в Telegram")
            return False
