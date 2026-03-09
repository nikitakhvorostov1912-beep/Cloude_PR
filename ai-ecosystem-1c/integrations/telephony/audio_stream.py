"""WebSocket audio stream handler for real-time call processing."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

CALL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_call_id(call_id: str) -> bool:
    """Validate call_id to prevent path traversal and injection."""
    return bool(CALL_ID_PATTERN.match(call_id))
