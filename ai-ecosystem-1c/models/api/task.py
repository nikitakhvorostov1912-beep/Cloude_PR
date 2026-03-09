"""Domain enums and classification models.

These are the core business-domain value objects used throughout the system:
routing, classification, task creation, and feedback loops.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────────────────────────────────
# Business Enums
# ──────────────────────────────────────────────────────────────────────
class Department(StrEnum):
    SUPPORT = "support"
    DEVELOPMENT = "development"
    IMPLEMENTATION = "implementation"
    PRESALE = "presale"
    SPECIALIST = "specialist"


class Product(StrEnum):
    BP = "БП"
    KA = "КА"
    ZUP = "ЗУП"
    UT = "УТ"
    RETAIL = "Розница"
    ERP = "ERP"
    CUSTOM = "Кастомная"
    UNKNOWN = "Неизвестно"


class TaskType(StrEnum):
    ERROR = "error"
    CONSULT = "consult"
    FEATURE = "feature"
    UPDATE = "update"
    PROJECT = "project"


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# ──────────────────────────────────────────────────────────────────────
# Classification result (output of Agent 03)
# ──────────────────────────────────────────────────────────────────────
class ClassificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    department: Department
    department_confidence: float = Field(ge=0.0, le=1.0)
    department_reason: str

    task_type: TaskType
    task_type_confidence: float = Field(ge=0.0, le=1.0)

    priority: Priority
    priority_confidence: float = Field(ge=0.0, le=1.0)
    priority_reason: str

    product: Optional[Product] = None
    product_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    description: str
    summary: str = Field(max_length=500)
    key_phrases: list[str] = Field(default_factory=list)
    reasoning: str = ""
    warnings: list[str] = Field(default_factory=list)

    used_deterministic_rule: Optional[str] = None
    llm_model: Optional[str] = None
    tokens_used: Optional[int] = None


# ──────────────────────────────────────────────────────────────────────
# Deterministic routing result (before LLM)
# ──────────────────────────────────────────────────────────────────────
class RoutingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    department: Department
    task_type: Optional[TaskType] = None
    priority: Optional[Priority] = None
    confidence: float = Field(ge=0.0, le=1.0)
    rule: str


# ──────────────────────────────────────────────────────────────────────
# Task creation (sent to 1C / Sakura)
# ──────────────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(max_length=200)
    description: str
    client_id: str
    assigned_to: Optional[str] = None
    priority: Priority
    product: Optional[Product] = None
    department: Department
    task_type: TaskType

    call_id: str
    audio_url: Optional[str] = None
    transcript_url: Optional[str] = None
    call_duration_sec: Optional[int] = None

    ai_classification: Optional[dict] = None  # type: ignore[type-arg]
    client_context: Optional[dict] = None  # type: ignore[type-arg]
    ai_solutions: Optional[list[dict]] = None  # type: ignore[type-arg]


class TaskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str
    task_number: str
    assigned_to: Optional[str] = None
    assigned_to_id: Optional[str] = None
    sla_deadline: Optional[str] = None
    status: str = "new"
