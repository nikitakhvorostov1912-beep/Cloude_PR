"""call_logs — every incoming call from Mango Office."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.db.classification import Classification
    from models.db.transcript import Transcript


class CallLog(TimestampMixin, Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    call_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    caller_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active"
    )  # active | completed | escalated | failed
    escalation_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    audio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI enrichment
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    transcripts: Mapped[list[Transcript]] = relationship(
        "Transcript", back_populates="call_log", cascade="all, delete-orphan"
    )
    classifications: Mapped[list[Classification]] = relationship(
        "Classification", back_populates="call_log", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_call_logs_phone_created", "caller_phone", "created_at"),
        Index("ix_call_logs_status", "status"),
    )
