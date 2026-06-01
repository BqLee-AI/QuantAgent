"""merge wallet and model config migration heads

Revision ID: 20260601_0001
Revises: 20260523_0001, 20260527_0002
Create Date: 2026-06-01
"""

from __future__ import annotations

from collections.abc import Sequence


revision: str = "20260601_0001"
down_revision: tuple[str, str] = ("20260523_0001", "20260527_0002")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 只合并 Alembic revision 图；两个父迁移已经分别创建 wallet 与 model config 表。
    pass


def downgrade() -> None:
    # Alembic 会按父迁移继续 downgrade；这里不改动任何 schema。
    pass
