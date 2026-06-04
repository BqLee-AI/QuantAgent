from __future__ import annotations

from unittest import TestCase

from quantagent.agent.streaming.adapter import chunk_to_safe_summary


class StreamingAdapterTest(TestCase):
    def test_chunk_to_safe_summary_does_not_return_raw_content(self) -> None:
        summary = chunk_to_safe_summary({"content": "secret prompt raw output", "other": 1})

        self.assertEqual(summary, "deepagents mapping chunk keys=[content, other]")

    def test_chunk_to_safe_summary_does_not_return_raw_string(self) -> None:
        summary = chunk_to_safe_summary("secret prompt raw output")

        self.assertEqual(summary, "deepagents string chunk length=24")
