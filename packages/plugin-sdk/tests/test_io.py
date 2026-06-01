from __future__ import annotations

import unittest

from quantagent.plugin_sdk import (
    DTO_VALIDATION_ERROR_CODE,
    NotificationSendInput,
    NotificationSendResult,
    PluginRuntimeError,
    SourceFetchInput,
    SourceFetchResult,
    SourceItemDraft,
    freeze_json_mapping,
)


class PluginSdkIoDtoTestCase(unittest.TestCase):
    def test_source_fetch_input_can_roundtrip_mapping_and_keeps_metadata_read_only(self) -> None:
        payload = {
            "query": "oil",
            "limit": 10,
            "cursor": "cursor-1",
            "metadata": {"source": "rss", "flags": ["fresh", True], "page": {"index": 1}},
        }

        dto = SourceFetchInput.from_mapping(payload)

        self.assertEqual(dto.query, "oil")
        self.assertEqual(dto.limit, 10)
        self.assertEqual(dto.cursor, "cursor-1")
        self.assertEqual(dto.to_mapping(), payload)
        with self.assertRaises(TypeError):
            dto.metadata["new"] = "value"  # type: ignore[index]

    def test_source_fetch_result_serializes_multiple_items(self) -> None:
        first = SourceItemDraft(
            external_id="a-1",
            title="Alpha",
            raw_payload={"score": 1, "tags": ["rss"]},
            metadata={"rank": 1},
        )
        second = SourceItemDraft(
            external_id="b-2",
            url="https://example.com/b-2",
            content="body",
            published_at="2026-05-27T00:00:00Z",
            metadata={"rank": 2},
        )

        result = SourceFetchResult(
            items=[first, second],
            next_cursor="cursor-2",
            metadata={"count": 2},
        )

        self.assertEqual(len(result.items), 2)
        self.assertEqual(
            result.to_mapping(),
            {
                "items": [
                    {
                        "external_id": "a-1",
                        "url": None,
                        "title": "Alpha",
                        "content": None,
                        "author": None,
                        "published_at": None,
                        "captured_at": None,
                        "raw_payload": {"score": 1, "tags": ["rss"]},
                        "metadata": {"rank": 1},
                    },
                    {
                        "external_id": "b-2",
                        "url": "https://example.com/b-2",
                        "title": None,
                        "content": "body",
                        "author": None,
                        "published_at": "2026-05-27T00:00:00Z",
                        "captured_at": None,
                        "raw_payload": {},
                        "metadata": {"rank": 2},
                    },
                ],
                "next_cursor": "cursor-2",
                "metadata": {"count": 2},
            },
        )

    def test_source_fetch_result_can_roundtrip_empty_result(self) -> None:
        payload = {"items": [], "next_cursor": None, "metadata": {"empty": True}}

        result = SourceFetchResult.from_mapping(payload)

        self.assertEqual(result.items, ())
        self.assertEqual(result.to_mapping(), payload)

    def test_notification_send_input_and_rejected_result_roundtrip(self) -> None:
        request = NotificationSendInput.from_mapping(
            {
                "channel": "discord",
                "text": "rate limited",
                "severity": "warning",
                "recipient": "ops-room",
                "metadata": {"attempt": 3},
            }
        )
        result = NotificationSendResult.from_mapping(
            {
                "accepted": False,
                "provider_message_id": None,
                "retryable": True,
                "metadata": {"provider_status": 429},
            }
        )

        self.assertEqual(
            request.to_mapping(),
            {
                "channel": "discord",
                "text": "rate limited",
                "severity": "warning",
                "recipient": "ops-room",
                "metadata": {"attempt": 3},
            },
        )
        self.assertEqual(
            result.to_mapping(),
            {
                "accepted": False,
                "provider_message_id": None,
                "retryable": True,
                "metadata": {"provider_status": 429},
            },
        )
        with self.assertRaises(TypeError):
            result.metadata["another"] = 1  # type: ignore[index]

    def test_json_safe_validation_rejects_unserializable_values(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            SourceItemDraft(raw_payload={"bad": object()})

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.stage, "invoke")
        self.assertEqual(raised.exception.details["value_type"], "object")

    def test_json_safe_validation_rejects_non_finite_numbers(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            SourceFetchInput(metadata={"score": float("nan")})

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.details["value_type"], "float")

    def test_source_fetch_result_requires_items_in_mapping(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            SourceFetchResult.from_mapping({"metadata": {}})

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.details["field"], "items")

    def test_from_mapping_uses_structured_error_for_invalid_payload(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            NotificationSendInput.from_mapping(
                {
                    "channel": "discord",
                    "text": 123,
                    "metadata": {"path": "/home/xxs/private"},
                },
                stage="config",
            )

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.stage, "config")
        self.assertEqual(raised.exception.details["field"], "text")

    def test_freeze_json_mapping_rejects_non_string_keys(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            freeze_json_mapping({1: "invalid"})

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.details["key_type"], "int")


if __name__ == "__main__":
    unittest.main()
