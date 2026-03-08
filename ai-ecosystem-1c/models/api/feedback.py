"""Specialist feedback on AI classification accuracy.

Collected after a task is resolved so the system can self-improve.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SpecialistFeedback(BaseModel):
    model_config = ConfigDict(frozen=True)

    call_id: str
    task_id: str
    specialist_id: Optional[str] = None

    # Classification accuracy
    classification_correct: Optional[bool] = None
    corrected_department: Optional[str] = None
    corrected_task_type: Optional[str] = None
    corrected_priority: Optional[str] = None
    correction_reason: Optional[str] = None

    # Solution quality
    solution_used: Optional[int] = Field(default=None, ge=1, le=4)
    solution_helpful: Optional[int] = Field(default=None, ge=1, le=5)
    actual_solution: Optional[str] = None

    # Overall
    overall_rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None
