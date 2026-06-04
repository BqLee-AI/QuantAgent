from __future__ import annotations

from collections.abc import AsyncIterator

from quantagent.agent.artifacts import ArtifactStore
from quantagent.agent.definitions.models import AgentDefinition, RuntimePolicy
from quantagent.agent.runtime.context import RunContextSection, RunContextSnapshot
from quantagent.agent.runtime.requests import AgentRunRequest
from quantagent.agent.streaming.adapter import EventSequencer
from quantagent.agent.streaming.events import AgentRunEvent, AgentRunEventType
from quantagent.agent.tools.profiles import ToolBinding, ToolProfile


def build_echo_run_request() -> AgentRunRequest:
    return AgentRunRequest(
        agent_run_id="run_test_echo",
        event_id="evt_test_echo",
        industry_id="industry_test",
        trace_id="trace_test_echo",
        agent_definition=AgentDefinition(
            agent_id="agent_test_echo",
            version="0.1.0",
            name="Echo Agent",
            system_prompt="Echo safely.",
            tool_ids=["quantagent.test.echo"],
        ),
        run_context=RunContextSnapshot(
            context_id="context_test_echo",
            sections=[RunContextSection(name="event", summary="A safe test event.")],
            safe_summary="Safe test run context.",
        ),
        tool_profile=ToolProfile(
            profile_id="tool_profile_test",
            tool_bindings=[ToolBinding(tool_id="quantagent.test.echo", name="echo", description="Echo text.")],
        ),
        runtime_policy=RuntimePolicy(model=None),
        input_message="Run echo test.",
    )


async def scripted_echo_runner(
    request: AgentRunRequest,
    sequencer: EventSequencer,
    artifact_store: ArtifactStore,
) -> AsyncIterator[AgentRunEvent]:
    yield sequencer.next(
        agent_run_id=request.agent_run_id,
        trace_id=request.trace_id,
        event_type=AgentRunEventType.TODO_UPDATED,
        payload={"todos": [{"content": "检查输入", "status": "completed"}]},
        safe_summary="Todo updated.",
    )
    artifact_ref = artifact_store.put(
        kind="runtime_output",
        producer_id=request.agent_definition.agent_id,
        payload={"summary": "echo result"},
        safe_summary="Echo runtime output artifact.",
    )
    yield sequencer.next(
        agent_run_id=request.agent_run_id,
        trace_id=request.trace_id,
        event_type=AgentRunEventType.ARTIFACT_CREATED,
        payload={"artifact_id": artifact_ref.artifact_id, "kind": artifact_ref.kind},
        safe_summary=artifact_ref.safe_summary,
    )
    yield sequencer.next(
        agent_run_id=request.agent_run_id,
        trace_id=request.trace_id,
        event_type=AgentRunEventType.RUN_OUTPUT,
        payload={"industry_analysis_artifact_id": artifact_ref.artifact_id},
        safe_summary="Echo run produced final output.",
    )
