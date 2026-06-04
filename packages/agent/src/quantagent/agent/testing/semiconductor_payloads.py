from __future__ import annotations

from typing import Any


def todos_for_scenario(scenario: str) -> list[dict[str, str]]:
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


def primary_evidence_board() -> dict[str, Any]:
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


def media_evidence_board() -> dict[str, Any]:
    return {
        "source_items": [
            {"source_kind": "event", "summary": "媒体报道 NVDA 财报超预期。"},
            {"source_kind": "prior_analysis", "summary": "同主题一手财报已触发 dry-run 做多和通知。"},
        ],
        "claims": [
            {"role": "interpretation", "statement": "媒体报道确认已处理的财报 surprise。"},
            {"role": "reference_point", "statement": "没有新增指引、管理层表述或冲突事实。"},
        ],
        "relation_summary": {"relation_type": "follow_up", "related_event_ids": ["evt_nvda_earnings_release_001"]},
        "gaps": [],
    }


def primary_thesis_evaluation(evidence_id: str, account_context_id: str) -> dict[str, Any]:
    return {
        "evidence_board_artifact_id": evidence_id,
        "account_context_id": account_context_id,
        "confidence_score": 0.92,
        "risk_level": "low",
        "event_relationship": "new_information",
        "prior_coverage": {"status": "none", "related_action_ids": [], "related_notification_ids": []},
        "suggested_intent": "propose_trade",
    }


def media_thesis_evaluation(evidence_id: str, account_context_id: str) -> dict[str, Any]:
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


def primary_industry_analysis(evidence_id: str, evaluation_id: str) -> dict[str, Any]:
    return {
        "event_id": "evt_nvda_earnings_release_001",
        "impact_summary": "一手财报和公开对照证据支持短期小仓位做多 NVDA。",
        "evidence_artifact_ids": [evidence_id],
        "thesis_evaluation_artifact_id": evaluation_id,
        "recommended_actions": ["open_long"],
        "confidence_score": 0.92,
        "risk_flags": ["valuation_rich", "gap_up_reversal", "call_transcript_missing"],
    }


def media_industry_analysis(evidence_id: str, evaluation_id: str) -> dict[str, Any]:
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


def primary_action_plan(analysis_id: str, evaluation_id: str, account_context_id: str) -> dict[str, Any]:
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


def primary_submission_result(action_plan_id: str, analysis_id: str, evidence_id: str) -> dict[str, Any]:
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
