"""model config minimal v1

Revision ID: 20260526_0001
Revises:
Create Date: 2026-05-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "model_invocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("agent_run_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_invocations_created_at", "model_invocations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_invocations_created_at", table_name="model_invocations")
    op.drop_table("model_invocations")
    op.drop_table("model_configs")
