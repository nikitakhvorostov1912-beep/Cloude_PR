"""classifications — AI classification results for each call."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from models.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.db.call_log import CallLog


class Classification(TimestampMixin, Base):
    __tablename__ = "classifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    call_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("call_logs.call_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    department: Mapped[str] = mapped_column(String(30), nullable=False)
    department_conf: Mapped[float] = mapped_column(Float, nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    task_type_conf: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_conf: Mapped[float] = mapped_column(Float, nullable=False)
    product: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    product_conf: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warnings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]

    llm_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationship
    call_log: Mapped[CallLog] = relationship("CallLog", back_populates="classifications")
