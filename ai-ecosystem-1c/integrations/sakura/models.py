"""Pydantic models for Sakura CRM API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SakuraClientResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    found: bool = False
    id: Optional[str] = None
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    product: Optional[str] = None
    product_version: Optional[str] = None
    assigned_specialist: Optional[str] = None
    assigned_specialist_id: Optional[str] = None
    contract_status: Optional[str] = None
    sla_level: str = "standard"
    tags: list[str] = Field(default_factory=list)
    nps_score: Optional[float] = None


class SakuraTaskItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    id: str
    created_at: str
    summary: str
    task_type: str
    product: str
    solution: Optional[str] = None
    resolved_at: Optional[str] = None
    time_to_resolve_hours: Optional[float] = None
    specialist: Optional[str] = None


class SakuraTasksResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tasks: list[SakuraTaskItem] = Field(default_factory=list)


class SakuraSpecialistResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    id: str
    name: str
    products_expertise: list[str] = Field(default_factory=list)
    current_task_count: int = 0
    is_available: bool = True
    working_hours: Optional[dict[str, str]] = None


class SakuraSpecialistsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    specialists: list[SakuraSpecialistResponse] = Field(default_factory=list)


class SakuraTaskCreate(BaseModel):
    """Full payload sent to Sakura when creating a task with AI enrichment."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    client_id: str
    assigned_to: Optional[str] = None
    priority: str
    product: Optional[str] = None

    ai_classification: Optional[dict[str, Any]] = None
    client_context: Optional[dict[str, Any]] = None
    ai_solutions: Optional[list[dict[str, Any]]] = None

    call_id: str
    audio_url: Optional[str] = None
    transcript_url: Optional[str] = None
    call_duration_sec: Optional[int] = None


class SakuraTaskCreateResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    task_id: str
    task_number: str
    assigned_to: Optional[str] = None
    assigned_to_id: Optional[str] = None
    sla_deadline: Optional[str] = None
    status: str = "new"
