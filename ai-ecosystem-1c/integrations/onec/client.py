"""HTTP client for 1C HTTP service with retry and circuit-breaker logic."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from integrations.onec.exceptions import OneCError, OneCServerError, OneCTimeoutError
from integrations.onec.models import OneCClientResponse, OneCTaskResponse
from orchestrator.config import OneCSettings

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Convert Russian phone: 8... → +7..., strip spaces."""
    cleaned = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if cleaned.startswith("8") and len(cleaned) == 11:
        cleaned = "+7" + cleaned[1:]
    elif cleaned.startswith("7") and len(cleaned) == 11:
        cleaned = "+" + cleaned
    return cleaned


class OneCClient:
    """Async HTTP client for 1C with exponential backoff retry."""

    def __init__(self, settings: OneCSettings) -> None:
        self._base_url = settings.base_url.rstrip("/")
        self._auth = (settings.username, settings.password) if settings.username else None
        self._timeout = settings.timeout_sec
        self._max_retries = settings.max_retries

    async def get_client_by_phone(self, phone: str) -> Optional[OneCClientResponse]:
        """GET /api/v1/client?phone=..."""
        normalized = _normalize_phone(phone)
        try:
            data = await self._request(
                "GET", "/client", params={"phone": normalized}
            )
        except OneCError as exc:
            if exc.status_code == 404:
                return None
            raise
        if data is None:
            return None
        return OneCClientResponse.model_validate(data)

    async def create_task(self, payload: dict[str, Any]) -> OneCTaskResponse:
        """POST /api/v1/tasks"""
        data = await self._request("POST", "/tasks", json_data=payload)
        if data is None:
            raise OneCError("Empty response from 1C task creation")
        return OneCTaskResponse.model_validate(data)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.request(
                        method, url, params=params, json=json_data, auth=self._auth
                    )
                    if response.status_code == 404:
                        raise OneCError("Not found", status_code=404)
                    if 400 <= response.status_code < 500:
                        raise OneCError(
                            f"1C client error: {response.status_code}",
                            status_code=response.status_code,
                        )
                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException:
                last_error = OneCTimeoutError(
                    f"1C timeout on attempt {attempt}/{self._max_retries}"
                )
                logger.warning(str(last_error))
            except httpx.ConnectError as exc:
                last_error = OneCError(f"1C connection failed: {exc}")
                logger.warning(str(last_error))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    last_error = OneCServerError(
                        f"1C server error: {exc.response.status_code}",
                        status_code=exc.response.status_code,
                    )
                    logger.warning(str(last_error))
                else:
                    raise OneCError(str(exc), status_code=exc.response.status_code)
            except OneCError:
                raise

            if attempt < self._max_retries:
                delay = self._backoff_delay(attempt)
                logger.info("Retrying 1C request in %.1fs (attempt %d)", delay, attempt)
                await asyncio.sleep(delay)

        raise last_error or OneCError("All retry attempts exhausted")

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        return min(1.0 * (2 ** (attempt - 1)), 8.0)
