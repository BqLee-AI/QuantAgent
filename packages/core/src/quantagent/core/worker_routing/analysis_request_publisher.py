from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from quantagent.core.events.envelope import EventEnvelope
from quantagent.core.events.ports import EventBusPublisher
from quantagent.plugin_sdk.io import freeze_json_mapping

from quantagent.core.worker_routing.models import (
    AnalysisRequestPayload,
    WorkerIndustryPublishResult,
)

logger = logging.getLogger(__name__)


class AnalysisRequestIdFactory(Protocol):
    def __call__(self) -> str: ...


@dataclass
class IndustryAnalysisRequestedPublisher:
    publisher: EventBusPublisher
    id_factory: AnalysisRequestIdFactory | None = None

    async def publish(
        self,
        payload: AnalysisRequestPayload,
    ) -> WorkerIndustryPublishResult:
        envelope = EventEnvelope(
            id=(self.id_factory or _default_event_id_factory)(),
            topic="industry.analysis.requested",
            payload=freeze_json_mapping(payload.to_mapping(), stage="publish"),
            producer="worker-industry-routing",
            created_at=datetime.now(UTC).isoformat(),
            correlation_id=payload.correlation_id or payload.request_id,
            causation_id=payload.source_message_id,
            headers=freeze_json_mapping(
                {
                    "binding_id": payload.binding_id,
                    "owner_type": payload.owner_type,
                    "owner_id": payload.owner_id,
                    "request_id": payload.request_id,
                    "plugin_id": payload.plugin_id,
                    "item_count": len(payload.items),
                    "degraded": payload.degraded,
                },
                stage="publish",
            ),
            retry_count=0,
        )
        await self.publisher.publish(envelope)
        logger.info(
            "Worker published industry.analysis.requested: message_id=%s source_message_id=%s binding_id=%s owner=%s:%s item_count=%s degraded=%s",
            envelope.id,
            payload.source_message_id,
            payload.binding_id,
            payload.owner_type,
            payload.owner_id,
            len(payload.items),
            payload.degraded,
            extra={
                "topic": "industry.analysis.requested",
                "message_id": envelope.id,
                "source_message_id": payload.source_message_id,
                "binding_id": payload.binding_id,
                "owner_type": payload.owner_type,
                "owner_id": payload.owner_id,
                "item_count": len(payload.items),
                "degraded": payload.degraded,
            },
        )
        return WorkerIndustryPublishResult(
            published=True,
            topic="industry.analysis.requested",
            request_payload=payload.to_mapping(),
            degraded=payload.degraded,
            item_count=len(payload.items),
        )


def _default_event_id_factory() -> str:
    return f"evt_{uuid4().hex}"
