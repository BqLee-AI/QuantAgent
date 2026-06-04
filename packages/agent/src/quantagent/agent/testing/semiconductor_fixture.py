from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from quantagent.agent.artifacts import ArtifactStore
from quantagent.agent.definitions.assets import load_agent_assets_from_directory
from quantagent.agent.definitions.models import AgentDefinition, RuntimePolicy
from quantagent.agent.runtime.context import RunContextSection, RunContextSnapshot
from quantagent.agent.runtime.requests import AgentRunRequest
from quantagent.agent.streaming.adapter import EventSequencer
from quantagent.agent.streaming.events import AgentRunEvent, AgentRunEventType
from quantagent.agent.tools.profiles import ToolProfile
from quantagent.agent.tools.schemas import (
    BuildActionPlanInput,
    EvaluateThesisInput,
    GetAccountContextInput,
    GetRunContextInput,
    SearchWebInput,
    SubmitActionPlanInput,
)


SEMICONDUCTOR_INDUSTRY_ID = "quantagent.official.industry.semiconductor"
MAIN_AGENT_ID = "quantagent.official.industry.semiconductor.agent.main"
RESEARCH_SUBAGENT_ID = "quantagent.official.industry.semiconductor.subagent.evidence_research_analyst"


@dataclass
class SemiconductorFixtureLedger:
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    subagent_tasks: list[dict[str, Any]] = field(default_factory=list)

    def record_tool(self, name: str, input_data: Mapping[str, Any]) -> None:
        self.tool_calls.append({"name": name, "input": dict(input_data)})

    def count_tool(self, name: str) -> int:
        return sum(1 for call in self.tool_calls if call["name"] == name)


@dataclass(frozen=True)
class SemiconductorAssets:
    agent_definition: AgentDefinition
    main_tool_profile: ToolProfile
    subagent_tool_profiles: dict[str, ToolProfile]


def load_semiconductor_assets(repo_root: Path | str) -> SemiconductorAssets:
    plugin_dir = Path(repo_root) / "plugins" / "industries" / "semiconductor-industry"
    agent_definition, main_profile, subagent_profiles = load_agent_assets_from_directory(plugin_dir / "agents")
    return SemiconductorAssets(
        agent_definition=agent_definition,
        main_tool_profile=main_profile,
        subagent_tool_profiles=subagent_profiles,
    )


