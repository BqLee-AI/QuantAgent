from __future__ import annotations

import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantagent.core.db.base import Base
from quantagent.core.db.repositories.event_intake_repository import EventIntakeRoutedEventRepository
from quantagent.core.event_intake import (
    EVENT_INTAKE_DECISION_SCHEMA_VERSION,
    FakeStructuredModelInvoker,
    IndustryEventContextBuilder,
    EventIntakeRoutedPublisher,
    SingleCallEventIntakeRunner,
    SqlAlchemyEventIntakeRoutedEventStore,
)
from quantagent.core.events import EventEnvelope, InMemoryEventBus
from quantagent.worker.consumer import (
    AnalysisRequestProcessingScope,
    IndustryAnalysisRequestHandler,
    InMemoryAnalysisRequestIntakeAuditSink,
)


class _RecordingHandler:
    def __init__(self) -> None:
        self.seen: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope)


class _RecordingRoutedEventStore:
    def __init__(self) -> None:
        self.records: list[tuple[EventEnvelope, object]] = []

    def record(self, *, envelope: EventEnvelope, result) -> object:
        self.records.append((envelope, result))
        return object()


class _ConcurrencyRecordingInvoker:
    def __init__(self, output: dict[str, object], *, delay: float = 0.01) -> None:
        self._output = output
        self._delay = delay
        self.active = 0
        self.max_active = 0
        self.invocation_count = 0

    async def invoke(self, *, context, output_schema: str):
        from quantagent.core.event_intake import StructuredModelInvocation

        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.invocation_count += 1
        try:
            await asyncio.sleep(self._delay)
            return StructuredModelInvocation(output={**self._output, "schema_version": output_schema})
        finally:
            self.active -= 1


class AnalysisRequestHandlerTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_handler_publishes_event_routed_for_analysis_request(self) -> None:
        bus = InMemoryEventBus()
        recorder = _RecordingHandler()
        await bus.subscribe(topics=("event.routed",), group_id="test", handler=recorder)
        invoker = FakeStructuredModelInvoker([self._route_output()])
        audit_sink = InMemoryAnalysisRequestIntakeAuditSink()
        routed_store = _RecordingRoutedEventStore()
        commits: list[str] = []
        handler = IndustryAnalysisRequestHandler(
            context_builder=IndustryEventContextBuilder(),
            runner=SingleCallEventIntakeRunner(invoker=invoker),
            routed_publisher=EventIntakeRoutedPublisher(bus, id_factory=lambda: "evt-routed-1"),
            audit_sink=audit_sink,
            routed_event_store=routed_store,
            commit=lambda: commits.append("commit"),
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
        self.assertEqual(len(routed_store.records), 1)
        self.assertEqual(commits, ["commit"])
        _, stored_result = routed_store.records[0]
        self.assertEqual(stored_result.context.trace.raw_event_id, "rawevt-worker-001")
        self.assertEqual(stored_result.context.trace.source_event_id, "entry-worker-001")

    async def test_handler_persists_v2_routed_read_model_with_real_store(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
        bus = InMemoryEventBus()
        recorder = _RecordingHandler()
        await bus.subscribe(topics=("event.routed",), group_id="test", handler=recorder)
        invoker = FakeStructuredModelInvoker([self._route_output()])
        handler = IndustryAnalysisRequestHandler(
            context_builder=IndustryEventContextBuilder(),
            runner=SingleCallEventIntakeRunner(invoker=invoker),
            routed_publisher=EventIntakeRoutedPublisher(bus, id_factory=lambda: "evt-routed-real-store"),
            audit_sink=InMemoryAnalysisRequestIntakeAuditSink(),
            routed_event_store=SqlAlchemyEventIntakeRoutedEventStore(
                EventIntakeRoutedEventRepository(session)
            ),
            commit=session.commit,
            rollback=session.rollback,
        )

        try:
            await handler.handle(self._analysis_request_envelope())
            await handler.handle(self._analysis_request_envelope())

            repository = EventIntakeRoutedEventRepository(session)
            stored = repository.get_by_event_id("evt-routed-real-store")
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertEqual(invoker.invocation_count, 2)
            self.assertEqual(len(recorder.seen), 2)
            self.assertEqual(stored.schema_version, EVENT_INTAKE_DECISION_SCHEMA_VERSION)
            self.assertEqual(stored.raw_event_id, "rawevt-worker-001")
            self.assertEqual(stored.decision, "route")
            self.assertEqual(stored.provider_invocation_count, 1)
            self.assertEqual(stored.key_fields["title"], "HBM demand update")
            self.assertEqual(stored.key_fields["short_summary"], "HBM demand is directly relevant.")
            self.assertEqual(stored.key_fields["priority"], "high")
            self.assertEqual(stored.output_json["schema_version"], EVENT_INTAKE_DECISION_SCHEMA_VERSION)
            self.assertNotIn("provider_raw_response", stored.output_json)
            self.assertNotIn("chain_of_thought", stored.output_json)
        finally:
            session.close()
            engine.dispose()

    async def test_handler_publishes_discard_for_malformed_analysis_request(self) -> None:
        bus = InMemoryEventBus()
        recorder = _RecordingHandler()
        await bus.subscribe(topics=("event.routed",), group_id="test", handler=recorder)
        invoker = FakeStructuredModelInvoker([self._route_output()])
        audit_sink = InMemoryAnalysisRequestIntakeAuditSink()
        routed_store = _RecordingRoutedEventStore()
        commits: list[str] = []
        handler = IndustryAnalysisRequestHandler(
            context_builder=IndustryEventContextBuilder(),
            runner=SingleCallEventIntakeRunner(invoker=invoker),
            routed_publisher=EventIntakeRoutedPublisher(bus, id_factory=lambda: "evt-routed-malformed"),
            audit_sink=audit_sink,
            routed_event_store=routed_store,
            commit=lambda: commits.append("commit"),
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
        self.assertEqual(len(routed_store.records), 1)
        self.assertEqual(commits, ["commit"])

    async def test_handler_limits_article_processing_concurrency(self) -> None:
        bus = InMemoryEventBus()
        recorder = _RecordingHandler()
        await bus.subscribe(topics=("event.routed",), group_id="test", handler=recorder)
        invoker = _ConcurrencyRecordingInvoker(self._route_output())
        handler = IndustryAnalysisRequestHandler(
            context_builder=IndustryEventContextBuilder(),
            runner=SingleCallEventIntakeRunner(invoker=invoker),
            routed_publisher=EventIntakeRoutedPublisher(bus),
            audit_sink=InMemoryAnalysisRequestIntakeAuditSink(),
            article_concurrency=3,
            processing_scope_factory=lambda: AnalysisRequestProcessingScope(
                runner=SingleCallEventIntakeRunner(invoker=invoker)
            ),
        )

        await handler.handle(self._analysis_request_envelope(item_count=10))

        self.assertEqual(invoker.invocation_count, 10)
        self.assertLessEqual(invoker.max_active, 3)
        self.assertEqual(len(recorder.seen), 10)

    def _analysis_request_envelope(self, *, item_count: int = 1) -> EventEnvelope:
        items = [
            {
                "url": f"https://example.com/hbm-{index}",
                "title": f"HBM demand update {index}",
                "summary_or_content": "HBM demand and advanced packaging capacity tighten.",
                "enrichment_status": "succeeded",
                "source_metadata": {
                    "raw_event_id": f"rawevt-worker-{index:03d}",
                    "source_event_id": f"entry-worker-{index:03d}",
                    "source": "rss",
                    "language": "en",
                },
            }
            for index in range(1, item_count + 1)
        ]
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
                "items": items,
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
