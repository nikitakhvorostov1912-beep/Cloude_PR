"""HTTP клиент для 1С сервиса.

Предоставляет два метода:
  - get_client_by_phone(phone) -> ClientInfo | None
  - create_task(task) -> TaskResponse

Retry логика: 3 попытки, экспоненциальный backoff, таймаут 5 сек.
Аутентификация: HTTP Basic Auth.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from models.task import ClientInfo, TaskCreate, TaskResponse
from orchestrator.config import OneCSettings, get_settings

logger = logging.getLogger(__name__)


class OneCClient:
    """Асинхронный HTTP клиент для REST API 1С."""

    def __init__(self, settings: OneCSettings | None = None) -> None:
        self._settings = settings or get_settings().onec
        self._base_url = self._settings.base_url.rstrip("/")
        self._auth = (self._settings.username, self._settings.password)
        self._timeout = self._settings.timeout
        self._max_retries = self._settings.max_retries
        self._base_delay = 1.0

    async def get_client_by_phone(self, phone: str) -> ClientInfo | None:
        """GET /client?phone=+7... -> ClientInfo или None (404)."""
        normalized = self._normalize_phone(phone)
        logger.info("Запрос клиента в 1С по телефону: %s", normalized)

        try:
            data = await self._request(
                "GET",
                "/client",
                params={"phone": normalized},
            )
            if data is None:
                logger.info("Клиент не найден в 1С: %s", normalized)
                return None
            client = ClientInfo(**data)
            logger.info(
                "Клиент найден: id=%s, name=%s, product=%s",
                client.id,
                client.name,
                client.product,
            )
            return client
        except OneCError:
            logger.exception("Ошибка запроса клиента: %s", normalized)
            raise

    async def create_task(self, task: TaskCreate) -> TaskResponse:
        """POST /tasks -> TaskResponse."""
        logger.info(
            "Создание задачи в 1С: department=%s, priority=%s, summary=%s",
            task.department,
            task.priority,
            task.summary,
        )

        data = await self._request(
            "POST",
            "/tasks",
            json_data=task.model_dump(mode="json"),
        )
        if data is None:
            raise OneCError("1С вернул пустой ответ при создании задачи")

        response = TaskResponse(**data)
        logger.info("Задача создана в 1С: task_id=%s", response.task_id)
        return response

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Выполняет HTTP запрос с retry логикой."""
        url = f"{self._base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.debug(
                    "1С запрос (попытка %d/%d): %s %s",
                    attempt,
                    self._max_retries,
                    method,
                    url,
                )
                async with httpx.AsyncClient(
                    auth=self._auth,
                    timeout=self._timeout,
                ) as client:
                    response = await client.request(
                        method,
                        url,
                        params=params,
                        json=json_data,
                    )

                logger.debug(
                    "1С ответ: status=%d, body_len=%d",
                    response.status_code,
                    len(response.content),
                )

                if response.status_code == 404:
                    return None

                if response.status_code >= 500:
                    raise OneCServerError(
                        f"Серверная ошибка 1С: {response.status_code}",
                        status_code=response.status_code,
                    )

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as exc:
                last_error = exc
                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Таймаут запроса к 1С (попытка %d/%d). Повтор через %.1f сек.",
                    attempt,
                    self._max_retries,
                    delay,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(delay)

            except httpx.ConnectError as exc:
                last_error = exc
                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Ошибка соединения с 1С (попытка %d/%d): %s",
                    attempt,
                    self._max_retries,
                    str(exc),
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(delay)

            except OneCServerError as exc:
                last_error = exc
                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Серверная ошибка 1С (попытка %d/%d): %s",
                    attempt,
                    self._max_retries,
                    str(exc),
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(delay)

            except httpx.HTTPStatusError as exc:
                # 4xx (кроме 404) — не повторяем
                logger.error("Ошибка HTTP от 1С: %s", exc)
                raise OneCError(
                    f"Ошибка при запросе к 1С: {exc.response.status_code}",
                    status_code=exc.response.status_code,
                ) from exc

        raise OneCError(
            f"Не удалось выполнить запрос к 1С после {self._max_retries} попыток",
            detail=str(last_error),
        )

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Нормализует номер телефона к формату +7XXXXXXXXXX."""
        digits = "".join(c for c in phone if c.isdigit())
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        if not digits.startswith("7"):
            digits = "7" + digits
        return f"+{digits}"

    def _calculate_delay(self, attempt: int) -> float:
        """Экспоненциальный backoff: 1s, 2s, 4s..."""
        return self._base_delay * (2 ** (attempt - 1))


class OneCError(Exception):
    """Ошибка взаимодействия с 1С."""

    def __init__(
        self,
        message: str = "Ошибка при запросе к 1С",
        *,
        status_code: int | None = None,
        detail: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class OneCServerError(OneCError):
    """Серверная ошибка 1С (5xx)."""
