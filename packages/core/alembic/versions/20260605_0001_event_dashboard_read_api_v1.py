"""event dashboard read api v1

Revision ID: 20260605_0001
Revises: 20260604_0002
Create Date: 2026-06-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0001"
down_revision: str | Sequence[str] | None = "20260604_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(length=256), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_authority", sa.String(length=128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_status", sa.String(length=32), nullable=False),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("credibility", sa.String(length=32), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=True),
        sa.Column("recommendation_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=True),
        sa.Column("risk_direction", sa.String(length=32), nullable=True),
        sa.Column("industries", sa.JSON(), nullable=False),
        sa.Column("entities", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("featured_reason", sa.Text(), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("raw_event_id", sa.String(length=64), nullable=True),
        sa.Column("routed_event_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("identity_kind", sa.String(length=32), nullable=False),
        sa.Column("identity_value", sa.String(length=256), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("latest_agent_run_id", sa.String(length=128), nullable=True),
        sa.Column("latest_tool_invocation_id", sa.String(length=128), nullable=True),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("degradation_notices", sa.JSON(), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=False),
        sa.Column("industry_impact_summary", sa.JSON(), nullable=False),
        sa.Column("best_action_summary", sa.JSON(), nullable=False),
        sa.Column("audit_refs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["approval_requests.approval_id"]),
        sa.ForeignKeyConstraint(["raw_event_id"], ["raw_events.raw_event_id"]),
        sa.ForeignKeyConstraint(["routed_event_id"], ["event_intake_routed_events.event_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_events_status_captured_event", "events", ["current_status", "captured_at", "event_id"])
    op.create_index("ix_events_analysis_captured_event", "events", ["analysis_status", "captured_at", "event_id"])
    op.create_index("ix_events_source_type_captured_event", "events", ["source_type", "captured_at", "event_id"])
    op.create_index(
        "ix_events_featured_priority_captured_event",
        "events",
        ["is_featured", "priority_score", "captured_at", "event_id"],
    )
    op.create_index("ix_events_raw_event_id", "events", ["raw_event_id"])
    op.create_index("ix_events_routed_event_id", "events", ["routed_event_id"])
    op.create_index("ix_events_trace_id", "events", ["trace_id"])
    op.create_index("uq_events_identity", "events", ["identity_kind", "identity_value"], unique=True)
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.create_index(
            "uq_events_raw_event_id_not_null",
            "events",
            ["raw_event_id"],
            unique=True,
            postgresql_where=sa.text("raw_event_id IS NOT NULL"),
        )
        op.create_index(
            "uq_events_routed_event_id_not_null",
            "events",
            ["routed_event_id"],
            unique=True,
            postgresql_where=sa.text("routed_event_id IS NOT NULL"),
        )
    else:
        op.create_index(
            "uq_events_raw_event_id_not_null",
            "events",
            ["raw_event_id"],
            unique=True,
            sqlite_where=sa.text("raw_event_id IS NOT NULL"),
        )
        op.create_index(
            "uq_events_routed_event_id_not_null",
            "events",
            ["routed_event_id"],
            unique=True,
            sqlite_where=sa.text("routed_event_id IS NOT NULL"),
        )

    op.create_table(
        "event_state_transitions",
        sa.Column("transition_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("reason_summary", sa.Text(), nullable=True),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("source_ref", sa.JSON(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("transition_id"),
    )
    op.create_index(
        "ix_event_state_transitions_event_created",
        "event_state_transitions",
        ["event_id", "created_at", "transition_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_state_transitions_event_created", table_name="event_state_transitions")
    op.drop_table("event_state_transitions")
    op.drop_index("uq_events_routed_event_id_not_null", table_name="events")
    op.drop_index("uq_events_raw_event_id_not_null", table_name="events")
    op.drop_index("uq_events_identity", table_name="events")
    op.drop_index("ix_events_trace_id", table_name="events")
    op.drop_index("ix_events_routed_event_id", table_name="events")
    op.drop_index("ix_events_raw_event_id", table_name="events")
    op.drop_index("ix_events_featured_priority_captured_event", table_name="events")
    op.drop_index("ix_events_source_type_captured_event", table_name="events")
    op.drop_index("ix_events_analysis_captured_event", table_name="events")
    op.drop_index("ix_events_status_captured_event", table_name="events")
    op.drop_table("events")
