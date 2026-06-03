from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RuntimeAuditNewsStatus = Literal["captured", "linked", "pending", "routed", "unavailable"]
RuntimeAuditNewsStage = Literal[
    "captured",
    "persisted",
    "scheduler_linked",
    "ai_intake_unavailable",
    "ai_intake_routed",
    "route_decided",
    "route_unavailable",
]
RuntimeAuditTimelineStatus = Literal["success", "pending", "warning", "unavailable"]
RuntimeAuditAgentStageStatus = Literal["success", "pending", "failed", "unavailable"]
RuntimeAuditAgentType = Literal["router_agent", "industry_main_agent"]


class RuntimeAuditNewsTraceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_event_id: str = Field(min_length=1)
    binding_id: str | None = None
    run_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None


class RuntimeAuditNewsRefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1)
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class RuntimeAuditNewsTimelineStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: RuntimeAuditNewsStage
    label: str = Field(min_length=1)
    status: RuntimeAuditTimelineStatus
    occurred_at: datetime | None = None
    summary: str = Field(min_length=1)
    refs: list[RuntimeAuditNewsRefResponse] = Field(default_factory=list)


class RuntimeAuditAgentStageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    agent_type: RuntimeAuditAgentType
    status: RuntimeAuditAgentStageStatus
    summary: str = Field(min_length=1)
    key_fields: dict[str, Any] = Field(default_factory=dict)
    output_json: dict[str, Any] | None = None
    refs: list[RuntimeAuditNewsRefResponse] = Field(default_factory=list)
    unavailable_reason: str | None = None


class RuntimeAuditNewsItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_event_id: str = Field(min_length=1)
    title: str | None = None
    canonical_url: str | None = None
    url_host: str | None = None
    source_plugin_id: str = Field(min_length=1)
    source_name: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    first_captured_at: datetime
    last_captured_at: datetime
    content_preview: str | None = None
    status: RuntimeAuditNewsStatus
    current_stage: RuntimeAuditNewsStage
    focus_stage: RuntimeAuditNewsStage
    trace: RuntimeAuditNewsTraceResponse
    timeline: list[RuntimeAuditNewsTimelineStepResponse]
    agent_stages: list[RuntimeAuditAgentStageResponse] = Field(default_factory=list)
    safe_details: dict[str, Any] = Field(default_factory=dict)


class RuntimeAuditNewsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RuntimeAuditNewsItemResponse]
    next_cursor: str | None = None
    generated_at: datetime
