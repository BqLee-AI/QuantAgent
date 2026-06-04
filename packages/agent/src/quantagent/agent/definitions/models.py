from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuntimePolicy(StrictModel):
    model: Any | None = Field(
        default=None,
        description="DeepAgents model identifier or chat model. None allows scripted test harnesses.",
    )
    max_tool_calls: int = Field(default=12, ge=0, le=100, description="Runtime-level visible tool call budget.")
    max_subagent_tasks: int = Field(default=1, ge=0, le=20, description="Runtime-level delegated task budget.")
    max_provider_calls: int = Field(default=8, ge=0, le=100, description="Provider call budget for the run.")
    max_todo_revisions: int = Field(default=2, ge=0, le=20, description="Expected todo revision budget.")
    timeout_seconds: float | None = Field(default=None, gt=0, description="Optional run timeout.")
    backend: Literal["state", "custom"] = Field(
        default="state",
        description="MVP defaults to DeepAgents StateBackend; custom is reserved for injected test/runtime backends.",
    )
    interrupt_on: dict[str, bool] = Field(
        default_factory=dict,
        description="DeepAgents interrupt_on mapping for sensitive tools. Approval execution is handled downstream.",
    )


class SubAgentDefinition(StrictModel):
    subagent_id: str = Field(min_length=1, description="Stable subagent definition id.")
    name: str = Field(min_length=1, description="DeepAgents-visible subagent name.")
    description: str = Field(min_length=1, description="When the main agent should delegate to this subagent.")
    system_prompt: str = Field(min_length=1, description="Complete subagent instructions.")
    tool_ids: list[str] = Field(default_factory=list, description="Tool ids requested by this subagent.")
    skill_paths: list[str] = Field(default_factory=list, description="Skill directories explicitly granted to this subagent.")
    max_tool_calls: int | None = Field(default=None, ge=0, le=100, description="Optional subagent tool budget.")
    output_schema_id: str | None = Field(default=None, description="Optional structured output schema reference.")


class AgentDefinition(StrictModel):
    agent_id: str = Field(min_length=1, description="Stable main agent definition id.")
    version: str = Field(min_length=1, description="Definition version recorded with each run.")
    name: str = Field(min_length=1, description="Human-readable agent name.")
    description: str = Field(default="", description="Short purpose summary.")
    system_prompt: str = Field(min_length=1, description="Main agent instructions.")
    tool_ids: list[str] = Field(default_factory=list, description="Tool ids requested by the main agent.")
    skill_paths: list[str] = Field(default_factory=list, description="Skill directories granted to the main agent.")
    subagents: list[SubAgentDefinition] = Field(default_factory=list, description="Custom DeepAgents subagents.")
    provider_policy_id: str | None = Field(default=None, description="Provider policy reference for later ProviderManager integration.")
    output_schema_id: str | None = Field(default=None, description="Structured output schema reference.")
