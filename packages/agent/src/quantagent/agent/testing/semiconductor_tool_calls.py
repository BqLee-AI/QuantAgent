from __future__ import annotations

from typing import Literal

from quantagent.agent.testing.semiconductor_assets import SemiconductorFixtureLedger
from quantagent.agent.tools.schemas import (
    BuildActionPlanInput,
    EvaluateThesisInput,
    GetAccountContextInput,
    GetRunContextInput,
    SearchWebInput,
    SubmitActionPlanInput,
)


def call_get_run_context(ledger: SemiconductorFixtureLedger, scenario: str) -> str:
    input_data = GetRunContextInput(
        sections=["event", "route_context", "industry_profile", "market_mapping", "tool_profile"],
        symbols=["NVDA"],
        max_tokens=2500 if scenario == "primary" else 1800,
    )
    ledger.record_tool("get_run_context", input_data.model_dump())
    return f"context_nvda_{scenario}"


def call_search(ledger: SemiconductorFixtureLedger, query: str) -> str:
    input_data = SearchWebInput(query=query, topic="finance", time_window="2h", max_results=5)
    ledger.record_tool("search_web", input_data.model_dump())
    return f"search_{len([call for call in ledger.tool_calls if call['name'] == 'search_web']) + 1}"


def call_get_account_context(ledger: SemiconductorFixtureLedger, scenario: str) -> str:
    input_data = GetAccountContextInput(
        symbols=["NVDA"],
        include_positions=True,
        include_open_orders=True,
        include_risk_limits=scenario == "primary",
        include_user_policy=scenario == "primary",
        include_broker_mode=True,
        include_recent_activity=True,
        activity_lookback_window="24h" if scenario == "primary" else "2h",
        relation_hints=[
            {"key": "issuer", "value": "NVIDIA"},
            {"key": "event_family", "value": "quarterly_earnings"},
        ],
    )
    ledger.record_tool("get_account_context", input_data.model_dump())
    return f"account_context_nvda_{scenario}"


def call_evaluate(
    ledger: SemiconductorFixtureLedger,
    evidence_board_artifact_id: str,
    industry_analysis_artifact_id: str | None,
    account_context_id: str,
    intent_hint: Literal["propose_trade", "record_only"],
) -> None:
    input_data = EvaluateThesisInput(
        evidence_board_artifact_id=evidence_board_artifact_id,
        industry_analysis_artifact_id=industry_analysis_artifact_id,
        account_context_id=account_context_id,
        intent_hint=intent_hint,
    )
    ledger.record_tool("evaluate_thesis", input_data.model_dump())


def call_build_action_plan(
    ledger: SemiconductorFixtureLedger,
    industry_analysis_artifact_id: str,
    thesis_evaluation_artifact_id: str,
    account_context_id: str,
) -> None:
    input_data = BuildActionPlanInput(
        industry_analysis_artifact_id=industry_analysis_artifact_id,
        thesis_evaluation_artifact_id=thesis_evaluation_artifact_id,
        account_context_id=account_context_id,
        target_symbols=["NVDA"],
        intended_action="open_long",
        conviction="high",
        time_horizon="short_term",
        constraints=["dry_run only", "no leverage", "notional below auto approval threshold"],
    )
    ledger.record_tool("build_action_plan", input_data.model_dump())


def call_submit_action_plan(
    ledger: SemiconductorFixtureLedger,
    action_plan_artifact_id: str,
    industry_analysis_artifact_id: str,
    evidence_artifact_id: str,
) -> None:
    input_data = SubmitActionPlanInput(
        action_plan_artifact_id=action_plan_artifact_id,
        industry_analysis_artifact_id=industry_analysis_artifact_id,
        evidence_artifact_ids=[evidence_artifact_id],
        requested_mode_hint="auto_if_allowed",
        dry_run_allowed=True,
        idempotency_key="nvda-quarterly-earnings-default-paper-open-long",
    )
    ledger.record_tool("submit_action_plan", input_data.model_dump())
