"""knowledge_entries — resolved patterns for RAG (Phase 2 stub)."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from models.db.base import Base, TimestampMixin


class KnowledgeEntry(TimestampMixin, Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)

    product: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    task_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    configuration_tags: Mapped[Optional[list]] = mapped_column(  # type: ignore[type-arg]
        JSON, nullable=True
    )
    client_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    vector_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    usefulness_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
