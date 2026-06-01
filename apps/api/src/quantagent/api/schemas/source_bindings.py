from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SourceBindingStatusValue = Literal["active", "paused", "disabled"]
RunStatusValue = Literal["queued", "running", "succeeded", "failed", "timeout", "cancelled"]
AllowedActionValue = Literal["pause", "resume", "run-now"]


class CursorPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[Any]
    next_cursor: str | None = None


class SourceBindingRunRefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    status: RunStatusValue
    started_at: datetime | None = None
    finished_at: datetime | None = None


class EffectiveConfigSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any] = Field(default_factory=dict)
    secret_fields_masked: list[str] = Field(default_factory=list)
    last_validated_at: str | None = None
    config_source_refs: list[str] = Field(default_factory=list)


class SourceBindingSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source_plugin_id: str = Field(min_length=1)
    owner_type: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    status: SourceBindingStatusValue
    blocked_reason: str | None = None
    schedule_summary: dict[str, Any] = Field(default_factory=dict)
    last_run_ref: SourceBindingRunRefResponse | None = None
    next_run_at: datetime | None = None
    health_summary: dict[str, Any] = Field(default_factory=dict)
    allowed_actions: list[AllowedActionValue] = Field(default_factory=list)


class SourceBindingDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source_plugin_id: str = Field(min_length=1)
    owner_type: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    status: SourceBindingStatusValue
    blocked_reason: str | None = None
    schedule_summary: dict[str, Any] = Field(default_factory=dict)
    last_run_ref: SourceBindingRunRefResponse | None = None
    next_run_at: datetime | None = None
    health_summary: dict[str, Any] = Field(default_factory=dict)
    allowed_actions: list[AllowedActionValue] = Field(default_factory=list)
    effective_config_summary: EffectiveConfigSummaryResponse
    config_version: str = Field(min_length=1)
    config_validation_status: str = Field(min_length=1)
    rate_limit_policy_summary: dict[str, Any] = Field(default_factory=dict)
    retry_policy_summary: dict[str, Any] = Field(default_factory=dict)
    last_error_summary: dict[str, Any] = Field(default_factory=dict)
    audit_refs: list[str] = Field(default_factory=list)
    recent_run_refs: list[SourceBindingRunRefResponse] = Field(default_factory=list)


class SourceBindingStateActionAcceptedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: str = Field(min_length=1)
    target_state: SourceBindingStatusValue
    already_in_target_state: bool
    accepted_at: datetime
    audit_ref: str = Field(min_length=1)


class SourceBindingRunNowAcceptedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: str = Field(min_length=1)
    accepted_at: datetime
    request_id: str = Field(min_length=1)
    requested_run_ref: str = Field(min_length=1)
    audit_ref: str = Field(min_length=1)


class SourceBindingListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SourceBindingSummaryResponse]
    next_cursor: str | None = None
