from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Any

from quantagent.agent.artifacts import ArtifactStore
from quantagent.agent.runtime.requests import AgentRunRequest
from quantagent.agent.streaming.adapter import EventSequencer
from quantagent.agent.streaming.events import AgentRunEvent, AgentRunEventType
from quantagent.agent.testing.semiconductor_assets import (
    MAIN_AGENT_ID,
    RESEARCH_SUBAGENT_ID,
    SemiconductorFixtureLedger,
)
from quantagent.agent.testing.semiconductor_payloads import (
    media_evidence_board,
    media_industry_analysis,
    media_thesis_evaluation,
    primary_action_plan,
    primary_evidence_board,
    primary_industry_analysis,
    primary_submission_result,
    primary_thesis_evaluation,
    todos_for_scenario,
)
from quantagent.agent.testing.semiconductor_tool_calls import (
    call_build_action_plan,
    call_evaluate,
    call_get_account_context,
    call_get_run_context,
    call_search,
    call_submit_action_plan,
)


def build_semiconductor_scripted_runner(ledger: SemiconductorFixtureLedger | None = None):
    active_ledger = ledger or SemiconductorFixtureLedger()

    async def _runner(
        request: AgentRunRequest,
        sequencer: EventSequencer,
        artifact_store: ArtifactStore,
    ) -> AsyncIterator[AgentRunEvent]:
        scenario = "media_follow_up" if request.event_id.endswith("media_beat_001") else "primary"
        yield _event(
            request,
            sequencer,
            AgentRunEventType.TODO_UPDATED,
            {"todos": todos_for_scenario(scenario)},
            "MainAgent planned the semiconductor analysis flow.",
        )

        call_get_run_context(active_ledger, scenario)
        yield _tool_completed(request, sequencer, "get_run_context", "Run context loaded.")

        if scenario == "primary":
            async for event in _run_primary_fixture(request, sequencer, artifact_store, active_ledger):
                yield event
            return

        async for event in _run_media_follow_up_fixture(request, sequencer, artifact_store, active_ledger):
            yield event

    _runner.ledger = active_ledger  # type: ignore[attr-defined]
    return _runner


