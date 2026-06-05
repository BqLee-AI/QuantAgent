from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


EventTimeRangeParam = Literal["today", "24h", "7d", "30d"]
EventSortParam = Literal["mixed", "latest", "priority"]
EventSectionStatus = Literal["ok", "empty", "unavailable", "error"]


class EventRefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1)
    id: str = Field(min_length=1)


class EventSourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    authority: str | None = None


class EventSummaryBucketsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_count: int = Field(ge=0)
    featured_count: int = Field(ge=0)
    analyzing_count: int = Field(ge=0)
    failed_or_review_count: int = Field(ge=0)
    pending_approval_count: int | None = Field(default=None, ge=0)


class EventListFiltersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_range: EventTimeRangeParam
    industry: list[str] = Field(default_factory=list)
    credibility: str | None = None
    analysis_status: str | None = None
    source_type: str | None = None
    sort: EventSortParam
    limit: int = Field(ge=1, le=100)
    cursor: str | None = None


class EventListItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str | None = None
    source: EventSourceResponse
    source_type: str | None = None
    source_url: str | None = None
    published_at: datetime | None = None
    captured_at: datetime
    current_status: str = Field(min_length=1)
    analysis_status: str = Field(min_length=1)
    credibility: str | None = None
    priority_score: float | None = None
    recommendation_score: float | None = None
    confidence: float | None = None
    risk_level: str | None = None
    risk_direction: str | None = None
    industries: list[str] = Field(default_factory=list)
    featured_reason: str | None = None
    trace_ref: EventRefResponse | None = None
    raw_event_ref: EventRefResponse | None = None
    routed_event_ref: EventRefResponse | None = None
    degradation_notices: list[dict[str, Any]] = Field(default_factory=list)


class EventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[EventListItemResponse] = Field(default_factory=list)
    next_cursor: str | None = None
    filters: EventListFiltersResponse
    summary_buckets: EventSummaryBucketsResponse
    generated_at: datetime


class EventStateTransitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transition_id: str = Field(min_length=1)
    from_status: str | None = None
    to_status: str = Field(min_length=1)
    reason_code: str | None = None
    reason_summary: str | None = None
    actor_type: str = Field(min_length=1)
    actor_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    created_at: datetime | None = None


class EventStateSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_status: str = Field(min_length=1)
    analysis_status: str = Field(min_length=1)
    version: int = Field(ge=1)
    transitions: list[EventStateTransitionResponse] = Field(default_factory=list)


class EventBestActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    action_hint: str | None = None
    recommendation_score: float | None = None
    confidence: float | None = None
    risk_level: str | None = None
    risk_direction: str | None = None
    approval_ref: EventRefResponse | None = None
    status: str | None = None
    unavailable_reason: str | None = None


class EventDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    fact_summary: dict[str, Any] = Field(default_factory=dict)
    score_summary: dict[str, Any] = Field(default_factory=dict)
    industry_impact: dict[str, Any] = Field(default_factory=dict)
    best_action: EventBestActionResponse
    approval_ref: EventRefResponse | None = None
    runtime_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    degradation_notices: list[dict[str, Any]] = Field(default_factory=list)
    audit_refs: list[dict[str, Any]] = Field(default_factory=list)
    state_summary: EventStateSummaryResponse
