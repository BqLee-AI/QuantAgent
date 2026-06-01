from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from quantagent.core.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class RawEventORM(Base):
    __tablename__ = "raw_events"

    raw_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_plugin_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_binding_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_bindings.binding_id"),
        nullable=True,
    )
    scheduler_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scheduler_runs.run_id"),
        nullable=True,
    )
    external_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    dedupe_strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


Index("ix_raw_events_binding_captured_at", RawEventORM.source_binding_id, RawEventORM.captured_at)
Index("ix_raw_events_run", RawEventORM.scheduler_run_id)
Index("ix_raw_events_plugin_published_at", RawEventORM.source_plugin_id, RawEventORM.published_at)
Index("ix_raw_events_plugin_external_id", RawEventORM.source_plugin_id, RawEventORM.external_id)
Index("ix_raw_events_dedupe_key", RawEventORM.dedupe_key, unique=True)