async def _run_primary_fixture(
    request: AgentRunRequest,
    sequencer: EventSequencer,
    artifact_store: ArtifactStore,
    ledger: SemiconductorFixtureLedger,
) -> AsyncIterator[AgentRunEvent]:
    ledger.subagent_tasks.append(
        {
            "agent": "evidence_research_analyst",
            "instruction_contains": ["current event", "search budget", "output format", "do not read account"],
        }
    )
    yield _event(
        request,
        sequencer,
        AgentRunEventType.SUBAGENT_STARTED,
        {"subagent_id": RESEARCH_SUBAGENT_ID, "name": "evidence_research_analyst"},
        "EvidenceResearchAnalyst started.",
    )
    evidence_ref = artifact_store.put(
        kind="evidence_board",
        producer_id=RESEARCH_SUBAGENT_ID,
        payload=primary_evidence_board(),
        safe_summary="EvidenceBoard: 一手财报数字强，公开对照材料支持 surprise，同时存在估值和跳空风险。",
        confidence_score=0.9,
    )
    search_id = call_search(ledger, "NVIDIA revenue guidance consensus data center gross margin")
    yield _tool_completed(request, sequencer, "search_web", "Public evidence search completed.")
    report_ref = artifact_store.put(
        kind="subagent_report",
        producer_id=RESEARCH_SUBAGENT_ID,
        payload={
            "report_id": "report_nvda_primary_research",
            "search_ids": [search_id],
            "evidence_board_artifact_id": evidence_ref.artifact_id,
            "summary": evidence_ref.safe_summary,
            "gaps": ["电话会全文尚未发布。"],
        },
        safe_summary="Research report produced evidence board and gaps.",
        created_from_ids=[evidence_ref.artifact_id],
        confidence_score=0.9,
    )
    yield _event(
        request,
        sequencer,
        AgentRunEventType.ARTIFACT_CREATED,
        {"artifact_id": evidence_ref.artifact_id, "kind": evidence_ref.kind},
        evidence_ref.safe_summary,
    )
    yield _event(
        request,
        sequencer,
        AgentRunEventType.SUBAGENT_COMPLETED,
        {"subagent_id": RESEARCH_SUBAGENT_ID, "artifact_ids": [report_ref.artifact_id, evidence_ref.artifact_id]},
        "EvidenceResearchAnalyst completed.",
    )

    account_context_id = call_get_account_context(ledger, "primary")
    yield _tool_completed(request, sequencer, "get_account_context", "Account context loaded.")
    evaluation_ref = artifact_store.put(
        kind="thesis_evaluation",
        producer_id="evaluate_thesis",
        payload=primary_thesis_evaluation(evidence_ref.artifact_id, account_context_id),
        safe_summary="ThesisEvaluation: propose_trade with high confidence and low risk.",
        created_from_ids=[evidence_ref.artifact_id],
        confidence_score=0.92,
    )
    call_evaluate(ledger, evidence_ref.artifact_id, None, account_context_id, "propose_trade")
    yield _tool_completed(request, sequencer, "evaluate_thesis", "Thesis evaluated.")
    analysis_ref = artifact_store.put(
        kind="industry_analysis",
        producer_id=MAIN_AGENT_ID,
        payload=primary_industry_analysis(evidence_ref.artifact_id, evaluation_ref.artifact_id),
        safe_summary="IndustryAnalysis: NVDA 一手财报支持小仓位 dry-run 做多计划。",
        created_from_ids=[evidence_ref.artifact_id, evaluation_ref.artifact_id],
        confidence_score=0.92,
    )
    action_plan_ref = artifact_store.put(
        kind="action_plan",
        producer_id="build_action_plan",
        payload=primary_action_plan(analysis_ref.artifact_id, evaluation_ref.artifact_id, account_context_id),
        safe_summary="ActionPlan: open long NVDA dry-run with stop loss, take profit, and monitoring.",
        created_from_ids=[analysis_ref.artifact_id, evaluation_ref.artifact_id],
        confidence_score=0.92,
    )
    call_build_action_plan(ledger, analysis_ref.artifact_id, evaluation_ref.artifact_id, account_context_id)
    yield _tool_completed(request, sequencer, "build_action_plan", "Action plan built.")
    submission_ref = artifact_store.put(
        kind="submission_result",
        producer_id="submit_action_plan",
        payload=primary_submission_result(action_plan_ref.artifact_id, analysis_ref.artifact_id, evidence_ref.artifact_id),
        safe_summary="SubmitActionPlanResult: execute_then_notify dry-run requested by policy gate.",
        created_from_ids=[action_plan_ref.artifact_id, analysis_ref.artifact_id, evidence_ref.artifact_id],
        confidence_score=0.92,
    )
    call_submit_action_plan(ledger, action_plan_ref.artifact_id, analysis_ref.artifact_id, evidence_ref.artifact_id)
    yield _tool_completed(request, sequencer, "submit_action_plan", "Action plan submitted to dry-run policy path.")
    submission_payload = dict(artifact_store.get(submission_ref.artifact_id).payload)
    for ref in (analysis_ref, action_plan_ref, submission_ref):
        yield _event(
            request,
            sequencer,
            AgentRunEventType.ARTIFACT_CREATED,
            {"artifact_id": ref.artifact_id, "kind": ref.kind},
            ref.safe_summary,
        )
    yield _event(
        request,
        sequencer,
        AgentRunEventType.RUN_OUTPUT,
        {
            "industry_analysis_artifact_id": analysis_ref.artifact_id,
            "action_plan_artifact_id": action_plan_ref.artifact_id,
            "submission_id": submission_ref.artifact_id,
            "trade_decision": _trade_decision_from_submission(submission_payload),
            "resolved_mode": submission_payload["resolved_mode"],
            "execution_status": submission_payload["execution_status"],
            "notification_status": submission_payload["notification_status"],
        },
        "NVDA first-party earnings run produced dry-run action submission.",
    )


