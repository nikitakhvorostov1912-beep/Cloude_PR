"""Call session state management — Redis-backed with TTL.

Each active call has a session stored in Redis with a 30-minute TTL.
For development, uses an in-memory dict fallback.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CallSessionStore:
    """Redis-backed call session store with in-memory fallback for dev."""

    def __init__(
        self,
        redis: Any = None,
        *,
        ttl_seconds: int = 1800,
    ) -> None:
        self._redis = redis
        self._ttl = ttl_seconds
        self._memory: dict[str, dict[str, Any]] = {}

    def _key(self, call_id: str) -> str:
        return f"call_session:{call_id}"

    async def get(self, call_id: str) -> Optional[dict[str, Any]]:
        """Retrieve session data for a call."""
        if self._redis is not None:
            raw = await self._redis.get(self._key(call_id))
            if raw is None:
                return None
            return json.loads(raw)

        entry = self._memory.get(call_id)
        if entry is None:
            return None
        if time.monotonic() - entry.get("_ts", 0) > self._ttl:
            self._memory.pop(call_id, None)
            return None
        return {k: v for k, v in entry.items() if not k.startswith("_")}

    async def set(self, call_id: str, data: dict[str, Any]) -> None:
        """Store session data with TTL."""
        if self._redis is not None:
            await self._redis.set(
                self._key(call_id),
                json.dumps(data, ensure_ascii=False, default=str),
                ex=self._ttl,
            )
            return

        self._memory[call_id] = {**data, "_ts": time.monotonic()}

    async def update(self, call_id: str, **fields: Any) -> None:
        """Merge fields into an existing session."""
        existing = await self.get(call_id) or {}
        existing.update(fields)
        await self.set(call_id, existing)

    async def delete(self, call_id: str) -> None:
        """Remove session data."""
        if self._redis is not None:
            await self._redis.delete(self._key(call_id))
            return
        self._memory.pop(call_id, None)

    async def exists(self, call_id: str) -> bool:
        """Check if a session exists."""
        if self._redis is not None:
            return bool(await self._redis.exists(self._key(call_id)))
        return call_id in self._memory

    async def get_active_count(self) -> int:
        """Count currently active sessions (approximate)."""
        if self._redis is not None:
            keys = []
            async for key in self._redis.scan_iter(match="call_session:*"):
                keys.append(key)
            return len(keys)
        # Clean expired entries
        now = time.monotonic()
        self._memory = {
            k: v
            for k, v in self._memory.items()
            if now - v.get("_ts", 0) <= self._ttl
        }
        return len(self._memory)
