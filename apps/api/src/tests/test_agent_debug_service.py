from __future__ import annotations

import asyncio
from unittest import TestCase
from unittest.mock import patch

from quantagent.api.schemas.agent_debug import AgentDebugRunRequest
from quantagent.api.services.agent_debug import AgentDebugRunService


class AgentDebugRunServiceTest(TestCase):
    def test_failure_frame_is_sanitized_after_stream_start(self) -> None:
        class BadRuntime:
            async def run_stream(self, request):
                raise RuntimeError("sk-secret prompt raw /tmp/private")
                yield  # pragma: no cover

        async def _run() -> str:
            service = AgentDebugRunService()
            with patch("quantagent.api.services.agent_debug.AgentRuntime", return_value=BadRuntime()):
                frames = [
                    frame
                    async for frame in service.stream_fixture_run(
                        fixture_id="semiconductor-nvda-earnings",
                        request=AgentDebugRunRequest(scenario="primary"),
                    )
                ]
            return "".join(frames)

        body = asyncio.run(_run())

        self.assertIn("event: run.failed", body)
        self.assertIn("RuntimeError: debug agent stream failed", body)
        self.assertNotIn("sk-secret", body)
        self.assertNotIn("prompt raw", body)
        self.assertNotIn("/tmp/private", body)
