from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from quantagent.api.schemas.events import EventListItemResponse, EventSummaryBucketsResponse


DashboardSectionStatus = Literal["ok", "empty", "unavailable", "error"]


class DashboardSectionMetaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: DashboardSectionStatus
    reason: str | None = None
    updated_at: datetime | None = None


class DashboardSectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: DashboardSectionMetaResponse
    data: dict[str, Any] = Field(default_factory=dict)


class DashboardApprovalItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    risk_level: str = Field(min_length=1)
    expires_at: str | None = None


class DashboardHealthItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    affected_event_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    runtime_ref: dict[str, str] | None = None


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    featured_events: DashboardSectionResponse
    approval_summary: DashboardSectionResponse
    health_summary: DashboardSectionResponse
    entry_metrics: DashboardSectionResponse
