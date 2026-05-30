from __future__ import annotations

import unittest

from quantagent.core.events import EventBusError, EventEnvelope, InMemoryEventBus


class RecordingHandler:
    def __init__(self) -> None:
        self.seen: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope)


class FailingHandler:
    async def handle(self, envelope: EventEnvelope) -> None:
        raise RuntimeError("dispatch failed")


class InMemoryEventBusTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_publish_dispatches_to_subscribed_handler(self) -> None:
        bus = InMemoryEventBus()
        handler = RecordingHandler()
        await bus.subscribe(
            topics=("source.event.captured",),
            group_id="group-a",
            handler=handler,
        )

        envelope = EventEnvelope(
            id="evt-1",
            topic="source.event.captured",
            payload={"external_id": "news-1"},
            producer="source-ingestion",
            created_at="2026-05-30T00:00:00Z",
        )
        published = await bus.publish(envelope)

        self.assertEqual(published.id, "evt-1")
        self.assertEqual(len(handler.seen), 1)
        self.assertEqual(handler.seen[0].payload["external_id"], "news-1")

    async def test_publish_rejects_unknown_topic(self) -> None:
        bus = InMemoryEventBus()
        envelope = EventEnvelope(
            id="evt-1",
            topic="unknown.topic",
            payload={},
            producer="source-ingestion",
            created_at="2026-05-30T00:00:00Z",
        )

        with self.assertRaises(EventBusError) as raised:
            await bus.publish(envelope)
        self.assertEqual(raised.exception.code, "EVENT_TOPIC_UNREGISTERED")

    async def test_subscribe_requires_group_id(self) -> None:
        bus = InMemoryEventBus()
        with self.assertRaises(EventBusError) as raised:
            await bus.subscribe(
                topics=("source.event.captured",),
                group_id="",
                handler=RecordingHandler(),
            )
        self.assertEqual(raised.exception.code, "EVENT_GROUP_ID_INVALID")

    async def test_handler_failure_becomes_structured_error(self) -> None:
        bus = InMemoryEventBus()
        await bus.subscribe(
            topics=("source.event.captured",),
            group_id="group-a",
            handler=FailingHandler(),
        )
        envelope = EventEnvelope(
            id="evt-1",
            topic="source.event.captured",
            payload={},
            producer="source-ingestion",
            created_at="2026-05-30T00:00:00Z",
        )

        with self.assertRaises(EventBusError) as raised:
            await bus.publish(envelope)
        self.assertEqual(raised.exception.code, "EVENT_HANDLER_FAILED")
        self.assertEqual(raised.exception.stage, "dispatch")


if __name__ == "__main__":
    unittest.main()
