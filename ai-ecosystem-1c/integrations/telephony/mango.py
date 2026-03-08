"""Mango Office webhook handler with HMAC-SHA256 signature verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from models.api.call import CallEventType, MangoCallEvent

logger = logging.getLogger(__name__)


def verify_mango_signature(
    vpbx_api_key: str,
    json_data: str,
    sign: str,
    *,
    expected_key: str,
    api_salt: str,
) -> bool:
    """Constant-time HMAC-SHA256 verification for Mango webhooks."""
    if not hmac.compare_digest(vpbx_api_key, expected_key):
        logger.warning("Mango: vpbx_api_key mismatch")
        return False
    expected_sign = hashlib.sha256(
        (vpbx_api_key + json_data + api_salt).encode("utf-8")
    ).hexdigest()
    return hmac.compare_digest(expected_sign, sign)


def parse_mango_event(raw_json: str) -> MangoCallEvent:
    """Parse the JSON body from Mango webhook into a typed event."""
    data: dict = json.loads(raw_json)  # type: ignore[type-arg]

    event_type = _resolve_event_type(data)
    caller = data.get("from", {})
    called = data.get("to", {})

    return MangoCallEvent(
        call_id=str(data.get("entry_id", data.get("call_id", ""))),
        **{"from": caller.get("number", "") if isinstance(caller, dict) else str(caller)},
        to=called.get("number", "") if isinstance(called, dict) else str(called),
        event_type=event_type,
        timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
    )


def _resolve_event_type(data: dict) -> CallEventType:  # type: ignore[type-arg]
    """Map Mango call states to our event types."""
    call_state = str(data.get("call_state", "")).lower()
    mapping = {
        "appeared": CallEventType.INCOMING,
        "connected": CallEventType.CONNECTED,
        "disconnected": CallEventType.DISCONNECTED,
        "on answered": CallEventType.CONNECTED,
        "on disconnected": CallEventType.COMPLETED,
    }
    return mapping.get(call_state, CallEventType.INCOMING)
