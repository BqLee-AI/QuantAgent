from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field
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
    from aiokafka.structs import TopicPartition
except ImportError:  # pragma: no cover - depends on local optional dependency.
    AIOKafkaAdminClient = None
    AIOKafkaConsumer = None
    AIOKafkaProducer = None
    NewTopic = None
    TopicAlreadyExistsError = None
    TopicPartition = None


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


@dataclass(frozen=True)
class _HandledMessage:
    message: Any


@dataclass
class _PartitionState:
    next_commit_offset: int | None = None
    completed_offsets: set[int] = field(default_factory=set)


class _PartitionCommitTracker:
    def __init__(self) -> None:
        self._states: dict[object, _PartitionState] = {}

    def mark_seen(self, message: Any) -> None:
        key = _message_partition_key(message)
        if key is None:
            return
        offset = _message_offset(message)
        if offset is None:
            return
        state = self._states.setdefault(key, _PartitionState(next_commit_offset=offset))
        if state.next_commit_offset is None or offset < state.next_commit_offset:
            state.next_commit_offset = offset

    def mark_completed(self, message: Any) -> None:
        key = _message_partition_key(message)
        offset = _message_offset(message)
        if key is None or offset is None:
            return
        state = self._states.setdefault(key, _PartitionState(next_commit_offset=offset))
        state.completed_offsets.add(offset)

    async def commit_ready(self, consumer: Any) -> None:
        offsets: dict[object, int] = {}
        for key, state in self._states.items():
            if state.next_commit_offset is None:
                continue
            next_offset = state.next_commit_offset
            while next_offset in state.completed_offsets:
                state.completed_offsets.remove(next_offset)
                next_offset += 1
            if next_offset != state.next_commit_offset:
                state.next_commit_offset = next_offset
                offsets[_to_topic_partition(key)] = next_offset
        if offsets:
            # 并发处理会乱序完成；只提交每个 partition 上连续完成的 offset，避免跳过失败消息。
            await consumer.commit(offsets=offsets)


def _message_partition_key(message: Any) -> tuple[str, int] | None:
    topic = getattr(message, "topic", None)
    partition = getattr(message, "partition", None)
    if isinstance(topic, str) and isinstance(partition, int):
        return topic, partition
    return None


def _message_offset(message: Any) -> int | None:
    offset = getattr(message, "offset", None)
    return offset if isinstance(offset, int) else None


def _to_topic_partition(key: tuple[str, int]) -> object:
    if TopicPartition is not None:
        return TopicPartition(key[0], key[1])
    return key


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
        session_timeout_ms: int = 120000,
        heartbeat_interval_ms: int = 3000,
        max_poll_interval_ms: int = 900000,
        consumer_concurrency: int = 10,
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
        self._consumer_topics: tuple[str, ...] | None = None
        self._consumer_group_id: str | None = None
        self._session_timeout_ms = session_timeout_ms
        self._heartbeat_interval_ms = heartbeat_interval_ms
        self._max_poll_interval_ms = max_poll_interval_ms
        self._consumer_concurrency = max(1, consumer_concurrency)

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

        await self._dispatch_message_and_commit(message=message, handler=handler, consumer=consumer)

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
                await self._consume_concurrently(consumer=consumer, handler=handler)
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
            self._consumer_topics = None
            self._consumer_group_id = None

    async def _dispatch_message(self, *, message: Any, handler: EventBusHandler) -> None:
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

    async def _dispatch_message_and_commit(self, *, message: Any, handler: EventBusHandler, consumer: Any) -> None:
        await self._dispatch_message(message=message, handler=handler)
        await consumer.commit()

    async def _consume_concurrently(self, *, consumer: Any, handler: EventBusHandler) -> None:
        tracker = _PartitionCommitTracker()
        in_flight: set[asyncio.Task[_HandledMessage]] = set()
        try:
            while True:
                while len(in_flight) < self._consumer_concurrency:
                    try:
                        # 如果已有消息正在处理，不为了填满并发槽位无限阻塞；先让已完成任务提交 offset。
                        timeout = 0.01 if in_flight else None
                        message = await asyncio.wait_for(consumer.getone(), timeout=timeout)
                    except asyncio.TimeoutError:
                        break
                    tracker.mark_seen(message)
                    in_flight.add(asyncio.create_task(self._handle_message_task(message=message, handler=handler)))

                if not in_flight:
                    continue
                done, in_flight = await asyncio.wait(in_flight, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    handled = task.result()
                    tracker.mark_completed(handled.message)
                await tracker.commit_ready(consumer)
        except asyncio.CancelledError:
            for task in in_flight:
                task.cancel()
            if in_flight:
                await asyncio.gather(*in_flight, return_exceptions=True)
            raise
        except Exception:
            for task in in_flight:
                task.cancel()
            if in_flight:
                await asyncio.gather(*in_flight, return_exceptions=True)
            raise

    async def _handle_message_task(self, *, message: Any, handler: EventBusHandler) -> "_HandledMessage":
        await self._dispatch_message(message=message, handler=handler)
        return _HandledMessage(message=message)

    async def _get_consumer(self, topics: tuple[str, ...], *, group_id: str) -> Any:
        if self._consumer is not None:
            if self._consumer_topics == topics and self._consumer_group_id == group_id:
                return self._consumer
            # aiokafka 的构造期 topic 是订阅真源；复用旧实例会导致新增 topic 永远不被消费。
            await self.close()
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
            session_timeout_ms=self._session_timeout_ms,
            heartbeat_interval_ms=self._heartbeat_interval_ms,
            max_poll_interval_ms=self._max_poll_interval_ms,
        )
        await self._topic_bootstrapper.ensure_topics(topics)
        await consumer.start()
        self._consumer = consumer
        self._consumer_topics = topics
        self._consumer_group_id = group_id
        return consumer
