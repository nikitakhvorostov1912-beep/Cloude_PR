"""Асинхронная фабрика сессий SQLAlchemy.

Инициализирует engine и async_session для работы с PostgreSQL.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from orchestrator.config import get_settings

engine = None
async_session_factory = None


def init_db() -> None:
    """Инициализирует engine и session factory (вызывается в lifespan)."""
    global engine, async_session_factory
    settings = get_settings()
    url = settings.db.database_url

    # SQLite не поддерживает pool_size / pool_pre_ping
    if "sqlite" in url:
        engine = create_async_engine(url, echo=settings.debug)
    else:
        engine = create_async_engine(
            url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency для получения async сессии БД."""
    if async_session_factory is None:
        raise RuntimeError("БД не инициализирована. Вызовите init_db().")
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    """Закрывает engine (вызывается при остановке)."""
    global engine
    if engine:
        await engine.dispose()
