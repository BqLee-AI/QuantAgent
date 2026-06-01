"""add source raw event tables

Revision ID: 20260521_0001
Revises:
Create Date: 2026-05-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260521_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raw_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_plugin_id", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("dedupe_key", sa.String(length=1024), nullable=False),
        sa.Column("dedupe_reason", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_raw_events_dedupe_key"),
    )
    op.create_index("ix_raw_events_captured_at", "raw_events", ["captured_at"])
    op.create_index("ix_raw_events_source_external", "raw_events", ["source_plugin_id", "external_id"])

    op.create_table(
        "source_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_plugin_id", sa.String(length=255), nullable=False),
        sa.Column("owner_type", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("effective_config", sa.JSON(), nullable=False),
        sa.Column("schedule_policy", sa.JSON(), nullable=False),
        sa.Column("retry_policy", sa.JSON(), nullable=False),
        sa.Column("rate_limit_policy", sa.JSON(), nullable=False),
        sa.Column("status", sa.Enum("enabled", "disabled", "failed", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_bindings_plugin_owner",
        "source_bindings",
        ["source_plugin_id", "owner_type", "owner_id"],
    )

    op.create_table(
        "source_fetch_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_binding_id", sa.String(length=36), nullable=False),
        sa.Column("source_plugin_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Enum("running", "succeeded", "failed", native_enum=False), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("stored_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_binding_id"], ["source_bindings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_fetch_runs_binding_started",
        "source_fetch_runs",
        ["source_binding_id", "started_at"],
    )
    op.create_index(
        "ix_source_fetch_runs_plugin_started",
        "source_fetch_runs",
        ["source_plugin_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_source_fetch_runs_plugin_started", table_name="source_fetch_runs")
    op.drop_index("ix_source_fetch_runs_binding_started", table_name="source_fetch_runs")
    op.drop_table("source_fetch_runs")
    op.drop_index("ix_source_bindings_plugin_owner", table_name="source_bindings")
    op.drop_table("source_bindings")
    op.drop_index("ix_raw_events_source_external", table_name="raw_events")
    op.drop_index("ix_raw_events_captured_at", table_name="raw_events")
    op.drop_table("raw_events")
