from __future__ import annotations

from unittest import TestCase

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from quantagent.agent.definitions.models import RuntimePolicy
from quantagent.agent.runtime import AgentRuntime
from quantagent.agent.testing import build_echo_run_request


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
