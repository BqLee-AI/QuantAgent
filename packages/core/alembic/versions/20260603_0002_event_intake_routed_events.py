"""event intake routed events read model

Revision ID: 20260603_0002
Revises: 20260603_0001
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260603_0002"
down_revision: str | Sequence[str] | None = "20260603_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_intake_routed_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("raw_event_id", sa.String(length=64), nullable=True),
        sa.Column("source_message_id", sa.String(length=128), nullable=True),
        sa.Column("analysis_request_id", sa.String(length=128), nullable=False),
        sa.Column("binding_id", sa.String(length=64), nullable=True),
        sa.Column("owner_type", sa.String(length=64), nullable=True),
        sa.Column("owner_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("discard_reason", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("key_fields", sa.JSON(), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("article_snapshot", sa.JSON(), nullable=False),
        sa.Column("provider_invocation_count", sa.Integer(), nullable=False),
        sa.Column("invocation_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_event_intake_routed_events_event_id"),
    )
    op.create_index(
        "ix_event_intake_routed_raw_event_created",
        "event_intake_routed_events",
        ["raw_event_id", "created_at"],
    )
    op.create_index(
        "ix_event_intake_routed_binding_created",
        "event_intake_routed_events",
        ["binding_id", "created_at"],
    )
    op.create_index("ix_event_intake_routed_request_id", "event_intake_routed_events", ["request_id"])
    op.create_index("ix_event_intake_routed_analysis_request", "event_intake_routed_events", ["analysis_request_id"])


def downgrade() -> None:
    op.drop_index("ix_event_intake_routed_analysis_request", table_name="event_intake_routed_events")
    op.drop_index("ix_event_intake_routed_request_id", table_name="event_intake_routed_events")
    op.drop_index("ix_event_intake_routed_binding_created", table_name="event_intake_routed_events")
    op.drop_index("ix_event_intake_routed_raw_event_created", table_name="event_intake_routed_events")
    op.drop_table("event_intake_routed_events")
