"""Точка входа приложения Survey Automation.

Запуск:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_config
from app.exceptions import register_exception_handlers


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ----------------------------------------------------------------------
# Lifespan
# ----------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Действия при запуске и остановке приложения."""
    config = get_config()
    data_dir = config.data_dir

    # Создаём директорию данных при запуске
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Директория данных: %s", data_dir)
    logger.info(
        "Сервер %s v%s запущен на %s:%d",
        config.app.title,
        config.app.version,
        config.app.host,
        config.app.port,
    )

    yield

    logger.info("Сервер остановлен")


# ----------------------------------------------------------------------
# Создание приложения
# ----------------------------------------------------------------------


def create_app() -> FastAPI:
    """Фабрика FastAPI-приложения."""
    config = get_config()

    application = FastAPI(
        title=config.app.title,
        version=config.app.version,
        description="Система автоматизации обработки интервью: "
        "транскрипция, анализ бизнес-процессов, генерация BPMN и документации.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Обработчики исключений
    # ------------------------------------------------------------------
    register_exception_handlers(application)

    # ------------------------------------------------------------------
    # Статические файлы (директория данных проектов)
    # ------------------------------------------------------------------
    data_dir = config.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    application.mount(
        "/data",
        StaticFiles(directory=str(data_dir)),
        name="project_data",
    )

    # ------------------------------------------------------------------
    # Роутеры
    # ------------------------------------------------------------------
    from app.api.routes import all_routers

    for api_router in all_routers:
        application.include_router(api_router)

    # ------------------------------------------------------------------
    # Эндпоинты
    # ------------------------------------------------------------------

    @application.get(
        "/",
        summary="Информация о приложении",
        description="Возвращает основные сведения о запущенном сервере.",
        tags=["Система"],
    )
    async def root() -> dict[str, str]:
        """Корневой эндпоинт с информацией о приложении."""
        return {
            "name": config.app.title,
            "version": config.app.version,
            "description": "Система автоматизации обработки интервью",
            "docs": "/docs",
        }

    @application.get(
        "/api/health",
        summary="Проверка состояния",
        description="Возвращает текущее состояние сервера и время.",
        tags=["Система"],
    )
    async def health_check() -> dict[str, str]:
        """Проверка работоспособности сервера."""
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": config.app.version,
        }

    return application


app: FastAPI = create_app()


# ----------------------------------------------------------------------
# Прямой запуск
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    cfg = get_config()
    uvicorn.run(
        "main:app",
        host=cfg.app.host,
        port=cfg.app.port,
        reload=True,
    )
