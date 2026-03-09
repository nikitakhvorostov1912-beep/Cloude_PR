"""Фасад уведомлений: Telegram + SMS.

Единая точка входа для отправки уведомлений.
"""
from __future__ import annotations

import logging

from services.sms_service import SMSConfig, SMSService
from services.telegram_bot import TelegramConfig, TelegramNotifier

logger = logging.getLogger(__name__)


class NotificationService:
    """Единый сервис уведомлений.

    Usage:
        service = NotificationService(telegram_config=..., sms_config=...)
        await service.notify_task_created(...)
    """

    def __init__(
        self,
        *,
        telegram_config: TelegramConfig | None = None,
        sms_config: SMSConfig | None = None,
    ) -> None:
        self._telegram = (
            TelegramNotifier(telegram_config) if telegram_config else None
        )
        self._sms = SMSService(sms_config) if sms_config else None

    async def notify_task_created(
        self,
        *,
        phone: str,
        task_number: str,
        client_name: str,
        task_type: str,
        priority: str,
        summary: str,
        department: str,
        assigned_to: str | None = None,
        call_duration: int | None = None,
        sla_hours: int = 4,
    ) -> dict[str, bool]:
        """Уведомляет о создании задачи (Telegram + SMS)."""
        results: dict[str, bool] = {}

        if self._telegram:
            results["telegram"] = await self._telegram.notify_new_task(
                task_number=task_number,
                client_name=client_name,
                task_type=task_type,
                priority=priority,
                summary=summary,
                department=department,
                assigned_to=assigned_to,
                call_duration=call_duration,
            )

        if self._sms:
            results["sms"] = await self._sms.send_task_confirmation(
                phone, task_number, sla_hours
            )

        return results

    async def notify_escalation(
        self,
        *,
        call_id: str,
        phone: str,
        caller_number: str,
        reason: str,
        client_name: str | None = None,
    ) -> dict[str, bool]:
        """Уведомляет об эскалации."""
        results: dict[str, bool] = {}

        if self._telegram:
            results["telegram"] = await self._telegram.notify_escalation(
                call_id=call_id,
                caller_number=caller_number,
                reason=reason,
                client_name=client_name,
            )

        if self._sms:
            results["sms"] = await self._sms.send_escalation_notice(phone)

        return results

    async def notify_missed_call(
        self,
        *,
        phone: str,
        client_name: str | None = None,
        next_working_time: str | None = None,
    ) -> dict[str, bool]:
        """Уведомляет о пропущенном звонке."""
        results: dict[str, bool] = {}

        if self._telegram:
            results["telegram"] = await self._telegram.notify_missed_call(
                caller_number=phone,
                client_name=client_name,
                next_working_time=next_working_time,
            )

        if self._sms and next_working_time:
            results["sms"] = await self._sms.send_off_hours_reply(
                phone, next_working_time
            )

        return results
