"""Call deduplication — 30-minute window to prevent duplicate task creation.

When the same phone number calls multiple times within the window,
the system links subsequent calls to the existing task instead of
creating new ones.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeduplicationEntry:
    phone: str
    call_id: str
    task_number: Optional[str]
    department: str
    created_at: float


class DeduplicationService:
    """Detect repeated calls from the same number within a time window.

    Uses Redis in production, in-memory dict in development.
    """

    def __init__(
        self,
        redis: Any = None,
        *,
        window_minutes: int = 30,
    ) -> None:
        self._redis = redis
        self._window_sec = window_minutes * 60
        self._memory: dict[str, DeduplicationEntry] = {}

    def _key(self, phone: str) -> str:
        return f"dedup:{phone}"

    async def check(self, phone: str) -> Optional[DeduplicationEntry]:
        """Check if a recent call exists for this phone number.

        Returns the existing entry if found within the window, else None.
        """
        if self._redis is not None:
            import json

            raw = await self._redis.get(self._key(phone))
            if raw is None:
                return None
            data = json.loads(raw)
            return DeduplicationEntry(**data)

        entry = self._memory.get(phone)
        if entry is None:
            return None
        if time.monotonic() - entry.created_at > self._window_sec:
            self._memory.pop(phone, None)
            return None
        return entry

    async def register(
        self,
        *,
        phone: str,
        call_id: str,
        task_number: Optional[str] = None,
        department: str = "support",
    ) -> None:
        """Register a call for deduplication tracking."""
        entry = DeduplicationEntry(
            phone=phone,
            call_id=call_id,
            task_number=task_number,
            department=department,
            created_at=time.monotonic(),
        )

        if self._redis is not None:
            import json

            await self._redis.set(
                self._key(phone),
                json.dumps(
                    {
                        "phone": entry.phone,
                        "call_id": entry.call_id,
                        "task_number": entry.task_number,
                        "department": entry.department,
                        "created_at": entry.created_at,
                    }
                ),
                ex=self._window_sec,
            )
            return

        self._memory[phone] = entry
        logger.debug("Dedup registered: phone=%s call_id=%s", phone, call_id)

    async def clear(self, phone: str) -> None:
        """Remove deduplication entry for a phone number."""
        if self._redis is not None:
            await self._redis.delete(self._key(phone))
            return
        self._memory.pop(phone, None)
