"""transcripts — full dialogue text and structured segments."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from models.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.db.call_log import CallLog


class Transcript(TimestampMixin, Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    call_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("call_logs.call_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    full_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_phrases: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    dialogue: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=False, default=list
    )  # [{role, text, timestamp}]

    language: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)
    stt_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationship
    call_log: Mapped[CallLog] = relationship("CallLog", back_populates="transcripts")
