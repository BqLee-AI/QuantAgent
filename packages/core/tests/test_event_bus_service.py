from __future__ import annotations

import unittest

from quantagent.core.events import InMemoryEventBus, SourceEventPublisher
from quantagent.plugin_sdk import SourceFetchResult, SourceItemDraft


class RecordingHandler:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def handle(self, envelope) -> None:
        self.payloads.append(dict(envelope.payload))


class SourceEventPublisherTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_publish_source_fetch_result_constructs_captured_event(self) -> None:
        bus = InMemoryEventBus()
        handler = RecordingHandler()
        await bus.subscribe(
            topics=("source.event.captured",),
            group_id="group-a",
            handler=handler,
        )
        publisher = SourceEventPublisher(bus, id_factory=lambda: "evt-fixed")
        result = SourceFetchResult(
            items=(
                SourceItemDraft(
                    external_id="news-1",
                    title="Oil update",
                    metadata={"source": "placeholder"},
                ),
            ),
            metadata={"source": "placeholder"},
        )

        envelope = await publisher.publish_source_fetch_result(
            result,
            producer="plugin-scheduling",
            request_id="req-1",
            plugin_id="quantagent.official.source.placeholder",
        )

        self.assertEqual(envelope.id, "evt-fixed")
        self.assertEqual(envelope.topic, "source.event.captured")
        self.assertEqual(envelope.headers["request_id"], "req-1")
        self.assertEqual(envelope.payload["plugin_id"], "quantagent.official.source.placeholder")
        self.assertEqual(envelope.payload["items"][0]["external_id"], "news-1")
        self.assertEqual(len(handler.payloads), 1)


if __name__ == "__main__":
    unittest.main()
