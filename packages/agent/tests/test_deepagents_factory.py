from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from quantagent.agent.definitions.models import AgentDefinition, RuntimePolicy, SubAgentDefinition
from quantagent.agent.runtime import AgentRuntime
from quantagent.agent.runtime.errors import AgentRuntimeError
from quantagent.agent.streaming.adapter import EventSequencer
from quantagent.agent.testing import build_echo_platform_tool, build_echo_run_request
from quantagent.agent.tools.profiles import ToolBinding, ToolProfile


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

    def test_default_factory_passes_minimal_tools_to_custom_subagents(self) -> None:
        class DummyGraph:
            def invoke(self, input_data, config=None):
                return {}

            def stream(self, input_data, config=None):
                return iter(())

        class NamedTool:
            def __init__(self, name: str) -> None:
                self.name = name

        request = build_echo_run_request().model_copy(
            update={
                "agent_definition": AgentDefinition(
                    agent_id="agent_semiconductor",
                    version="0.1.0",
                    name="Semiconductor MainAgent",
                    system_prompt="Use DeepAgents planning.",
                    tool_ids=[
                        "quantagent.core.tool.get_run_context",
                        "quantagent.core.tool.get_account_context",
                        "quantagent.core.tool.build_action_plan",
                        "quantagent.core.tool.submit_action_plan",
                    ],
                    subagents=[
                        SubAgentDefinition(
                            subagent_id="subagent_research",
                            name="evidence_research_analyst",
                            description="Research public evidence.",
                            system_prompt="Search evidence only.",
                            tool_ids=[
                                "quantagent.core.tool.get_run_context",
                                "quantagent.official.source.tavily.search_web",
                            ],
                        )
                    ],
                ),
                "tool_profile": ToolProfile(
                    profile_id="tool_profile_semiconductor",
                    tool_bindings=[
                        ToolBinding(
                            tool_id="quantagent.core.tool.get_run_context",
                            name="get_run_context",
                            description="Read run context.",
                        ),
                        ToolBinding(
                            tool_id="quantagent.official.source.tavily.search_web",
                            name="search_web",
                            description="Search web.",
                        ),
                        ToolBinding(
                            tool_id="quantagent.core.tool.get_account_context",
                            name="get_account_context",
                            description="Read account context.",
                        ),
                        ToolBinding(
                            tool_id="quantagent.core.tool.build_action_plan",
                            name="build_action_plan",
                            description="Build action plan.",
                            risk_level="high",
                        ),
                        ToolBinding(
                            tool_id="quantagent.core.tool.submit_action_plan",
                            name="submit_action_plan",
                            description="Submit action plan.",
                            risk_level="critical",
                            requires_interrupt=True,
                        ),
                    ],
                ),
                "runtime_policy": RuntimePolicy(model=FakeListChatModel(responses=["done"])),
            }
        )
        tools = [
            NamedTool("get_run_context"),
            NamedTool("search_web"),
            NamedTool("get_account_context"),
            NamedTool("build_action_plan"),
            NamedTool("submit_action_plan"),
        ]

        with patch("deepagents.create_deep_agent", return_value=DummyGraph()) as create_deep_agent:
            AgentRuntime._default_deep_agent_factory(request, tools)

        kwargs = create_deep_agent.call_args.kwargs
        self.assertEqual([tool.name for tool in kwargs["tools"]], ["get_run_context", "get_account_context", "build_action_plan", "submit_action_plan"])
        self.assertEqual(len(kwargs["subagents"]), 1)
        research_tools = kwargs["subagents"][0]["tools"]
        self.assertEqual([tool.name for tool in research_tools], ["get_run_context", "search_web"])
        self.assertNotIn("get_account_context", {tool.name for tool in research_tools})
        self.assertNotIn("submit_action_plan", {tool.name for tool in research_tools})
