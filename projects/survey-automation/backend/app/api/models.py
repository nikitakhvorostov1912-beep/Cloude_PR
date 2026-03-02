"""Pydantic модели запросов и ответов API.

Все модели используют ConfigDict(from_attributes=True) для совместимости
с ORM-объектами и словарями из сервисного слоя.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------------------------
# Проекты
# ----------------------------------------------------------------------


class ProjectCreate(BaseModel):
    """Запрос на создание проекта."""

    name: str = Field(..., min_length=1, max_length=255, description="Название проекта")
    description: str = Field(default="", max_length=2000, description="Описание проекта")


class ProjectResponse(BaseModel):
    """Ответ с данными проекта."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Идентификатор проекта")
    name: str = Field(..., description="Название проекта")
    description: str = Field(default="", description="Описание проекта")
    created_at: str = Field(..., description="Дата создания (ISO 8601)")
    updated_at: str = Field(..., description="Дата последнего обновления (ISO 8601)")
    status: str = Field(default="created", description="Статус проекта")
    pipeline_state: dict[str, Any] = Field(
        default_factory=dict, description="Состояние пайплайна обработки"
    )


class ProjectListResponse(BaseModel):
    """Ответ со списком проектов."""

    projects: list[ProjectResponse] = Field(default_factory=list, description="Список проектов")
    total: int = Field(..., description="Общее количество проектов")


# ----------------------------------------------------------------------
# Транскрипции
# ----------------------------------------------------------------------


class TranscriptResponse(BaseModel):
    """Ответ с данными транскрипции."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Идентификатор транскрипции")
    filename: str = Field(default="", description="Имя исходного файла")
    dialogue: list[dict[str, Any]] = Field(
        default_factory=list, description="Диалог по сегментам"
    )
    full_text: str = Field(default="", description="Полный текст транскрипции")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Метаданные транскрипции"
    )
    speaker_stats: dict[str, Any] = Field(
        default_factory=dict, description="Статистика по спикерам"
    )


# ----------------------------------------------------------------------
# Процессы
# ----------------------------------------------------------------------


class ProcessResponse(BaseModel):
    """Ответ с данными извлечённого бизнес-процесса."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Идентификатор процесса")
    name: str = Field(..., description="Название процесса")
    department: str = Field(default="", description="Подразделение")
    description: str = Field(default="", description="Описание процесса")
    status: str = Field(default="draft", description="Статус процесса: draft, reviewed, approved")
    trigger: str = Field(default="", description="Триггер запуска процесса")
    result: str = Field(default="", description="Ожидаемый результат процесса")
    participants: list[dict[str, Any] | str] = Field(
        default_factory=list, description="Участники процесса"
    )
    steps: list[dict[str, Any]] = Field(
        default_factory=list, description="Шаги процесса"
    )
    decisions: list[dict[str, Any]] = Field(
        default_factory=list, description="Точки принятия решений"
    )
    pain_points: list[dict[str, Any] | str] = Field(
        default_factory=list, description="Проблемные точки"
    )
    integrations: list[str] = Field(
        default_factory=list, description="Интеграции с системами"
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="Метрики процесса"
    )


class ProcessUpdate(BaseModel):
    """Запрос на обновление процесса (все поля опциональны)."""

    name: str | None = Field(default=None, description="Название процесса")
    department: str | None = Field(default=None, description="Подразделение")
    description: str | None = Field(default=None, description="Описание процесса")
    status: str | None = Field(default=None, description="Статус процесса")
    trigger: str | None = Field(default=None, description="Триггер запуска процесса")
    result: str | None = Field(default=None, description="Ожидаемый результат процесса")
    participants: list[str] | None = Field(default=None, description="Участники процесса")
    steps: list[dict[str, Any]] | None = Field(default=None, description="Шаги процесса")
    decisions: list[dict[str, Any]] | None = Field(
        default=None, description="Точки принятия решений"
    )
    pain_points: list[str] | None = Field(default=None, description="Проблемные точки")
    integrations: list[str] | None = Field(
        default=None, description="Интеграции с системами"
    )
    metrics: dict[str, Any] | None = Field(default=None, description="Метрики процесса")


