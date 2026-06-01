"""raw event persistence v1

Revision ID: 20260601_0005
Revises: 20260601_0004
Create Date: 2026-06-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260601_0005"
down_revision = "20260601_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_events",
        sa.Column("raw_event_id", sa.String(length=64), nullable=False),
        sa.Column("source_plugin_id", sa.String(length=128), nullable=False),
        sa.Column("source_binding_id", sa.String(length=64), nullable=True),
        sa.Column("scheduler_run_id", sa.String(length=64), nullable=True),
        sa.Column("external_id", sa.String(length=512), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=256), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("dedupe_strategy", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scheduler_run_id"], ["scheduler_runs.run_id"]),
        sa.ForeignKeyConstraint(["source_binding_id"], ["source_bindings.binding_id"]),
        sa.PrimaryKeyConstraint("raw_event_id"),
    )
    op.create_index("ix_raw_events_binding_captured_at", "raw_events", ["source_binding_id", "captured_at"])
    op.create_index("ix_raw_events_run", "raw_events", ["scheduler_run_id"])
    op.create_index("ix_raw_events_plugin_published_at", "raw_events", ["source_plugin_id", "published_at"])
    op.create_index("ix_raw_events_plugin_external_id", "raw_events", ["source_plugin_id", "external_id"])
    op.create_index("ix_raw_events_dedupe_key", "raw_events", ["dedupe_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_raw_events_dedupe_key", table_name="raw_events")
    op.drop_index("ix_raw_events_plugin_external_id", table_name="raw_events")
    op.drop_index("ix_raw_events_plugin_published_at", table_name="raw_events")
    op.drop_index("ix_raw_events_run", table_name="raw_events")
    op.drop_index("ix_raw_events_binding_captured_at", table_name="raw_events")
    op.drop_table("raw_events")