def build_nvda_earnings_run_request(
    *,
    repo_root: Path | str,
    scenario: Literal["primary", "media_follow_up"],
) -> AgentRunRequest:
    assets = load_semiconductor_assets(repo_root)
    event_id = "evt_nvda_earnings_release_001" if scenario == "primary" else "evt_nvda_media_beat_001"
    event_summary = (
        "NVIDIA 一手财报公告，包含收入、data center、毛利率和下一季度收入指引。"
        if scenario == "primary"
        else "NVIDIA 财报超预期的二手媒体报道，疑似同一季度财报主题 follow-up。"
    )

    return AgentRunRequest(
        agent_run_id=f"run_nvda_{scenario}",
        event_id=event_id,
        industry_id=SEMICONDUCTOR_INDUSTRY_ID,
        trace_id=f"trace_nvda_{scenario}",
        agent_definition=assets.agent_definition,
        run_context=RunContextSnapshot(
            context_id=f"context_nvda_{scenario}",
            sections=[
                RunContextSection(
                    name="event",
                    summary=event_summary,
                    data={
                        "symbols": ["NVDA"],
                        "issuer": "NVIDIA",
                        "event_family": "quarterly_earnings",
                        "source_tier": "primary" if scenario == "primary" else "secondary",
                    },
                ),
                RunContextSection(
                    name="route_context",
                    summary="Router assigned this event to semiconductor with direct relationship.",
                    data={"owner_id": "semiconductor", "relationship": "direct"},
                ),
                RunContextSection(
                    name="market_mapping",
                    summary="NVDA maps directly to AI GPU and data center accelerator demand.",
                    data={"symbols": ["NVDA", "MU", "TSM", "ASML"]},
                ),
            ],
            safe_summary=f"NVDA {scenario} semiconductor run context.",
        ),
        tool_profile=assets.main_tool_profile,
        runtime_policy=RuntimePolicy(model=None, max_subagent_tasks=1),
        input_message=f"Analyze {event_id} with the semiconductor MainAgent MVP flow.",
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
            {
                "todos": _todos_for_scenario(scenario),
            },
            "MainAgent planned the semiconductor analysis flow.",
        )

        context_id = _call_get_run_context(active_ledger, scenario)
        yield _tool_completed(request, sequencer, "get_run_context", "Run context loaded.")

        if scenario == "primary":
            active_ledger.subagent_tasks.append(
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
                payload=_primary_evidence_board(),
                safe_summary="EvidenceBoard: 一手财报数字强，公开对照材料支持 surprise，同时存在估值和跳空风险。",
                confidence_score=0.9,
            )
            search_id = _call_search(active_ledger, "NVIDIA revenue guidance consensus data center gross margin")
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
                {
                    "subagent_id": RESEARCH_SUBAGENT_ID,
                    "artifact_ids": [report_ref.artifact_id, evidence_ref.artifact_id],
                },
                "EvidenceResearchAnalyst completed.",
            )
            account_context_id = _call_get_account_context(active_ledger, scenario)
            yield _tool_completed(request, sequencer, "get_account_context", "Account context loaded.")
            evaluation_ref = artifact_store.put(
                kind="thesis_evaluation",
                producer_id="evaluate_thesis",
                payload=_primary_thesis_evaluation(evidence_ref.artifact_id, account_context_id),
                safe_summary="ThesisEvaluation: propose_trade with high confidence and low risk.",
                created_from_ids=[evidence_ref.artifact_id],
                confidence_score=0.92,
            )
            _call_evaluate(active_ledger, evidence_ref.artifact_id, None, account_context_id, "propose_trade")
            yield _tool_completed(request, sequencer, "evaluate_thesis", "Thesis evaluated.")
            analysis_ref = artifact_store.put(
                kind="industry_analysis",
                producer_id=MAIN_AGENT_ID,
                payload=_primary_industry_analysis(evidence_ref.artifact_id, evaluation_ref.artifact_id),
                safe_summary="IndustryAnalysis: NVDA 一手财报支持小仓位 dry-run 做多计划。",
                created_from_ids=[evidence_ref.artifact_id, evaluation_ref.artifact_id],
                confidence_score=0.92,
            )
            action_plan_ref = artifact_store.put(
                kind="action_plan",
                producer_id="build_action_plan",
                payload=_primary_action_plan(analysis_ref.artifact_id, evaluation_ref.artifact_id, account_context_id),
                safe_summary="ActionPlan: open long NVDA dry-run with stop loss, take profit, and monitoring.",
                created_from_ids=[analysis_ref.artifact_id, evaluation_ref.artifact_id],
                confidence_score=0.92,
            )
            _call_build_action_plan(active_ledger, analysis_ref.artifact_id, evaluation_ref.artifact_id, account_context_id)
            yield _tool_completed(request, sequencer, "build_action_plan", "Action plan built.")
            submission_ref = artifact_store.put(
                kind="submission_result",
                producer_id="submit_action_plan",
                payload=_primary_submission_result(action_plan_ref.artifact_id, analysis_ref.artifact_id, evidence_ref.artifact_id),
                safe_summary="SubmitActionPlanResult: execute_then_notify dry-run requested by policy gate.",
                created_from_ids=[action_plan_ref.artifact_id, analysis_ref.artifact_id, evidence_ref.artifact_id],
                confidence_score=0.92,
            )
            _call_submit_action_plan(active_ledger, action_plan_ref.artifact_id, analysis_ref.artifact_id, evidence_ref.artifact_id)
            yield _tool_completed(request, sequencer, "submit_action_plan", "Action plan submitted to dry-run policy path.")
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
                    "trade_decision": "submit_dry_run_open_long",
                },
                "NVDA first-party earnings run produced dry-run action submission.",
            )
            return

        evidence_ref = artifact_store.put(
            kind="evidence_board",
            producer_id=MAIN_AGENT_ID,
            payload=_media_evidence_board(),
            safe_summary="EvidenceBoard: 二手报道确认已覆盖财报 surprise，没有新增实质信息。",
            confidence_score=0.84,
        )
        _call_search(active_ledger, "NVIDIA beats expectations AI demand earnings media report original release")
        yield _tool_completed(request, sequencer, "search_web", "Lightweight follow-up search completed.")
        account_context_id = _call_get_account_context(active_ledger, scenario)
        yield _tool_completed(request, sequencer, "get_account_context", "Recent activity loaded.")
        evaluation_ref = artifact_store.put(
            kind="thesis_evaluation",
            producer_id="evaluate_thesis",
            payload=_media_thesis_evaluation(evidence_ref.artifact_id, account_context_id),
            safe_summary="ThesisEvaluation: record_only because prior coverage is complete.",
            created_from_ids=[evidence_ref.artifact_id],
            confidence_score=0.84,
        )
        _call_evaluate(active_ledger, evidence_ref.artifact_id, None, account_context_id, "record_only")
        yield _tool_completed(request, sequencer, "evaluate_thesis", "Follow-up thesis evaluated.")
        analysis_ref = artifact_store.put(
            kind="industry_analysis",
            producer_id=MAIN_AGENT_ID,
            payload=_media_industry_analysis(evidence_ref.artifact_id, evaluation_ref.artifact_id),
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

    _runner.ledger = active_ledger  # type: ignore[attr-defined]
    return _runner


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


def _todos_for_scenario(scenario: str) -> list[dict[str, str]]:
    if scenario == "primary":
        return [
            {"content": "读取 run context", "status": "completed"},
            {"content": "委派 evidence_research_analyst 补充证据", "status": "completed"},
            {"content": "读取账户和近期活动", "status": "completed"},
            {"content": "评估 thesis 并构建 ActionPlan", "status": "completed"},
            {"content": "提交 dry-run 行动并输出 IndustryAnalysis", "status": "completed"},
        ]
    return [
        {"content": "读取 follow-up run context", "status": "completed"},
        {"content": "检查同主题近期 action 和通知", "status": "completed"},
        {"content": "轻量核验是否有新增事实", "status": "completed"},
        {"content": "record_only 输出 IndustryAnalysis", "status": "completed"},
    ]


def _call_get_run_context(ledger: SemiconductorFixtureLedger, scenario: str) -> str:
    input_data = GetRunContextInput(
        sections=["event", "route_context", "industry_profile", "market_mapping", "tool_profile"],
        symbols=["NVDA"],
        max_tokens=2500 if scenario == "primary" else 1800,
    )
    ledger.record_tool("get_run_context", input_data.model_dump())
    return f"context_nvda_{scenario}"


def _call_search(ledger: SemiconductorFixtureLedger, query: str) -> str:
    input_data = SearchWebInput(query=query, topic="finance", time_window="2h", max_results=5)
    ledger.record_tool("search_web", input_data.model_dump())
    return f"search_{len([call for call in ledger.tool_calls if call['name'] == 'search_web']) + 1}"


def _call_get_account_context(ledger: SemiconductorFixtureLedger, scenario: str) -> str:
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


def _call_evaluate(
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


def _call_build_action_plan(
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


def _call_submit_action_plan(
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


def _primary_evidence_board() -> dict[str, Any]:
    return {
        "source_items": [
            {"source_kind": "event", "summary": "公司一手公告披露收入、data center、毛利率和指引。"},
            {"source_kind": "search_result", "summary": "公开对照材料低于公告数字和指引。"},
        ],
        "claims": [
            {"role": "raw_fact", "statement": "一手公告披露强劲收入和 data center 结果。"},
            {"role": "reference_point", "statement": "公告和指引高于可获得公开对照材料。"},
            {"role": "conflict", "statement": "估值拥挤和跳空回撤仍是主要风险。"},
        ],
        "relation_summary": {"relation_type": "new_information", "related_event_ids": []},
        "gaps": ["电话会全文尚未发布。"],
    }


def _media_evidence_board() -> dict[str, Any]:
    return {
        "source_items": [
            {"source_kind": "event", "summary": "媒体报道 NVDA 财报超预期。"},
            {"source_kind": "prior_analysis", "summary": "同主题一手财报已触发 dry-run 做多和通知。"},
        ],
        "claims": [
            {"role": "interpretation", "statement": "媒体报道确认已处理的财报 surprise。"},
            {"role": "reference_point", "statement": "没有新增指引、管理层表述或冲突事实。"},
        ],
        "relation_summary": {
            "relation_type": "follow_up",
            "related_event_ids": ["evt_nvda_earnings_release_001"],
        },
        "gaps": [],
    }


def _primary_thesis_evaluation(evidence_id: str, account_context_id: str) -> dict[str, Any]:
    return {
        "evidence_board_artifact_id": evidence_id,
        "account_context_id": account_context_id,
        "confidence_score": 0.92,
        "risk_level": "low",
        "event_relationship": "new_information",
        "prior_coverage": {"status": "none", "related_action_ids": [], "related_notification_ids": []},
        "suggested_intent": "propose_trade",
    }


def _media_thesis_evaluation(evidence_id: str, account_context_id: str) -> dict[str, Any]:
    return {
        "evidence_board_artifact_id": evidence_id,
        "account_context_id": account_context_id,
        "confidence_score": 0.84,
        "risk_level": "low",
        "event_relationship": "follow_up",
        "prior_coverage": {
            "status": "fully_covered",
            "related_action_ids": ["action_nvda_earnings_open_long_001"],
            "related_notification_ids": ["notify_nvda_action_result_001"],
        },
        "suggested_intent": "record_only",
    }


def _primary_industry_analysis(evidence_id: str, evaluation_id: str) -> dict[str, Any]:
    return {
        "event_id": "evt_nvda_earnings_release_001",
        "impact_summary": "一手财报和公开对照证据支持短期小仓位做多 NVDA。",
        "evidence_artifact_ids": [evidence_id],
        "thesis_evaluation_artifact_id": evaluation_id,
        "recommended_actions": ["open_long"],
        "confidence_score": 0.92,
        "risk_flags": ["valuation_rich", "gap_up_reversal", "call_transcript_missing"],
    }


def _media_industry_analysis(evidence_id: str, evaluation_id: str) -> dict[str, Any]:
    return {
        "event_id": "evt_nvda_media_beat_001",
        "impact_summary": "二手媒体报道确认已处理主题，不新增交易动作。",
        "evidence_artifact_ids": [evidence_id],
        "thesis_evaluation_artifact_id": evaluation_id,
        "recommended_actions": [],
        "action_plan_artifact_id": None,
        "submission_id": None,
        "metadata": {
            "event_relationship": "follow_up",
            "related_action_ids": ["action_nvda_earnings_open_long_001"],
            "related_notification_ids": ["notify_nvda_action_result_001"],
            "notification_decision": "suppressed_duplicate",
            "trade_decision": "no_action_duplicate",
        },
    }


def _primary_action_plan(analysis_id: str, evaluation_id: str, account_context_id: str) -> dict[str, Any]:
    return {
        "intent": "trade",
        "action_side": "increase_risk",
        "industry_analysis_artifact_id": analysis_id,
        "thesis_evaluation_artifact_id": evaluation_id,
        "account_context_id": account_context_id,
        "target_symbols": ["NVDA"],
        "orders": [
            {
                "symbol": "NVDA",
                "side": "buy",
                "order_intent": "open",
                "notional": 9500,
                "portfolio_pct": 0.095,
                "order_type": "market",
            }
        ],
        "risk_controls": {
            "stop_loss": "-4.5% from execution reference price",
            "take_profit": "+9% from execution reference price",
            "max_loss_amount": 430,
            "invalidation_conditions": [
                "电话会削弱 data center 需求判断",
                "跌回财报发布前收盘价且 SOX 同步走弱",
            ],
        },
        "monitoring_plan": {
            "triggers": [
                {"metric": "NVDA price", "condition": "drawdown >= 4.5%", "action": "reanalyze_or_reduce"},
                {"metric": "earnings_call_transcript", "condition": "available", "action": "reanalyze"},
            ]
        },
        "user_notification": {
            "delivery_policy": "send",
            "summary": "一手财报和对照证据支持 dry-run 小仓位做多，最终状态由平台策略决定。",
        },
    }


def _primary_submission_result(action_plan_id: str, analysis_id: str, evidence_id: str) -> dict[str, Any]:
    return {
        "action_plan_artifact_id": action_plan_id,
        "industry_analysis_artifact_id": analysis_id,
        "evidence_artifact_ids": [evidence_id],
        "resolved_mode": "execute_then_notify",
        "policy_gate_status": "allowed",
        "execution_status": "dry_run_requested",
        "notification_status": "sent",
        "monitoring_task_ids": ["monitor_nvda_stop_001", "monitor_nvda_transcript_001"],
        "executed_changes": [{"symbol": "NVDA", "side": "buy", "notional": 9500, "status": "dry_run_requested"}],
    }
