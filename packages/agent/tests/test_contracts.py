from __future__ import annotations

from pydantic import ValidationError
from unittest import TestCase

from quantagent.agent.artifacts import ArtifactRef
from quantagent.agent.definitions import AgentDefinition


class ContractTest(TestCase):
    def test_agent_definition_rejects_unknown_fields(self) -> None:
        with self.assertRaises(ValidationError):
            AgentDefinition.model_validate(
                {
                    "agent_id": "agent_test",
                    "version": "0.1.0",
                    "name": "Test",
                    "system_prompt": "Do work.",
                    "unknown": "not allowed",
                }
            )

    def test_artifact_ref_uses_artifact_id_namespace(self) -> None:
        ref = ArtifactRef(
            artifact_id="artifact_123",
            kind="runtime_output",
            producer_id="agent_test",
            safe_summary="safe",
        )

        self.assertEqual(ref.artifact_id, "artifact_123")
