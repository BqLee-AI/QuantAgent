from __future__ import annotations

import unittest

from quantagent.core.events import EventBusError, EventEnvelope
from quantagent.core.worker_routing import WorkerRouteResult, WorkerRouteStatus, ConsumerDisposition
from quantagent.worker.consumer import CapturedSourceEventHandler, InMemoryWorkerRouteAuditSink


class _StubRoutingService:
    def __init__(self, result: WorkerRouteResult) -> None:
        self._result = result

    async def route(self, event):
        return self._result


class CapturedEventHandlerTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_retryable_route_result_raises_event_bus_error_after_audit(self) -> None:
        audit_sink = InMemoryWorkerRouteAuditSink()
        handler = CapturedSourceEventHandler(
            routing_service=_StubRoutingService(
                WorkerRouteResult(
                    message_id="evt-retry",
                    binding_id="binding-001",
                    status=WorkerRouteStatus.FAILED,
                    consumer_disposition=ConsumerDisposition.NACK_OR_SCHEDULE_RETRY,
                    retryable=True,
                    audit_required=True,
                    reason_code="INDUSTRY_ENTRYPOINT_FAILED",
                    audit_payload={"binding_id": "binding-001"},
                )
            ),
            audit_sink=audit_sink,
        )

        with self.assertRaises(EventBusError) as ctx:
            await handler.handle(self._envelope())

        self.assertEqual(ctx.exception.code, "INDUSTRY_ENTRYPOINT_FAILED")
        self.assertEqual(len(audit_sink.entries), 1)

    async def test_non_retryable_result_only_records_audit(self) -> None:
        audit_sink = InMemoryWorkerRouteAuditSink()
        handler = CapturedSourceEventHandler(
            routing_service=_StubRoutingService(
                WorkerRouteResult(
                    message_id="evt-ok",
                    binding_id="binding-001",
                    status=WorkerRouteStatus.ROUTED,
                    consumer_disposition=ConsumerDisposition.ACK_AND_RECORD_ROUTED,
                    retryable=False,
                    audit_required=True,
                    reason_code=None,
                    audit_payload={"binding_id": "binding-001"},
                )
            ),
            audit_sink=audit_sink,
        )

        await handler.handle(self._envelope())

        self.assertEqual(len(audit_sink.entries), 1)
        self.assertEqual(audit_sink.entries[0].message_id, "evt-ok")

    def _envelope(self) -> EventEnvelope:
        return EventEnvelope(
            id="evt-1",
            topic="source.event.captured",
            payload={
                "binding_id": "binding-001",
                "plugin_id": "quantagent.official.source.test",
                "items": [{"external_id": "item-1"}],
                "metadata": {},
            },
            producer="scheduler-loop",
            created_at="2026-06-02T08:00:00+00:00",
            correlation_id="req-001",
            causation_id="run-001",
            headers={
                "binding_id": "binding-001",
                "request_id": "req-001",
                "plugin_id": "quantagent.official.source.test",
                "item_count": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
