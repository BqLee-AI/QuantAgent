from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from quantagent.agent.runtime.context import ToolRuntimeContext
from quantagent.agent.tools.adapter import PlatformTool
from quantagent.agent.tools.profiles import ToolBinding


class EchoToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, description="Text to echo.")


def build_echo_platform_tool() -> PlatformTool[EchoToolInput]:
    def _echo(input_data: EchoToolInput, runtime_context: ToolRuntimeContext) -> dict[str, str]:
        return {
            "echo": input_data.text,
            "agent_run_id": runtime_context.agent_run_id,
            "event_id": runtime_context.event_id,
        }

    return PlatformTool(
        binding=ToolBinding(tool_id="quantagent.test.echo", name="echo", description="Echo text for runtime tests."),
        input_model=EchoToolInput,
        callable=_echo,
    )
