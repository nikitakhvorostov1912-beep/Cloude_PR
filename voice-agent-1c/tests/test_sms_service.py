"""Тесты SMS сервиса (SMSC.ru)."""
from __future__ import annotations

import pytest

from services.sms_service import SMSC_API_URL, SMSConfig, SMSService


@pytest.fixture
def sms_config():
    return SMSConfig(login="test_login", password="test_pass")


@pytest.fixture
def sms_service(sms_config):
    return SMSService(config=sms_config)


class TestSMSSend:
    @pytest.mark.asyncio
    async def test_task_confirmation(self, sms_service, httpx_mock):
        """SMS подтверждение задачи."""
        httpx_mock.add_response(
            method="POST",
            json={"id": 1, "cnt": 1},
        )

        result = await sms_service.send_task_confirmation(
            "+79001234567", "4521", 2
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_confirmation_text(self, sms_service, httpx_mock):
        """Текст SMS подтверждения."""
        httpx_mock.add_response(method="POST", json={"id": 1, "cnt": 1})

        await sms_service.send_task_confirmation("+79001234567", "4521", 2)

        request = httpx_mock.get_request()
        body = request.content.decode("utf-8")
        assert "4521" in body
        assert "2" in body

    @pytest.mark.asyncio
    async def test_escalation_notice(self, sms_service, httpx_mock):
        """SMS уведомление об эскалации."""
        httpx_mock.add_response(method="POST", json={"id": 2, "cnt": 1})

        result = await sms_service.send_escalation_notice("+79001234567")
        assert result is True

    @pytest.mark.asyncio
    async def test_off_hours_reply(self, sms_service, httpx_mock):
        """SMS ответ в нерабочее время."""
        httpx_mock.add_response(method="POST", json={"id": 3, "cnt": 1})

        result = await sms_service.send_off_hours_reply(
            "+79001234567", "в понедельник в 9:00"
        )
        assert result is True


class TestSMSErrors:
    @pytest.mark.asyncio
    async def test_empty_login(self):
        """Без логина -> False."""
        config = SMSConfig(login="", password="")
        service = SMSService(config=config)

        result = await service.send_task_confirmation("+79001234567", "1", 2)
        assert result is False

    @pytest.mark.asyncio
    async def test_api_error(self, sms_service, httpx_mock):
        """Ошибка SMSC API -> False."""
        httpx_mock.add_response(
            method="POST",
            json={"error": "invalid login", "error_code": 2},
        )

        result = await sms_service.send_task_confirmation("+79001234567", "1", 2)
        assert result is False
