"""SMS сервис через SMSC.ru REST API.

Отправляет SMS уведомления клиентам:
  - Подтверждение создания задачи
  - Уведомление об эскалации
  - Ответ в нерабочее время
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

SMSC_API_URL = "https://smsc.ru/sys/send.php"


@dataclass
class SMSConfig:
    """Настройки SMSC.ru."""

    login: str
    password: str
    sender: str = "VoiceAgent"


class SMSService:
    """Отправка SMS через SMSC.ru.

    Usage:
        sms = SMSService(config=SMSConfig(login="...", password="..."))
        await sms.send_task_confirmation("+79001234567", "4521", 2)
    """

    def __init__(self, config: SMSConfig) -> None:
        self._config = config

    async def send_task_confirmation(
        self,
        phone: str,
        task_number: str,
        sla_hours: int,
    ) -> bool:
        """Подтверждение создания обращения."""
        text = (
            f"Обращение #{task_number} принято. "
            f"Специалист свяжется с вами в течение {sla_hours} ч. "
            f"Франчайзи 1С"
        )
        return await self._send(phone, text)

    async def send_escalation_notice(self, phone: str) -> bool:
        """Уведомление о переводе на специалиста."""
        text = (
            "Ваш звонок переведён на специалиста. "
            "Если связь прервётся, мы перезвоним. "
            "Франчайзи 1С"
        )
        return await self._send(phone, text)

    async def send_off_hours_reply(
        self, phone: str, next_time: str
    ) -> bool:
        """Ответ в нерабочее время."""
        text = (
            f"Спасибо за звонок. Сейчас нерабочее время. "
            f"Перезвоним {next_time}. "
            f"Франчайзи 1С"
        )
        return await self._send(phone, text)

    async def _send(self, phone: str, text: str) -> bool:
        """Отправляет SMS через SMSC.ru API."""
        if not self._config.login:
            logger.warning("SMSC логин не настроен, SMS не отправлена")
            return False

        params = {
            "login": self._config.login,
            "psw": self._config.password,
            "phones": phone,
            "mes": text,
            "sender": self._config.sender,
            "charset": "utf-8",
            "fmt": 3,  # JSON ответ
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(SMSC_API_URL, params=params)
                response.raise_for_status()
                data = response.json()

            if "error" in data:
                logger.error("SMSC ошибка: %s", data.get("error_code"))
                return False

            logger.info("SMS отправлена на %s: %d сообщений", phone, data.get("cnt", 0))
            return True

        except httpx.HTTPError:
            logger.exception("Ошибка отправки SMS")
            return False
