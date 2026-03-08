"""SMS notifications via SMSC.ru API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from orchestrator.config import SMSSettings

logger = logging.getLogger(__name__)

SMSC_API_URL = "https://smsc.ru/sys/send.php"


@dataclass(frozen=True)
class SMSResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class SMSService:
    """Send SMS via SMSC.ru REST API."""

    def __init__(self, settings: SMSSettings) -> None:
        self._settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.login and self._settings.password)

    async def send(
        self,
        *,
        phone: str,
        message: str,
        sender: Optional[str] = None,
    ) -> SMSResult:
        """Send an SMS message.

        Args:
            phone: Recipient phone number (any format, SMSC normalizes).
            message: Message text (up to 800 chars for Cyrillic).
            sender: Override sender name.
        """
        if not self.is_configured:
            logger.debug("SMS: not configured, skipping")
            return SMSResult(success=False, error="not_configured")

        params = {
            "login": self._settings.login,
            "psw": self._settings.password,
            "phones": phone,
            "mes": message[:800],
            "sender": sender or self._settings.sender_name,
            "fmt": "3",  # JSON response
            "charset": "utf-8",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(SMSC_API_URL, params=params)
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    error_msg = data.get("error", "unknown")
                    logger.warning("SMS send failed: %s", error_msg)
                    return SMSResult(success=False, error=error_msg)

                msg_id = str(data.get("id", ""))
                logger.info("SMS sent to %s, id=%s", phone, msg_id)
                return SMSResult(success=True, message_id=msg_id)

        except Exception:
            logger.exception("SMS send error")
            return SMSResult(success=False, error="transport_error")

    async def send_task_notification(
        self,
        *,
        phone: str,
        task_number: str,
        department: str,
    ) -> SMSResult:
        """Send task creation notification to the client."""
        message = (
            f"Ваше обращение зарегистрировано. "
            f"Номер задачи: {task_number}. "
            f"Отдел: {department}. "
            f"Специалист свяжется с вами в рабочее время."
        )
        return await self.send(phone=phone, message=message)
