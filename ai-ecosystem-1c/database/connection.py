"""Async SQLAlchemy engine and session factory.

Supports PostgreSQL (asyncpg) for production and SQLite (aiosqlite) for
dev/test.  Connection pooling is configured automatically based on the
database URL.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from orchestrator.config import get_settings

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _build_engine(url: str, *, echo: bool = False) -> AsyncEngine:
    is_sqlite = "sqlite" in url
    kwargs: dict = {"echo": echo}
    if not is_sqlite:
        kwargs.update(pool_pre_ping=True, pool_size=10, max_overflow=20)
    return create_async_engine(url, **kwargs)


def init_db(*, url: str | None = None, echo: bool | None = None) -> None:
    """Initialise the global engine and session factory."""
    global _engine, _session_factory
    settings = get_settings()
    db_url = url or settings.database.url
    db_echo = echo if echo is not None else settings.database.echo
    _engine = _build_engine(db_url, echo=db_echo)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def get_engine() -> AsyncEngine:
    if _engine is None:
        init_db()
    assert _engine is not None
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async session with auto-commit/rollback."""
    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
