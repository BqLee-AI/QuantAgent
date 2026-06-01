from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


BackendHealthStatus = Literal["healthy", "degraded", "unavailable", "not_configured"]
RuntimeResourceState = Literal["ready", "empty", "unavailable"]
RuntimeHealthSocketStatus = Literal["connected", "degraded", "unknown"]
RuntimePartialStatus = Literal["ready", "degraded", "unavailable"]


class RuntimeInspectPageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    returned: int = Field(ge=0)
    cursor: str | None = None
    next_cursor: str | None = None


class RuntimeInspectUnavailable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: RuntimePartialStatus
    reason: str = Field(min_length=1)
    message: str = Field(min_length=1)


class RuntimeErrorSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(min_length=1)
    error_message_summary: str = Field(min_length=1)
    failure_stage: str | None = None
    retryable: bool | None = None


class RuntimeRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    resource: str = Field(min_length=1)


class RuntimeListMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: RuntimeResourceState
    page: RuntimeInspectPageInfo
    unavailable: RuntimeInspectUnavailable | None = None


class RuntimeListResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")

    items: list[T]
    meta: RuntimeListMeta


class RuntimeHealthSeveritySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critical: int = Field(ge=0)
    warning: int = Field(ge=0)
    info: int = Field(ge=0)


class RuntimeBackendStatusSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api: BackendHealthStatus
    scheduler: BackendHealthStatus
    worker: BackendHealthStatus


class RuntimeHealthSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_agent_run_count: int = Field(ge=0)
    recent_failed_agent_run_count: int = Field(ge=0)
    recent_failed_tool_invocation_count: int = Field(ge=0)
    runtime_error_severity_summary: RuntimeHealthSeveritySummary
    backend_status: RuntimeBackendStatusSummary
    websocket_status_hint: RuntimeHealthSocketStatus
    partial_status: RuntimePartialStatus
    unavailable_resources: list[RuntimeInspectUnavailable] = Field(default_factory=list)
    generated_at: datetime


class AgentRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    event_id: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    run_type: str = Field(min_length=1)
    status: str = Field(min_length=1)
    provider_policy: str | None = None
    model_used: str | None = None
    token_usage_summary: dict[str, Any] | None = None
    cost_estimate_summary: dict[str, Any] | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    error_summary: RuntimeErrorSummaryPayload | None = None


class AgentRunDetail(AgentRunSummary):
    input_summary: dict[str, Any] | None = None
    output_summary: dict[str, Any] | None = None
    related_tool_invocation_refs: list[RuntimeRef] = Field(default_factory=list)
    scheduler_run_ref: RuntimeRef | None = None


class ToolInvocationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invocation_id: str = Field(min_length=1)
    agent_run_id: str | None = None
    event_id: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    tool_id: str = Field(min_length=1)
    plugin_id: str | None = None
    risk_level: str | None = None
    status: str = Field(min_length=1)
    retry_count: int = Field(ge=0)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    error_summary: RuntimeErrorSummaryPayload | None = None


class ToolInvocationDetail(ToolInvocationSummary):
    input_summary: dict[str, Any] | None = None
    output_summary: dict[str, Any] | None = None
    approval_ref: RuntimeRef | None = None


class SchedulerRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    binding_id: str | None = None
    plugin_id: str | None = None
    request_id: str | None = None
    trigger_type: str = Field(min_length=1)
    status: str = Field(min_length=1)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    error_summary: RuntimeErrorSummaryPayload | None = None


class SchedulerRunDetail(SchedulerRunSummary):
    event_ref: RuntimeRef | None = None
    captured_count_summary: dict[str, int] | None = None


class RuntimeErrorSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_id: str = Field(min_length=1)
    component: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    status: str = Field(min_length=1)
    error_code: str = Field(min_length=1)
    error_message_summary: str = Field(min_length=1)
    provider: str | None = None
    provider_policy: str | None = None
    trace_id: str | None = None
    event_id: str | None = None
    plugin_id: str | None = None
    created_at: datetime


class RuntimeErrorDetail(RuntimeErrorSummary):
    details_summary: dict[str, Any] | None = None
    related_refs: dict[str, RuntimeRef] | None = None
