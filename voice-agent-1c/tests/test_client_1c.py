"""Тесты HTTP-клиента 1С."""
from __future__ import annotations

import pytest
import pytest_asyncio

from integrations.client_1c import OneCClient, OneCError
from models.task import TaskCreate
from orchestrator.config import OneCSettings


@pytest.fixture
def onec_settings():
    return OneCSettings(
        base_url="http://test-1c/api/v1",
        username="test",
        password="test",
        timeout=2.0,
        max_retries=2,
    )


@pytest.fixture
def onec_client(onec_settings):
    return OneCClient(settings=onec_settings)


# --- Тесты поиска клиента ---


@pytest.mark.asyncio
async def test_get_client_found(onec_client, httpx_mock):
    """Клиент найден -> ClientInfo."""
    httpx_mock.add_response(
        url="http://test-1c/api/v1/client?phone=%2B79001234567",
        json={
            "found": True,
            "id": "00001234",
            "name": "ООО Ромашка",
            "product": "КА",
            "contract_status": "active",
            "assigned_specialist": "Иванов Иван",
            "sla_level": "standard",
        },
    )

    result = await onec_client.get_client_by_phone("+79001234567")
    assert result is not None
    assert result.id == "00001234"
    assert result.name == "ООО Ромашка"
    assert result.product == "КА"


@pytest.mark.asyncio
async def test_get_client_not_found(onec_client, httpx_mock):
    """Клиент не найден -> None."""
    httpx_mock.add_response(
        url="http://test-1c/api/v1/client?phone=%2B79001234567",
        status_code=404,
    )

    result = await onec_client.get_client_by_phone("+79001234567")
    assert result is None


@pytest.mark.asyncio
async def test_get_client_server_error_retry(onec_client, httpx_mock):
    """Серверная ошибка 500 -> retry -> успех."""
    httpx_mock.add_response(
        url="http://test-1c/api/v1/client?phone=%2B79001234567",
        status_code=500,
    )
    httpx_mock.add_response(
        url="http://test-1c/api/v1/client?phone=%2B79001234567",
        json={
            "found": True,
            "id": "00005678",
            "name": "ИП Петров",
            "product": "БП",
            "contract_status": "active",
            "sla_level": "standard",
        },
    )

    result = await onec_client.get_client_by_phone("+79001234567")
    assert result is not None
    assert result.id == "00005678"


@pytest.mark.asyncio
async def test_get_client_all_retries_failed(onec_client, httpx_mock):
    """Все попытки неуспешны -> OneCError."""
    httpx_mock.add_response(
        url="http://test-1c/api/v1/client?phone=%2B79001234567",
        status_code=500,
    )
    httpx_mock.add_response(
        url="http://test-1c/api/v1/client?phone=%2B79001234567",
        status_code=500,
    )

    with pytest.raises(OneCError, match="Не удалось выполнить запрос"):
        await onec_client.get_client_by_phone("+79001234567")


# --- Тесты создания задачи ---


@pytest.mark.asyncio
async def test_create_task_success(onec_client, httpx_mock):
    """Задача создана успешно."""
    httpx_mock.add_response(
        url="http://test-1c/api/v1/tasks",
        json={
            "task_id": "TASK-4521",
            "task_number": "4521",
            "assigned_to": "Иванов Иван",
            "sla_deadline": "2024-01-15T14:30:00",
        },
        status_code=201,
    )

    task = TaskCreate(
        client_id="00001234",
        department="support",
        product="КА",
        task_type="error",
        priority="critical",
        summary="Не проводятся документы",
        description="С утра документы не проходят",
        call_id="call-001",
    )

    result = await onec_client.create_task(task)
    assert result.task_id == "TASK-4521"
    assert result.assigned_to == "Иванов Иван"


# --- Тесты нормализации телефона ---


class TestPhoneNormalization:
    def test_8_prefix(self):
        assert OneCClient._normalize_phone("89001234567") == "+79001234567"

    def test_plus7_prefix(self):
        assert OneCClient._normalize_phone("+79001234567") == "+79001234567"

    def test_7_prefix(self):
        assert OneCClient._normalize_phone("79001234567") == "+79001234567"

    def test_with_dashes(self):
        assert OneCClient._normalize_phone("8-900-123-45-67") == "+79001234567"

    def test_with_parentheses(self):
        assert OneCClient._normalize_phone("+7(900)123-45-67") == "+79001234567"
