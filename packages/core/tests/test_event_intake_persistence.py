from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quantagent.core.db.base import Base
from quantagent.core.db.repositories.event_intake_repository import EventIntakeRoutedEventRepository
from quantagent.core.event_intake import (
    EVENT_INTAKE_DECISION_SCHEMA_VERSION,
    EventIntakeRoutedPublisher,
    FakeStructuredModelInvoker,
    IndustryEventContextBuilder,
    SingleCallEventIntakeRunner,
    SqlAlchemyEventIntakeRoutedEventStore,
)
from quantagent.core.events import EventEnvelope, InMemoryEventBus


class EventIntakePersistenceTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()

    async def asyncTearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    async def test_store_records_routed_event_once_and_links_raw_event(self) -> None:
        context = IndustryEventContextBuilder().build_contexts(self._analysis_request_envelope())[0]
        result = await SingleCallEventIntakeRunner(
            invoker=FakeStructuredModelInvoker([self._route_output()])
        ).run(context)
        routed = await EventIntakeRoutedPublisher(
            InMemoryEventBus(),
            id_factory=lambda: "evt-routed-persist-1",
        ).publish(result)
        store = SqlAlchemyEventIntakeRoutedEventStore(EventIntakeRoutedEventRepository(self.session))

        first = store.record(envelope=routed, result=result)
        second = store.record(envelope=routed, result=result)
        self.session.commit()

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.event_id, "evt-routed-persist-1")
        self.assertEqual(first.schema_version, EVENT_INTAKE_DECISION_SCHEMA_VERSION)
        self.assertEqual(first.raw_event_id, "rawevt-persist-001")
        self.assertEqual(first.binding_id, "binding-semi")
        self.assertEqual(first.owner_id, "semiconductor")
        self.assertEqual(first.request_id, "req-1")
        self.assertEqual(first.decision, "route")
        self.assertEqual(first.status, "success")
        self.assertEqual(first.key_fields["short_summary"], "HBM demand is directly relevant.")
        self.assertEqual(first.output_json["decision"], "route")
        self.assertNotIn("provider_raw_response", first.output_json)
        self.assertNotIn("chain_of_thought", first.output_json)
        self.assertNotIn("full article body", str(first.output_json))

        latest = EventIntakeRoutedEventRepository(self.session).list_latest_by_raw_event_ids(["rawevt-persist-001"])
        self.assertEqual(latest["rawevt-persist-001"].event_id, "evt-routed-persist-1")

    def _analysis_request_envelope(self) -> EventEnvelope:
        return EventEnvelope(
            id="evt-analysis-persist-1",
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
                        "source_metadata": {
                            "raw_event_id": "rawevt-persist-001",
                            "source_event_id": "entry-persist-001",
                            "source": "rss",
                            "language": "en",
                        },
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
