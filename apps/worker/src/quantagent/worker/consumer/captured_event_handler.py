from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from quantagent.core.events import EventBusError, EventEnvelope
from quantagent.core.worker_routing import (
    WorkerCapturedEventRoutingService,
    WorkerRouteAuditEntry,
    build_audit_entry,
    decode_captured_source_event,
)

logger = logging.getLogger(__name__)


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
        logger.info(
            "Worker captured event handling started: message_id=%s binding_id=%s plugin_id=%s item_count=%s",
            event.message_id,
            event.binding_id,
            event.plugin_id,
            event.item_count,
            extra={
                "message_id": event.message_id,
                "binding_id": event.binding_id,
                "plugin_id": event.plugin_id,
                "item_count": event.item_count,
            },
        )
        result = await self.routing_service.route(event)
        self.audit_sink.record(build_audit_entry(result))
        logger.info(
            (
                "Worker captured event routed: message_id=%s binding_id=%s status=%s "
                "owner=%s:%s route_target=%s disposition=%s reason_code=%s retryable=%s"
            ),
            result.message_id,
            result.binding_id,
            result.status.value,
            result.owner_type,
            result.owner_id,
            result.route_target,
            result.consumer_disposition.value,
            result.reason_code,
            result.retryable,
            extra={
                "message_id": result.message_id,
                "binding_id": result.binding_id,
                "status": result.status.value,
                "owner_type": result.owner_type,
                "owner_id": result.owner_id,
                "route_target": result.route_target,
                "consumer_disposition": result.consumer_disposition.value,
                "reason_code": result.reason_code,
                "retryable": result.retryable,
            },
        )
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
