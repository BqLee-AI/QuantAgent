from __future__ import annotations

from unittest import TestCase

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from quantagent.agent.definitions.models import RuntimePolicy
from quantagent.agent.runtime import AgentRuntime
from quantagent.agent.runtime.errors import AgentRuntimeError
from quantagent.agent.streaming.adapter import EventSequencer
from quantagent.agent.testing import build_echo_platform_tool, build_echo_run_request


class DeepAgentsFactoryTest(TestCase):
    def test_default_factory_builds_graph_with_fake_chat_model(self) -> None:
        request = build_echo_run_request().model_copy(
            update={
                "runtime_policy": RuntimePolicy(model=FakeListChatModel(responses=["done"])),
            }
        )

        graph = AgentRuntime._default_deep_agent_factory(request, [])

        self.assertTrue(hasattr(graph, "invoke"))
        self.assertTrue(hasattr(graph, "stream"))

    def test_runtime_builds_langchain_tools_from_platform_tools(self) -> None:
        runtime = AgentRuntime(tools=[build_echo_platform_tool()])
        request = build_echo_run_request()

        tools = runtime._build_langchain_tools(request, EventSequencer())

        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "echo")

    def test_runtime_rejects_unprofiled_tool_request(self) -> None:
        runtime = AgentRuntime(tools=[build_echo_platform_tool()])
        request = build_echo_run_request().model_copy(
            update={
                "tool_profile": build_echo_run_request().tool_profile.model_copy(update={"tool_bindings": []}),
            }
        )

        with self.assertRaises(AgentRuntimeError):
            runtime._build_langchain_tools(request, EventSequencer())
