from __future__ import annotations

import asyncio
import unittest

from quantagent.core.events import (
    EventBusError,
    EventEnvelope,
    KafkaEventBusConsumer,
    KafkaEventBusPublisher,
)
from quantagent.core.events.kafka import KafkaTopicBootstrapper


class FakeTopic:
    def __init__(self, *, name: str, num_partitions: int, replication_factor: int) -> None:
        self.name = name
        self.num_partitions = num_partitions
        self.replication_factor = replication_factor


class FakeAdmin:
    created_topic_names: list[str] = []
    start_count = 0
    close_count = 0

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    async def start(self) -> None:
        type(self).start_count += 1

    async def close(self) -> None:
        type(self).close_count += 1

    async def list_topics(self) -> set[str]:
        return set()

    async def create_topics(self, topics) -> None:
        type(self).created_topic_names.extend(topic.name for topic in topics)


class TopicAlreadyExistsError(Exception):
    pass


class AlreadyExistsAdmin(FakeAdmin):
    async def create_topics(self, topics) -> None:
        raise TopicAlreadyExistsError("topic already exists")


class PartiallyExistingAdmin(FakeAdmin):
    async def list_topics(self) -> set[str]:
        return {"source.event.captured"}


class FailingAdmin(FakeAdmin):
    async def create_topics(self, topics) -> None:
        raise RuntimeError("broker unavailable")


class FakeProducer:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.sent: list[tuple[str, bytes]] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def send_and_wait(self, topic: str, value: bytes) -> None:
        self.sent.append((topic, value))


class FakeMessage:
    def __init__(self, value: bytes, *, topic: str = "source.event.captured", partition: int = 0, offset: int = 0) -> None:
        self.value = value
        self.topic = topic
        self.partition = partition
        self.offset = offset


class FakeConsumer:
    def __init__(self, *topics, **kwargs) -> None:
        self.topics = topics
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.committed = False
        self.commit_count = 0
        self.committed_offsets: list[object] = []
        self.messages: list[FakeMessage] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def getone(self):
        if not self.messages:
            await asyncio.sleep(3600)
        return self.messages.pop(0)

    async def commit(self, offsets=None) -> None:
        self.committed = True
        self.commit_count += 1
        self.committed_offsets.append(offsets)


class SequencedConsumerFactory:
    def __init__(self, consumers: list[FakeConsumer]) -> None:
        self.consumers = consumers
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def __call__(self, *topics, **kwargs):
        self.calls.append((tuple(topics), dict(kwargs)))
        return self.consumers[len(self.calls) - 1]


class RecordingHandler:
    def __init__(self) -> None:
        self.envelopes: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.envelopes.append(envelope)


class DispatchingHandler:
    def __init__(self) -> None:
        self.seen: list[str] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope.topic)


class DelayedRecordingHandler:
    def __init__(self, delays: dict[str, float]) -> None:
        self._delays = delays
        self.seen: list[str] = []
        self.active = 0
        self.max_active = 0

    async def handle(self, envelope: EventEnvelope) -> None:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(self._delays.get(envelope.id, 0))
            self.seen.append(envelope.id)
        finally:
            self.active -= 1


class FailingOffsetHandler:
    def __init__(self) -> None:
        self.seen: list[str] = []
        self.cancelled: list[str] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope.id)
        if envelope.id == "evt-fails":
            raise RuntimeError("boom")
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            self.cancelled.append(envelope.id)
            raise


class KafkaEventBusTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeAdmin.created_topic_names = []
        FakeAdmin.start_count = 0
        FakeAdmin.close_count = 0

    async def test_kafka_publisher_uses_factory_and_topic_policy(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured",),
            admin_factory=FakeAdmin,
            topic_factory=FakeTopic,
        )
        publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
            topic_bootstrapper=bootstrapper,
        )
        envelope = EventEnvelope(
            id="evt-1",
            topic="source.event.captured",
            payload={"external_id": "news-1"},
            producer="source-ingestion",
            created_at="2026-05-30T00:00:00Z",
        )

        published = await publisher.publish(envelope)

        self.assertEqual(published.id, "evt-1")
        self.assertIn("source.event.captured", FakeAdmin.created_topic_names)
        self.assertTrue(publisher._producer.started)
        self.assertEqual(publisher._producer.sent[0][0], "source.event.captured")
        await publisher.close()
        self.assertTrue(publisher._producer is None)

    async def test_kafka_consumer_decodes_message_and_commits(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("event.routed",),
            admin_factory=FakeAdmin,
            topic_factory=FakeTopic,
        )
        codec_publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
            topic_bootstrapper=bootstrapper,
        )
        envelope = EventEnvelope(
            id="evt-1",
            topic="event.routed",
            payload={"event_id": "e-1"},
            producer="worker-router",
            created_at="2026-05-30T00:00:00Z",
        )
        encoded = codec_publisher._codec.encode(envelope)
        fake_consumer = FakeConsumer("event.routed", group_id="group-a")
        fake_consumer.messages.append(FakeMessage(encoded))
        factory = SequencedConsumerFactory([fake_consumer])
        consumer = KafkaEventBusConsumer(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            consumer_factory=factory,
            topic_bootstrapper=bootstrapper,
        )
        handler = RecordingHandler()

        await consumer.subscribe(
            topics=("event.routed",),
            group_id="group-a",
            handler=handler,
        )

        self.assertEqual(len(handler.envelopes), 1)
        self.assertEqual(handler.envelopes[0].payload["event_id"], "e-1")
        self.assertEqual(factory.calls[0][1]["session_timeout_ms"], 120000)
        self.assertEqual(factory.calls[0][1]["heartbeat_interval_ms"], 3000)
        self.assertEqual(factory.calls[0][1]["max_poll_interval_ms"], 900000)
        self.assertIn("event.routed", FakeAdmin.created_topic_names)
        self.assertTrue(fake_consumer.committed)
        await consumer.close()
        self.assertTrue(consumer._consumer is None)

    async def test_kafka_consumer_recreates_when_topic_set_changes(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured", "industry.analysis.requested"),
            admin_factory=FakeAdmin,
            topic_factory=FakeTopic,
        )
        codec_publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
            topic_bootstrapper=bootstrapper,
        )
        first_envelope = EventEnvelope(
            id="evt-1",
            topic="source.event.captured",
            payload={"event_id": "e-1"},
            producer="scheduler-loop",
            created_at="2026-05-30T00:00:00Z",
        )
        second_envelope = EventEnvelope(
            id="evt-2",
            topic="industry.analysis.requested",
            payload={"event_id": "e-2"},
            producer="worker-router",
            created_at="2026-05-30T00:00:00Z",
        )
        first_consumer = FakeConsumer("source.event.captured", group_id="group-a")
        second_consumer = FakeConsumer("source.event.captured", "industry.analysis.requested", group_id="group-a")
        first_consumer.messages.append(FakeMessage(codec_publisher._codec.encode(first_envelope)))
        second_consumer.messages.append(FakeMessage(codec_publisher._codec.encode(second_envelope)))
        factory = SequencedConsumerFactory([first_consumer, second_consumer])
        consumer = KafkaEventBusConsumer(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            consumer_factory=factory,
            topic_bootstrapper=bootstrapper,
        )
        handler = RecordingHandler()

        await consumer.subscribe(topics=("source.event.captured",), group_id="group-a", handler=handler)
        await consumer.subscribe(
            topics=("source.event.captured", "industry.analysis.requested"),
            group_id="group-a",
            handler=handler,
        )

        self.assertTrue(first_consumer.stopped)
        self.assertEqual(factory.calls[0][0], ("source.event.captured",))
        self.assertEqual(factory.calls[1][0], ("source.event.captured", "industry.analysis.requested"))
        self.assertEqual([item.topic for item in handler.envelopes], ["source.event.captured", "industry.analysis.requested"])
        await consumer.close()

    async def test_kafka_topic_bootstrap_is_idempotent(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured",),
            admin_factory=FakeAdmin,
            topic_factory=FakeTopic,
        )

        await bootstrapper.ensure_topics(("source.event.captured",))
        await bootstrapper.ensure_topics(("source.event.captured",))

        self.assertEqual(FakeAdmin.start_count, 1)
        self.assertEqual(FakeAdmin.close_count, 1)

    async def test_kafka_topic_bootstrap_ignores_existing_topics(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured",),
            admin_factory=AlreadyExistsAdmin,
            topic_factory=FakeTopic,
        )

        await bootstrapper.ensure_topics(("source.event.captured",))

    async def test_kafka_topic_bootstrap_creates_only_missing_topics(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured", "industry.analysis.requested"),
            admin_factory=PartiallyExistingAdmin,
            topic_factory=FakeTopic,
        )

        await bootstrapper.ensure_topics(("source.event.captured", "industry.analysis.requested"))

        self.assertNotIn("source.event.captured", FakeAdmin.created_topic_names)
        self.assertIn("industry.analysis.requested", FakeAdmin.created_topic_names)

    async def test_kafka_topic_bootstrap_wraps_admin_failure(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured",),
            admin_factory=FailingAdmin,
            topic_factory=FakeTopic,
        )

        with self.assertRaises(EventBusError) as raised:
            await bootstrapper.ensure_topics(("source.event.captured",))

        self.assertEqual(raised.exception.code, "EVENT_KAFKA_TOPIC_BOOTSTRAP_FAILED")

    async def test_kafka_backend_missing_dependency_raises_config_error(self) -> None:
        publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=None,
        )
        publisher._producer_factory = None

        with self.assertRaises(EventBusError) as raised:
            await publisher.publish(
                EventEnvelope(
                    id="evt-1",
                    topic="source.event.captured",
                    payload={},
                    producer="source-ingestion",
                    created_at="2026-05-30T00:00:00Z",
                )
            )
        self.assertEqual(raised.exception.code, "EVENT_KAFKA_DEPENDENCY_MISSING")

    async def test_kafka_consumer_reuses_single_subscription_for_multiple_topics(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured", "industry.analysis.requested"),
            admin_factory=FakeAdmin,
            topic_factory=FakeTopic,
        )
        codec_publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
            topic_bootstrapper=bootstrapper,
        )
        first = codec_publisher._codec.encode(
            EventEnvelope(
                id="evt-1",
                topic="source.event.captured",
                payload={"external_id": "news-1"},
                producer="scheduler",
                created_at="2026-05-30T00:00:00Z",
            )
        )
        second = codec_publisher._codec.encode(
            EventEnvelope(
                id="evt-2",
                topic="industry.analysis.requested",
                payload={"owner_id": "semiconductor"},
                producer="worker",
                created_at="2026-05-30T00:00:00Z",
            )
        )
        fake_consumer = FakeConsumer("source.event.captured", "industry.analysis.requested", group_id="group-a")
        fake_consumer.messages.extend(
            [
                FakeMessage(first, topic="source.event.captured", partition=0, offset=0),
                FakeMessage(second, topic="industry.analysis.requested", partition=0, offset=1),
            ]
        )
        consumer = KafkaEventBusConsumer(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            consumer_factory=lambda *topics, **kwargs: fake_consumer,
            topic_bootstrapper=bootstrapper,
        )
        handler = DispatchingHandler()

        await consumer.subscribe(
            topics=("source.event.captured", "industry.analysis.requested"),
            group_id="group-a",
            handler=handler,
        )
        await consumer.subscribe(
            topics=("source.event.captured", "industry.analysis.requested"),
            group_id="group-a",
            handler=handler,
        )

        self.assertEqual(handler.seen, ["source.event.captured", "industry.analysis.requested"])

    async def test_kafka_consumer_can_consume_forever_until_cancelled(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured", "industry.analysis.requested"),
            admin_factory=FakeAdmin,
            topic_factory=FakeTopic,
        )
        codec_publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
            topic_bootstrapper=bootstrapper,
        )
        first = codec_publisher._codec.encode(
            EventEnvelope(
                id="evt-1",
                topic="source.event.captured",
                payload={"external_id": "news-1"},
                producer="scheduler",
                created_at="2026-05-30T00:00:00Z",
            )
        )
        second = codec_publisher._codec.encode(
            EventEnvelope(
                id="evt-2",
                topic="industry.analysis.requested",
                payload={"owner_id": "semiconductor"},
                producer="worker",
                created_at="2026-05-30T00:00:00Z",
            )
        )
        fake_consumer = FakeConsumer("source.event.captured", "industry.analysis.requested", group_id="group-a")
        fake_consumer.messages.extend([FakeMessage(first), FakeMessage(second)])
        consumer = KafkaEventBusConsumer(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            consumer_factory=lambda *topics, **kwargs: fake_consumer,
            topic_bootstrapper=bootstrapper,
        )
        handler = DispatchingHandler()

        task = asyncio.create_task(
            consumer.consume_forever(
                topics=("source.event.captured", "industry.analysis.requested"),
                group_id="group-a",
                handler=handler,
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertEqual(handler.seen, ["source.event.captured", "industry.analysis.requested"])
        self.assertGreaterEqual(fake_consumer.commit_count, 1)
        self.assertIn(1, _committed_offset_values(fake_consumer.committed_offsets))

    async def test_kafka_consume_forever_processes_messages_concurrently_and_commits_contiguous_offsets(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured",),
            admin_factory=FakeAdmin,
            topic_factory=FakeTopic,
        )
        codec_publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
            topic_bootstrapper=bootstrapper,
        )
        first = codec_publisher._codec.encode(
            EventEnvelope(
                id="evt-slow",
                topic="source.event.captured",
                payload={"external_id": "news-1"},
                producer="scheduler",
                created_at="2026-05-30T00:00:00Z",
            )
        )
        second = codec_publisher._codec.encode(
            EventEnvelope(
                id="evt-fast",
                topic="source.event.captured",
                payload={"external_id": "news-2"},
                producer="scheduler",
                created_at="2026-05-30T00:00:00Z",
            )
        )
        fake_consumer = FakeConsumer("source.event.captured", group_id="group-a")
        fake_consumer.messages.extend(
            [
                FakeMessage(first, topic="source.event.captured", partition=0, offset=0),
                FakeMessage(second, topic="source.event.captured", partition=0, offset=1),
            ]
        )
        consumer = KafkaEventBusConsumer(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            consumer_factory=lambda *topics, **kwargs: fake_consumer,
            topic_bootstrapper=bootstrapper,
            consumer_concurrency=2,
        )
        handler = DelayedRecordingHandler({"evt-slow": 0.02, "evt-fast": 0.0})

        task = asyncio.create_task(
            consumer.consume_forever(
                topics=("source.event.captured",),
                group_id="group-a",
                handler=handler,
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertEqual(set(handler.seen), {"evt-slow", "evt-fast"})
        self.assertEqual(handler.max_active, 2)
        self.assertGreaterEqual(fake_consumer.commit_count, 1)
        self.assertIn(2, _committed_offset_values(fake_consumer.committed_offsets))

    async def test_kafka_consume_forever_cleans_in_flight_tasks_when_handler_fails(self) -> None:
        bootstrapper = KafkaTopicBootstrapper(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            topics=("source.event.captured",),
            admin_factory=FakeAdmin,
            topic_factory=FakeTopic,
        )
        codec_publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
            topic_bootstrapper=bootstrapper,
        )
        first = codec_publisher._codec.encode(
            EventEnvelope(
                id="evt-fails",
                topic="source.event.captured",
                payload={"external_id": "news-1"},
                producer="scheduler",
                created_at="2026-05-30T00:00:00Z",
            )
        )
        second = codec_publisher._codec.encode(
            EventEnvelope(
                id="evt-cancelled",
                topic="source.event.captured",
                payload={"external_id": "news-2"},
                producer="scheduler",
                created_at="2026-05-30T00:00:00Z",
            )
        )
        fake_consumer = FakeConsumer("source.event.captured", group_id="group-a")
        fake_consumer.messages.extend(
            [
                FakeMessage(first, topic="source.event.captured", partition=0, offset=0),
                FakeMessage(second, topic="source.event.captured", partition=0, offset=1),
            ]
        )
        consumer = KafkaEventBusConsumer(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            consumer_factory=lambda *topics, **kwargs: fake_consumer,
            topic_bootstrapper=bootstrapper,
            consumer_concurrency=2,
        )
        handler = FailingOffsetHandler()

        with self.assertRaises(EventBusError):
            await consumer.consume_forever(
                topics=("source.event.captured",),
                group_id="group-a",
                handler=handler,
            )

        self.assertIn("evt-fails", handler.seen)
        self.assertIn("evt-cancelled", handler.cancelled)
        self.assertNotIn(2, _committed_offset_values(fake_consumer.committed_offsets))


def _committed_offset_values(committed_offsets: list[object]) -> set[int]:
    values: set[int] = set()
    for offsets in committed_offsets:
        if not isinstance(offsets, dict):
            continue
        for value in offsets.values():
            if isinstance(value, int):
                values.add(value)
    return values


if __name__ == "__main__":
    unittest.main()
