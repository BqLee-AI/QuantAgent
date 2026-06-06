from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from quantagent.core.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class EventORM(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_authority: Mapped[str | None] = mapped_column(String(128), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_status: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False)
    credibility: Mapped[str | None] = mapped_column(String(32), nullable=True)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommendation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_direction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    industries: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    entities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    featured_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("raw_events.raw_event_id"),
        nullable=True,
    )
    routed_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("event_intake_routed_events.event_id"),
        nullable=True,
    )
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    identity_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    identity_value: Mapped[str] = mapped_column(String(256), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    latest_agent_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latest_tool_invocation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.approval_id"),
        nullable=True,
    )
    degradation_notices: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    evidence_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    industry_impact_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    best_action_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    audit_refs: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class EventStateTransitionORM(Base):
    __tablename__ = "event_state_transitions"

    transition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.event_id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_ref: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


Index("ix_events_status_captured_event", EventORM.current_status, EventORM.captured_at, EventORM.event_id)
Index("ix_events_analysis_captured_event", EventORM.analysis_status, EventORM.captured_at, EventORM.event_id)
Index("ix_events_source_type_captured_event", EventORM.source_type, EventORM.captured_at, EventORM.event_id)
Index("ix_events_featured_priority_captured_event", EventORM.is_featured, EventORM.priority_score, EventORM.captured_at, EventORM.event_id)
Index("ix_events_raw_event_id", EventORM.raw_event_id)
Index("ix_events_routed_event_id", EventORM.routed_event_id)
Index("ix_events_trace_id", EventORM.trace_id)
Index("uq_events_identity", EventORM.identity_kind, EventORM.identity_value, unique=True)
Index(
    "uq_events_raw_event_id_not_null",
    EventORM.raw_event_id,
    unique=True,
    sqlite_where=EventORM.raw_event_id.is_not(None),
    postgresql_where=EventORM.raw_event_id.is_not(None),
)
Index(
    "uq_events_routed_event_id_not_null",
    EventORM.routed_event_id,
    unique=True,
    sqlite_where=EventORM.routed_event_id.is_not(None),
    postgresql_where=EventORM.routed_event_id.is_not(None),
)
Index(
    "ix_event_state_transitions_event_created",
    EventStateTransitionORM.event_id,
    EventStateTransitionORM.created_at,
    EventStateTransitionORM.transition_id,
)
