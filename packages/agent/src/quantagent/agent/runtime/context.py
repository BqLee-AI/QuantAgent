from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from quantagent.agent.artifacts.models import ArtifactRef


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunContextSection(StrictModel):
    name: str = Field(min_length=1, description="Context section name, e.g. event or route_context.")
    summary: str = Field(min_length=1, description="Compressed context summary for the agent.")
    data: dict[str, Any] = Field(default_factory=dict, description="Small structured context without secrets.")
    artifact_ref: ArtifactRef | None = Field(default=None, description="Artifact reference when the context is large.")


class RunContextSnapshot(StrictModel):
    context_id: str = Field(min_length=1, description="Audit id for this run context snapshot.")
    sections: list[RunContextSection] = Field(default_factory=list, description="Bounded run context sections.")
    artifact_refs: list[ArtifactRef] = Field(default_factory=list, description="Extra artifact refs available to this run.")
    safe_summary: str = Field(min_length=1, description="Prompt/log-safe context summary.")


class ToolRuntimeContext(StrictModel):
    agent_run_id: str = Field(description="Current AgentRun id injected by AgentRuntime.")
    event_id: str = Field(description="Current event id injected by AgentRuntime.")
    industry_id: str = Field(description="Current industry package id.")
    agent_id: str = Field(description="Current main agent definition id.")
    trace_id: str = Field(description="Trace id spanning runtime, tool, audit, and logs.")
    tool_profile_id: str = Field(description="Resolved tool profile id.")
    subagent_id: str | None = Field(default=None, description="SubAgent id when tool is executed inside a subagent.")
