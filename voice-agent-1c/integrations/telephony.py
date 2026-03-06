"""Обработчик вебхуков Mango Office.

Принимает POST от Mango Office в формате:
  - vpbx_api_key: API ключ
  - sign: SHA-256(api_key + json + api_salt)
  - json: строка с данными события

Валидирует подпись, парсит событие, сохраняет в БД.
"""
from __future__ import annotations

import hashlib
import json as json_lib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CallLog
from database.session import get_session
from models.call import CallEventType, MangoCallEvent, MangoWebhookPayload
from orchestrator.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["telephony"])


def verify_mango_signature(
    vpbx_api_key: str,
    json_data: str,
    sign: str,
    *,
    expected_key: str,
    api_salt: str,
) -> bool:
    """Проверяет подпись запроса Mango Office.

    Алгоритм: sha256(vpbx_api_key + json_data + api_salt)
    """
    if vpbx_api_key != expected_key:
        logger.warning("Неверный vpbx_api_key: %s", vpbx_api_key)
        return False

    expected_sign = hashlib.sha256(
        (vpbx_api_key + json_data + api_salt).encode("utf-8")
    ).hexdigest()

    return expected_sign == sign


@router.post(
    "/mango/call",
    status_code=status.HTTP_200_OK,
    summary="Вебхук входящего звонка Mango Office",
)
async def mango_call_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Обрабатывает входящий вебхук звонка от Mango Office."""
    settings = get_settings()

    # Mango отправляет application/x-www-form-urlencoded
    form = await request.form()
    try:
        payload = MangoWebhookPayload(
            vpbx_api_key=str(form.get("vpbx_api_key", "")),
            sign=str(form.get("sign", "")),
            json=str(form.get("json", "")),
        )
    except Exception as exc:
        logger.error("Ошибка парсинга вебхука Mango: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный формат вебхука",
        ) from exc

    # Проверка подписи
    if not verify_mango_signature(
        vpbx_api_key=payload.vpbx_api_key,
        json_data=payload.json,
        sign=payload.sign,
        expected_key=settings.mango.api_key,
        api_salt=settings.mango.api_salt,
    ):
        logger.warning("Невалидная подпись вебхука Mango")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невалидная подпись",
        )

    # Парсинг JSON события
    try:
        event_data = json_lib.loads(payload.json)
        event = MangoCallEvent(**event_data)
    except (json_lib.JSONDecodeError, Exception) as exc:
        logger.error("Ошибка парсинга JSON события: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный JSON события",
        ) from exc

    # Определяем тип события
    event_type = _resolve_event_type(event.call_state)

    # Сохраняем в БД
    call_log = CallLog(
        mango_call_id=event.call_id,
        mango_entry_id=event.entry_id,
        caller_number=event.from_number,
        called_number=event.to_number,
        line_number=event.line_number,
        event_type=event_type,
        call_state=event.call_state,
        direction="incoming",
        raw_webhook_data=event_data,
        call_started_at=datetime.fromtimestamp(event.timestamp, tz=timezone.utc),
    )
    session.add(call_log)
    await session.flush()

    logger.info(
        "Вебхук Mango: call_id=%s, from=%s, state=%s, event=%s",
        event.call_id,
        event.from_number,
        event.call_state,
        event_type,
    )

    return {"status": "ok"}


def _resolve_event_type(call_state: str) -> str:
    """Определяет тип события по call_state Mango Office."""
    state_map = {
        "Appeared": CallEventType.INCOMING,
        "Connected": CallEventType.CONNECTED,
        "Disconnected": CallEventType.COMPLETED,
    }
    return state_map.get(call_state, f"call.{call_state.lower()}" if call_state else "call.unknown")
