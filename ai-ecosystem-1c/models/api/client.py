"""Client context assembled from Sakura CRM and 1C data.

Agent 02 (Identifier) builds this during every incoming call by
querying both external systems in parallel.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RecentTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    created_at: str
    summary: str
    task_type: str
    product: str
    solution: Optional[str] = None
    resolved_at: Optional[str] = None
    time_to_resolve_hours: Optional[float] = None
    specialist: Optional[str] = None


class ClientContext(BaseModel):
    """Full client profile assembled from Sakura + 1C."""

    model_config = ConfigDict(frozen=True)

    found: bool = False

    # Identifiers
    sakura_id: Optional[str] = None
    onec_id: Optional[str] = None

    # Basic info
    name: Optional[str] = None
    contact_person: Optional[str] = None

    # Product configuration
    product: Optional[str] = None
    product_version: Optional[str] = None
    customizations: list[str] = Field(default_factory=list)

    # Contract
    contract_status: Optional[str] = None
    contract_expires: Optional[str] = None
    sla_level: str = "standard"

    # Assignment
    assigned_specialist: Optional[str] = None
    assigned_specialist_id: Optional[str] = None

    # History
    recent_tasks: list[RecentTask] = Field(default_factory=list)

    # Warnings
    config_warnings: list[str] = Field(default_factory=list)


class SpecialistInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    products_expertise: list[str] = Field(default_factory=list)
    current_task_count: int = 0
    is_available: bool = True
    working_hours: Optional[dict[str, str]] = None


class SpecialistAssignment(BaseModel):
    model_config = ConfigDict(frozen=True)

    specialist_id: str
    specialist_name: Optional[str] = None
    reason: str
    current_load: Optional[int] = None
