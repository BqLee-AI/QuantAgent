"""merge core alembic heads before source binding persistence

Revision ID: 20260601_0003
Revises: 20260523_0001, 20260527_0002
Create Date: 2026-06-01
"""

from __future__ import annotations


revision = "20260601_0003"
down_revision = ("20260523_0001", "20260527_0002")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
