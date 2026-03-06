"""SQLAlchemy ORM модели: CallLog, Transcript.

Все модели используют UUID первичные ключи и timestamp-поля с timezone.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""


class CallLog(Base):
    """Лог входящих звонков."""

    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Идентификаторы Mango Office
    mango_call_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    mango_entry_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Информация о звонящем
    caller_number: Mapped[str] = mapped_column(String(20), index=True)
    called_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    line_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Состояние звонка
    event_type: Mapped[str] = mapped_column(String(32))
    call_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), default="incoming")

    # Интеграция с 1С
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_known_client: Mapped[bool] = mapped_column(default=False)

    # Результат маршрутизации
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Сырые данные
    raw_webhook_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Временные метки
    call_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    call_ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Связи
    transcripts: Mapped[list[Transcript]] = relationship(
        back_populates="call_log", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_call_logs_caller_created", "caller_number", "created_at"),
    )


class Transcript(Base):
    """Транскрипция звонка (Phase 2 — STT, но создаём схему сейчас)."""

    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    call_log_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("call_logs.id", ondelete="CASCADE")
    )

    # Контент
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    segments: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Результат AI-классификации
    classification: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Метаданные
    language: Mapped[str] = mapped_column(String(8), default="ru")
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Связи
    call_log: Mapped[CallLog] = relationship(back_populates="transcripts")
