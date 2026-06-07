from __future__ import annotations

import unittest

from quantagent.core.event_intake import (
    EVENT_INTAKE_DECISION_SCHEMA_VERSION,
    ContentCompleteness,
    DiscardReason,
    EnrichmentStatus,
    EventIntakeBudget,
    EventIntakeRoutedPublisher,
    EventIntakeValidationError,
    FakeStructuredModelInvoker,
    IndustryEventContextBuilder,
    IntakeDecision,
    SingleCallEventIntakeRunner,
)
from quantagent.core.events import EventEnvelope, InMemoryEventBus
from quantagent.plugin_sdk.io import dto_validation_error


class _RecordingHandler:
    def __init__(self) -> None:
        self.seen: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope)


class EventIntakeTestCase(unittest.IsolatedAsyncioTestCase):
    def test_context_builder_preserves_trace_and_degraded_marker(self) -> None:
        context = self._build_single_context(
            item={
                "url": "https://example.com/rss-only",
                "title": "HBM demand update",
                "summary_or_content": "RSS summary only",
                "enrichment_status": "failed_degraded",
                "source_metadata": {"source": "rss", "published_at": "2026-06-02T00:00:00Z"},
                "enrichment_error_code": "READABILITY_TIMEOUT",
            }
        )

        self.assertEqual(context.trace.message_id, "evt-analysis-1")
        self.assertEqual(context.trace.source_message_id, "evt-source-1")
        self.assertEqual(context.trace.binding_id, "binding-semi")
        self.assertEqual(context.trace.owner_id, "semiconductor")
        self.assertEqual(context.source.enrichment_status, EnrichmentStatus.FAILED_DEGRADED)
        self.assertEqual(context.source.degraded_reason, "READABILITY_TIMEOUT")
        self.assertEqual(context.article.content_completeness, ContentCompleteness.RSS_SUMMARY_ONLY)
        self.assertFalse(context.article.body_content_available)
        self.assertEqual(context.industry_candidates[0].industry_id, "semiconductor")

    def test_context_is_json_safe_and_rejects_runtime_objects(self) -> None:
        context = self._build_single_context()
        mapping = context.to_mapping()

        self.assertEqual(mapping["schema_version"], "industry_event_context.v1")
        with self.assertRaises(TypeError):
            mapping["unsafe"] = "value"  # type: ignore[index]
        with self.assertRaises(type(dto_validation_error("x"))):
            EventEnvelope(
                id="evt-unsafe",
                topic="industry.analysis.requested",
                producer="test",
                created_at="2026-06-02T00:00:00Z",
                payload={"items": [{"source_metadata": {"provider_client": object()}}]},
            )

    def test_budget_uses_full_body_when_under_limit(self) -> None:
        context = self._build_single_context(
            budget=EventIntakeBudget(max_input_chars=200, max_body_chars=100),
            item={"summary_or_content": "a" * 80, "enrichment_status": "succeeded"},
        )

        self.assertEqual(context.article.content_completeness, ContentCompleteness.FULL)
        self.assertEqual(len(context.article.body_excerpt or ""), 80)

    def test_budget_uses_deterministic_excerpt_when_over_limit(self) -> None:
        context = self._build_single_context(
            budget=EventIntakeBudget(max_input_chars=200, max_body_chars=50),
            item={"summary_or_content": "a" * 120, "enrichment_status": "succeeded"},
        )

        self.assertEqual(context.article.content_completeness, ContentCompleteness.EXCERPTED)
        self.assertEqual(len(context.article.body_excerpt or ""), 50)
        self.assertEqual(context.article.excerpt_start, 0)
        self.assertEqual(context.article.excerpt_end, 50)
        self.assertEqual(context.article.content_length_chars, 120)

    async def test_direct_semiconductor_fixture_routes_once(self) -> None:
        invoker = FakeStructuredModelInvoker(
            [
                self._route_output(
                    relationship="direct",
                )
            ]
        )
        runner = SingleCallEventIntakeRunner(invoker=invoker)
        result = await runner.run(self._build_single_context())

        self.assertEqual(invoker.invocation_count, 1)
        self.assertEqual(result.provider_invocation_count, 1)
        self.assertEqual(result.decision.decision, IntakeDecision.ROUTE)
        self.assertEqual(result.decision.industry_relevance[0].relationship.value, "direct")
        self.assertEqual(result.decision.routing.target_industries, ("semiconductor",))
        self.assertEqual(result.decision.schema_version, EVENT_INTAKE_DECISION_SCHEMA_VERSION)
        self.assertEqual(result.decision.structured_news.canonical_title, "HBM 需求变化影响存储供应链")
        self.assertEqual(result.decision.structured_news.event_type_label, "供需变化")
        self.assertEqual(result.decision.structured_news.tags[0]["label"], "存储")
        self.assertEqual(result.decision.routing.next_step_hint, "交给半导体行业 MainAgent 做进一步分析。")
        self.assertEqual(result.decision.audit.output_language, "zh-CN")

    async def test_indirect_ai_infra_fixture_is_not_discarded(self) -> None:
        invoker = FakeStructuredModelInvoker(
            [
                self._route_output(
                    relationship="indirect",
                    title="Hyperscaler AI capex rises",
                    summary="AI server capex increases demand for memory bandwidth and GPU supply chain.",
                )
            ]
        )
        runner = SingleCallEventIntakeRunner(invoker=invoker)
        result = await runner.run(
            self._build_single_context(
                item={
                    "title": "Hyperscaler AI capex rises",
                    "summary_or_content": "Data center buildout raises memory bandwidth demand.",
                    "enrichment_status": "succeeded",
                    "source_metadata": {"language": "en"},
                }
            )
        )

        self.assertEqual(result.decision.decision, IntakeDecision.ROUTE)
        self.assertEqual(result.decision.industry_relevance[0].relationship.value, "indirect")
        self.assertEqual(invoker.invocation_count, 1)

    async def test_unrelated_spam_fixture_discards_without_deep_analysis(self) -> None:
        invoker = FakeStructuredModelInvoker([self._discard_output(reason="spam")])
        runner = SingleCallEventIntakeRunner(invoker=invoker)
        result = await runner.run(
            self._build_single_context(
                item={
                    "title": "Top phone cases discount",
                    "summary_or_content": "SEO gadget review with affiliate links.",
                    "enrichment_status": "succeeded",
                }
            )
        )

        self.assertEqual(result.decision.decision, IntakeDecision.DISCARD)
        self.assertEqual(result.decision.discard_reason, DiscardReason.SPAM)
        self.assertFalse(result.decision.routing.requires_deep_analysis)
        self.assertEqual(invoker.invocation_count, 1)

    async def test_unsupported_language_discards_without_provider_invocation(self) -> None:
        invoker = FakeStructuredModelInvoker([self._route_output()])
        runner = SingleCallEventIntakeRunner(invoker=invoker)
        result = await runner.run(
            self._build_single_context(
                item={
                    "title": "HBM",
                    "summary_or_content": "Body",
                    "enrichment_status": "succeeded",
                    "source_metadata": {"language": "xx-unsupported"},
                }
            )
        )

        self.assertEqual(result.decision.decision, IntakeDecision.DISCARD)
        self.assertEqual(result.decision.discard_reason, DiscardReason.UNSUPPORTED_LANGUAGE)
        self.assertIn("语言", result.decision.audit.reason_summary)
        self.assertEqual(result.provider_invocation_count, 0)
        self.assertEqual(invoker.invocation_count, 0)

    async def test_malformed_item_discards_with_chinese_summary_without_provider_invocation(self) -> None:
        invoker = FakeStructuredModelInvoker([self._route_output()])
        runner = SingleCallEventIntakeRunner(invoker=invoker)
        result = await runner.run(
            self._build_single_context(
                item={
                    "title": "",
                    "summary_or_content": "",
                    "url": "",
                    "enrichment_status": "succeeded",
                }
            )
        )

        self.assertEqual(result.decision.decision, IntakeDecision.DISCARD)
        self.assertEqual(result.decision.discard_reason, DiscardReason.MALFORMED)
        self.assertIn("缺少可用标题", result.decision.audit.reason_summary)
        self.assertEqual(result.provider_invocation_count, 0)
        self.assertEqual(invoker.invocation_count, 0)

    async def test_invalid_model_output_becomes_review_not_route(self) -> None:
        invoker = FakeStructuredModelInvoker(
            [
                {
                    "schema_version": EVENT_INTAKE_DECISION_SCHEMA_VERSION,
                    "decision": "route",
                    "discard_reason": "not_discarded",
                    "quality": {
                        "is_spam": False,
                        "noise_flags": (),
                        "content_completeness": "full",
                        "enrichment_status": "succeeded",
                        "confidence": 0.9,
                    },
                    "industry_relevance": (),
                    "structured_news": {"canonical_title": "Invalid", "short_summary": "Invalid"},
                    "routing": {
                        "target_industries": (),
                        "target_topics": (),
                        "priority": "normal",
                        "requires_deep_analysis": True,
                        "requires_human_review": False,
                    },
                    "audit": {
                        "reason_summary": "Invalid route",
                        "evidence_field_refs": ("article.title",),
                        "schema_validation_status": "valid",
                    },
                }
            ]
        )
        runner = SingleCallEventIntakeRunner(invoker=invoker)
        result = await runner.run(self._build_single_context())

        self.assertEqual(result.decision.decision, IntakeDecision.REVIEW)
        self.assertEqual(result.decision.audit.failure_code, "EVENT_INTAKE_VALIDATION_FAILED")
        self.assertIn("未通过 Router Agent schema 校验", result.decision.audit.reason_summary)
        self.assertFalse(result.decision.routing.requires_deep_analysis)
        self.assertEqual(invoker.invocation_count, 1)

    async def test_provider_failure_becomes_review_with_chinese_summary(self) -> None:
        class FailingInvoker:
            async def invoke(self, *, context, output_schema):  # type: ignore[no-untyped-def]
                raise RuntimeError("boom")

        result = await SingleCallEventIntakeRunner(invoker=FailingInvoker()).run(self._build_single_context())

        self.assertEqual(result.decision.decision, IntakeDecision.REVIEW)
        self.assertEqual(result.decision.audit.failure_code, "PROVIDER_UNAVAILABLE")
        self.assertIn("结构化模型服务暂时不可用", result.decision.audit.reason_summary)
        self.assertEqual(result.provider_invocation_count, 1)

    async def test_review_only_invoker_outputs_chinese_user_visible_fields(self) -> None:
        result = await SingleCallEventIntakeRunner(invoker=__import__(
            "quantagent.core.event_intake.runner",
            fromlist=["ReviewOnlyStructuredModelInvoker"],
        ).ReviewOnlyStructuredModelInvoker()).run(self._build_single_context())

        self.assertEqual(result.decision.decision, IntakeDecision.REVIEW)
        self.assertIn("未配置 Router Agent 模型服务", result.decision.structured_news.short_summary)
        self.assertIn("worker 未配置结构化模型 provider", result.decision.audit.reason_summary)

    async def test_publisher_emits_event_routed_without_full_content(self) -> None:
        bus = InMemoryEventBus()
        recorder = _RecordingHandler()
        await bus.subscribe(topics=("event.routed",), group_id="test", handler=recorder)
        context = self._build_single_context(item={"summary_or_content": "full body " * 50, "enrichment_status": "succeeded"})
        result = await SingleCallEventIntakeRunner(
            invoker=FakeStructuredModelInvoker([self._route_output()])
        ).run(context)

        published = await EventIntakeRoutedPublisher(bus, id_factory=lambda: "evt-routed-1").publish(result)

        self.assertEqual(published.topic, "event.routed")
        self.assertEqual(published.payload["schema_version"], EVENT_INTAKE_DECISION_SCHEMA_VERSION)
        self.assertEqual(published.payload["decision"], "route")
        self.assertIn("article", published.payload)
        self.assertNotIn("body_excerpt", published.payload["article"])
        self.assertEqual(published.headers["schema_version"], EVENT_INTAKE_DECISION_SCHEMA_VERSION)
        self.assertEqual(len(recorder.seen), 1)

    def test_decision_consistency_rules(self) -> None:
        with self.assertRaises(EventIntakeValidationError):
            self._decision_from(self._discard_output(reason="not_discarded"))
        with self.assertRaises(EventIntakeValidationError):
            self._decision_from(self._route_output(targets=()))
        with self.assertRaises(EventIntakeValidationError):
            self._decision_from(self._review_output(requires_human_review=False, confidence=0.9))

    def _build_single_context(
        self,
        *,
        item: dict[str, object] | None = None,
        budget: EventIntakeBudget | None = None,
    ):
        builder = IndustryEventContextBuilder(budget=budget or EventIntakeBudget(max_input_chars=256_000, max_body_chars=220_000))
        contexts = builder.build_contexts(
            self._analysis_request_envelope(
                item={
                    "url": "https://example.com/hbm",
                    "title": "HBM demand update",
                    "summary_or_content": "HBM demand and advanced packaging capacity tighten.",
                    "enrichment_status": "succeeded",
                    "source_metadata": {"source": "rss", "language": "en"},
                    **(item or {}),
                }
            )
        )
        self.assertEqual(len(contexts), 1)
        return contexts[0]

    def _analysis_request_envelope(self, *, item: dict[str, object]) -> EventEnvelope:
        return EventEnvelope(
            id="evt-analysis-1",
            topic="industry.analysis.requested",
            payload={
                "owner_type": "industry",
                "owner_id": "semiconductor",
                "binding_id": "binding-semi",
                "source_message_id": "evt-source-1",
                "request_id": "req-1",
                "plugin_id": "quantagent.official.source.rss",
                "correlation_id": "corr-1",
                "causation_id": "evt-source-1",
                "degraded": item.get("enrichment_status") == "failed_degraded",
                "items": [item],
            },
            producer="worker-industry-routing",
            created_at="2026-06-02T00:00:00Z",
            correlation_id="corr-1",
            causation_id="evt-source-1",
            headers={"binding_id": "binding-semi", "owner_id": "semiconductor", "request_id": "req-1"},
        )

    def _decision_from(self, payload: dict[str, object]):
        context = self._build_single_context()
        return __import__("quantagent.core.event_intake.decision", fromlist=["EventIntakeDecisionV1"]).EventIntakeDecisionV1.from_mapping(
            payload,
            trace=context.to_mapping()["trace"],
        )

    def _route_output(
        self,
        *,
        relationship: str = "direct",
        title: str = "HBM demand update",
        summary: str = "HBM demand is relevant to semiconductor memory.",
        targets: tuple[str, ...] = ("semiconductor",),
    ) -> dict[str, object]:
        return {
            "schema_version": EVENT_INTAKE_DECISION_SCHEMA_VERSION,
            "decision": "route",
            "discard_reason": "not_discarded",
            "quality": {
                "is_spam": False,
                "noise_flags": (),
                "content_completeness": "full",
                "enrichment_status": "succeeded",
                "confidence": 0.88,
                "reason_summary": "内容信息量充足，适合进入半导体路由判断。",
                "risk_flags": (),
            },
            "industry_relevance": (
                {
                    "industry_id": "semiconductor",
                    "relationship": relationship,
                    "relevance_score": 0.91,
                    "reason_summary": "文章直接涉及 HBM 与先进封装，和半导体存储链条直接相关。",
                },
            ),
            "structured_news": {
                "canonical_title": "HBM 需求变化影响存储供应链" if title == "HBM demand update" else title,
                "short_summary": "HBM 需求和先进封装产能仍然紧张。" if summary == "HBM demand is relevant to semiconductor memory." else summary,
                "bullet_summary": ("HBM 需求继续影响存储供应链。",),
                "event_type": "supply_demand",
                "event_type_label": "供需变化",
                "tags": ({"code": "memory", "label": "存储"},),
                "entities": ("HBM",),
                "companies": ("SK hynix",),
                "tickers": (),
                "technologies": ("HBM", "advanced packaging"),
                "products": ("memory",),
                "locations": (),
                "numbers": (),
                "time_horizon": "near_term",
                "source_facts": (summary,),
                "uncertainties": (),
            },
            "routing": {
                "target_industries": targets,
                "target_topics": ("memory",),
                "priority": "high",
                "requires_deep_analysis": True,
                "requires_human_review": False,
                "dedupe_key_hint": "https://example.com/hbm",
                "reason_summary": "该事件可能影响半导体存储链条的供需判断。",
                "next_step_hint": "交给半导体行业 MainAgent 做进一步分析。",
            },
            "audit": {
                "reason_summary": "基于文章标题和正文中的 HBM 证据判定为相关。",
                "evidence_field_refs": ("article.title", "article.body_excerpt"),
                "schema_validation_status": "valid",
                "source_language": "en",
                "output_language": "zh-CN",
            },
        }

    def _discard_output(self, *, reason: str = "irrelevant") -> dict[str, object]:
        return {
            "schema_version": EVENT_INTAKE_DECISION_SCHEMA_VERSION,
            "decision": "discard",
            "discard_reason": reason,
            "quality": {
                "is_spam": reason == "spam",
                "noise_flags": (reason,),
                "content_completeness": "full",
                "enrichment_status": "succeeded",
                "confidence": 0.92,
            },
            "industry_relevance": (),
            "structured_news": {
                "canonical_title": "Noise",
                "short_summary": "No useful semiconductor facts.",
                "bullet_summary": (),
                "event_type": "noise",
                "entities": (),
                "companies": (),
                "tickers": (),
                "technologies": (),
                "products": (),
                "locations": (),
                "numbers": (),
                "time_horizon": None,
                "source_facts": (),
                "uncertainties": (),
            },
            "routing": {
                "target_industries": (),
                "target_topics": (),
                "priority": "low",
                "requires_deep_analysis": False,
                "requires_human_review": False,
                "dedupe_key_hint": None,
            },
            "audit": {
                "reason_summary": "Discarded as noise.",
                "evidence_field_refs": ("article.title",),
                "schema_validation_status": "valid",
            },
        }

    def _review_output(self, *, requires_human_review: bool, confidence: float) -> dict[str, object]:
        return {
            "schema_version": EVENT_INTAKE_DECISION_SCHEMA_VERSION,
            "decision": "review",
            "discard_reason": "not_discarded",
            "quality": {
                "is_spam": False,
                "noise_flags": ("uncertain",),
                "content_completeness": "full",
                "enrichment_status": "succeeded",
                "confidence": confidence,
            },
            "industry_relevance": (),
            "structured_news": {"canonical_title": "Review", "short_summary": "Review needed."},
            "routing": {
                "target_industries": (),
                "target_topics": (),
                "priority": "low",
                "requires_deep_analysis": False,
                "requires_human_review": requires_human_review,
            },
            "audit": {
                "reason_summary": "Review needed.",
                "evidence_field_refs": ("article.title",),
                "schema_validation_status": "valid",
            },
        }


if __name__ == "__main__":
    unittest.main()
