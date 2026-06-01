from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from quantagent.core.events import EventBusError, EventEnvelope
from quantagent.core.worker_routing import (
    WorkerCapturedEventRoutingService,
    WorkerRouteAuditEntry,
    build_audit_entry,
    decode_captured_source_event,
)


class WorkerRouteAuditSink(Protocol):
    def record(self, entry: WorkerRouteAuditEntry) -> None: ...


@dataclass
class InMemoryWorkerRouteAuditSink:
    entries: list[WorkerRouteAuditEntry] = field(default_factory=list)

    def record(self, entry: WorkerRouteAuditEntry) -> None:
        self.entries.append(entry)


@dataclass
class CapturedSourceEventHandler:
    routing_service: WorkerCapturedEventRoutingService
    audit_sink: WorkerRouteAuditSink

    async def handle(self, envelope: EventEnvelope) -> None:
        event = decode_captured_source_event(envelope)
        result = await self.routing_service.route(event)
        self.audit_sink.record(build_audit_entry(result))
        if result.retryable:
            # 先写入结构化审计，再把可重试失败抛回 transport，避免 Kafka nack 后只剩日志没有真源。
            raise EventBusError(
                code=result.reason_code or "WORKER_ROUTE_RETRYABLE_FAILURE",
                message="Captured source event routing failed and should be retried.",
                stage="worker_routing",
                details={
                    "message_id": result.message_id,
                    "binding_id": result.binding_id,
                    "route_status": result.status.value,
                },
                retryable=True,
            )
