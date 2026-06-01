from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from quantagent.core.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceBindingStatus(str, enum.Enum):
    enabled = "enabled"
    disabled = "disabled"
    failed = "failed"


class SourceFetchRunStatus(str, enum.Enum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class RawEvent(Base):
    __tablename__ = "raw_events"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_raw_events_dedupe_key"),
        Index("ix_raw_events_source_external", "source_plugin_id", "external_id"),
        Index("ix_raw_events_captured_at", "captured_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_plugin_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    dedupe_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    dedupe_reason: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SourceBinding(Base):
    __tablename__ = "source_bindings"
    __table_args__ = (
        Index("ix_source_bindings_plugin_owner", "source_plugin_id", "owner_type", "owner_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_plugin_id: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    effective_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    schedule_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    retry_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rate_limit_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[SourceBindingStatus] = mapped_column(
        Enum(SourceBindingStatus, native_enum=False),
        default=SourceBindingStatus.enabled,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SourceFetchRun(Base):
    __tablename__ = "source_fetch_runs"
    __table_args__ = (
        Index("ix_source_fetch_runs_binding_started", "source_binding_id", "started_at"),
        Index("ix_source_fetch_runs_plugin_started", "source_plugin_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_binding_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("source_bindings.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_plugin_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[SourceFetchRunStatus] = mapped_column(
        Enum(SourceFetchRunStatus, native_enum=False),
        default=SourceFetchRunStatus.running,
        nullable=False,
    )
    fetched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
