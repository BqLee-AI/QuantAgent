from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from quantagent.agent.artifacts.models import ArtifactRef
from quantagent.agent.definitions.models import AgentDefinition, RuntimePolicy
from quantagent.agent.runtime.context import RunContextSnapshot
from quantagent.agent.streaming.events import AgentRunEvent
from quantagent.agent.tools.profiles import ToolProfile


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentRunRequest(StrictModel):
    agent_run_id: str = Field(min_length=1, description="Stable id for this AgentRun.")
    event_id: str = Field(min_length=1, description="Bound event id from Router/Intake.")
    industry_id: str = Field(min_length=1, description="Industry package id.")
    trace_id: str = Field(min_length=1, description="Trace id for logs and audit.")
    agent_definition: AgentDefinition = Field(description="Main agent definition.")
    run_context: RunContextSnapshot = Field(description="Bounded context snapshot.")
    tool_profile: ToolProfile = Field(description="Resolved allowed tools and risk metadata.")
    runtime_policy: RuntimePolicy = Field(default_factory=RuntimePolicy, description="Run limits and DeepAgents options.")
    input_message: str = Field(min_length=1, description="User/event instruction sent to DeepAgents.")


class AgentRunResult(StrictModel):
    agent_run_id: str = Field(description="AgentRun id.")
    status: str = Field(description="completed or failed.")
    output_summary: str = Field(default="", description="Safe final output summary.")
    artifact_refs: list[ArtifactRef] = Field(default_factory=list, description="Artifacts produced during this run.")
    events: list[AgentRunEvent] = Field(default_factory=list, description="Events emitted during non-streaming run.")
