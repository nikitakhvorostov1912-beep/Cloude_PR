"""Клиент для взаимодействия с Anthropic Claude API.

Обеспечивает отправку запросов к Claude, парсинг JSON-ответов,
обработку ошибок API, retry-логику с экспоненциальной задержкой
и логирование потребления токенов.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import anthropic
import httpx

from app.config import AnalysisConfig
from app.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class LLMClient:
    """Асинхронный клиент для Anthropic Claude API.

    Attributes:
        config: Настройки модели (model, max_tokens, temperature).
        _client: Экземпляр anthropic.AsyncAnthropic.
        _max_retries: Максимальное число попыток при ошибках API.
        _base_delay: Базовая задержка (сек) для экспоненциального backoff.
    """

    _max_retries: int = 3
    _base_delay: float = 1.0

    def __init__(self, config: AnalysisConfig) -> None:
        """Инициализирует LLM-клиент.

        Args:
            config: Настройки анализа (модель, токены, температура).

        Raises:
            ProcessingError: Если переменная окружения ANTHROPIC_API_KEY не задана.
        """
        self.config = config

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProcessingError(
                "Переменная окружения ANTHROPIC_API_KEY не задана. "
                "Установите ключ API Anthropic для работы с LLM.",
                detail={"env_var": "ANTHROPIC_API_KEY"},
            )

        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )
        logger.info(
            "LLM-клиент инициализирован: модель=%s, max_tokens=%d, temperature=%.2f",
            config.model,
            config.max_tokens,
            config.temperature,
        )

    async def send(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
    ) -> str:
        """Отправляет запрос к Claude API и возвращает текстовый ответ.

        Реализует retry-логику с экспоненциальной задержкой при ошибках
        rate limit и серверных ошибках.

        Args:
            system: Системный промпт (контекст и инструкции).
            user: Пользовательский запрос (данные для анализа).
            max_tokens: Максимум токенов в ответе. Если None -- используется config.max_tokens.

        Returns:
            Текстовый ответ от Claude.

        Raises:
            ProcessingError: При неудачном запросе после всех попыток.
        """
        effective_max_tokens = max_tokens or self.config.max_tokens
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.debug(
                    "Отправка запроса к Claude (попытка %d/%d): модель=%s, max_tokens=%d",
                    attempt,
                    self._max_retries,
                    self.config.model,
                    effective_max_tokens,
                )

                response = await self._client.messages.create(
                    model=self.config.model,
                    max_tokens=effective_max_tokens,
                    temperature=self.config.temperature,
                    system=system,
                    messages=[
                        {"role": "user", "content": user},
                    ],
                )

                # Логирование потребления токенов
                usage = response.usage
                logger.info(
                    "Ответ от Claude получен: input_tokens=%d, output_tokens=%d, "
                    "stop_reason=%s",
                    usage.input_tokens,
                    usage.output_tokens,
                    response.stop_reason,
                )

                # Извлекаем текст из ответа
                text_content = self._extract_text(response)

                if response.stop_reason == "max_tokens":
                    logger.warning(
                        "Ответ обрезан по лимиту токенов (%d). "
                        "Рассмотрите увеличение max_tokens.",
                        effective_max_tokens,
                    )

                return text_content

            except anthropic.RateLimitError as exc:
                last_error = exc
                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Превышен лимит запросов API (попытка %d/%d). "
                    "Повторная попытка через %.1f сек.",
                    attempt,
                    self._max_retries,
                    delay,
                )
                await asyncio.sleep(delay)

            except anthropic.InternalServerError as exc:
                last_error = exc
                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Серверная ошибка API (попытка %d/%d): %s. "
                    "Повторная попытка через %.1f сек.",
                    attempt,
                    self._max_retries,
                    str(exc),
                    delay,
                )
                await asyncio.sleep(delay)

            except anthropic.APIConnectionError as exc:
                last_error = exc
                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Ошибка соединения с API (попытка %d/%d): %s. "
                    "Повторная попытка через %.1f сек.",
                    attempt,
                    self._max_retries,
                    str(exc),
                    delay,
                )
                await asyncio.sleep(delay)

            except anthropic.AuthenticationError as exc:
                # Ошибка аутентификации -- retry не поможет
                logger.error(
                    "Ошибка аутентификации API: %s. Проверьте ANTHROPIC_API_KEY.",
                    str(exc),
                )
                raise ProcessingError(
                    "Ошибка аутентификации Anthropic API. "
                    "Проверьте корректность ключа ANTHROPIC_API_KEY.",
                    detail={"error_type": "AuthenticationError", "message": str(exc)},
                ) from exc

            except anthropic.BadRequestError as exc:
                # Некорректный запрос -- retry не поможет
                logger.error("Некорректный запрос к API: %s", str(exc))
                raise ProcessingError(
                    "Некорректный запрос к Anthropic API. "
                    "Возможно, превышен лимит контекста модели.",
                    detail={"error_type": "BadRequestError", "message": str(exc)},
                ) from exc

            except Exception as exc:
                logger.exception("Непредвиденная ошибка при обращении к Claude API")
                raise ProcessingError(
                    f"Непредвиденная ошибка при обращении к Claude API: {type(exc).__name__}",
                    detail={"error_type": type(exc).__name__, "message": str(exc)},
                ) from exc

        # Все попытки исчерпаны
        error_msg = (
            f"Не удалось получить ответ от Claude API после {self._max_retries} попыток."
        )
        logger.error(error_msg)
        raise ProcessingError(
            error_msg,
            detail={
                "attempts": self._max_retries,
                "last_error": str(last_error) if last_error else None,
            },
        )

    async def send_json(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Отправляет запрос и парсит JSON из ответа Claude.

        Claude может оборачивать JSON в markdown-блоки ```json ... ```.
        Метод извлекает JSON из любого такого обрамления.

        Args:
            system: Системный промпт.
            user: Пользовательский запрос.
            max_tokens: Максимум токенов. Если None -- из конфигурации.

        Returns:
            Распарсенный словарь из JSON-ответа.

        Raises:
            ProcessingError: Если ответ не содержит валидного JSON.
        """
        raw_response = await self.send(system, user, max_tokens=max_tokens)

        try:
            parsed = self._parse_json_response(raw_response)
            logger.debug(
                "JSON успешно извлечён из ответа (тип: %s, ключей: %s)",
                type(parsed).__name__,
                len(parsed) if isinstance(parsed, dict) else "N/A",
            )
            return parsed if isinstance(parsed, dict) else {"data": parsed}
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "Не удалось извлечь JSON из ответа Claude. "
                "Длина ответа: %d символов. Ошибка: %s",
                len(raw_response),
                str(exc),
            )
            raise ProcessingError(
                "Не удалось извлечь JSON из ответа LLM. "
                "Модель вернула некорректный формат.",
                detail={
                    "error": str(exc),
                    "response_length": len(raw_response),
                    "response_preview": raw_response[:500],
                },
            ) from exc

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(response: anthropic.types.Message) -> str:
        """Извлекает текстовое содержимое из ответа Claude.

        Args:
            response: Ответ Anthropic API.

        Returns:
            Объединённый текст всех TextBlock-ов.

        Raises:
            ProcessingError: Если ответ не содержит текстовых блоков.
        """
        text_parts: list[str] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

        if not text_parts:
            raise ProcessingError(
                "Ответ от Claude не содержит текстового содержимого.",
                detail={"content_types": [b.type for b in response.content]},
            )

        return "\n".join(text_parts)

    @staticmethod
    def _parse_json_response(text: str) -> Any:
        """Извлекает и парсит JSON из текстового ответа.

        Обрабатывает случаи:
        - Чистый JSON без обрамления.
        - JSON в markdown-блоке ```json ... ```.
        - JSON в markdown-блоке ``` ... ```.
        - JSON с текстовыми комментариями до/после.

        Args:
            text: Текстовый ответ от Claude.

        Returns:
            Распарсенный JSON-объект.

        Raises:
            ValueError: Если JSON не найден или невалиден.
        """
        cleaned = text.strip()

        # Попытка 1: прямой парсинг
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.debug("Прямой парсинг JSON не удался, пробуем извлечь из markdown")

        # Попытка 2: извлечь JSON из markdown-блока ```json ... ```
        json_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```",
            cleaned,
            re.DOTALL,
        )
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1).strip())
            except json.JSONDecodeError:
                logger.debug("Парсинг JSON из markdown-блока не удался, пробуем извлечь по скобкам")

        # Попытка 3: найти первый { или [ и последний } или ]
        # для извлечения JSON из текста с комментариями
        first_brace = -1
        last_brace = -1
        for i, ch in enumerate(cleaned):
            if ch in "{[":
                first_brace = i
                break

        for i in range(len(cleaned) - 1, -1, -1):
            if cleaned[i] in "}]":
                last_brace = i
                break

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = cleaned[first_brace : last_brace + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                logger.debug("Парсинг JSON-кандидата по скобкам не удался")

        raise ValueError(
            "Не удалось обнаружить валидный JSON в ответе. "
            f"Длина текста: {len(cleaned)} символов."
        )

    def _calculate_delay(self, attempt: int) -> float:
        """Рассчитывает задержку для экспоненциального backoff.

        Args:
            attempt: Номер текущей попытки (начиная с 1).

        Returns:
            Задержка в секундах.
        """
        return self._base_delay * (2 ** (attempt - 1))
