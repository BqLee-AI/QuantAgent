from __future__ import annotations

import unittest

from quantagent.core.events import (
    EventBusError,
    EventEnvelope,
    KafkaEventBusConsumer,
    KafkaEventBusPublisher,
)


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
    def __init__(self, value: bytes) -> None:
        self.value = value


class FakeConsumer:
    def __init__(self, *topics, **kwargs) -> None:
        self.topics = topics
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.committed = False
        self.messages: list[FakeMessage] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def getone(self):
        if not self.messages:
            raise TimeoutError("no messages")
        return self.messages.pop(0)

    async def commit(self) -> None:
        self.committed = True


class RecordingHandler:
    def __init__(self) -> None:
        self.envelopes: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.envelopes.append(envelope)


class KafkaEventBusTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_kafka_publisher_uses_factory_and_topic_policy(self) -> None:
        publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
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
        self.assertTrue(publisher._producer.started)
        self.assertEqual(publisher._producer.sent[0][0], "source.event.captured")
        await publisher.close()
        self.assertTrue(publisher._producer is None)

    async def test_kafka_consumer_decodes_message_and_commits(self) -> None:
        codec_publisher = KafkaEventBusPublisher(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            producer_factory=FakeProducer,
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
        consumer = KafkaEventBusConsumer(
            bootstrap_servers="localhost:9092",
            client_id="quantagent-test",
            consumer_factory=lambda *topics, **kwargs: fake_consumer,
        )
        handler = RecordingHandler()

        await consumer.subscribe(
            topics=("event.routed",),
            group_id="group-a",
            handler=handler,
        )

        self.assertEqual(len(handler.envelopes), 1)
        self.assertEqual(handler.envelopes[0].payload["event_id"], "e-1")
        self.assertTrue(fake_consumer.committed)
        await consumer.close()
        self.assertTrue(consumer._consumer is None)

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


if __name__ == "__main__":
    unittest.main()
