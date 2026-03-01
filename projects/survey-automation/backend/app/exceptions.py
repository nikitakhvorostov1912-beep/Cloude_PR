"""Пользовательские исключения и глобальные обработчики ошибок.

Все сообщения об ошибках на русском языке для единообразия
пользовательского интерфейса.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Базовое исключение
# ----------------------------------------------------------------------


class AppError(Exception):
    """Базовое исключение приложения.

    Attributes:
        message: Сообщение об ошибке (на русском языке).
        status_code: HTTP-код ответа.
        detail: Дополнительные сведения для отладки.
    """

    def __init__(
        self,
        message: str = "Внутренняя ошибка сервера",
        *,
        status_code: int = 500,
        detail: Any = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Сериализует ошибку в словарь для JSON-ответа."""
        result: dict[str, Any] = {
            "error": True,
            "message": self.message,
            "status_code": self.status_code,
        }
        if self.detail is not None:
            result["detail"] = self.detail
        return result


# ----------------------------------------------------------------------
# Специализированные исключения
# ----------------------------------------------------------------------


class NotFoundError(AppError):
    """Ресурс не найден (HTTP 404)."""

    def __init__(
        self,
        message: str = "Запрашиваемый ресурс не найден",
        *,
        detail: Any = None,
    ) -> None:
        super().__init__(message, status_code=404, detail=detail)


class ValidationError(AppError):
    """Ошибка валидации входных данных (HTTP 422)."""

    def __init__(
        self,
        message: str = "Ошибка валидации данных",
        *,
        detail: Any = None,
    ) -> None:
        super().__init__(message, status_code=422, detail=detail)


class ProcessingError(AppError):
    """Ошибка обработки данных (HTTP 500)."""

    def __init__(
        self,
        message: str = "Ошибка при обработке данных",
        *,
        detail: Any = None,
    ) -> None:
        super().__init__(message, status_code=500, detail=detail)


class PipelineError(AppError):
    """Ошибка в конвейере обработки (HTTP 500)."""

    def __init__(
        self,
        message: str = "Ошибка в конвейере обработки",
        *,
        detail: Any = None,
    ) -> None:
        super().__init__(message, status_code=500, detail=detail)


class ExportError(AppError):
    """Ошибка экспорта данных (HTTP 500)."""

    def __init__(
        self,
        message: str = "Ошибка при экспорте данных",
        *,
        detail: Any = None,
    ) -> None:
        super().__init__(message, status_code=500, detail=detail)


# ----------------------------------------------------------------------
# Глобальные обработчики исключений для FastAPI
# ----------------------------------------------------------------------


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Обработчик для всех AppError и его наследников."""
    logger.error(
        "AppError [%d]: %s | detail=%s",
        exc.status_code,
        exc.message,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Обработчик для всех непредвиденных исключений."""
    logger.exception("Необработанное исключение: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Внутренняя ошибка сервера",
            "status_code": 500,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует глобальные обработчики исключений в приложении FastAPI.

    Args:
        app: Экземпляр FastAPI-приложения.
    """
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
