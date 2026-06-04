from __future__ import annotations

import asyncio
from unittest import TestCase

from quantagent.agent.runtime import AgentRuntime
from quantagent.agent.streaming.events import AgentRunEventType
from quantagent.agent.testing import build_echo_run_request, scripted_echo_runner


class RuntimeStreamTest(TestCase):
    def test_runtime_scripted_stream_emits_lifecycle_and_artifact_events(self) -> None:
        async def _run() -> None:
            runtime = AgentRuntime(scripted_runner=scripted_echo_runner)

            events = [event async for event in runtime.run_stream(build_echo_run_request())]

            self.assertEqual(
                [event.type for event in events],
                [
                    AgentRunEventType.RUN_STARTED,
                    AgentRunEventType.TODO_UPDATED,
                    AgentRunEventType.ARTIFACT_CREATED,
                    AgentRunEventType.RUN_OUTPUT,
                    AgentRunEventType.RUN_COMPLETED,
                ],
            )
            self.assertEqual(events[0].seq, 1)
            self.assertTrue(events[-1].payload["artifact_ids"])

        asyncio.run(_run())

    def test_runtime_run_collects_stream_result(self) -> None:
        async def _run() -> None:
            runtime = AgentRuntime(scripted_runner=scripted_echo_runner)

            result = await runtime.run(build_echo_run_request())

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.output_summary, "Echo run produced final output.")
            self.assertTrue(result.artifact_refs)

        asyncio.run(_run())
