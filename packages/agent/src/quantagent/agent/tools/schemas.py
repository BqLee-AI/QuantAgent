from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolInvocationSummary(StrictModel):
    invocation_id: str = Field(description="Runtime tool invocation id.")
    tool_id: str = Field(description="Stable platform tool id.")
    name: str = Field(description="DeepAgents-visible tool name.")
    status: str = Field(description="started, completed, or failed.")
    safe_summary: str = Field(description="Display-safe summary without secrets.")


class GetRunContextInput(StrictModel):
    sections: list[str] = Field(
        min_length=1,
        description="Context sections to read from the current run; event_id and run_id are injected by runtime.",
    )
    symbols: list[str] = Field(default_factory=list, description="Optional symbols used to compress mapping or activity context.")
    max_tokens: int | None = Field(default=None, ge=256, le=8000, description="Requested context budget; runtime may reduce it.")


class SearchWebInput(StrictModel):
    query: str = Field(min_length=3, max_length=500, description="Narrow public web search query.")
    topic: Literal["news", "general", "finance", "company", "regulation"] = Field(
        default="general",
        description="Search intent used for provider parameters, caching, and audit grouping.",
    )
    time_window: str | None = Field(default=None, description="Search time window, for example 1h, 24h, 7d, or custom.")
    max_results: int | None = Field(default=None, ge=1, le=10, description="Requested result count; runtime may lower it.")
    include_answer: bool = Field(default=False, description="Whether to request a provider answer; answers are leads, not facts.")
    include_raw_content: bool = Field(default=False, description="MVP keeps raw content off by default to avoid large prompt payloads.")


class RelationHintInput(StrictModel):
    key: str = Field(min_length=1, description="Relation dimension, for example issuer, event_family, or topic_key.")
    value: str = Field(min_length=1, description="Relation value used to find covered actions or notifications.")


class GetAccountContextInput(StrictModel):
    symbols: list[str] = Field(default_factory=list, description="Symbols to scope account and recent activity summaries.")
    include_positions: bool = Field(default=True, description="Whether to include current positions.")
    include_open_orders: bool = Field(default=True, description="Whether to include open orders.")
    include_risk_limits: bool = Field(default=True, description="Whether to include risk limits.")
    include_user_policy: bool = Field(default=True, description="Whether to include user automation policy summary.")
    include_broker_mode: bool = Field(default=True, description="Whether to include the current broker mode.")
    include_recent_activity: bool = Field(default=False, description="Whether to include recent actions, notifications, and monitors.")
    activity_lookback_window: str | None = Field(default=None, description="Recent activity lookback window, for example 2h or 24h.")
    relation_hints: list[RelationHintInput] = Field(default_factory=list, description="Hints for same-topic action lookup.")


class EvaluateThesisInput(StrictModel):
    evidence_board_artifact_id: str = Field(description="EvidenceBoard artifact id produced in this run.")
    industry_analysis_artifact_id: str | None = Field(
        default=None,
        description="Optional draft IndustryAnalysis artifact id when a draft exists before evaluation.",
    )
    account_context_id: str | None = Field(default=None, description="Optional account context id for novelty and prior coverage checks.")
    intent_hint: Literal["evaluate", "propose_trade", "record_only"] = Field(
        default="evaluate",
        description="MainAgent's requested evaluation mode; tool remains responsible for final suggested intent.",
    )


class BuildActionPlanInput(StrictModel):
    industry_analysis_artifact_id: str = Field(description="IndustryAnalysis draft artifact id.")
    thesis_evaluation_artifact_id: str = Field(description="ThesisEvaluation artifact id.")
    account_context_id: str = Field(description="Authorized account context id.")
    target_symbols: list[str] = Field(min_length=1, description="Symbols to include in the plan.")
    intended_action: str = Field(min_length=1, description="General action intent, for example open_long or reduce_risk.")
    conviction: Literal["low", "medium", "high"] = Field(description="Conviction bucket from the evaluated thesis.")
    time_horizon: str = Field(min_length=1, description="Expected action horizon.")
    constraints: list[str] = Field(default_factory=list, description="Small list of non-sensitive risk and execution constraints.")


class SubmitActionPlanInput(StrictModel):
    action_plan_artifact_id: str = Field(description="ActionPlan artifact id to submit.")
    industry_analysis_artifact_id: str = Field(description="IndustryAnalysis artifact id associated with the action.")
    evidence_artifact_ids: list[str] = Field(default_factory=list, description="Evidence artifact ids supporting the action.")
    requested_mode_hint: Literal["auto_if_allowed", "manual", "dry_run_only"] = Field(
        default="auto_if_allowed",
        description="Requested submission mode hint; policy gate still owns final mode.",
    )
    dry_run_allowed: bool = Field(default=True, description="Whether dry-run or mock execution is allowed.")
    idempotency_key: str = Field(min_length=1, description="Stable idempotency key for the action request.")
