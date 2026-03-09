"""Pydantic models for 1C HTTP service API responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OneCClientResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    found: bool = False
    id: Optional[str] = None
    name: Optional[str] = None
    contact_person: Optional[str] = None
    product: Optional[str] = None
    product_version: Optional[str] = None
    customizations: list[str] = Field(default_factory=list)
    contract_status: Optional[str] = None
    contract_expires: Optional[str] = None
    assigned_specialist: Optional[str] = None
    assigned_specialist_id: Optional[str] = None
    sla_level: str = "standard"
    known_issues: list[str] = Field(default_factory=list)


class OneCTaskResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    task_id: str
    task_number: str
    assigned_to: Optional[str] = None
    assigned_to_id: Optional[str] = None
    sla_deadline: Optional[str] = None
    status: str = "new"
