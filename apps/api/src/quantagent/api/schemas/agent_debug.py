from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentDebugRunRequest(StrictModel):
    scenario: Literal["primary", "media_follow_up"] = Field(
        default="primary",
        description="NVDA earnings fixture scenario to run.",
    )


class AgentDebugFixtureSummary(StrictModel):
    fixture_id: str = Field(description="Stable debug fixture id.")
    name: str = Field(description="Human-readable fixture name.")
    scenarios: list[str] = Field(description="Supported scenario ids.")
    description: str = Field(description="Display-safe fixture description.")


class AgentDebugSseEvent(StrictModel):
    event_id: str = Field(description="Runtime event id.")
    agent_run_id: str = Field(description="AgentRun id.")
    type: str = Field(description="Stable AgentRunEvent type.")
    seq: int = Field(ge=1, description="Monotonic event sequence.")
    created_at: datetime = Field(description="Event creation time.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Small structured payload without secrets.")
    safe_summary: str | None = Field(default=None, description="Display-safe event summary.")
    trace_id: str = Field(description="Trace id spanning runtime, tools, audit, and logs.")
