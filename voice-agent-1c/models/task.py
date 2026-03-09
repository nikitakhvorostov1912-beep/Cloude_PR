"""Pydantic модели: задачи и классификация обращений.

Модели для взаимодействия с 1С и AI-классификацией.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Department(StrEnum):
    """Отделы для маршрутизации."""

    SUPPORT = "support"
    DEVELOPMENT = "development"
    IMPLEMENTATION = "implementation"
    PRESALE = "presale"
    SPECIALIST = "specialist"


class Product(StrEnum):
    """Продукты 1С."""

    BP = "БП"
    KA = "КА"
    ZUP = "ЗУП"
    UT = "УТ"
    RETAIL = "Розница"
    ERP = "ERP"
    CUSTOM = "Кастомная"
    UNKNOWN = "Неизвестно"


class TaskType(StrEnum):
    """Типы обращений."""

    ERROR = "error"
    CONSULT = "consult"
    FEATURE = "feature"
    UPDATE = "update"
    PROJECT = "project"


class Priority(StrEnum):
    """Приоритеты."""

    CRITICAL = "critical"  # 30 мин SLA
    HIGH = "high"  # 2 часа
    NORMAL = "normal"  # До конца дня
    LOW = "low"


class Classification(BaseModel):
    """Результат AI-классификации обращения.

    Формат соответствует master prompt JSON.
    """

    model_config = ConfigDict(from_attributes=True)

    department: Department = Field(..., description="Целевой отдел")
    product: Product = Field(default=Product.UNKNOWN, description="Продукт 1С")
    task_type: TaskType = Field(..., description="Тип обращения")
    priority: Priority = Field(default=Priority.NORMAL, description="Приоритет")
    description: str = Field(default="", description="Подробное описание проблемы")
    summary: str = Field(default="", description="Одна строка для карточки")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Уверенность классификации"
    )


class RoutingResult(BaseModel):
    """Результат маршрутизации на основе правил."""

    department: Department
    priority: Priority
    reason: str = Field(default="", description="Объяснение решения")


# --- Модели API 1С ---


class ClientInfo(BaseModel):
    """Ответ 1С: информация о клиенте по телефону."""

    model_config = ConfigDict(extra="allow")

    found: bool = Field(default=True, description="Клиент найден")
    id: str = Field(..., description="ID клиента в 1С")
    name: str = Field(default="", description="Название организации")
    product: str = Field(default="", description="Основной продукт")
    contract_status: str = Field(default="", description="Статус договора")
    assigned_specialist: str | None = Field(
        default=None, description="Закреплённый специалист"
    )
    sla_level: str = Field(default="standard", description="Уровень SLA")


class TaskCreate(BaseModel):
    """Запрос на создание задачи в 1С."""

    client_id: str | None = Field(default=None, description="ID клиента")
    department: str = Field(..., description="Целевой отдел")
    product: str = Field(default="", description="Продукт 1С")
    task_type: str = Field(..., description="Тип обращения")
    priority: str = Field(default="normal", description="Приоритет")
    summary: str = Field(default="", description="Краткое описание")
    description: str = Field(default="", description="Полное описание")
    source: str = Field(default="voice_agent", description="Источник")
    call_id: str = Field(default="", description="ID звонка Mango")
    transcript_url: str | None = Field(default=None, description="URL транскрипта")
    audio_url: str | None = Field(default=None, description="URL записи")


class TaskResponse(BaseModel):
    """Ответ 1С: созданная задача."""

    model_config = ConfigDict(extra="allow")

    task_id: str = Field(..., description="ID задачи в 1С")
    task_number: str = Field(default="", description="Номер задачи")
    assigned_to: str | None = Field(default=None, description="Назначена на")
    sla_deadline: str | None = Field(default=None, description="Срок SLA")
