from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import unittest

from quantagent.core.events import InMemoryEventBus
from quantagent.core.events import EventEnvelope
from quantagent.core.registry.models import (
    PluginManifest,
    PluginRecord,
    PluginSource,
    PluginStatus,
    PluginType,
)
from quantagent.core.scheduling import SourceBindingStatus
from quantagent.core.worker_routing import (
    FailingIndustryGateway,
    IndustryAnalysisRequestedPublisher,
    NoopIndustryGateway,
    SourceBindingOwnerResolver,
    TopicPublishingIndustryGateway,
    WorkerArticleEnrichmentService,
    WorkerCapturedEventRoutingService,
    decode_captured_source_event,
)
from quantagent.core.worker_routing.enrichment_service import AnalysisRequestItem, EnrichmentStatus


@dataclass(frozen=True)
class _FakeBindingRecord:
    binding_id: str
    owner_type: str
    owner_id: str
    source_plugin_id: str
    source_plugin_version: str | None
    effective_config_snapshot: dict[str, object]
    schedule_policy: dict[str, object]
    retry_policy: dict[str, object]
    rate_limit_policy: dict[str, object]
    status: SourceBindingStatus
    last_run_id: str | None
    last_run_status: object | None
    last_run_at: datetime | None
    last_success_at: datetime | None
    next_run_at: datetime | None
    last_heartbeat_at: datetime | None
    consecutive_failure_count: int
    disabled_reason: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None


class _FakeBindingService:
    def __init__(self, bindings: dict[str, _FakeBindingRecord]) -> None:
        self._bindings = bindings

    def get_binding(self, binding_id: str) -> _FakeBindingRecord | None:
        return self._bindings.get(binding_id)


class _FakeRegistry:
    def __init__(self, readability_record: PluginRecord | None) -> None:
        self._readability_record = readability_record

    def get_plugin(self, plugin_id: str) -> PluginRecord | None:
        if plugin_id == "quantagent.official.source.readability":
            return self._readability_record
        return None


class _FakeRuntime:
    def __init__(self, *, output: dict[str, object] | None = None, error_code: str | None = None) -> None:
        self._output = output
        self._error_code = error_code

    async def invoke(self, record, *, capability, request_id, config=None, input=None, metadata=None):
        class _Invocation:
            def __init__(self, *, output, error_code):
                self.result = None if output is None else type("Result", (), {"output": output})()
                self.error = None if error_code is None else type(
                    "Error",
                    (),
                    {"code": error_code, "message": error_code, "stage": "invoke"},
                )()

        return _Invocation(output=self._output, error_code=self._error_code)


class _ConcurrencyRecordingRuntime:
    def __init__(self, *, delay: float = 0.01) -> None:
        self.active = 0
        self.max_active = 0
        self.invocation_count = 0
        self._delay = delay

    async def invoke(self, record, *, capability, request_id, config=None, input=None, metadata=None):
        class _Invocation:
            def __init__(self, *, output):
                self.result = type("Result", (), {"output": output})()
                self.error = None

        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.invocation_count += 1
        try:
            await asyncio.sleep(self._delay)
            return _Invocation(
                output={
                    "items": [
                        {
                            "url": (input or {}).get("url"),
                            "title": f"enriched {self.invocation_count}",
                            "content": "Long enriched article body " * 20,
                            "metadata": {"canonical_url": (input or {}).get("url")},
                            "raw_payload": {},
                        }
                    ],
                    "next_cursor": None,
                    "metadata": {"source": "readability"},
                }
            )
        finally:
            self.active -= 1


class _RecordingAnalysisHandler:
    def __init__(self) -> None:
        self.seen: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope)


class WorkerCapturedEventRoutingTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_decode_prefers_binding_id_for_routing(self) -> None:
        event = decode_captured_source_event(self._envelope(binding_id="binding-001"))

        self.assertEqual(event.binding_id, "binding-001")
        self.assertEqual(event.plugin_id, "quantagent.official.source.test")
        self.assertEqual(event.item_count, 1)

    async def test_route_active_industry_binding_to_gateway(self) -> None:
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({"binding-001": self._binding_record()}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=NoopIndustryGateway(),
        )

        result = await routing.route(
            decode_captured_source_event(self._envelope(binding_id="binding-001", short_content=True))
        )

        self.assertEqual(result.status.value, "routed")
        self.assertEqual(result.consumer_disposition.value, "ack_and_record_routed")
        self.assertEqual(result.route_target, "industry:oil")
        self.assertFalse(result.retryable)

    async def test_route_semiconductor_binding_publishes_industry_analysis_requested(self) -> None:
        bus = InMemoryEventBus()
        handler = _RecordingAnalysisHandler()
        await bus.subscribe(
            topics=("industry.analysis.requested",),
            group_id="analysis-tests",
            handler=handler,
        )
        readability_record = PluginRecord(
            id="quantagent.official.source.readability",
            source=PluginSource.OFFICIAL,
            path=self._repo_plugin_path(),
            status=PluginStatus.VALID,
            manifest=PluginManifest(
                id="quantagent.official.source.readability",
                name="Readability Link Reader",
                type=PluginType.SOURCE,
                version="0.1.0",
                entrypoint="src.readability_source:plugin",
                capabilities=("source.fetch",),
                config_schema="config.schema.json",
            ),
            config_schema_path=None,
            last_error=None,
        )
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({"binding-001": self._binding_record(owner_id="semiconductor")}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=TopicPublishingIndustryGateway(
                publisher=IndustryAnalysisRequestedPublisher(bus, id_factory=lambda: "evt-analysis-1")
            ),
            enrichment_service=WorkerArticleEnrichmentService(
                registry=_FakeRegistry(readability_record),
                runtime=_FakeRuntime(
                    output={
                        "items": [
                            {
                                "url": "https://example.com/article",
                                "title": "HBM Demand Surges",
                                "content": "Long enriched article body " * 20,
                                "metadata": {"canonical_url": "https://example.com/article"},
                                "raw_payload": {},
                            }
                        ],
                        "next_cursor": None,
                        "metadata": {"source": "readability"},
                    }
                ),
            ),
        )

        result = await routing.route(
            decode_captured_source_event(self._envelope(binding_id="binding-001", short_content=True))
        )

        self.assertEqual(result.status.value, "routed")
        self.assertEqual(result.reason_code, "INDUSTRY_ANALYSIS_REQUESTED_PUBLISHED")
        self.assertEqual(len(handler.seen), 1)
        published = handler.seen[0]
        self.assertEqual(published.topic, "industry.analysis.requested")
        self.assertEqual(published.payload["owner_id"], "semiconductor")
        self.assertFalse(published.payload["degraded"])
        self.assertEqual(published.payload["items"][0]["enrichment_status"], "succeeded")

    async def test_route_semiconductor_binding_degrades_when_readability_fails(self) -> None:
        bus = InMemoryEventBus()
        handler = _RecordingAnalysisHandler()
        await bus.subscribe(
            topics=("industry.analysis.requested",),
            group_id="analysis-tests",
            handler=handler,
        )
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({"binding-001": self._binding_record(owner_id="semiconductor")}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=TopicPublishingIndustryGateway(
                publisher=IndustryAnalysisRequestedPublisher(bus, id_factory=lambda: "evt-analysis-2")
            ),
            enrichment_service=WorkerArticleEnrichmentService(
                registry=_FakeRegistry(None),
                runtime=_FakeRuntime(error_code="PLUGIN_INVOKE_FAILED"),
            ),
        )

        result = await routing.route(decode_captured_source_event(self._envelope(binding_id="binding-001", short_content=True)))

        self.assertEqual(result.status.value, "routed")
        self.assertEqual(len(handler.seen), 1)
        published = handler.seen[0]
        self.assertTrue(published.payload["degraded"])
        self.assertEqual(published.payload["items"][0]["enrichment_status"], "failed_degraded")
        self.assertEqual(
            published.payload["items"][0]["enrichment_error_code"],
            "READABILITY_PLUGIN_NOT_REGISTERED",
        )

    async def test_readability_enrichment_limits_article_concurrency(self) -> None:
        readability_record = PluginRecord(
            id="quantagent.official.source.readability",
            source=PluginSource.OFFICIAL,
            path=self._repo_plugin_path(),
            status=PluginStatus.VALID,
            manifest=PluginManifest(
                id="quantagent.official.source.readability",
                name="Readability Link Reader",
                type=PluginType.SOURCE,
                version="0.1.0",
                entrypoint="src.readability_source:plugin",
                capabilities=("source.fetch",),
                config_schema="config.schema.json",
            ),
            config_schema_path=None,
            last_error=None,
        )
        runtime = _ConcurrencyRecordingRuntime()
        service = WorkerArticleEnrichmentService(
            registry=_FakeRegistry(readability_record),
            runtime=runtime,
            article_concurrency=3,
        )

        items = await service.build_analysis_items(
            owner_id="semiconductor",
            event=decode_captured_source_event(
                self._envelope(binding_id="binding-001", short_content=True, item_count=10)
            ),
        )

        self.assertEqual(len(items), 10)
        self.assertEqual(runtime.invocation_count, 10)
        self.assertLessEqual(runtime.max_active, 3)

    async def test_missing_binding_id_is_controlled_failure(self) -> None:
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=NoopIndustryGateway(),
        )

        result = await routing.route(decode_captured_source_event(self._envelope(binding_id=None)))

        self.assertEqual(result.reason_code, "CAPTURED_EVENT_BINDING_ID_MISSING")
        self.assertEqual(result.status.value, "failed")
        self.assertEqual(result.consumer_disposition.value, "ack_and_record_failure")
        self.assertFalse(result.retryable)

    async def test_binding_not_found_is_non_retryable_failure(self) -> None:
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=NoopIndustryGateway(),
        )

        result = await routing.route(decode_captured_source_event(self._envelope(binding_id="binding-missing")))

        self.assertEqual(result.reason_code, "SOURCE_BINDING_NOT_FOUND")
        self.assertEqual(result.consumer_disposition.value, "ack_and_record_failure")
        self.assertFalse(result.retryable)

    async def test_non_active_binding_is_ignored(self) -> None:
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({"binding-001": self._binding_record(status=SourceBindingStatus.PAUSED)}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=NoopIndustryGateway(),
        )

        result = await routing.route(decode_captured_source_event(self._envelope(binding_id="binding-001")))

        self.assertEqual(result.reason_code, "SOURCE_BINDING_NOT_ACTIVE")
        self.assertEqual(result.status.value, "ignored")
        self.assertEqual(result.consumer_disposition.value, "ack_and_record_ignored")

    async def test_unsupported_owner_does_not_fallback_to_plugin_id(self) -> None:
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({"binding-001": self._binding_record(owner_type="runtime")}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=NoopIndustryGateway(),
        )

        result = await routing.route(decode_captured_source_event(self._envelope(binding_id="binding-001")))

        self.assertEqual(result.reason_code, "CAPTURED_EVENT_OWNER_UNSUPPORTED")
        self.assertEqual(result.status.value, "failed")
        self.assertEqual(result.consumer_disposition.value, "ack_and_record_failure")

    async def test_duplicate_message_is_acknowledged_on_second_delivery(self) -> None:
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({"binding-001": self._binding_record()}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=NoopIndustryGateway(),
        )

        first = await routing.route(
            decode_captured_source_event(self._envelope(binding_id="binding-001", message_id="evt-dup"))
        )
        second = await routing.route(
            decode_captured_source_event(self._envelope(binding_id="binding-001", message_id="evt-dup"))
        )

        self.assertEqual(first.status.value, "routed")
        self.assertEqual(second.reason_code, "CAPTURED_EVENT_DUPLICATE")
        self.assertEqual(second.status.value, "duplicate")
        self.assertEqual(second.consumer_disposition.value, "ack_and_record_duplicate")

    async def test_gateway_failure_is_retryable_and_not_marked_duplicate(self) -> None:
        routing = WorkerCapturedEventRoutingService(
            binding_service=_FakeBindingService({"binding-001": self._binding_record()}),
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=FailingIndustryGateway(error_summary={"message": "temporary downstream error"}),
        )

        first = await routing.route(
            decode_captured_source_event(self._envelope(binding_id="binding-001", message_id="evt-retry"))
        )
        second = await routing.route(
            decode_captured_source_event(self._envelope(binding_id="binding-001", message_id="evt-retry"))
        )

        self.assertEqual(first.reason_code, "INDUSTRY_ENTRYPOINT_FAILED")
        self.assertTrue(first.retryable)
        self.assertEqual(first.consumer_disposition.value, "nack_or_schedule_retry")
        self.assertEqual(second.reason_code, "INDUSTRY_ENTRYPOINT_FAILED")
        self.assertTrue(second.retryable)

    def _binding_record(
        self,
        *,
        owner_type: str = "industry",
        owner_id: str = "oil",
        status: SourceBindingStatus = SourceBindingStatus.ACTIVE,
    ) -> _FakeBindingRecord:
        now = datetime(2026, 6, 2, 8, 0, tzinfo=UTC)
        return _FakeBindingRecord(
            binding_id="binding-001",
            owner_type=owner_type,
            owner_id=owner_id,
            source_plugin_id="quantagent.official.source.test",
            source_plugin_version="1.0.0",
            effective_config_snapshot={},
            schedule_policy={},
            retry_policy={},
            rate_limit_policy={},
            status=status,
            last_run_id=None,
            last_run_status=None,
            last_run_at=None,
            last_success_at=None,
            next_run_at=None,
            last_heartbeat_at=None,
            consecutive_failure_count=0,
            disabled_reason=None,
            created_at=now,
            updated_at=now,
            created_by="test",
            updated_by="test",
        )

    def _envelope(
        self,
        *,
        binding_id: str | None,
        message_id: str = "evt-001",
        short_content: bool = False,
        item_count: int = 1,
    ) -> EventEnvelope:
        payload = {
            "plugin_id": "quantagent.official.source.test",
            "items": [
                {
                    "external_id": f"item-{index}",
                    "url": f"https://example.com/article-{index}",
                    "title": f"HBM Demand Surges {index}",
                    "content": "short summary" if short_content else "This is a long enough body to avoid enrichment." * 8,
                    "metadata": {"source": "rss"},
                }
                for index in range(1, item_count + 1)
            ],
            "metadata": {"source": "rss"},
        }
        headers: dict[str, object] = {
            "request_id": "req-001",
            "plugin_id": "quantagent.official.source.test",
            "item_count": item_count,
        }
        if binding_id is not None:
            payload["binding_id"] = binding_id
            headers["binding_id"] = binding_id
        return EventEnvelope(
            id=message_id,
            topic="source.event.captured",
            payload=payload,
            producer="scheduler-loop",
            created_at="2026-06-02T08:00:00+00:00",
            correlation_id="req-001",
            causation_id="run-001",
            headers=headers,
        )

    def _repo_plugin_path(self):
        return __import__("pathlib").Path(__file__).resolve().parents[3] / "plugins" / "sources" / "readability-source"


if __name__ == "__main__":
    unittest.main()
