from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RawEventSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_event_id: str = Field(min_length=1)
    source_plugin_id: str = Field(min_length=1)
    external_id: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    first_captured_at: datetime
    last_captured_at: datetime
    dedupe_strategy: str = Field(min_length=1)
    duplicate_capture_count: int = Field(ge=0)
    first_binding_id: str | None = None
    first_run_id: str | None = None
    content_preview: str | None = None
    metadata_summary: dict[str, Any] = Field(default_factory=dict)


class RawEventDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_event_id: str = Field(min_length=1)
    source_plugin_id: str = Field(min_length=1)
    external_id: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    first_captured_at: datetime
    last_captured_at: datetime
    dedupe_strategy: str = Field(min_length=1)
    duplicate_capture_count: int = Field(ge=0)
    first_binding_id: str | None = None
    first_run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class RawEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RawEventSummaryResponse]
    next_cursor: str | None = None
