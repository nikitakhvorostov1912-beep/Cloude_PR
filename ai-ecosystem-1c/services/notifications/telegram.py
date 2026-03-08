"""Telegram notifications — admin alerts and escalation notices."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from orchestrator.config import TelegramSettings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


@dataclass(frozen=True)
class TelegramResult:
    success: bool
    message_id: Optional[int] = None
    error: Optional[str] = None


class TelegramService:
    """Send messages to Telegram via Bot API."""

    def __init__(self, settings: TelegramSettings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.bot_token and self._settings.admin_chat_id)

    async def send_message(
        self,
        text: str,
        *,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> TelegramResult:
        """Send a text message via Telegram Bot API.

        Args:
            text: Message text (HTML or plain).
            chat_id: Target chat. Defaults to admin_chat_id.
            parse_mode: "HTML" or "MarkdownV2".
        """
        if not self.is_configured:
            logger.debug("Telegram: not configured, skipping")
            return TelegramResult(success=False, error="not_configured")

        target = chat_id or self._settings.admin_chat_id
        url = f"{TELEGRAM_API}/bot{self._settings.bot_token}/sendMessage"
        payload = {
            "chat_id": target,
            "text": text[:4096],
            "parse_mode": parse_mode,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                if not data.get("ok"):
                    error_msg = data.get("description", "unknown")
                    logger.warning("Telegram send failed: %s", error_msg)
                    return TelegramResult(success=False, error=error_msg)

                msg_id = data["result"]["message_id"]
                return TelegramResult(success=True, message_id=msg_id)

        except Exception:
            logger.exception("Telegram send error")
            return TelegramResult(success=False, error="transport_error")

    async def notify_escalation(
        self,
        *,
        call_id: str,
        phone: str,
        reason: str,
        context: str,
    ) -> TelegramResult:
        """Alert admin about an escalated call."""
        text = (
            "<b>Эскалация звонка</b>\n\n"
            f"<b>Call ID:</b> <code>{call_id}</code>\n"
            f"<b>Телефон:</b> {phone}\n"
            f"<b>Причина:</b> {reason}\n\n"
            f"<b>Контекст:</b>\n{context[:1000]}"
        )
        return await self.send_message(text)

    async def notify_low_confidence(
        self,
        *,
        call_id: str,
        department: str,
        confidence: float,
        task_number: Optional[str] = None,
    ) -> TelegramResult:
        """Alert admin about low-confidence classification."""
        task_info = f"\n<b>Задача:</b> {task_number}" if task_number else ""
        text = (
            "<b>Низкая уверенность AI</b>\n\n"
            f"<b>Call ID:</b> <code>{call_id}</code>\n"
            f"<b>Отдел:</b> {department}\n"
            f"<b>Уверенность:</b> {confidence:.0%}{task_info}\n\n"
            "Требуется ручная проверка."
        )
        return await self.send_message(text)
