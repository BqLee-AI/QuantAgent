from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


RiskLevel = Literal["low", "medium", "high", "critical"]


class ToolBinding(StrictModel):
    tool_id: str = Field(min_length=1, description="Stable platform tool id.")
    name: str = Field(min_length=1, description="DeepAgents-visible tool name.")
    description: str = Field(min_length=1, description="Tool description shown to the model.")
    risk_level: RiskLevel = Field(default="low", description="Risk metadata for runtime policy and audit.")
    timeout_seconds: float | None = Field(default=None, gt=0, description="Optional execution timeout.")
    requires_interrupt: bool = Field(default=False, description="Whether DeepAgents interrupt_on should guard this tool.")


class ToolProfile(StrictModel):
    profile_id: str = Field(min_length=1, description="Resolved tool profile id.")
    tool_bindings: list[ToolBinding] = Field(default_factory=list, description="Allowed tools for this run.")
    max_tool_calls: int = Field(default=12, ge=0, le=100, description="Maximum visible tool calls allowed.")
    timeout_seconds: float | None = Field(default=None, gt=0, description="Default tool timeout.")
    permission_scope: str = Field(default="default", description="Safe permission scope summary.")
