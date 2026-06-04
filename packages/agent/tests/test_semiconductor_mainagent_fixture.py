from __future__ import annotations

import asyncio
from pathlib import Path
from unittest import TestCase

from pydantic import ValidationError

from quantagent.agent.artifacts import InMemoryArtifactStore
from quantagent.agent.runtime import AgentRuntime
from quantagent.agent.streaming.events import AgentRunEventType
from quantagent.agent.testing import (
    SemiconductorFixtureLedger,
    build_nvda_earnings_run_request,
    build_semiconductor_scripted_runner,
    load_semiconductor_assets,
)
from quantagent.agent.tools.schemas import (
    BuildActionPlanInput,
    EvaluateThesisInput,
    GetAccountContextInput,
    SearchWebInput,
    SubmitActionPlanInput,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class SemiconductorMainAgentFixtureTest(TestCase):
    def test_semiconductor_assets_define_minimal_tool_profiles(self) -> None:
        assets = load_semiconductor_assets(REPO_ROOT)

        self.assertEqual(assets.agent_definition.agent_id, "quantagent.official.industry.semiconductor.agent.main")
        self.assertEqual(
            assets.agent_definition.tool_ids,
            [
                "quantagent.core.tool.get_run_context",
                "quantagent.official.source.tavily.search_web",
                "quantagent.core.tool.get_account_context",
                "quantagent.core.tool.evaluate_thesis",
                "quantagent.core.tool.build_action_plan",
                "quantagent.core.tool.submit_action_plan",
            ],
        )
        self.assertEqual(len(assets.agent_definition.subagents), 1)
        research = assets.agent_definition.subagents[0]
        self.assertEqual(research.name, "evidence_research_analyst")
        self.assertEqual(
            research.tool_ids,
            [
                "quantagent.core.tool.get_run_context",
                "quantagent.official.source.tavily.search_web",
            ],
        )
        forbidden = {"notify_user", "request_approval", "request_broker_action", "request_monitoring"}
        visible_names = {binding.name for binding in assets.main_tool_profile.tool_bindings}
        self.assertTrue(forbidden.isdisjoint(visible_names))
        self.assertNotIn("get_account_context", {binding.name for binding in assets.subagent_tool_profiles[research.subagent_id].tool_bindings})

    def test_tool_schemas_reject_scene_specific_fields(self) -> None:
        with self.assertRaises(ValidationError):
            SearchWebInput.model_validate({"query": "NVIDIA results", "expected_revenue": "46B"})
        with self.assertRaises(ValidationError):
            EvaluateThesisInput.model_validate(
                {
                    "evidence_board_artifact_id": "artifact_evidence",
                    "earnings_surprise": "beat",
                }
            )
        with self.assertRaises(ValidationError):
            BuildActionPlanInput.model_validate(
                {
                    "industry_analysis_artifact_id": "artifact_analysis",
                    "thesis_evaluation_artifact_id": "artifact_eval",
                    "account_context_id": "context_account",
                    "target_symbols": ["NVDA"],
                    "intended_action": "open_long",
                    "conviction": "high",
                    "time_horizon": "short_term",
                    "nvda_specific_signal": "ai_demand",
                }
            )
        with self.assertRaises(ValidationError):
            SubmitActionPlanInput.model_validate(
                {
                    "action_plan_artifact_id": "artifact_plan",
                    "industry_analysis_artifact_id": "artifact_analysis",
                    "idempotency_key": "key",
                    "expected_revenue": "46B",
                }
            )

    def test_primary_earnings_fixture_streams_action_submission(self) -> None:
        async def _run() -> None:
            ledger = SemiconductorFixtureLedger()
            artifact_store = InMemoryArtifactStore()
            runtime = AgentRuntime(
                artifact_store=artifact_store,
                scripted_runner=build_semiconductor_scripted_runner(ledger),
            )

            result = await runtime.run(build_nvda_earnings_run_request(repo_root=REPO_ROOT, scenario="primary"))

            self.assertEqual(result.status, "completed")
            event_types = [event.type for event in result.events]
            self.assertIn(AgentRunEventType.TODO_UPDATED, event_types)
            self.assertIn(AgentRunEventType.SUBAGENT_STARTED, event_types)
            self.assertIn(AgentRunEventType.SUBAGENT_COMPLETED, event_types)
            self.assertIn(AgentRunEventType.TOOL_COMPLETED, event_types)
            self.assertIn(AgentRunEventType.ARTIFACT_CREATED, event_types)
            self.assertIn(AgentRunEventType.RUN_OUTPUT, event_types)
            self.assertEqual(ledger.count_tool("submit_action_plan"), 1)
            self.assertEqual(ledger.count_tool("build_action_plan"), 1)
            self.assertEqual(len(ledger.subagent_tasks), 1)

            submission = _first_payload(artifact_store, "submission_result")
            self.assertEqual(submission["resolved_mode"], "execute_then_notify")
            self.assertEqual(submission["policy_gate_status"], "allowed")
            self.assertEqual(submission["execution_status"], "dry_run_requested")
            output_event = next(event for event in result.events if event.type == AgentRunEventType.RUN_OUTPUT)
            self.assertEqual(output_event.payload["resolved_mode"], submission["resolved_mode"])
            self.assertEqual(output_event.payload["execution_status"], submission["execution_status"])
            self.assertEqual(output_event.payload["notification_status"], submission["notification_status"])
            self.assertEqual(output_event.payload["trade_decision"], "submit_dry_run_open_long")
            action_plan = _first_payload(artifact_store, "action_plan")
            self.assertEqual(action_plan["intent"], "trade")
            self.assertIn("risk_controls", action_plan)
            self.assertIn("monitoring_plan", action_plan)
            self.assertEqual(action_plan["user_notification"]["delivery_policy"], "send")
            self.assertNotIn("approved", action_plan)
            self.assertNotIn("executed", action_plan)
            self.assertNotIn("notified", action_plan)

        asyncio.run(_run())

    def test_media_follow_up_fixture_is_record_only_without_submit(self) -> None:
        async def _run() -> None:
            ledger = SemiconductorFixtureLedger()
            artifact_store = InMemoryArtifactStore()
            runtime = AgentRuntime(
                artifact_store=artifact_store,
                scripted_runner=build_semiconductor_scripted_runner(ledger),
            )

            result = await runtime.run(build_nvda_earnings_run_request(repo_root=REPO_ROOT, scenario="media_follow_up"))

            self.assertEqual(result.status, "completed")
            self.assertEqual(ledger.count_tool("submit_action_plan"), 0)
            self.assertEqual(ledger.count_tool("build_action_plan"), 0)
            self.assertEqual(ledger.count_tool("get_account_context"), 1)
            self.assertEqual(len(ledger.subagent_tasks), 0)

            evaluation = _first_payload(artifact_store, "thesis_evaluation")
            self.assertEqual(evaluation["suggested_intent"], "record_only")
            self.assertEqual(evaluation["prior_coverage"]["status"], "fully_covered")
            analysis = _first_payload(artifact_store, "industry_analysis")
            self.assertEqual(analysis["recommended_actions"], [])
            self.assertIsNone(analysis["action_plan_artifact_id"])
            self.assertIsNone(analysis["submission_id"])
            self.assertEqual(analysis["metadata"]["notification_decision"], "suppressed_duplicate")
            self.assertEqual(analysis["metadata"]["trade_decision"], "no_action_duplicate")

        asyncio.run(_run())

    def test_ledger_uses_id_first_tool_inputs(self) -> None:
        async def _run() -> None:
            ledger = SemiconductorFixtureLedger()
            runtime = AgentRuntime(scripted_runner=build_semiconductor_scripted_runner(ledger))

            await runtime.run(build_nvda_earnings_run_request(repo_root=REPO_ROOT, scenario="primary"))

            build_call = next(call for call in ledger.tool_calls if call["name"] == "build_action_plan")
            self.assertIn("industry_analysis_artifact_id", build_call["input"])
            self.assertIn("thesis_evaluation_artifact_id", build_call["input"])
            self.assertIn("account_context_id", build_call["input"])
            self.assertNotIn("full_account_json", build_call["input"])
            submit_call = next(call for call in ledger.tool_calls if call["name"] == "submit_action_plan")
            self.assertIn("action_plan_artifact_id", submit_call["input"])
            self.assertIn("evidence_artifact_ids", submit_call["input"])

        asyncio.run(_run())


def _first_payload(artifact_store: InMemoryArtifactStore, kind: str) -> dict:
    ref = next(ref for ref in artifact_store.list_for_run() if ref.kind == kind)
    return dict(artifact_store.get(ref.artifact_id).payload)
