from __future__ import annotations

import unittest

from quantagent.core.approval import (
    ActionRequest,
    ActionRequestedHandler,
    ApprovalEventPublisher,
    ApprovalInput,
    ApprovalInputReceivedHandler,
    ApprovalOrchestrationService,
    FakeActionExecutor,
    FakePolicyGate,
    InMemoryApprovalRepository,
)
from quantagent.core.events.errors import EventBusError
from quantagent.core.events import EventEnvelope, EventTopicPolicy, InMemoryEventBus


class ApprovalEventBusTopicsTestCase(unittest.IsolatedAsyncioTestCase):
    def test_topic_policy_accepts_hitl_topics(self) -> None:
        policy = EventTopicPolicy()

        self.assertEqual(policy.validate("action.requested"), "action.requested")
        self.assertEqual(policy.validate("approval.input_received"), "approval.input_received")
        with self.assertRaises(EventBusError):
            policy.validate("approval.unknown")

    async def test_handlers_adapt_envelopes_to_service(self) -> None:
        bus = InMemoryEventBus()
        repository = InMemoryApprovalRepository()
        service = ApprovalOrchestrationService(
            repository=repository,
            event_publisher=ApprovalEventPublisher(bus),
            policy_gate=FakePolicyGate(),
            executor=FakeActionExecutor(),
            id_factory=_fixed_id,
        )
        input_handler = ApprovalInputReceivedHandler(service)
        await bus.subscribe(topics=("action.requested",), group_id="approval", handler=ActionRequestedHandler(service))
        await bus.subscribe(topics=("approval.input_received",), group_id="approval", handler=input_handler)

        action = ActionRequest(
            id="act-1",
            action_type="adjust_strategy",
            action_side="increase_risk",
            target_type="strategy",
            target_id="strategy-1",
        )
        await bus.publish(
            EventEnvelope(
                id="evt-act",
                topic="action.requested",
                payload=action.to_mapping(),
                producer="test",
                created_at="2026-06-01T00:00:00+00:00",
            )
        )
        approval = repository.get_approval_request_by_action_id("act-1")
        self.assertIsNotNone(approval)

        await bus.publish(
            EventEnvelope(
                id="evt-input",
                topic="approval.input_received",
                payload=ApprovalInput(
                    id="inp-1",
                    approval_id=approval.id,
                    channel="web",
                    actor_ref="user:test",
                    structured_payload={"intent": "approve"},
                ).to_mapping(),
                producer="test",
                created_at="2026-06-01T00:00:01+00:00",
            )
        )

        decision = repository.latest_decision(approval.id)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.status.value, "execution_requested")


def _fixed_id(prefix: str) -> str:
    return f"{prefix}-fixed"


if __name__ == "__main__":
    unittest.main()
