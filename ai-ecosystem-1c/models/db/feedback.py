"""specialist_feedback — feedback from specialists on AI accuracy."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.db.base import Base, TimestampMixin


class SpecialistFeedback(TimestampMixin, Base):
    __tablename__ = "specialist_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    call_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("call_logs.call_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(String(50), nullable=False)
    specialist_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Classification accuracy
    classification_correct: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    corrected_department: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    corrected_task_type: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    corrected_priority: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    correction_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Solution quality
    solution_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    solution_helpful: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Overall
    overall_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
