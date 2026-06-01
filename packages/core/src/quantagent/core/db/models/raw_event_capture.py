from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from quantagent.core.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class RawEventCaptureORM(Base):
    __tablename__ = "raw_event_captures"

    capture_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    raw_event_id: Mapped[str] = mapped_column(
        ForeignKey("raw_events.raw_event_id"),
        nullable=False,
    )
    source_plugin_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_binding_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_bindings.binding_id"),
        nullable=True,
    )
    scheduler_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scheduler_runs.run_id"),
        nullable=True,
    )
    capture_dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    capture_status: Mapped[str] = mapped_column(String(32), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


Index("ix_raw_event_captures_raw_event_captured_at", RawEventCaptureORM.raw_event_id, RawEventCaptureORM.captured_at)
Index("ix_raw_event_captures_binding_captured_at", RawEventCaptureORM.source_binding_id, RawEventCaptureORM.captured_at)
Index("ix_raw_event_captures_run_canonical", RawEventCaptureORM.scheduler_run_id, RawEventCaptureORM.raw_event_id, unique=True)
Index("ix_raw_event_captures_capture_dedupe_key", RawEventCaptureORM.capture_dedupe_key, unique=True)