async def _run_media_follow_up_fixture(
    request: AgentRunRequest,
    sequencer: EventSequencer,
    artifact_store: ArtifactStore,
    ledger: SemiconductorFixtureLedger,
) -> AsyncIterator[AgentRunEvent]:
    evidence_ref = artifact_store.put(
        kind="evidence_board",
        producer_id=MAIN_AGENT_ID,
        payload=media_evidence_board(),
        safe_summary="EvidenceBoard: 二手报道确认已覆盖财报 surprise，没有新增实质信息。",
        confidence_score=0.84,
    )
    call_search(ledger, "NVIDIA beats expectations AI demand earnings media report original release")
    yield _tool_completed(request, sequencer, "search_web", "Lightweight follow-up search completed.")
    account_context_id = call_get_account_context(ledger, "media_follow_up")
    yield _tool_completed(request, sequencer, "get_account_context", "Recent activity loaded.")
    evaluation_ref = artifact_store.put(
        kind="thesis_evaluation",
        producer_id="evaluate_thesis",
        payload=media_thesis_evaluation(evidence_ref.artifact_id, account_context_id),
        safe_summary="ThesisEvaluation: record_only because prior coverage is complete.",
        created_from_ids=[evidence_ref.artifact_id],
        confidence_score=0.84,
    )
    call_evaluate(ledger, evidence_ref.artifact_id, None, account_context_id, "record_only")
    yield _tool_completed(request, sequencer, "evaluate_thesis", "Follow-up thesis evaluated.")
    analysis_ref = artifact_store.put(
        kind="industry_analysis",
        producer_id=MAIN_AGENT_ID,
        payload=media_industry_analysis(evidence_ref.artifact_id, evaluation_ref.artifact_id),
        safe_summary="IndustryAnalysis: follow-up media report is record_only and duplicate notification suppressed.",
        created_from_ids=[evidence_ref.artifact_id, evaluation_ref.artifact_id],
        confidence_score=0.84,
    )
    for ref in (evidence_ref, evaluation_ref, analysis_ref):
        yield _event(
            request,
            sequencer,
            AgentRunEventType.ARTIFACT_CREATED,
            {"artifact_id": ref.artifact_id, "kind": ref.kind},
            ref.safe_summary,
        )
    yield _event(
        request,
        sequencer,
        AgentRunEventType.RUN_OUTPUT,
        {
            "industry_analysis_artifact_id": analysis_ref.artifact_id,
            "action_plan_artifact_id": None,
            "submission_id": None,
            "trade_decision": "no_action_duplicate",
            "notification_decision": "suppressed_duplicate",
        },
        "NVDA media follow-up run produced record_only IndustryAnalysis.",
    )


def _event(
    request: AgentRunRequest,
    sequencer: EventSequencer,
    event_type: AgentRunEventType,
    payload: Mapping[str, Any],
    safe_summary: str,
) -> AgentRunEvent:
    return sequencer.next(
        agent_run_id=request.agent_run_id,
        trace_id=request.trace_id,
        event_type=event_type,
        payload=dict(payload),
        safe_summary=safe_summary,
    )


def _tool_completed(request: AgentRunRequest, sequencer: EventSequencer, tool_name: str, summary: str) -> AgentRunEvent:
    return _event(
        request,
        sequencer,
        AgentRunEventType.TOOL_COMPLETED,
        {"tool_name": tool_name},
        summary,
    )


def _trade_decision_from_submission(submission_payload: Mapping[str, Any]) -> str:
    if submission_payload.get("resolved_mode") == "execute_then_notify" and submission_payload.get("execution_status") == "dry_run_requested":
        return "submit_dry_run_open_long"
    return "submission_not_executed"
