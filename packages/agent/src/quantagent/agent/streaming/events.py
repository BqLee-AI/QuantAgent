from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentRunEventType(StrEnum):
    RUN_STARTED = "run.started"
    MODEL_DELTA = "model.delta"
    TODO_UPDATED = "todo.updated"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    SUBAGENT_STARTED = "subagent.started"
    SUBAGENT_COMPLETED = "subagent.completed"
    ARTIFACT_CREATED = "artifact.created"
    RUN_OUTPUT = "run.output"
    RUN_FAILED = "run.failed"
    RUN_COMPLETED = "run.completed"


class AgentRunEvent(StrictModel):
    event_id: str = Field(default_factory=lambda: f"agent_evt_{uuid4().hex}", description="Runtime event id.")
    agent_run_id: str = Field(description="AgentRun id.")
    type: AgentRunEventType = Field(description="Stable event type.")
    seq: int = Field(ge=1, description="Monotonic sequence within the run.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event creation time.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Small structured payload without secrets.")
    safe_summary: str | None = Field(default=None, description="Optional display-safe summary.")
    trace_id: str = Field(description="Trace id spanning runtime, tools, audit, and logs.")
