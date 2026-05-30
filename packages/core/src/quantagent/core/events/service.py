from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from typing import Protocol
from uuid import uuid4

from quantagent.core.events.config import EventBusSettings
from quantagent.core.events.envelope import EventEnvelope
from quantagent.core.events.kafka import KafkaEventBusConsumer, KafkaEventBusPublisher
from quantagent.core.events.memory import InMemoryEventBus
from quantagent.core.events.ports import EventBusPublisher
from quantagent.plugin_sdk import SourceFetchResult
from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping


class EventIdFactory(Protocol):
    def __call__(self) -> str: ...


@dataclass(frozen=True)
class EventBusRuntime:
    publisher: EventBusPublisher
    consumer: object
    backend: str

    async def close(self) -> None:
        await _maybe_close(self.consumer)
        if self.publisher is not self.consumer:
            await _maybe_close(self.publisher)


def build_event_bus_runtime(settings: EventBusSettings) -> EventBusRuntime:
    if settings.backend == "kafka":
        return EventBusRuntime(
            publisher=KafkaEventBusPublisher(
                bootstrap_servers=settings.kafka_bootstrap_servers or "",
                client_id=settings.kafka_client_id,
            ),
            consumer=KafkaEventBusConsumer(
                bootstrap_servers=settings.kafka_bootstrap_servers or "",
                client_id=settings.kafka_client_id,
            ),
            backend="kafka",
        )

    bus = InMemoryEventBus()
    return EventBusRuntime(
        publisher=bus,
        consumer=bus,
        backend="memory",
    )


@dataclass
class SourceEventPublisher:
    publisher: EventBusPublisher
    id_factory: EventIdFactory | None = None

    async def publish_source_fetch_result(
        self,
        result: SourceFetchResult,
        *,
        producer: str,
        request_id: str,
        plugin_id: str,
        causation_id: str | None = None,
        correlation_id: str | None = None,
    ) -> EventEnvelope:
        envelope = EventEnvelope(
            id=(self.id_factory or _default_event_id_factory)(),
            topic="source.event.captured",
            payload=_source_fetch_payload(result, plugin_id=plugin_id),
            producer=producer,
            created_at=datetime.now(UTC).isoformat(),
            correlation_id=correlation_id or request_id,
            causation_id=causation_id,
            headers=freeze_json_mapping(
                {
                    "request_id": request_id,
                    "plugin_id": plugin_id,
                    "item_count": len(result.items),
                },
                stage="publish",
            ),
            retry_count=0,
        )
        return await self.publisher.publish(envelope)


def _default_event_id_factory() -> str:
    return f"evt_{uuid4().hex}"


def _source_fetch_payload(result: SourceFetchResult, *, plugin_id: str) -> JsonObject:
    return freeze_json_mapping(
        {
            "plugin_id": plugin_id,
            "items": [item.to_mapping() for item in result.items],
            "next_cursor": result.next_cursor,
            "metadata": dict(result.metadata),
        },
        stage="publish",
    )


async def _maybe_close(value: Any) -> None:
    close = getattr(value, "close", None)
    if callable(close):
        await close()
