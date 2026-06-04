from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from quantagent.agent.artifacts import ArtifactStore, InMemoryArtifactStore
from quantagent.agent.runtime.context import ToolRuntimeContext
from quantagent.agent.runtime.errors import AgentRuntimeError, DeepAgentsUnavailableError
from quantagent.agent.runtime.requests import AgentRunRequest, AgentRunResult
from quantagent.agent.streaming.adapter import EventSequencer, chunk_to_safe_summary
from quantagent.agent.streaming.events import AgentRunEvent, AgentRunEventType
from quantagent.agent.tools.adapter import PlatformTool


class DeepAgentGraph(Protocol):
    def invoke(self, input_data: Mapping[str, Any], config: Mapping[str, Any] | None = None) -> Any: ...

    def stream(self, input_data: Mapping[str, Any], config: Mapping[str, Any] | None = None) -> Iterable[Any]: ...


DeepAgentFactory = Callable[[AgentRunRequest, Sequence[Any]], DeepAgentGraph]
ScriptedRunner = Callable[[AgentRunRequest, EventSequencer, ArtifactStore], AsyncIterator[AgentRunEvent]]


@dataclass(frozen=True)
class AgentRuntimeDependencies:
    tools: list[PlatformTool[Any]]
    artifact_store: ArtifactStore
    deep_agent_factory: DeepAgentFactory | None = None
    scripted_runner: ScriptedRunner | None = None


