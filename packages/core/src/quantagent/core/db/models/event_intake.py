from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from quantagent.core.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class EventIntakeRoutedEventORM(Base):
    __tablename__ = "event_intake_routed_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    analysis_request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    binding_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    discard_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    key_fields: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    source_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    article_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    provider_invocation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invocation_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


Index("ix_event_intake_routed_raw_event_created", EventIntakeRoutedEventORM.raw_event_id, EventIntakeRoutedEventORM.created_at)
Index("ix_event_intake_routed_binding_created", EventIntakeRoutedEventORM.binding_id, EventIntakeRoutedEventORM.created_at)
Index("ix_event_intake_routed_request_id", EventIntakeRoutedEventORM.request_id)
Index("ix_event_intake_routed_analysis_request", EventIntakeRoutedEventORM.analysis_request_id)
