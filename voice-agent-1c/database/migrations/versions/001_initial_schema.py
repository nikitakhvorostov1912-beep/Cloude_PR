"""Initial schema: call_logs + transcripts.

Revision ID: 001_initial
Revises: None
Create Date: 2026-03-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        # Mango Office
        sa.Column("mango_call_id", sa.String(64), unique=True, nullable=False),
        sa.Column("mango_entry_id", sa.String(64), nullable=True),
        # Звонящий
        sa.Column("caller_number", sa.String(20), nullable=False),
        sa.Column("called_number", sa.String(20), nullable=True),
        sa.Column("line_number", sa.String(20), nullable=True),
        # Состояние
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("call_state", sa.String(32), nullable=True),
        sa.Column("direction", sa.String(16), nullable=False, server_default="incoming"),
        # Клиент 1С
        sa.Column("client_id", sa.String(64), nullable=True),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("is_known_client", sa.Boolean(), nullable=False, server_default="false"),
        # Маршрутизация
        sa.Column("task_id", sa.String(64), nullable=True),
        sa.Column("department", sa.String(64), nullable=True),
        sa.Column("priority", sa.String(16), nullable=True),
        # Данные
        sa.Column("raw_webhook_data", sa.JSON(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        # Временные метки
        sa.Column("call_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("call_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_call_logs_mango_call_id", "call_logs", ["mango_call_id"], unique=True)
    op.create_index("ix_call_logs_caller_number", "call_logs", ["caller_number"])
    op.create_index("ix_call_logs_caller_created", "call_logs", ["caller_number", "created_at"])

    op.create_table(
        "transcripts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "call_log_id",
            sa.String(36),
            sa.ForeignKey("call_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Контент
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("segments", sa.JSON(), nullable=True),
        # AI-классификация
        sa.Column("classification", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        # Метаданные
        sa.Column("language", sa.String(8), nullable=False, server_default="ru"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_transcripts_call_log_id", "transcripts", ["call_log_id"])


def downgrade() -> None:
    op.drop_table("transcripts")
    op.drop_table("call_logs")
