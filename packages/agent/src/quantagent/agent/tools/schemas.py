from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolInvocationSummary(StrictModel):
    invocation_id: str = Field(description="Runtime tool invocation id.")
    tool_id: str = Field(description="Stable platform tool id.")
    name: str = Field(description="DeepAgents-visible tool name.")
    status: str = Field(description="started, completed, or failed.")
    safe_summary: str = Field(description="Display-safe summary without secrets.")
