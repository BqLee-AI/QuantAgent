from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from quantagent.core.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class SchedulerRunORM(Base):
    __tablename__ = "scheduler_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    binding_id: Mapped[str] = mapped_column(
        ForeignKey("source_bindings.binding_id"),
        nullable=False,
    )
    source_plugin_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_plugin_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trigger_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeout_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retryable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    output_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    captured_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


Index("ix_scheduler_runs_binding_started_at", SchedulerRunORM.binding_id, SchedulerRunORM.started_at)
Index("ix_scheduler_runs_binding_created_at", SchedulerRunORM.binding_id, SchedulerRunORM.created_at)
Index("ix_scheduler_runs_request_id", SchedulerRunORM.request_id)
Index("ix_scheduler_runs_status", SchedulerRunORM.status)
