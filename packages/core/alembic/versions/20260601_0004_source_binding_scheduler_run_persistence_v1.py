"""source binding scheduler run persistence v1

Revision ID: 20260601_0004
Revises: 20260601_0003
Create Date: 2026-06-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260601_0004"
down_revision = "20260601_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_bindings",
        sa.Column("binding_id", sa.String(length=64), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("source_plugin_id", sa.String(length=128), nullable=False),
        sa.Column("source_plugin_version", sa.String(length=64), nullable=True),
        sa.Column("effective_config_snapshot", sa.JSON(), nullable=False),
        sa.Column("schedule_policy", sa.JSON(), nullable=False),
        sa.Column("retry_policy", sa.JSON(), nullable=False),
        sa.Column("rate_limit_policy", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_run_id", sa.String(length=64), nullable=True),
        sa.Column("last_run_status", sa.String(length=32), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disabled_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("binding_id"),
    )
    op.create_index("ix_source_bindings_status_next_run_at", "source_bindings", ["status", "next_run_at"])
    op.create_index("ix_source_bindings_owner", "source_bindings", ["owner_type", "owner_id"])
    op.create_index("ix_source_bindings_plugin", "source_bindings", ["source_plugin_id"])

    op.create_table(
        "scheduler_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("binding_id", sa.String(length=64), nullable=False),
        sa.Column("source_plugin_id", sa.String(length=128), nullable=False),
        sa.Column("source_plugin_version", sa.String(length=64), nullable=True),
        sa.Column("trigger_mode", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("timeout_ms", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("failure_stage", sa.String(length=32), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=True),
        sa.Column("output_summary", sa.JSON(), nullable=False),
        sa.Column("captured_count", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["binding_id"], ["source_bindings.binding_id"]),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_scheduler_runs_binding_started_at", "scheduler_runs", ["binding_id", "started_at"])
    op.create_index("ix_scheduler_runs_binding_created_at", "scheduler_runs", ["binding_id", "created_at"])
    op.create_index("ix_scheduler_runs_request_id", "scheduler_runs", ["request_id"])
    op.create_index("ix_scheduler_runs_status", "scheduler_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_scheduler_runs_status", table_name="scheduler_runs")
    op.drop_index("ix_scheduler_runs_request_id", table_name="scheduler_runs")
    op.drop_index("ix_scheduler_runs_binding_created_at", table_name="scheduler_runs")
    op.drop_index("ix_scheduler_runs_binding_started_at", table_name="scheduler_runs")
    op.drop_table("scheduler_runs")

    op.drop_index("ix_source_bindings_plugin", table_name="source_bindings")
    op.drop_index("ix_source_bindings_owner", table_name="source_bindings")
    op.drop_index("ix_source_bindings_status_next_run_at", table_name="source_bindings")
    op.drop_table("source_bindings")
