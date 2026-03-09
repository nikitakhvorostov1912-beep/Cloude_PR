"""001 — initial schema: call_logs, transcripts, classifications, feedback, knowledge.

Revision ID: 001
Create Date: 2026-03-07
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # call_logs
    op.create_table(
        "call_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("call_id", sa.String(100), unique=True, nullable=False),
        sa.Column("caller_phone", sa.String(20), nullable=False),
        sa.Column("client_id", sa.String(50), nullable=True),
        sa.Column("client_name", sa.String(200), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_sec", sa.Integer, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("escalation_reason", sa.String(200), nullable=True),
        sa.Column("audio_url", sa.Text, nullable=True),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_call_logs_call_id", "call_logs", ["call_id"])
    op.create_index("ix_call_logs_caller_phone", "call_logs", ["caller_phone"])
    op.create_index("ix_call_logs_phone_created", "call_logs", ["caller_phone", "created_at"])
    op.create_index("ix_call_logs_status", "call_logs", ["status"])

    # transcripts
    op.create_table(
        "transcripts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "call_id",
            sa.String(100),
            sa.ForeignKey("call_logs.call_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_text", sa.Text, nullable=False, server_default=""),
        sa.Column("key_phrases", sa.JSON, nullable=True),
        sa.Column("dialogue", sa.JSON, nullable=False),
        sa.Column("language", sa.String(5), nullable=False, server_default="ru"),
        sa.Column("stt_provider", sa.String(50), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transcripts_call_id", "transcripts", ["call_id"])

    # classifications
    op.create_table(
        "classifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "call_id",
            sa.String(100),
            sa.ForeignKey("call_logs.call_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", sa.String(50), nullable=True),
        sa.Column("department", sa.String(30), nullable=False),
        sa.Column("department_conf", sa.Float, nullable=False),
        sa.Column("task_type", sa.String(30), nullable=False),
        sa.Column("task_type_conf", sa.Float, nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("priority_conf", sa.Float, nullable=False),
        sa.Column("product", sa.String(30), nullable=True),
        sa.Column("product_conf", sa.Float, nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("warnings", sa.JSON, nullable=True),
        sa.Column("llm_model", sa.String(50), nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_classifications_call_id", "classifications", ["call_id"])

    # specialist_feedback
    op.create_table(
        "specialist_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "call_id",
            sa.String(100),
            sa.ForeignKey("call_logs.call_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", sa.String(50), nullable=False),
        sa.Column("specialist_id", sa.String(50), nullable=True),
        sa.Column("classification_correct", sa.Boolean, nullable=True),
        sa.Column("corrected_department", sa.String(30), nullable=True),
        sa.Column("corrected_task_type", sa.String(30), nullable=True),
        sa.Column("corrected_priority", sa.String(20), nullable=True),
        sa.Column("correction_reason", sa.Text, nullable=True),
        sa.Column("solution_used", sa.Integer, nullable=True),
        sa.Column("solution_helpful", sa.Integer, nullable=True),
        sa.Column("actual_solution", sa.Text, nullable=True),
        sa.Column("overall_rating", sa.Integer, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_specialist_feedback_call_id", "specialist_feedback", ["call_id"])

    # knowledge_entries (Phase 2 prep)
    op.create_table(
        "knowledge_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("problem", sa.Text, nullable=False),
        sa.Column("solution", sa.Text, nullable=False),
        sa.Column("product", sa.String(30), nullable=True),
        sa.Column("task_type", sa.String(30), nullable=True),
        sa.Column("department", sa.String(30), nullable=True),
        sa.Column("configuration_tags", sa.JSON, nullable=True),
        sa.Column("client_type", sa.String(30), nullable=True),
        sa.Column("vector_id", sa.String(100), nullable=True),
        sa.Column("usefulness_score", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("knowledge_entries")
    op.drop_table("specialist_feedback")
    op.drop_table("classifications")
    op.drop_table("transcripts")
    op.drop_table("call_logs")
