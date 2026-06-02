from __future__ import annotations

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
        return WorkerIndustryPublishResult(
            published=True,
            topic="industry.analysis.requested",
            request_payload=payload.to_mapping(),
            degraded=payload.degraded,
            item_count=len(payload.items),
        )


def _default_event_id_factory() -> str:
    return f"evt_{uuid4().hex}"
