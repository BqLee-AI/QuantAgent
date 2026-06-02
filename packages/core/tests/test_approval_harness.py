from __future__ import annotations

import unittest

from quantagent.core.approval import (
    ActionRequest,
    ActionRequestedHandler,
    ApprovalEventPublisher,
    ApprovalInput,
    ApprovalInputReceivedHandler,
    ApprovalNotificationHandoffAdapter,
    ApprovalOrchestrationService,
    FakeAIActionProducer,
    FakeActionExecutor,
    FakeHumanInputProducer,
    FakeNotificationHandoffProducer,
    FakeNotificationConsumer,
    FakePolicyGate,
    InMemoryApprovalRepository,
)
from quantagent.core.events import InMemoryEventBus
from quantagent.core.notifications.models import NotificationApprovalHandoffRequest


class ApprovalHarnessTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_fake_message_loop_and_redacted_authorization_message(self) -> None:
        bus = InMemoryEventBus()
        repository = InMemoryApprovalRepository()
        service = ApprovalOrchestrationService(
            repository=repository,
            event_publisher=ApprovalEventPublisher(bus),
            policy_gate=FakePolicyGate(),
            executor=FakeActionExecutor(),
            id_factory=_fixed_id,
        )
        notification_consumer = FakeNotificationConsumer()
        input_handler = ApprovalInputReceivedHandler(service)
        await bus.subscribe(topics=("action.requested",), group_id="approval", handler=ActionRequestedHandler(service))
        await bus.subscribe(topics=("notification.requested",), group_id="notification", handler=notification_consumer)
        await bus.subscribe(topics=("approval.input_received",), group_id="approval", handler=input_handler)

        action = ActionRequest(
            id="act-1",
            action_type="adjust_strategy",
            action_side="increase_risk",
            target_type="strategy",
            target_id="strategy-1",
            proposed_payload={
                "summary": "raise risk",
                "api_key": "secret-token",
                "prompt": "full private prompt token=abc123",
            },
        )
        await FakeAIActionProducer(bus).publish_action(action)

        message = notification_consumer.latest_message
        self.assertIsNotNone(message)
        self.assertEqual(message.approval_id, "approval-fixed")
        rendered = str(message.to_mapping())
        self.assertNotIn("secret-token", rendered)
        self.assertNotIn("abc123", rendered)
        self.assertIn("required_confirmation_level", message.to_mapping())

        await FakeHumanInputProducer(bus).publish_input(
            ApprovalInput(
                id="input-1",
                approval_id=message.approval_id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "approve"},
            )
        )

        decision = repository.latest_decision(message.approval_id)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.status.value, "execution_requested")

    async def test_raw_text_ambiguous_input_escalates_in_harness(self) -> None:
        bus = InMemoryEventBus()
        service = ApprovalOrchestrationService(
            repository=InMemoryApprovalRepository(),
            event_publisher=ApprovalEventPublisher(bus),
            policy_gate=FakePolicyGate(),
            executor=FakeActionExecutor(),
            id_factory=_fixed_id,
        )
        input_handler = ApprovalInputReceivedHandler(service)
        notification_consumer = FakeNotificationConsumer()
        await bus.subscribe(topics=("action.requested",), group_id="approval", handler=ActionRequestedHandler(service))
        await bus.subscribe(topics=("notification.requested",), group_id="notification", handler=notification_consumer)
        await bus.subscribe(topics=("approval.input_received",), group_id="approval", handler=input_handler)

        await FakeAIActionProducer(bus).publish_action(
            ActionRequest(
                id="act-2",
                action_type="adjust_strategy",
                action_side="increase_risk",
                target_type="strategy",
                target_id="strategy-1",
            )
        )
        message = notification_consumer.latest_message
        await FakeHumanInputProducer(bus).publish_input(
            ApprovalInput(
                id="input-2",
                approval_id=message.approval_id,
                channel="discord",
                actor_ref="discord:user",
                raw_text="ok probably",
            )
        )

        decision = service.repository.latest_decision(message.approval_id)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.status.value, "escalated")

    async def test_notification_handoff_directly_enters_approval_evaluation(self) -> None:
        bus = InMemoryEventBus()
        executor = FakeActionExecutor()
        service = ApprovalOrchestrationService(
            repository=InMemoryApprovalRepository(),
            event_publisher=ApprovalEventPublisher(bus),
            policy_gate=FakePolicyGate(),
            executor=executor,
            id_factory=_fixed_id,
        )
        approval = (
            await service.submit_action(
                ActionRequest(
                    id="act-handoff",
                    action_type="adjust_strategy",
                    action_side="increase_risk",
                    target_type="strategy",
                    target_id="strategy-1",
                )
            )
        ).approval

        result = await FakeNotificationHandoffProducer(
            ApprovalNotificationHandoffAdapter(service=service)
        ).handoff(approval_id=approval.id, text="approve")

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.metadata["decision_status"], "escalated")
        self.assertEqual(len(executor.calls), 0)

    async def test_notification_handoff_can_publish_input_received_event(self) -> None:
        bus = InMemoryEventBus()
        seen = []

        class _Handler:
            async def handle(self, envelope):
                seen.append(envelope)

        await bus.subscribe(topics=("approval.input_received",), group_id="approval", handler=_Handler())
        adapter = ApprovalNotificationHandoffAdapter(publisher=bus)

        result = await adapter.handoff(
            NotificationApprovalHandoffRequest(
                handoff_id="handoff-1",
                fact_id="fact-1",
                plugin_id="quantagent.official.notification.fake",
                transport="discord",
                request_id="req-1",
                correlation_id="corr-1",
                interaction_id="interaction-1",
                source_id="channel-1",
                text="approve",
                payload_summary={"approval_id": "approval-1", "intent": "approve"},
                metadata={"approval_input_id": "input-1"},
                received_at="2026-06-01T00:00:02+00:00",
                author_id="user-1",
            )
        )

        self.assertEqual(result.status, "queued")
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].topic, "approval.input_received")
        self.assertEqual(seen[0].payload["approval_id"], "approval-1")

    async def test_notification_handoff_default_input_id_is_stable_for_retries(self) -> None:
        bus = InMemoryEventBus()
        executor = FakeActionExecutor()
        service = ApprovalOrchestrationService(
            repository=InMemoryApprovalRepository(),
            event_publisher=ApprovalEventPublisher(bus),
            policy_gate=FakePolicyGate(),
            executor=executor,
            id_factory=_fixed_id,
        )
        approval = (
            await service.submit_action(
                ActionRequest(
                    id="act-stable-handoff",
                    action_type="monitor",
                    action_side="increase_risk",
                    target_type="strategy",
                    target_id="strategy-1",
                    user_policy={"mode": "approval_required", "required_confirmation_level": "soft_confirm"},
                )
            )
        ).approval
        adapter = ApprovalNotificationHandoffAdapter(service=service)
        request = NotificationApprovalHandoffRequest(
            handoff_id="handoff-retry",
            fact_id="fact-retry",
            plugin_id="quantagent.official.notification.fake",
            transport="web",
            request_id="req-retry",
            correlation_id="corr-retry",
            interaction_id="interaction-retry",
            source_id="source-retry",
            text="approve",
            payload_summary={"approval_id": approval.id},
            metadata={},
            received_at="2026-06-01T00:00:02+00:00",
            author_id="user-1",
        )

        first = await adapter.handoff(request)
        second = await adapter.handoff(request)

        self.assertEqual(first.metadata["input_id"], "approval_input_fact-retry_interaction-retry")
        self.assertEqual(second.metadata["input_id"], "approval_input_fact-retry_interaction-retry")
        self.assertEqual(first.metadata["decision_status"], "execution_requested")
        self.assertEqual(second.metadata["decision_status"], "execution_requested")
        self.assertEqual(len(executor.calls), 1)

    async def test_notification_handoff_failure_paths_do_not_execute(self) -> None:
        cases = [
            ("missing_approval_id", None, None, "approve"),
            ("unknown_approval", "missing-approval", None, "approve"),
            ("terminal_after_reject", "approval-fixed", "reject-first", None),
            ("duplicate_input", "approval-fixed", "duplicate-first", None),
            ("ambiguous_text", "approval-fixed", None, None),
            ("manual_only_weak_confirm", "approval-fixed", "manual-only", None),
        ]
        for case_name, approval_id, setup, intent in cases:
            with self.subTest(case_name=case_name):
                bus = InMemoryEventBus()
                repository = InMemoryApprovalRepository()
                executor = FakeActionExecutor()
                service = ApprovalOrchestrationService(
                    repository=repository,
                    event_publisher=ApprovalEventPublisher(bus),
                    policy_gate=FakePolicyGate(),
                    executor=executor,
                    id_factory=_fixed_id,
                )
                action = ActionRequest(
                    id=f"act-{case_name}",
                    action_type="execute_order" if setup == "manual-only" else "adjust_strategy",
                    action_side="increase_risk",
                    target_type="strategy",
                    target_id="strategy-1",
                    risk_flags=("manual_only",) if setup == "manual-only" else (),
                )
                if approval_id is not None and approval_id != "missing-approval":
                    approval = (await service.submit_action(action)).approval
                    approval_id = approval.id
                if setup == "reject-first":
                    # 这里预置 input-first，依赖 adapter 后续派生出不同 input id，才能验证终态后新输入被 ignored。
                    await service.submit_input(
                        ApprovalInput(
                            id="input-first",
                            approval_id=approval_id,
                            channel="web",
                            actor_ref="user:test",
                            structured_payload={"intent": "reject"},
                        )
                    )
                if setup == "duplicate-first":
                    # 这里预置 input-notif_fact_1，依赖 adapter 复用相同派生 id，才能验证重复输入复用既有 rejected 决策。
                    await service.submit_input(
                        ApprovalInput(
                            id="input-notif_fact_1",
                            approval_id=approval_id,
                            channel="web",
                            actor_ref="user:test",
                            structured_payload={"intent": "reject"},
                        )
                    )

                result = await FakeNotificationHandoffProducer(
                    ApprovalNotificationHandoffAdapter(service=service)
                ).handoff(
                    approval_id=approval_id or "",
                    text="approval_id: missing-approval approve"
                    if approval_id == "missing-approval"
                    else ("approve" if case_name in {"terminal_after_reject", "duplicate_input", "manual_only_weak_confirm"} else "maybe later"),
                    intent=intent,
                )

                self.assertEqual(len(executor.calls), 0)
                if case_name == "missing_approval_id":
                    self.assertEqual(result.status, "failed")
                elif case_name == "unknown_approval":
                    self.assertEqual(result.metadata["decision_status"], "blocked")
                elif case_name == "terminal_after_reject":
                    self.assertEqual(result.metadata["decision_status"], "ignored")
                elif case_name == "duplicate_input":
                    self.assertEqual(result.metadata["decision_status"], "rejected")
                else:
                    self.assertEqual(result.metadata["decision_status"], "escalated")


def _fixed_id(prefix: str) -> str:
    return f"{prefix}-fixed"


if __name__ == "__main__":
    unittest.main()
