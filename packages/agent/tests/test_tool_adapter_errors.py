from __future__ import annotations

import asyncio
from unittest import TestCase

from pydantic import BaseModel, ConfigDict, Field

from quantagent.agent.runtime.context import ToolRuntimeContext
from quantagent.agent.runtime.errors import ToolAdapterError
from quantagent.agent.streaming.adapter import EventSequencer
from quantagent.agent.tools.adapter import PlatformTool, ToolAdapter
from quantagent.agent.tools.profiles import ToolBinding


class FailingToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)


class ToolAdapterErrorTest(TestCase):
    def test_tool_error_summary_does_not_include_exception_text(self) -> None:
        async def _run() -> None:
            def _fail(input_data: FailingToolInput, runtime_context: ToolRuntimeContext) -> dict[str, str]:
                raise RuntimeError("secret-token=/tmp/private prompt raw")

            context = ToolRuntimeContext(
                agent_run_id="run_1",
                event_id="evt_1",
                industry_id="industry_test",
                agent_id="agent_test",
                trace_id="trace_1",
                tool_profile_id="profile_1",
            )
            adapter = ToolAdapter(runtime_context=context, sequencer=EventSequencer())
            tool = PlatformTool(
                binding=ToolBinding(tool_id="quantagent.test.fail", name="fail", description="Fail safely."),
                input_model=FailingToolInput,
                callable=_fail,
            )

            with self.assertRaises(ToolAdapterError) as caught:
                await adapter.invoke(tool, {"text": "hello"})

            self.assertEqual(str(caught.exception), "RuntimeError: tool execution failed")

        asyncio.run(_run())
