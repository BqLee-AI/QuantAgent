from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from quantagent.core.events.codec import EventBusCodec
from quantagent.core.events.envelope import EventEnvelope
from quantagent.core.events.errors import EventBusError
from quantagent.core.events.ports import EventBusConsumer, EventBusHandler, EventBusPublisher
from quantagent.core.events.topics import EventTopicPolicy


class InMemoryEventBus(EventBusPublisher, EventBusConsumer):
    def __init__(
        self,
        *,
        topic_policy: EventTopicPolicy | None = None,
        codec: EventBusCodec | None = None,
    ) -> None:
        self._topic_policy = topic_policy or EventTopicPolicy()
        self._codec = codec or EventBusCodec()
        self._handlers_by_topic: dict[str, list[tuple[str, EventBusHandler]]] = defaultdict(list)

    async def publish(self, envelope: EventEnvelope) -> EventEnvelope:
        self._topic_policy.validate(envelope.topic)
        encoded = self._codec.encode(envelope)
        decoded = self._codec.decode(encoded)
        for _, handler in list(self._handlers_by_topic.get(decoded.topic, [])):
            try:
                await handler.handle(decoded)
            except EventBusError:
                raise
            except Exception as exc:
                raise EventBusError(
                    code="EVENT_HANDLER_FAILED",
                    message="Event handler raised an unexpected error.",
                    stage="dispatch",
                    details={"error_type": exc.__class__.__name__, "topic": decoded.topic},
                    retryable=True,
                ) from exc
        return decoded

    async def subscribe(
        self,
        *,
        topics: Iterable[str],
        group_id: str,
        handler: EventBusHandler,
    ) -> None:
        if not isinstance(group_id, str) or not group_id.strip():
            raise EventBusError(
                code="EVENT_GROUP_ID_INVALID",
                message="Consumer group id must be a non-empty string.",
                stage="subscribe",
            )
        for topic in topics:
            validated_topic = self._topic_policy.validate(topic)
            self._handlers_by_topic[validated_topic].append((group_id, handler))

    async def consume_forever(
        self,
        *,
        topics: Iterable[str],
        group_id: str,
        handler: EventBusHandler,
    ) -> None:
        await self.subscribe(topics=topics, group_id=group_id, handler=handler)
