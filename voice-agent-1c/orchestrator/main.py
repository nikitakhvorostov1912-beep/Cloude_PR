"""Точка входа приложения Voice Agent 1C.

Запуск:
    uvicorn orchestrator.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.config import get_settings

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Действия при запуске и остановке приложения."""
    settings = get_settings()
    logger.info("Запуск %s v%s", settings.app_title, settings.app_version)

    # Инициализация БД
    from database.session import close_db, init_db, engine

    init_db()

    # Для SQLite: создаём таблицы автоматически
    from database.session import engine as db_engine
    if db_engine and "sqlite" in str(db_engine.url):
        from database.models import Base
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite таблицы созданы")

    logger.info("База данных инициализирована")

    # Инициализация Redis-менеджера сессий
    from orchestrator.session import SessionManager

    session_manager = SessionManager()
    _app.state.session_manager = session_manager
    logger.info("Redis сессии инициализированы")

    # Инициализация Voice Dialog (Phase 2)
    if settings.yandex.api_key and settings.ai.api_key:
        _init_dialog_services(_app, settings)
    else:
        logger.warning(
            "Voice Dialog не инициализирован: нет YANDEX_API_KEY или ANTHROPIC_API_KEY"
        )

    yield

    # Очистка
    await session_manager.close()
    await close_db()
    logger.info("Сервер остановлен")


def _init_dialog_services(_app: FastAPI, settings: object) -> None:
    """Инициализирует сервисы голосового диалога."""
    from integrations.client_1c import OneCClient
    from services.ai_agent import AIAgent
    from services.dialog_orchestrator import DialogOrchestrator
    from services.stt import YandexSTTService
    from services.tts import YandexTTSService

    stt = YandexSTTService(
        api_key=settings.yandex.api_key,
        folder_id=settings.yandex.folder_id,
        model=settings.yandex.stt_model,
        language=settings.yandex.stt_language,
        sample_rate=settings.yandex.stt_sample_rate,
        silence_threshold_ms=settings.yandex.stt_silence_threshold_ms,
    )

    tts = YandexTTSService(
        api_key=settings.yandex.api_key,
        folder_id=settings.yandex.folder_id,
        voice=settings.yandex.tts_voice,
        speed=settings.yandex.tts_speed,
        emotion=settings.yandex.tts_emotion,
        sample_rate=settings.yandex.tts_sample_rate,
    )

    ai_agent = AIAgent(
        api_key=settings.ai.api_key,
        model=settings.ai.model,
        max_tokens=settings.ai.max_tokens,
        temperature=settings.ai.temperature,
        confidence_threshold=settings.ai.confidence_threshold,
        max_questions=settings.ai.max_questions,
    )

    onec_client = OneCClient(settings=settings.onec)

    orchestrator = DialogOrchestrator(
        stt=stt,
        tts=tts,
        ai_agent=ai_agent,
        onec_client=onec_client,
    )

    _app.state.dialog_orchestrator = orchestrator
    logger.info("Voice Dialog инициализирован: STT + Claude + TTS")


def create_app() -> FastAPI:
    """Фабрика FastAPI-приложения."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description=(
            "Голосовой AI-агент для франчайзи 1С. "
            "Приём звонков, идентификация клиентов, "
            "голосовой диалог (STT + Claude + TTS), маршрутизация обращений."
        ),
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS — в production задать ALLOWED_ORIGINS через env
    cors_origins = settings.allowed_origins if settings.allowed_origins else ["http://localhost:3000", "http://localhost:3001"]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Роутеры
    from integrations.telephony import router as telephony_router

    application.include_router(telephony_router)

    # WebSocket роутер (Phase 2)
    from api.routes.ws import router as ws_router

    application.include_router(ws_router)

    # Dashboard API (Phase 4)
    from api.routes.dashboard import router as dashboard_router

    application.include_router(dashboard_router)

    # Voice Preview API
    from api.routes.voices import router as voices_router

    application.include_router(voices_router)

    # Эндпоинты системы
    @application.get("/", tags=["Система"])
    async def root():
        return {
            "name": settings.app_title,
            "version": settings.app_version,
            "docs": "/docs",
        }

    @application.get("/api/health", tags=["Система"])
    async def health_check():
        dialog_ready = hasattr(application.state, "dialog_orchestrator")
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.app_version,
            "dialog_ready": dialog_ready,
        }

    return application


app: FastAPI = create_app()

if __name__ == "__main__":
    import uvicorn

    cfg = get_settings()
    uvicorn.run(
        "orchestrator.main:app",
        host=cfg.host,
        port=cfg.port,
        reload=cfg.debug,
    )
