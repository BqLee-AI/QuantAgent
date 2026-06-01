from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from quantagent.core.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class SourceBindingORM(Base):
    __tablename__ = "source_bindings"

    binding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_plugin_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_plugin_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    effective_config_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    schedule_policy: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    retry_policy: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    rate_limit_policy: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    disabled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


Index("ix_source_bindings_status_next_run_at", SourceBindingORM.status, SourceBindingORM.next_run_at)
Index("ix_source_bindings_owner", SourceBindingORM.owner_type, SourceBindingORM.owner_id)
Index("ix_source_bindings_plugin", SourceBindingORM.source_plugin_id)