# ----------------------------------------------------------------------
# GAP-анализ
# ----------------------------------------------------------------------


class GapResponse(BaseModel):
    """Ответ с данными GAP-анализа."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Идентификатор GAP")
    process_name: str = Field(..., description="Название процесса")
    function_name: str = Field(default="", description="Название функции")
    coverage: str = Field(default="", description="Степень покрытия (полное/частичное/отсутствует)")
    erp_module: str = Field(default="", description="Модуль ERP-системы")
    gap_description: str = Field(default="", description="Описание разрыва")
    recommendation: str = Field(default="", description="Рекомендация")
    effort: str = Field(default="", description="Оценка трудозатрат")


# ----------------------------------------------------------------------
# Требования
# ----------------------------------------------------------------------


class RequirementResponse(BaseModel):
    """Ответ с данными требования."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Идентификатор требования")
    type: str = Field(default="", description="Тип требования (функциональное/нефункциональное)")
    module: str = Field(default="", description="Модуль системы")
    description: str = Field(default="", description="Описание требования")
    priority: str = Field(default="", description="Приоритет (высокий/средний/низкий)")
    source: str = Field(default="", description="Источник требования")
    effort: str = Field(default="", description="Оценка трудозатрат")


# ----------------------------------------------------------------------
# Пайплайн
# ----------------------------------------------------------------------


class StageInfoResponse(BaseModel):
    """Информация о стадии пайплайна."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="Код стадии")
    label: str = Field(description="Название стадии")
    status: str = Field(default="pending", description="Статус стадии")
    progress: float = Field(default=0.0, description="Прогресс стадии")
    error: str | None = Field(default=None, description="Ошибка")
    completed: bool = Field(default=False, description="Завершена ли стадия")


class PipelineStatusResponse(BaseModel):
    """Ответ со статусом пайплайна обработки."""

    model_config = ConfigDict(from_attributes=True)

    project_id: str = Field(default="", description="ID проекта")
    current_stage: str | None = Field(default=None, description="Текущий этап пайплайна")
    stages: list[StageInfoResponse] = Field(
        default_factory=list, description="Информация по стадиям"
    )
    completed_stages: list[str] = Field(
        default_factory=list, description="Завершённые этапы"
    )
    overall_progress: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Общий прогресс в процентах"
    )


class PipelineStageRequest(BaseModel):
    """Запрос на запуск этапа пайплайна."""

    stage: str = Field(..., description="Название этапа для запуска")


class ErpConfigRequest(BaseModel):
    """Конфигурация ERP для GAP-анализа."""

    erp_system: str = Field(default="1C:ERP", description="Название ERP-системы")
    modules: list[str] = Field(default_factory=list, description="Модули ERP для анализа")
    version: str = Field(default="", description="Версия ERP-системы")


# ----------------------------------------------------------------------
# Загрузка файлов
# ----------------------------------------------------------------------


class UploadResponse(BaseModel):
    """Ответ после загрузки файла."""

    message: str = Field(..., description="Сообщение о результате")
    file_id: str = Field(..., description="Идентификатор загруженного файла")
    filename: str = Field(..., description="Имя сохранённого файла")


class ImportFolderRequest(BaseModel):
    """Запрос на импорт файлов из папки."""

    path: str = Field(..., min_length=1, description="Путь к папке с файлами")


class ImportFolderResponse(BaseModel):
    """Ответ после импорта файлов из папки."""

    message: str = Field(..., description="Сообщение о результате")
    imported_files: list[str] = Field(
        default_factory=list, description="Список импортированных файлов"
    )
    skipped_files: list[str] = Field(
        default_factory=list, description="Список пропущенных файлов"
    )
    total_imported: int = Field(default=0, description="Количество импортированных файлов")


# ----------------------------------------------------------------------
# Общие
# ----------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Стандартный ответ с ошибкой."""

    detail: str = Field(..., description="Описание ошибки")
    error_code: str | None = Field(default=None, description="Код ошибки")


class MessageResponse(BaseModel):
    """Простой ответ с сообщением."""

    message: str = Field(..., description="Сообщение")
