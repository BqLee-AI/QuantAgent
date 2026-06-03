from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from quantagent.core.events.codec import EventBusCodec
from quantagent.core.events.envelope import EventEnvelope
from quantagent.core.events.errors import EventBusError
from quantagent.core.events.ports import EventBusConsumer, EventBusHandler, EventBusPublisher
from quantagent.core.events.topics import DEFAULT_EVENT_TOPICS, EventTopicPolicy

try:  # pragma: no cover - exercised via integration boundary or import failure tests.
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    from aiokafka.errors import TopicAlreadyExistsError
except ImportError:  # pragma: no cover - depends on local optional dependency.
    AIOKafkaAdminClient = None
    AIOKafkaConsumer = None
    AIOKafkaProducer = None
    NewTopic = None
    TopicAlreadyExistsError = None


class KafkaTopicBootstrapper:
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        client_id: str,
        topics: Iterable[str] = DEFAULT_EVENT_TOPICS,
        admin_factory: Any | None = None,
        topic_factory: Any | None = None,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._topics = tuple(dict.fromkeys(topics))
        self._admin_factory = admin_factory or AIOKafkaAdminClient
        self._topic_factory = topic_factory or NewTopic
        self._bootstrapped = False
        self._lock = asyncio.Lock()

    async def ensure_topics(self, topics: Iterable[str]) -> None:
        if self._bootstrapped:
            return
        requested = tuple(dict.fromkeys(topics))
        async with self._lock:
            if self._bootstrapped:
                return
            await self._create_topics(tuple(dict.fromkeys((*self._topics, *requested))))
            self._bootstrapped = True

    async def _create_topics(self, topics: tuple[str, ...]) -> None:
        if self._admin_factory is None or self._topic_factory is None:
            raise EventBusError(
                code="EVENT_KAFKA_DEPENDENCY_MISSING",
                message="Kafka backend requires optional aiokafka admin dependency.",
                stage="config",
            )
        admin = self._admin_factory(
            bootstrap_servers=self._bootstrap_servers,
            client_id=f"{self._client_id}-admin",
        )
        try:
            await admin.start()
            existing_topics = set(await admin.list_topics())
            new_topics = [
                self._topic_factory(name=topic, num_partitions=1, replication_factor=1)
                for topic in topics
                if topic not in existing_topics
            ]
            if not new_topics:
                return
            try:
                # 默认 Kafka 运行态不能依赖用户手工建 topic；这里做幂等 bootstrap，消除冷启动 topic missing 噪声。
                await admin.create_topics(new_topics)
            except Exception as exc:
                if not _is_topic_already_exists_error(exc):
                    raise
        except Exception as exc:
            raise EventBusError(
                code="EVENT_KAFKA_TOPIC_BOOTSTRAP_FAILED",
                message="Kafka topic bootstrap failed.",
                stage="topic_bootstrap",
                details={"error_type": exc.__class__.__name__},
                retryable=True,
            ) from exc
        finally:
            await admin.close()


def _is_topic_already_exists_error(exc: Exception) -> bool:
    if TopicAlreadyExistsError is not None and isinstance(exc, TopicAlreadyExistsError):
        return True
    if isinstance(exc, (list, tuple)):
        return all(isinstance(item, Exception) and _is_topic_already_exists_error(item) for item in exc)
    if isinstance(exc, BaseExceptionGroup):
        return all(_is_topic_already_exists_error(item) for item in exc.exceptions)
    error_type = exc.__class__.__name__
    return error_type in {"TopicAlreadyExistsError", "TopicAlreadyExists"}


class KafkaEventBusPublisher(EventBusPublisher):
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        client_id: str,
        topic_policy: EventTopicPolicy | None = None,
        codec: EventBusCodec | None = None,
        producer_factory: Any | None = None,
        topic_bootstrapper: KafkaTopicBootstrapper | None = None,
    ) -> None:
        self._topic_policy = topic_policy or EventTopicPolicy()
        self._codec = codec or EventBusCodec()
        self._producer_factory = producer_factory or AIOKafkaProducer
        self._topic_bootstrapper = topic_bootstrapper or KafkaTopicBootstrapper(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            topics=self._topic_policy.topics,
        )
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
        await self._topic_bootstrapper.ensure_topics(self._topic_policy.topics)
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
        topic_bootstrapper: KafkaTopicBootstrapper | None = None,
    ) -> None:
        self._topic_policy = topic_policy or EventTopicPolicy()
        self._codec = codec or EventBusCodec()
        self._consumer_factory = consumer_factory or AIOKafkaConsumer
        self._topic_bootstrapper = topic_bootstrapper or KafkaTopicBootstrapper(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            topics=self._topic_policy.topics,
        )
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
        """执行一次单条消息拉取并返回。"""
        if not isinstance(group_id, str) or not group_id.strip():
            raise EventBusError(
                code="EVENT_GROUP_ID_INVALID",
                message="Consumer group id must be a non-empty string.",
                stage="subscribe",
            )
        validated_topics = tuple(self._topic_policy.validate(topic) for topic in topics)
        consumer = await self._get_consumer(validated_topics, group_id=group_id)

        try:
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

        await self._dispatch_message(message=message, handler=handler, consumer=consumer)

    async def consume_forever(
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
        validated_topics = tuple(self._topic_policy.validate(topic) for topic in topics)
        consumer = await self._get_consumer(validated_topics, group_id=group_id)

        try:
            while True:
                message = await consumer.getone()
                await self._dispatch_message(message=message, handler=handler, consumer=consumer)
        except asyncio.CancelledError:
            raise
        except EventBusError:
            raise
        except Exception as exc:
            raise EventBusError(
                code="EVENT_CONSUME_FAILED",
                message="Kafka consume failed.",
                stage="subscribe",
                details={"error_type": exc.__class__.__name__},
                retryable=True,
            ) from exc

    async def close(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def _dispatch_message(self, *, message: Any, handler: EventBusHandler, consumer: Any) -> None:
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
        await self._topic_bootstrapper.ensure_topics(topics)
        await consumer.start()
        self._consumer = consumer
        return consumer
