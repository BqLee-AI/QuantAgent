from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar
from uuid import uuid4

from pydantic import BaseModel

from quantagent.agent.runtime.context import ToolRuntimeContext
from quantagent.agent.runtime.errors import ToolAdapterError
from quantagent.agent.streaming.adapter import EventSequencer
from quantagent.agent.streaming.events import AgentRunEvent, AgentRunEventType
from quantagent.agent.tools.profiles import ToolBinding

InputModelT = TypeVar("InputModelT", bound=BaseModel)


class PlatformToolCallable(Protocol[InputModelT]):
    def __call__(self, input_data: InputModelT, runtime_context: ToolRuntimeContext) -> Mapping[str, Any] | Awaitable[Mapping[str, Any]]: ...


@dataclass(frozen=True)
class PlatformTool(Generic[InputModelT]):
    binding: ToolBinding
    input_model: type[InputModelT]
    callable: PlatformToolCallable[InputModelT]


class ToolAdapter:
    def __init__(
        self,
        *,
        runtime_context: ToolRuntimeContext,
        sequencer: EventSequencer,
    ) -> None:
        self._runtime_context = runtime_context
        self._sequencer = sequencer

    async def invoke(self, tool: PlatformTool[InputModelT], raw_input: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[AgentRunEvent]]:
        input_data = tool.input_model.model_validate(dict(raw_input))
        invocation_id = f"tool_inv_{uuid4().hex}"
        events = [
            self._sequencer.next(
                agent_run_id=self._runtime_context.agent_run_id,
                trace_id=self._runtime_context.trace_id,
                event_type=AgentRunEventType.TOOL_STARTED,
                payload={"invocation_id": invocation_id, "tool_id": tool.binding.tool_id, "name": tool.binding.name},
                safe_summary=f"Tool {tool.binding.name} started.",
            )
        ]

        try:
            result = tool.callable(input_data, self._runtime_context)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # noqa: BLE001
            safe_error = _safe_error_summary(exc)
            events.append(
                self._sequencer.next(
                    agent_run_id=self._runtime_context.agent_run_id,
                    trace_id=self._runtime_context.trace_id,
                    event_type=AgentRunEventType.TOOL_FAILED,
                    payload={"invocation_id": invocation_id, "tool_id": tool.binding.tool_id, "error": safe_error},
                    safe_summary=f"Tool {tool.binding.name} failed.",
                )
            )
            raise ToolAdapterError(safe_error) from exc

        events.append(
            self._sequencer.next(
                agent_run_id=self._runtime_context.agent_run_id,
                trace_id=self._runtime_context.trace_id,
                event_type=AgentRunEventType.TOOL_COMPLETED,
                payload={"invocation_id": invocation_id, "tool_id": tool.binding.tool_id},
                safe_summary=f"Tool {tool.binding.name} completed.",
            )
        )
        return dict(result), events


def _safe_error_summary(exc: Exception) -> str:
    """错误摘要只保留类别，原始异常内容可能带 secret、路径、prompt 或 provider 请求。"""

    return f"{type(exc).__name__}: tool execution failed"
