"""HTTP client for Sakura CRM with retry and error handling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from integrations.sakura.models import (
    SakuraClientResponse,
    SakuraSpecialistsResponse,
    SakuraTaskCreate,
    SakuraTaskCreateResponse,
    SakuraTasksResponse,
)
from orchestrator.config import SakuraSettings

logger = logging.getLogger(__name__)


class SakuraError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SakuraClient:
    """Async HTTP client for Sakura CRM."""

    def __init__(self, settings: SakuraSettings) -> None:
        self._base_url = settings.base_url.rstrip("/")
        self._api_key = settings.api_key
        self._timeout = settings.timeout_sec
        self._max_retries = 3

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def get_client_by_phone(self, phone: str) -> Optional[SakuraClientResponse]:
        """GET /api/clients/by-phone?phone=..."""
        data = await self._request("GET", "/clients/by-phone", params={"phone": phone})
        if data is None:
            return None
        resp = SakuraClientResponse.model_validate(data)
        return resp if resp.found else None

    async def get_recent_tasks(
        self, client_id: str, *, limit: int = 5, include_solutions: bool = True
    ) -> list[dict[str, Any]]:
        """GET /api/clients/{id}/tasks?limit=5&include_solutions=true"""
        params: dict[str, str] = {
            "limit": str(limit),
            "include_solutions": str(include_solutions).lower(),
        }
        data = await self._request("GET", f"/clients/{client_id}/tasks", params=params)
        if data is None:
            return []
        parsed = SakuraTasksResponse.model_validate(data)
        return [t.model_dump() for t in parsed.tasks]

    async def get_specialists_by_department(
        self, department: str, *, available_only: bool = True
    ) -> SakuraSpecialistsResponse:
        """GET /api/specialists/by-department?department=..."""
        params: dict[str, str] = {
            "department": department,
            "available_only": str(available_only).lower(),
        }
        data = await self._request("GET", "/specialists/by-department", params=params)
        if data is None:
            return SakuraSpecialistsResponse()
        return SakuraSpecialistsResponse.model_validate(data)

    async def create_task(self, payload: SakuraTaskCreate) -> SakuraTaskCreateResponse:
        """POST /api/tasks — create task with full AI enrichment."""
        data = await self._request("POST", "/tasks", json_data=payload.model_dump())
        if data is None:
            raise SakuraError("Empty response from Sakura task creation")
        return SakuraTaskCreateResponse.model_validate(data)

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
                        method,
                        url,
                        params=params,
                        json=json_data,
                        headers=self._headers(),
                    )
                    if response.status_code == 404:
                        return None
                    if 400 <= response.status_code < 500:
                        raise SakuraError(
                            f"Sakura client error: {response.status_code}",
                            status_code=response.status_code,
                        )
                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException:
                last_error = SakuraError(f"Sakura timeout attempt {attempt}/{self._max_retries}")
                logger.warning(str(last_error))
            except httpx.ConnectError as exc:
                last_error = SakuraError(f"Sakura connection failed: {exc}")
                logger.warning(str(last_error))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    last_error = SakuraError(f"Sakura server error: {exc.response.status_code}")
                    logger.warning(str(last_error))
                else:
                    raise SakuraError(str(exc), status_code=exc.response.status_code)
            except SakuraError:
                raise

            if attempt < self._max_retries:
                delay = min(1.0 * (2 ** (attempt - 1)), 8.0)
                await asyncio.sleep(delay)

        raise last_error or SakuraError("All retry attempts exhausted")
