from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from quantagent.core.events.codec import EventBusCodec
from quantagent.core.events.envelope import EventEnvelope
from quantagent.core.events.errors import EventBusError
from quantagent.core.events.ports import EventBusConsumer, EventBusHandler, EventBusPublisher
from quantagent.core.events.topics import EventTopicPolicy

try:  # pragma: no cover - exercised via integration boundary or import failure tests.
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
except ImportError:  # pragma: no cover - depends on local optional dependency.
    AIOKafkaConsumer = None
    AIOKafkaProducer = None


class KafkaEventBusPublisher(EventBusPublisher):
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        client_id: str,
        topic_policy: EventTopicPolicy | None = None,
        codec: EventBusCodec | None = None,
        producer_factory: Any | None = None,
    ) -> None:
        self._topic_policy = topic_policy or EventTopicPolicy()
        self._codec = codec or EventBusCodec()
        self._producer_factory = producer_factory or AIOKafkaProducer
        self._producer = None
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id

    async def publish(self, envelope: EventEnvelope) -> EventEnvelope:
        producer = await self._get_producer()
        validated_topic = self._topic_policy.validate(envelope.topic)
        try:
            await producer.send_and_wait(validated_topic, self._codec.encode(envelope))
        except Exception as exc:
            raise EventBusError(
                code="EVENT_PUBLISH_FAILED",
                message="Kafka publish failed.",
                stage="publish",
                details={"error_type": exc.__class__.__name__, "topic": validated_topic},
                retryable=True,
            ) from exc
        return envelope

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def _get_producer(self) -> Any:
        if self._producer is not None:
            return self._producer
        if self._producer_factory is None:
            raise EventBusError(
                code="EVENT_KAFKA_DEPENDENCY_MISSING",
                message="Kafka backend requires optional aiokafka dependency.",
                stage="config",
            )
        producer = self._producer_factory(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
        )
        await producer.start()
        self._producer = producer
        return producer


class KafkaEventBusConsumer(EventBusConsumer):
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        client_id: str,
        topic_policy: EventTopicPolicy | None = None,
        codec: EventBusCodec | None = None,
        consumer_factory: Any | None = None,
    ) -> None:
        self._topic_policy = topic_policy or EventTopicPolicy()
        self._codec = codec or EventBusCodec()
        self._consumer_factory = consumer_factory or AIOKafkaConsumer
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._consumer = None

    async def subscribe(
        self,
        *,
        topics: Iterable[str],
        group_id: str,
        handler: EventBusHandler,
    ) -> None:
        """执行一次单条消息拉取并返回。

        当前 consumer 只用于 V1 smoke/integration 边界验证：一次 `subscribe(...)`
        最多处理一条消息，然后显式返回，避免在 API / 测试里隐式启动长期循环。
        真正的常驻消费循环应由 worker/scheduler 后续在更外层生命周期中托管。
        """
        if not isinstance(group_id, str) or not group_id.strip():
            raise EventBusError(
                code="EVENT_GROUP_ID_INVALID",
                message="Consumer group id must be a non-empty string.",
                stage="subscribe",
            )
        validated_topics = tuple(self._topic_policy.validate(topic) for topic in topics)
        consumer = await self._get_consumer(validated_topics, group_id=group_id)

        try:
            # V1 有意只 poll 一条消息，用于 smoke/contract 验证，而不是在这里内置长期消费循环。
            message = await asyncio.wait_for(consumer.getone(), timeout=1.0)
        except asyncio.TimeoutError:
            return
        except Exception as exc:
            raise EventBusError(
                code="EVENT_CONSUME_FAILED",
                message="Kafka consume failed.",
                stage="subscribe",
                details={"error_type": exc.__class__.__name__},
                retryable=True,
            ) from exc

        envelope = self._codec.decode(getattr(message, "value", message))
        try:
            await handler.handle(envelope)
        except EventBusError:
            raise
        except Exception as exc:
            raise EventBusError(
                code="EVENT_HANDLER_FAILED",
                message="Event handler raised an unexpected error.",
                stage="dispatch",
                details={"error_type": exc.__class__.__name__, "topic": envelope.topic},
                retryable=True,
            ) from exc
        await consumer.commit()

    async def close(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def _get_consumer(self, topics: tuple[str, ...], *, group_id: str) -> Any:
        if self._consumer is not None:
            return self._consumer
        if self._consumer_factory is None:
            raise EventBusError(
                code="EVENT_KAFKA_DEPENDENCY_MISSING",
                message="Kafka backend requires optional aiokafka dependency.",
                stage="config",
            )
        consumer = self._consumer_factory(
            *topics,
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
            group_id=group_id,
            enable_auto_commit=False,
        )
        await consumer.start()
        self._consumer = consumer
        return consumer
