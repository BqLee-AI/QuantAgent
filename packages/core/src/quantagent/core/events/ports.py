from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from quantagent.core.events.envelope import EventEnvelope


@runtime_checkable
class EventBusHandler(Protocol):
    async def handle(self, envelope: EventEnvelope) -> None: ...


@runtime_checkable
class EventBusPublisher(Protocol):
    async def publish(self, envelope: EventEnvelope) -> EventEnvelope: ...


@runtime_checkable
class EventBusConsumer(Protocol):
    async def subscribe(
        self,
        *,
        topics: Iterable[str],
        group_id: str,
        handler: EventBusHandler,
    ) -> None: ...

    async def consume_forever(
        self,
        *,
        topics: Iterable[str],
        group_id: str,
        handler: EventBusHandler,
    ) -> None: ...
