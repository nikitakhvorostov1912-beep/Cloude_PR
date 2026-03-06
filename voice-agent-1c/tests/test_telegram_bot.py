"""Тесты Telegram уведомлений."""
from __future__ import annotations

import pytest

from services.telegram_bot import TelegramConfig, TelegramNotifier


@pytest.fixture
def config():
    return TelegramConfig(
        bot_token="123456:ABC",
        support_chat_id="-100123",
        admin_chat_id="-100456",
    )


@pytest.fixture
def notifier(config):
    return TelegramNotifier(config=config)


class TestNotifyNewTask:
    @pytest.mark.asyncio
    async def test_send_new_task(self, notifier, httpx_mock):
        """Отправка уведомления о новой задаче."""
        httpx_mock.add_response(
            method="POST",
            json={"ok": True, "result": {"message_id": 1}},
        )

        result = await notifier.notify_new_task(
            task_number="4521",
            client_name="ООО Ромашка",
            task_type="error",
            priority="critical",
            summary="Не проводятся документы",
            department="support",
            assigned_to="Иванов Иван",
            call_duration=134,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_task_message_content(self, notifier, httpx_mock):
        """Содержимое сообщения о задаче."""
        httpx_mock.add_response(
            method="POST",
            json={"ok": True, "result": {"message_id": 1}},
        )

        await notifier.notify_new_task(
            task_number="4521",
            client_name="ООО Ромашка",
            task_type="error",
            priority="critical",
            summary="Не проводятся документы",
            department="support",
        )

        request = httpx_mock.get_request()
        import json
        body = json.loads(request.content)
        assert "4521" in body["text"]
        assert "ООО Ромашка" in body["text"]
        assert body["parse_mode"] == "HTML"


class TestNotifyEscalation:
    @pytest.mark.asyncio
    async def test_escalation_alert(self, notifier, httpx_mock):
        """Отправка алерта об эскалации."""
        httpx_mock.add_response(
            method="POST",
            json={"ok": True, "result": {"message_id": 2}},
        )

        result = await notifier.notify_escalation(
            call_id="call-001",
            caller_number="+79001234567",
            reason="Клиент просит живого человека",
            client_name="ИП Петров",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_escalation_uses_admin_chat(self, notifier, httpx_mock):
        """Эскалация отправляется в admin чат."""
        httpx_mock.add_response(
            method="POST",
            json={"ok": True, "result": {"message_id": 2}},
        )

        await notifier.notify_escalation(
            call_id="call-001",
            caller_number="+79001234567",
            reason="test",
        )

        request = httpx_mock.get_request()
        import json
        body = json.loads(request.content)
        assert body["chat_id"] == "-100456"  # admin_chat_id


class TestNotifyMissedCall:
    @pytest.mark.asyncio
    async def test_missed_call(self, notifier, httpx_mock):
        """Уведомление о пропущенном звонке."""
        httpx_mock.add_response(
            method="POST",
            json={"ok": True, "result": {"message_id": 3}},
        )

        result = await notifier.notify_missed_call(
            caller_number="+79001234567",
            client_name="ООО Тест",
            next_working_time="в понедельник в 9:00",
        )

        assert result is True


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_empty_token(self):
        """Без токена -> False."""
        config = TelegramConfig(bot_token="", support_chat_id="-100")
        notifier = TelegramNotifier(config=config)

        result = await notifier.notify_new_task(
            task_number="1",
            client_name="Test",
            task_type="error",
            priority="normal",
            summary="Test",
            department="support",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_api_error(self, notifier, httpx_mock):
        """Ошибка Telegram API -> False."""
        httpx_mock.add_response(
            method="POST",
            json={"ok": False, "description": "Bad Request"},
        )

        result = await notifier.notify_new_task(
            task_number="1",
            client_name="Test",
            task_type="error",
            priority="normal",
            summary="Test",
            department="support",
        )

        assert result is False
