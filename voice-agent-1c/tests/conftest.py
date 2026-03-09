"""Фикстуры для тестов Voice Agent.

Использует aiosqlite для тестов без Docker PostgreSQL.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base
from orchestrator.config import (
    AISettings,
    AppSettings,
    DatabaseSettings,
    MangoSettings,
    OneCSettings,
    RedisSettings,
    YandexSettings,
    get_settings,
)


@pytest.fixture
def settings():
    """Тестовые настройки."""
    return AppSettings(
        app_title="Voice Agent Test",
        app_version="0.0.1-test",
        mango=MangoSettings(
            api_key="test_key",
            api_salt="test_salt",
            webhook_secret="test_secret",
        ),
        onec=OneCSettings(
            base_url="http://test-1c/api/v1",
            username="test",
            password="test",
        ),
        db=DatabaseSettings(database_url="sqlite+aiosqlite:///:memory:"),
        redis=RedisSettings(redis_url="redis://localhost:6379"),
        yandex=YandexSettings(
            api_key="test_yandex_key",
            folder_id="test_folder_id",
        ),
        ai=AISettings(
            ANTHROPIC_API_KEY="test_anthropic_key",
        ),
    )


@pytest_asyncio.fixture
async def db_engine():
    """Async SQLAlchemy engine с in-memory SQLite."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Async SQLAlchemy session."""
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session


@pytest.fixture
def app(settings, db_engine):
    """Test FastAPI application."""
    from database import session as db_module

    get_settings.cache_clear()

    # Подменяем настройки во всех местах импорта
    mock_settings = lambda: settings  # noqa: E731
    patches = [
        patch("orchestrator.config.get_settings", mock_settings),
        patch("integrations.telephony.get_settings", mock_settings),
    ]

    for p in patches:
        p.start()

    db_module.engine = db_engine
    db_module.async_session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    from orchestrator.main import create_app

    application = create_app()
    yield application

    for p in patches:
        p.stop()
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
