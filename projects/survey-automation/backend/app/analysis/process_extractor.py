"""Извлечение бизнес-процессов из транскрипций интервью.

Использует LLM (Claude API) для анализа текста интервью и структурированного
извлечения бизнес-процессов с шагами, участниками, болевыми точками,
точками принятия решений и метриками.

Результат представляется в виде типизированных Pydantic-моделей, пригодных
для дальнейшей генерации BPMN-диаграмм и GAP-анализа.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.exceptions import ProcessingError

from .llm_client import LLMClient
from .prompts import EXTRACT_PROCESSES_PROMPT, SYSTEM_PROMPT
from .validator import ProcessValidator

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Pydantic-модели данных бизнес-процесса
# ----------------------------------------------------------------------


class ProcessStep(BaseModel):
    """Шаг бизнес-процесса.

    Attributes:
        order: Порядковый номер шага.
        name: Название действия (начинается с глагола).
        description: Подробное описание шага.
        performer: Исполнитель (роль/должность).
        inputs: Входные документы/данные.
        outputs: Выходные документы/результаты.
        systems: Используемые информационные системы.
    """

    order: int
    name: str
    description: str
    performer: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)


class Decision(BaseModel):
    """Точка принятия решения (ветвление) в процессе.

    Attributes:
        condition: Условие / вопрос (Да/Нет).
        yes_branch: Действие при положительном ответе.
        no_branch: Действие при отрицательном ответе.
    """

    condition: str
    yes_branch: str
    no_branch: str


class PainPoint(BaseModel):
    """Болевая точка (проблема) в процессе.

    Attributes:
        description: Описание проблемы.
        severity: Серьёзность: low, medium, high, critical.
        category: Категория: efficiency, quality, compliance,
            integration, manual_work.
    """

    description: str
    severity: str = Field(
        pattern=r"^(low|medium|high|critical)$",
        description="Серьёзность: low, medium, high, critical",
    )
    category: str = Field(
        pattern=r"^(efficiency|quality|compliance|integration|manual_work)$",
        description="Категория проблемы",
    )


class ProcessData(BaseModel):
    """Полные данные извлечённого бизнес-процесса.

    Attributes:
        id: Уникальный идентификатор процесса (proc_XXX).
        name: Название процесса.
        description: Описание процесса (2-5 предложений).
        department: Подразделение / отдел.
        trigger: Событие, запускающее процесс.
        result: Результат / выход процесса.
        participants: Список участников с ролями.
        steps: Последовательность шагов.
        decisions: Точки принятия решений.
        pain_points: Болевые точки / проблемы.
        integrations: Список интеграций с другими системами/отделами.
        metrics: Метрики и KPI процесса.
        source_transcript: Исходный текст транскрипции.
        assumptions: Допущения, сделанные при извлечении.
    """

    id: str
    name: str
    description: str = ""
    department: str = ""
    trigger: str = ""
    result: str = ""
    participants: list[dict] = Field(default_factory=list)
    steps: list[ProcessStep] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    pain_points: list[PainPoint] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    source_transcript: str = ""
    assumptions: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------------
# Экстрактор процессов
# ----------------------------------------------------------------------


class ProcessExtractor:
    """Извлекает бизнес-процессы из текстов транскрипций интервью.

    Использует LLM-клиент для отправки транскрипции с промптом
    и парсит структурированный JSON-ответ в типизированные модели.

    Attributes:
        _llm: Клиент для обращения к Anthropic Claude API.
        _validator: Валидатор для проверки извлечённых данных.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        validator: ProcessValidator | None = None,
    ) -> None:
        """Инициализирует экстрактор процессов.

        Args:
            llm_client: Клиент LLM для отправки запросов.
            validator: Валидатор данных процессов. Если не указан,
                создаётся экземпляр по умолчанию.
        """
        self._llm = llm_client
        self._validator = validator or ProcessValidator()

    async def extract(self, transcript_text: str) -> list[ProcessData]:
        """Извлекает бизнес-процессы из текста транскрипции.

        Отправляет транскрипцию в LLM, парсит JSON-ответ,
        валидирует результат и возвращает список ProcessData.

        Args:
            transcript_text: Текст транскрипции интервью.

        Returns:
            Список извлечённых бизнес-процессов.

        Raises:
            ProcessingError: При ошибке LLM-запроса, парсинга или валидации.
        """
        if not transcript_text or not transcript_text.strip():
            raise ProcessingError(
                "Текст транскрипции пуст. Невозможно извлечь процессы.",
                detail={"transcript_length": 0},
            )

        logger.info(
            "Начало извлечения процессов из транскрипции (%d символов).",
            len(transcript_text),
        )

        # Формируем запрос к LLM
        user_prompt = EXTRACT_PROCESSES_PROMPT.format(
            transcript_text=transcript_text,
        )

        # Отправляем запрос
        raw_response = await self._llm.send_json(
            system=SYSTEM_PROMPT,
            user=user_prompt,
        )

        # Извлекаем список процессов из ответа
        raw_processes = self._extract_process_list(raw_response)

        # Парсим и валидируем каждый процесс
        processes: list[ProcessData] = []
        validation_errors: list[str] = []
        validation_warnings: list[str] = []

        for i, raw_proc in enumerate(raw_processes):
            # Валидация структуры
            validation = self._validator.validate_process(raw_proc)
            validation_warnings.extend(validation.warnings)

            if not validation.valid:
                validation_errors.extend(validation.errors)
                logger.warning(
                    "Процесс #%d не прошёл валидацию: %s",
                    i + 1,
                    "; ".join(validation.errors),
                )
                continue

            # Парсинг в Pydantic-модель
            try:
                process = self._parse_process(raw_proc, transcript_text)
                processes.append(process)
                logger.info(
                    "Извлечён процесс: id=%s, name='%s', шагов=%d, "
                    "болевых точек=%d",
                    process.id,
                    process.name,
                    len(process.steps),
                    len(process.pain_points),
                )
            except Exception as exc:
                error_msg = (
                    f"Ошибка парсинга процесса #{i + 1}: {exc}"
                )
                validation_errors.append(error_msg)
                logger.warning(error_msg)

        if not processes:
            raise ProcessingError(
                "Не удалось извлечь ни одного бизнес-процесса из транскрипции.",
                detail={
                    "raw_process_count": len(raw_processes),
                    "validation_errors": validation_errors,
                    "transcript_length": len(transcript_text),
                },
            )

        if validation_warnings:
            logger.info(
                "Предупреждения валидации (%d): %s",
                len(validation_warnings),
                "; ".join(validation_warnings[:10]),
            )

        logger.info(
            "Извлечение завершено: %d процессов из %d кандидатов.",
            len(processes),
            len(raw_processes),
        )

        return processes

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_process_list(response: dict[str, Any]) -> list[dict]:
        """Извлекает список процессов из ответа LLM.

        LLM может вернуть:
        - Список напрямую (если send_json обернул в {"data": [...]}).
        - Словарь с ключом "processes" или "data".
        - Один процесс (оборачивается в список).

        Args:
            response: Распарсенный JSON-ответ от LLM.

        Returns:
            Список словарей с данными процессов.

        Raises:
            ProcessingError: Если не удаётся извлечь процессы из ответа.
        """
        # Если ответ содержит ключ "data" со списком
        if "data" in response and isinstance(response["data"], list):
            return response["data"]

        # Если ответ содержит ключ "processes"
        if "processes" in response and isinstance(response["processes"], list):
            return response["processes"]

        # Если ответ сам является словарём с полями процесса (один процесс)
        if "id" in response and "name" in response:
            return [response]

        # Если ответ -- обёртка и содержит список на верхнем уровне
        # (send_json может вернуть {"data": [...]} для массивов)
        for key, value in response.items():
            if isinstance(value, list) and len(value) > 0:
                if isinstance(value[0], dict) and ("id" in value[0] or "name" in value[0]):
                    return value

        raise ProcessingError(
            "Не удалось извлечь список процессов из ответа LLM. "
            "Ответ не содержит ожидаемой структуры.",
            detail={
                "response_keys": list(response.keys()),
                "response_preview": str(response)[:500],
            },
        )

    @staticmethod
    def _parse_process(
        raw: dict[str, Any], transcript_text: str
    ) -> ProcessData:
        """Парсит словарь в Pydantic-модель ProcessData.

        Обрабатывает вариации формата ответа LLM: различия
        в именах полей, типах, вложенности.

        Args:
            raw: Словарь с данными одного процесса.
            transcript_text: Исходная транскрипция (сохраняется в модели).

        Returns:
            ProcessData с заполненными полями.
        """
        # Гарантируем наличие id
        process_id = raw.get("id") or f"proc_{uuid.uuid4().hex[:8]}"

        # Парсим шаги
        steps: list[ProcessStep] = []
        for step_raw in raw.get("steps", []):
            if isinstance(step_raw, dict):
                try:
                    steps.append(ProcessStep(
                        order=step_raw.get("order", len(steps) + 1),
                        name=step_raw.get("name", ""),
                        description=step_raw.get("description", ""),
                        performer=step_raw.get("performer", ""),
                        inputs=_ensure_str_list(step_raw.get("inputs")),
                        outputs=_ensure_str_list(step_raw.get("outputs")),
                        systems=_ensure_str_list(step_raw.get("systems")),
                    ))
                except Exception as exc:
                    logger.warning(
                        "Не удалось распарсить шаг процесса '%s': %s",
                        process_id,
                        exc,
                    )

        # Парсим решения
        decisions: list[Decision] = []
        for dec_raw in raw.get("decisions", []):
            if isinstance(dec_raw, dict):
                try:
                    decisions.append(Decision(
                        condition=dec_raw.get("condition", ""),
                        yes_branch=dec_raw.get("yes_branch", ""),
                        no_branch=dec_raw.get("no_branch", ""),
                    ))
                except Exception as exc:
                    logger.warning(
                        "Не удалось распарсить решение процесса '%s': %s",
                        process_id,
                        exc,
                    )

        # Парсим болевые точки
        pain_points: list[PainPoint] = []
        for pp_raw in raw.get("pain_points", []):
            if isinstance(pp_raw, dict):
                try:
                    pain_points.append(PainPoint(
                        description=pp_raw.get("description", ""),
                        severity=pp_raw.get("severity", "medium"),
                        category=pp_raw.get("category", "efficiency"),
                    ))
                except Exception as exc:
                    logger.warning(
                        "Не удалось распарсить болевую точку процесса '%s': %s",
                        process_id,
                        exc,
                    )

        # Парсим participants (может быть списком строк или словарей)
        participants = _normalize_participants(raw.get("participants", []))

        # Парсим metrics (может быть списком или словарём)
        metrics = _normalize_metrics(raw.get("metrics"))

        return ProcessData(
            id=process_id,
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            department=raw.get("department", ""),
            trigger=raw.get("trigger", ""),
            result=raw.get("result", ""),
            participants=participants,
            steps=steps,
            decisions=decisions,
            pain_points=pain_points,
            integrations=_ensure_str_list(raw.get("integrations")),
            metrics=metrics,
            source_transcript=transcript_text,
            assumptions=_ensure_str_list(raw.get("assumptions")),
        )


# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------


def _ensure_str_list(value: Any) -> list[str]:
    """Гарантирует, что значение является списком строк.

    Args:
        value: Произвольное значение.

    Returns:
        Список строк. Пустой список, если значение некорректно.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        return [value]
    return []


def _normalize_participants(
    raw_participants: Any,
) -> list[dict]:
    """Нормализует список участников.

    LLM может вернуть:
    - Список строк: ["Менеджер", "Кладовщик"]
    - Список словарей: [{"role": "Менеджер", "department": "Продажи"}]

    Args:
        raw_participants: Сырые данные об участниках.

    Returns:
        Список словарей с ключом 'role' минимум.
    """
    if not isinstance(raw_participants, list):
        return []

    result: list[dict] = []
    for item in raw_participants:
        if isinstance(item, str):
            result.append({"role": item})
        elif isinstance(item, dict):
            result.append(item)
    return result


def _normalize_metrics(raw_metrics: Any) -> dict:
    """Нормализует метрики процесса.

    LLM может вернуть:
    - Словарь: {"time": "2-3 часа", "volume": "20-30 заказов"}
    - Список строк: ["Время: 2-3 часа", "Объём: 20-30 заказов"]

    Args:
        raw_metrics: Сырые данные о метриках.

    Returns:
        Словарь метрик. Пустой словарь, если данные некорректны.
    """
    if isinstance(raw_metrics, dict):
        return raw_metrics
    if isinstance(raw_metrics, list):
        return {
            f"metric_{i + 1}": str(item)
            for i, item in enumerate(raw_metrics)
            if item is not None
        }
    return {}
