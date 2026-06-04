from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ArtifactKind = Literal[
    "run_context",
    "search_result",
    "evidence_board",
    "subagent_report",
    "thesis_evaluation",
    "action_plan",
    "industry_analysis",
    "submission_result",
    "tool_result",
    "runtime_output",
]


class ArtifactRef(StrictModel):
    artifact_id: str = Field(description="Current AgentRun-scoped artifact id.")
    kind: ArtifactKind = Field(description="Artifact type for permission and downstream handling.")
    producer_id: str = Field(description="Tool, main agent, subagent, or runtime component that produced this artifact.")
    safe_summary: str = Field(description="Prompt/log-safe summary without secrets or full reasoning.")
    confidence_score: float | None = Field(default=None, ge=0, le=1, description="Optional producer confidence.")
    created_from_ids: list[str] = Field(default_factory=list, description="Upstream artifact/context/search ids.")
