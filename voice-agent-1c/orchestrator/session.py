"""Управление активными сессиями звонков через Redis.

TTL-based хранение: сессия автоматически удаляется через 30 минут.
Используется для идемпотентности (30-минутное окно по номеру).
"""
from __future__ import annotations

import logging
from datetime import timedelta

import redis.asyncio as aioredis

from models.call import CallSession
from orchestrator.config import get_settings

logger = logging.getLogger(__name__)

SESSION_TTL = timedelta(minutes=30)
KEY_PREFIX = "voice_agent:session:"
PHONE_PREFIX = "voice_agent:phone:"


class SessionManager:
    """Управление Redis-сессиями звонков."""

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis = redis_client

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            settings = get_settings()
            url = settings.redis.redis_url
            if url.startswith("fake://"):
                import fakeredis.aioredis
                self._redis = fakeredis.aioredis.FakeRedis()
            else:
                self._redis = aioredis.from_url(url)
        return self._redis

    async def save_session(self, session: CallSession) -> None:
        """Сохраняет сессию звонка в Redis с TTL."""
        r = await self._get_redis()
        key = f"{KEY_PREFIX}{session.call_id}"
        phone_key = f"{PHONE_PREFIX}{session.caller_number}"
        data = session.model_dump_json()
        ttl = int(SESSION_TTL.total_seconds())
        await r.set(key, data, ex=ttl)
        await r.set(phone_key, session.call_id, ex=ttl)
        logger.debug("Сессия сохранена: %s", session.call_id)

    async def get_session(self, call_id: str) -> CallSession | None:
        """Получает сессию по call_id."""
        r = await self._get_redis()
        data = await r.get(f"{KEY_PREFIX}{call_id}")
        if data is None:
            return None
        return CallSession.model_validate_json(data)

    async def get_active_session_by_phone(self, phone: str) -> CallSession | None:
        """Проверяет наличие активной сессии по номеру (идемпотентность)."""
        r = await self._get_redis()
        call_id = await r.get(f"{PHONE_PREFIX}{phone}")
        if call_id is None:
            return None
        call_id_str = call_id.decode() if isinstance(call_id, bytes) else call_id
        return await self.get_session(call_id_str)

    async def delete_session(self, call_id: str) -> None:
        """Удаляет сессию."""
        r = await self._get_redis()
        session = await self.get_session(call_id)
        await r.delete(f"{KEY_PREFIX}{call_id}")
        if session:
            await r.delete(f"{PHONE_PREFIX}{session.caller_number}")

    async def close(self) -> None:
        """Закрывает Redis соединение."""
        if self._redis:
            await self._redis.close()
