from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


EventDecision = Literal["route", "review", "discard"]
EventStatus = Literal["success", "failed"]
EventTimelineStatus = Literal["success", "warning", "failed", "unavailable"]
EventAgentStageStatus = Literal["success", "failed", "unavailable"]
EventAgentType = Literal["router_agent", "industry_main_agent"]


class EventTraceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_event_id: str = Field(min_length=1)
    routed_event_id: str = Field(min_length=1)
    binding_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    analysis_request_id: str | None = None
    source_message_id: str | None = None


class EventRefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1)
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class EventTimelineStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: EventTimelineStatus
    occurred_at: datetime | None = None
    summary: str = Field(min_length=1)
    refs: list[EventRefResponse] = Field(default_factory=list)


class EventAgentStageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(min_length=1)
    routed_event_id: str | None = None
    agent_name: str = Field(min_length=1)
    agent_type: EventAgentType
    status: EventAgentStageStatus
    summary: str = Field(min_length=1)
    key_fields: dict[str, Any] = Field(default_factory=dict)
    refs: list[EventRefResponse] = Field(default_factory=list)
    unavailable_reason: str | None = None
    has_output_json: bool = False


class EventListItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_event_id: str = Field(min_length=1)
    routed_event_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    title: str | None = None
    url: str | None = None
    url_host: str | None = None
    source_name: str | None = None
    source_plugin_id: str | None = None
    published_at: datetime | None = None
    routed_at: datetime
    decision: EventDecision
    discard_reason: str | None = None
    status: EventStatus
    summary: str | None = None
    event_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    priority: str | None = None
    relationship_summary: str | None = None
    target_industries: list[str] = Field(default_factory=list)
    target_topics: list[str] = Field(default_factory=list)
    quality: dict[str, Any] = Field(default_factory=dict)
    trace: EventTraceResponse
    timeline: list[EventTimelineStepResponse] = Field(default_factory=list)
    router_stage_summary: EventAgentStageResponse


class EventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[EventListItemResponse]
    next_cursor: str | None = None
    generated_at: datetime


class EventDetailResponse(EventListItemResponse):
    safe_details: dict[str, Any] = Field(default_factory=dict)
    agent_stages: list[EventAgentStageResponse] = Field(default_factory=list)


class EventRouterOutputResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_event_id: str = Field(min_length=1)
    routed_event_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    agent_stage: EventAgentStageResponse
    output_json: dict[str, Any]
    trace: EventTraceResponse