class AgentRuntime:
    def __init__(
        self,
        *,
        tools: list[PlatformTool[Any]] | None = None,
        artifact_store: ArtifactStore | None = None,
        deep_agent_factory: DeepAgentFactory | None = None,
        scripted_runner: ScriptedRunner | None = None,
    ) -> None:
        self._deps = AgentRuntimeDependencies(
            tools=tools or [],
            artifact_store=artifact_store or InMemoryArtifactStore(),
            deep_agent_factory=deep_agent_factory,
            scripted_runner=scripted_runner,
        )

    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        events: list[AgentRunEvent] = []
        async for event in self.run_stream(request):
            events.append(event)
        status = "completed" if events and events[-1].type == AgentRunEventType.RUN_COMPLETED else "failed"
        output = next((event.safe_summary or "" for event in reversed(events) if event.type == AgentRunEventType.RUN_OUTPUT), "")
        return AgentRunResult(
            agent_run_id=request.agent_run_id,
            status=status,
            output_summary=output,
            artifact_refs=self._deps.artifact_store.list_for_run(),
            events=events,
        )

    async def run_stream(self, request: AgentRunRequest) -> AsyncIterator[AgentRunEvent]:
        sequencer = EventSequencer()
        yield sequencer.next(
            agent_run_id=request.agent_run_id,
            trace_id=request.trace_id,
            event_type=AgentRunEventType.RUN_STARTED,
            payload={
                "event_id": request.event_id,
                "industry_id": request.industry_id,
                "agent_id": request.agent_definition.agent_id,
                "agent_version": request.agent_definition.version,
            },
            safe_summary=f"AgentRun {request.agent_run_id} started.",
        )

        try:
            if self._deps.scripted_runner is not None:
                async for event in self._deps.scripted_runner(request, sequencer, self._deps.artifact_store):
                    yield event
            else:
                async for event in self._run_deep_agent(request, sequencer):
                    yield event

            yield sequencer.next(
                agent_run_id=request.agent_run_id,
                trace_id=request.trace_id,
                event_type=AgentRunEventType.RUN_COMPLETED,
                payload={"artifact_ids": [ref.artifact_id for ref in self._deps.artifact_store.list_for_run()]},
                safe_summary=f"AgentRun {request.agent_run_id} completed.",
            )
        except Exception as exc:  # noqa: BLE001
            safe_error = _safe_runtime_error_summary(exc)
            yield sequencer.next(
                agent_run_id=request.agent_run_id,
                trace_id=request.trace_id,
                event_type=AgentRunEventType.RUN_FAILED,
                payload={"error": safe_error},
                safe_summary=f"AgentRun {request.agent_run_id} failed.",
            )

    def tool_runtime_context(self, request: AgentRunRequest, *, subagent_id: str | None = None) -> ToolRuntimeContext:
        return ToolRuntimeContext(
            agent_run_id=request.agent_run_id,
            event_id=request.event_id,
            industry_id=request.industry_id,
            agent_id=request.agent_definition.agent_id,
            subagent_id=subagent_id,
            trace_id=request.trace_id,
            tool_profile_id=request.tool_profile.profile_id,
        )

    async def _run_deep_agent(self, request: AgentRunRequest, sequencer: EventSequencer) -> AsyncIterator[AgentRunEvent]:
        factory = self._deps.deep_agent_factory or self._default_deep_agent_factory
        tool_events: list[AgentRunEvent] = []
        graph = factory(request, self._build_langchain_tools(request, sequencer, tool_events))
        config = {"configurable": {"thread_id": request.agent_run_id}}
        input_data = {"messages": [{"role": "user", "content": request.input_message}]}

        stream = graph.stream(input_data, config=config)
        last_summary = ""
        for chunk in stream:
            while tool_events:
                yield tool_events.pop(0)
            summary = chunk_to_safe_summary(chunk)
            last_summary = summary
            yield sequencer.next(
                agent_run_id=request.agent_run_id,
                trace_id=request.trace_id,
                event_type=AgentRunEventType.MODEL_DELTA,
                payload={"summary": summary},
                safe_summary=summary,
            )

        while tool_events:
            yield tool_events.pop(0)
        yield sequencer.next(
            agent_run_id=request.agent_run_id,
            trace_id=request.trace_id,
            event_type=AgentRunEventType.RUN_OUTPUT,
            payload={"source": "stream"},
            safe_summary=last_summary or "DeepAgents stream completed.",
        )

    @staticmethod
    def _default_deep_agent_factory(request: AgentRunRequest, tools: Sequence[Any]) -> DeepAgentGraph:
        try:
            from deepagents import create_deep_agent
        except Exception as exc:  # noqa: BLE001
            raise DeepAgentsUnavailableError("deepagents dependency is unavailable") from exc

        if request.runtime_policy.model is None:
            raise DeepAgentsUnavailableError("runtime_policy.model is required when no scripted_runner is provided")

        subagents = [
            {
                "name": subagent.name,
                "description": subagent.description,
                "system_prompt": subagent.system_prompt,
                "tools": [],
                "skills": subagent.skill_paths or None,
            }
            for subagent in request.agent_definition.subagents
        ]

        required_interrupts = {
            binding.name: True
            for binding in request.tool_profile.tool_bindings
            if binding.requires_interrupt and binding.tool_id in request.agent_definition.tool_ids
        }
        interrupt_on = {**required_interrupts, **request.runtime_policy.interrupt_on}

        checkpointer = None
        if interrupt_on:
            try:
                from langgraph.checkpoint.memory import MemorySaver
            except Exception as exc:  # noqa: BLE001
                raise DeepAgentsUnavailableError("langgraph MemorySaver is unavailable for interrupt_on") from exc
            checkpointer = MemorySaver()

        # DeepAgents 负责 planner、tool loop、task/subagent 和 backend；这里仅做平台边界配置。
        return create_deep_agent(
            model=request.runtime_policy.model,
            tools=list(tools),
            system_prompt=request.agent_definition.system_prompt,
            subagents=subagents or None,
            skills=request.agent_definition.skill_paths or None,
            interrupt_on=interrupt_on or None,
            checkpointer=checkpointer,
        )

    def _build_langchain_tools(
        self,
        request: AgentRunRequest,
        sequencer: EventSequencer,
        event_buffer: list[AgentRunEvent] | None = None,
    ) -> list[Any]:
        if not self._deps.tools:
            return []

        try:
            from langchain_core.tools import StructuredTool
        except Exception as exc:  # noqa: BLE001
            raise AgentRuntimeError("langchain_core StructuredTool is unavailable") from exc

        runtime_context = self.tool_runtime_context(request)
        adapter = self._tool_adapter(runtime_context=runtime_context, sequencer=sequencer)
        allowed_bindings = {binding.tool_id: binding for binding in request.tool_profile.tool_bindings}
        requested_tool_ids = set(request.agent_definition.tool_ids)
        injected_tools = {tool.binding.tool_id: tool for tool in self._deps.tools}

        unauthorized = requested_tool_ids - set(allowed_bindings)
        missing = requested_tool_ids - set(injected_tools)
        if unauthorized:
            raise AgentRuntimeError(f"unauthorized tools requested: {', '.join(sorted(unauthorized))}")
        if missing:
            raise AgentRuntimeError(f"requested tools unavailable: {', '.join(sorted(missing))}")

        wrapped_tools = []

        for tool_id in request.agent_definition.tool_ids:
            platform_tool = injected_tools[tool_id]
            async def _call_tool(_platform_tool: PlatformTool[Any] = platform_tool, **kwargs: Any) -> Mapping[str, Any]:
                result, events = await adapter.invoke(_platform_tool, kwargs)
                if event_buffer is not None:
                    event_buffer.extend(events)
                return result

            wrapped_tools.append(
                StructuredTool.from_function(
                    coroutine=_call_tool,
                    name=platform_tool.binding.name,
                    description=platform_tool.binding.description,
                    args_schema=platform_tool.input_model,
                )
            )

        return wrapped_tools

    @staticmethod
    def _tool_adapter(*, runtime_context: ToolRuntimeContext, sequencer: EventSequencer) -> Any:
        from quantagent.agent.tools.adapter import ToolAdapter

        return ToolAdapter(runtime_context=runtime_context, sequencer=sequencer)


def _safe_runtime_error_summary(exc: Exception) -> str:
    """Runtime 失败事件不能包含 provider/prompt/secret 原文，只暴露错误类别。"""

    return f"{type(exc).__name__}: agent runtime failed"
