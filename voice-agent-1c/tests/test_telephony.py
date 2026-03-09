"""Тесты вебхука Mango Office."""
from __future__ import annotations

import hashlib
import json

import pytest

from integrations.telephony import verify_mango_signature


def _make_sign(api_key: str, json_data: str, salt: str) -> str:
    """Создаёт валидную подпись Mango Office."""
    return hashlib.sha256((api_key + json_data + salt).encode("utf-8")).hexdigest()


EVENT_DATA = {
    "entry_id": "entry-001",
    "call_id": "call-001",
    "timestamp": 1700000000,
    "seq": 1,
    "call_state": "Appeared",
    "from": "+79001234567",
    "to": "+74951234567",
    "line_number": "line-1",
}


# --- Unit тесты подписи ---


class TestVerifyMangoSignature:
    def test_valid_signature(self):
        json_data = json.dumps(EVENT_DATA)
        sign = _make_sign("test_key", json_data, "test_salt")
        assert verify_mango_signature(
            vpbx_api_key="test_key",
            json_data=json_data,
            sign=sign,
            expected_key="test_key",
            api_salt="test_salt",
        )

    def test_wrong_api_key(self):
        json_data = json.dumps(EVENT_DATA)
        sign = _make_sign("test_key", json_data, "test_salt")
        assert not verify_mango_signature(
            vpbx_api_key="wrong_key",
            json_data=json_data,
            sign=sign,
            expected_key="test_key",
            api_salt="test_salt",
        )

    def test_wrong_sign(self):
        json_data = json.dumps(EVENT_DATA)
        assert not verify_mango_signature(
            vpbx_api_key="test_key",
            json_data=json_data,
            sign="invalid_signature",
            expected_key="test_key",
            api_salt="test_salt",
        )

    def test_wrong_salt(self):
        json_data = json.dumps(EVENT_DATA)
        sign = _make_sign("test_key", json_data, "wrong_salt")
        assert not verify_mango_signature(
            vpbx_api_key="test_key",
            json_data=json_data,
            sign=sign,
            expected_key="test_key",
            api_salt="test_salt",
        )


# --- Integration тесты эндпоинта ---


@pytest.mark.asyncio
async def test_webhook_valid_signature(client):
    """Корректный payload -> 200, звонок залогирован."""
    json_data = json.dumps(EVENT_DATA)
    sign = _make_sign("test_key", json_data, "test_salt")

    response = await client.post(
        "/api/v1/webhooks/mango/call",
        data={
            "vpbx_api_key": "test_key",
            "sign": sign,
            "json": json_data,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    """Неверная подпись -> 403."""
    json_data = json.dumps(EVENT_DATA)

    response = await client.post(
        "/api/v1/webhooks/mango/call",
        data={
            "vpbx_api_key": "test_key",
            "sign": "invalid_sign",
            "json": json_data,
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_invalid_json(client):
    """Некорректный JSON -> 400."""
    bad_json = "not a json"
    sign = _make_sign("test_key", bad_json, "test_salt")

    response = await client.post(
        "/api/v1/webhooks/mango/call",
        data={
            "vpbx_api_key": "test_key",
            "sign": sign,
            "json": bad_json,
        },
    )
    assert response.status_code == 400
