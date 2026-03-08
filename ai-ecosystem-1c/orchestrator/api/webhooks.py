"""Mango Office webhook endpoint — POST /webhooks/mango/incoming."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from integrations.telephony.mango import parse_mango_event, verify_mango_signature
from orchestrator.config import AppSettings, get_settings
from orchestrator.dependencies import get_call_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/mango/incoming")
async def mango_incoming(
    request: Request,
    settings: AppSettings = Depends(get_settings),
    call_handler: Any = Depends(get_call_handler),
) -> dict[str, str]:
    """Handle incoming call webhook from Mango Office.

    Mango sends form-encoded data with HMAC signature.
    """
    body = await request.body()

    # Verify HMAC signature
    if settings.mango.webhook_secret:
        signature = request.headers.get("X-Mango-Signature", "")
        if not verify_mango_signature(
            body=body,
            signature=signature,
            secret=settings.mango.webhook_secret,
        ):
            logger.warning("Invalid Mango webhook signature")
            raise HTTPException(status_code=403, detail="Неверная подпись")

    # Parse event
    try:
        form_data = await request.form()
        raw: dict[str, Any] = dict(form_data)
        event = parse_mango_event(raw)
    except Exception:
        logger.exception("Failed to parse Mango webhook")
        raise HTTPException(status_code=400, detail="Неверный формат данных")

    # Process through pipeline
    try:
        result = await call_handler.handle_incoming(event)
        logger.info(
            "call_id=%s webhook processed dedup=%s",
            result.call_id,
            result.deduplicated,
        )
    except Exception:
        logger.exception("Pipeline error for call_id=%s", event.call_id)
        raise HTTPException(status_code=500, detail="Ошибка обработки звонка")

    return {"status": "ok", "call_id": event.call_id}
