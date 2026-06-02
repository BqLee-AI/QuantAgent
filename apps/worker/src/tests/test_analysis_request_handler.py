from __future__ import annotations

import unittest

from quantagent.core.event_intake import (
    EVENT_INTAKE_DECISION_SCHEMA_VERSION,
    FakeStructuredModelInvoker,
    IndustryEventContextBuilder,
    EventIntakeRoutedPublisher,
    SingleCallEventIntakeRunner,
)
from quantagent.core.events import EventEnvelope, InMemoryEventBus
from quantagent.worker.consumer import IndustryAnalysisRequestHandler, InMemoryAnalysisRequestIntakeAuditSink


class _RecordingHandler:
    def __init__(self) -> None:
        self.seen: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope)


class AnalysisRequestHandlerTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_handler_publishes_event_routed_for_analysis_request(self) -> None:
        bus = InMemoryEventBus()
        recorder = _RecordingHandler()
        await bus.subscribe(topics=("event.routed",), group_id="test", handler=recorder)
        invoker = FakeStructuredModelInvoker([self._route_output()])
        audit_sink = InMemoryAnalysisRequestIntakeAuditSink()
        handler = IndustryAnalysisRequestHandler(
            context_builder=IndustryEventContextBuilder(),
            runner=SingleCallEventIntakeRunner(invoker=invoker),
            routed_publisher=EventIntakeRoutedPublisher(bus, id_factory=lambda: "evt-routed-1"),
            audit_sink=audit_sink,
        )

        await handler.handle(self._analysis_request_envelope())

        self.assertEqual(invoker.invocation_count, 1)
        self.assertEqual(len(recorder.seen), 1)
        routed = recorder.seen[0]
        self.assertEqual(routed.topic, "event.routed")
        self.assertEqual(routed.payload["schema_version"], EVENT_INTAKE_DECISION_SCHEMA_VERSION)
        self.assertEqual(routed.payload["decision"], "route")
        self.assertEqual(routed.payload["routing"]["target_industries"], ("semiconductor",))
        self.assertEqual(routed.headers["owner_id"], "semiconductor")
        self.assertEqual(len(audit_sink.entries), 1)
        self.assertEqual(audit_sink.entries[0]["provider_invocation_count"], 1)

    async def test_handler_publishes_discard_for_malformed_analysis_request(self) -> None:
        bus = InMemoryEventBus()
        recorder = _RecordingHandler()
        await bus.subscribe(topics=("event.routed",), group_id="test", handler=recorder)
        invoker = FakeStructuredModelInvoker([self._route_output()])
        audit_sink = InMemoryAnalysisRequestIntakeAuditSink()
        handler = IndustryAnalysisRequestHandler(
            context_builder=IndustryEventContextBuilder(),
            runner=SingleCallEventIntakeRunner(invoker=invoker),
            routed_publisher=EventIntakeRoutedPublisher(bus, id_factory=lambda: "evt-routed-malformed"),
            audit_sink=audit_sink,
        )

        await handler.handle(
            EventEnvelope(
                id="evt-analysis-bad",
                topic="industry.analysis.requested",
                payload={
                    "owner_type": "industry",
                    "owner_id": "semiconductor",
                    "binding_id": "binding-semi",
                    "source_message_id": "evt-source-1",
                    "request_id": "req-1",
                    "plugin_id": "quantagent.official.source.rss",
                    "items": "not-an-array",
                },
                producer="worker-industry-routing",
                created_at="2026-06-02T00:00:00Z",
                headers={"binding_id": "binding-semi", "owner_id": "semiconductor", "request_id": "req-1"},
            )
        )

        self.assertEqual(invoker.invocation_count, 0)
        self.assertEqual(len(recorder.seen), 1)
        routed = recorder.seen[0]
        self.assertEqual(routed.payload["decision"], "discard")
        self.assertEqual(routed.payload["discard_reason"], "malformed")
        self.assertEqual(len(audit_sink.entries), 1)
        self.assertEqual(audit_sink.entries[0]["discard_reason"], "malformed")

    def _analysis_request_envelope(self) -> EventEnvelope:
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
                "degraded": False,
                "items": [
                    {
                        "url": "https://example.com/hbm",
                        "title": "HBM demand update",
                        "summary_or_content": "HBM demand and advanced packaging capacity tighten.",
                        "enrichment_status": "succeeded",
                        "source_metadata": {"source": "rss", "language": "en"},
                    }
                ],
            },
            producer="worker-industry-routing",
            created_at="2026-06-02T00:00:00Z",
            correlation_id="corr-1",
            causation_id="evt-source-1",
            headers={"binding_id": "binding-semi", "owner_id": "semiconductor", "request_id": "req-1"},
        )

    def _route_output(self) -> dict[str, object]:
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
            },
            "industry_relevance": (
                {
                    "industry_id": "semiconductor",
                    "relationship": "direct",
                    "relevance_score": 0.91,
                    "reason_summary": "HBM demand is directly relevant.",
                },
            ),
            "structured_news": {
                "canonical_title": "HBM demand update",
                "short_summary": "HBM demand is directly relevant.",
                "bullet_summary": ("HBM demand is directly relevant.",),
                "event_type": "supply_demand",
                "entities": ("HBM",),
                "companies": (),
                "tickers": (),
                "technologies": ("HBM",),
                "products": ("memory",),
                "locations": (),
                "numbers": (),
                "time_horizon": "near_term",
                "source_facts": ("HBM demand and advanced packaging capacity tighten.",),
                "uncertainties": (),
            },
            "routing": {
                "target_industries": ("semiconductor",),
                "target_topics": ("memory",),
                "priority": "high",
                "requires_deep_analysis": True,
                "requires_human_review": False,
                "dedupe_key_hint": "https://example.com/hbm",
            },
            "audit": {
                "reason_summary": "Direct semiconductor memory relevance.",
                "evidence_field_refs": ("article.title", "article.body_excerpt"),
                "schema_validation_status": "valid",
            },
        }


if __name__ == "__main__":
    unittest.main()
