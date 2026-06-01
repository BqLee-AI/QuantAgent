from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import unittest

from quantagent.core.events import EventEnvelope
from quantagent.core.scheduling import SourceBindingStatus
from quantagent.core.worker_routing import (
    FailingIndustryGateway,
    NoopIndustryGateway,
    SourceBindingOwnerResolver,
    WorkerCapturedEventRoutingService,
    decode_captured_source_event,
)


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

        result = await routing.route(decode_captured_source_event(self._envelope(binding_id="binding-001")))

        self.assertEqual(result.status.value, "routed")
        self.assertEqual(result.consumer_disposition.value, "ack_and_record_routed")
        self.assertEqual(result.route_target, "industry:oil")
        self.assertFalse(result.retryable)

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
        status: SourceBindingStatus = SourceBindingStatus.ACTIVE,
    ) -> _FakeBindingRecord:
        now = datetime(2026, 6, 2, 8, 0, tzinfo=UTC)
        return _FakeBindingRecord(
            binding_id="binding-001",
            owner_type=owner_type,
            owner_id="oil",
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

    def _envelope(self, *, binding_id: str | None, message_id: str = "evt-001") -> EventEnvelope:
        payload = {
            "plugin_id": "quantagent.official.source.test",
            "items": [{"external_id": "item-1"}],
            "metadata": {"source": "rss"},
        }
        headers: dict[str, object] = {
            "request_id": "req-001",
            "plugin_id": "quantagent.official.source.test",
            "item_count": 1,
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


if __name__ == "__main__":
    unittest.main()
