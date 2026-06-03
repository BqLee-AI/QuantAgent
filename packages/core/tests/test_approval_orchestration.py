from __future__ import annotations

import unittest

from quantagent.core.approval import (
    ActionRequest,
    ActionExecutionResult,
    ApprovalDecisionStatus,
    ApprovalEventPublisher,
    ApprovalInput,
    ApprovalOrchestrationService,
    ApprovalRequest,
    ApprovalRequestStatus,
    ConfirmationLevel,
    ExecutionStatus,
    ExpirationAction,
    FakeActionExecutor,
    FakePolicyGate,
    InMemoryApprovalRepository,
)
from quantagent.core.events import EventEnvelope, InMemoryEventBus


class RecordingHandler:
    def __init__(self) -> None:
        self.seen: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope)


class ApprovalOrchestrationTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.bus = InMemoryEventBus()
        self.completed = RecordingHandler()
        self.notifications = RecordingHandler()
        await self.bus.subscribe(topics=("approval.completed",), group_id="test", handler=self.completed)
        await self.bus.subscribe(topics=("notification.requested",), group_id="test", handler=self.notifications)

    async def test_approval_requested_payload_uses_safe_summary(self) -> None:
        approval_requested = RecordingHandler()
        await self.bus.subscribe(topics=("approval.requested",), group_id="test", handler=approval_requested)
        service, _, _, _ = self._service()

        await service.submit_action(
            ActionRequest(
                id="act-sensitive",
                action_type="adjust_strategy",
                action_side="increase_risk",
                target_type="strategy",
                target_id="strategy-1",
                proposed_payload={
                    "prompt": "private strategy thesis without token marker",
                    "private_policy": "never publish this policy body",
                    "broker_order": {"symbol": "BTC-USD", "side": "buy"},
                },
            )
        )

        self.assertEqual(len(approval_requested.seen), 1)
        payload = approval_requested.seen[0].payload
        rendered = str(payload)
        self.assertNotIn("proposed_payload", payload)
        self.assertNotIn("private strategy thesis without token marker", rendered)
        self.assertNotIn("never publish this policy body", rendered)
        self.assertNotIn("broker_order", rendered)
        self.assertEqual(payload["approval_id"], "approval-fixed")
        self.assertEqual(payload["action_request_id"], "act-sensitive")
        self.assertEqual(payload["safe_context"]["risk_level"], "high")

    async def test_approve_calls_policy_gate_and_executor(self) -> None:
        service, gate, executor, repository = self._service()
        result = await service.submit_action(_approval_required_action())
        approval = result.approval

        input_result = await service.submit_input(
            ApprovalInput(
                id="input-1",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "approve"},
            )
        )

        self.assertEqual(input_result.decision.status, ApprovalDecisionStatus.EXECUTION_REQUESTED)
        self.assertEqual(input_result.decision.execution_status, ExecutionStatus.DRY_RUN_REQUESTED)
        self.assertEqual(len(gate.calls), 1)
        self.assertEqual(len(executor.calls), 1)
        self.assertIs(repository.latest_decision(approval.id), input_result.decision)

    async def test_reject_does_not_call_executor(self) -> None:
        service, gate, executor, _ = self._service()
        approval = (await service.submit_action(_approval_required_action())).approval

        result = await service.submit_input(
            ApprovalInput(
                id="input-1",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "reject"},
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.REJECTED)
        self.assertEqual(len(gate.calls), 0)
        self.assertEqual(len(executor.calls), 0)

    async def test_request_reanalysis_does_not_call_executor(self) -> None:
        service, gate, executor, _ = self._service()
        approval = (await service.submit_action(_approval_required_action())).approval

        result = await service.submit_input(
            ApprovalInput(
                id="input-1",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "request_reanalysis"},
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.REANALYSIS_REQUESTED)
        self.assertEqual(len(gate.calls), 0)
        self.assertEqual(len(executor.calls), 0)

    async def test_unclear_text_escalates(self) -> None:
        service, gate, executor, _ = self._service()
        approval = (await service.submit_action(_approval_required_action())).approval

        result = await service.submit_input(
            ApprovalInput(
                id="input-1",
                approval_id=approval.id,
                channel="discord",
                actor_ref="discord:user",
                raw_text="sounds fine I guess",
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.ESCALATED)
        self.assertEqual(len(gate.calls), 0)
        self.assertEqual(len(executor.calls), 0)

    async def test_discord_prefixed_approval_text_is_parsed_but_still_weak_confirmation(self) -> None:
        service, gate, executor, _ = self._service()
        approval = (await service.submit_action(_approval_required_action())).approval

        result = await service.submit_input(
            ApprovalInput(
                id="input-discord-prefixed",
                approval_id=approval.id,
                channel="discord",
                actor_ref="discord:user",
                raw_text=f"approval_id: {approval.id} approve",
            )
        )

        self.assertEqual(result.evaluation.interpreted_intent.value, "escalate")
        self.assertTrue(result.evaluation.requires_stronger_confirmation)
        self.assertEqual(result.decision.status, ApprovalDecisionStatus.ESCALATED)
        self.assertEqual(len(gate.calls), 0)
        self.assertEqual(len(executor.calls), 0)

    async def test_structured_intent_is_normalized(self) -> None:
        service, gate, executor, _ = self._service()
        approval = (await service.submit_action(_approval_required_action())).approval

        result = await service.submit_input(
            ApprovalInput(
                id="input-structured-normalized",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": " APPROVE "},
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.EXECUTION_REQUESTED)
        self.assertEqual(len(gate.calls), 1)
        self.assertEqual(len(executor.calls), 1)

    async def test_prefixed_reject_and_reanalysis_text_are_parsed(self) -> None:
        cases = [
            ("reject", ApprovalDecisionStatus.REJECTED),
            ("reanalysis", ApprovalDecisionStatus.REANALYSIS_REQUESTED),
        ]
        for command, expected_status in cases:
            with self.subTest(command=command):
                service, gate, executor, _ = self._service()
                approval = (await service.submit_action(_approval_required_action())).approval

                result = await service.submit_input(
                    ApprovalInput(
                        id=f"input-discord-{command}",
                        approval_id=approval.id,
                        channel="discord",
                        actor_ref="discord:user",
                        raw_text=f"approval_id: {approval.id} {command}",
                    )
                )

                self.assertEqual(result.decision.status, expected_status)
                self.assertEqual(len(gate.calls), 0)
                self.assertEqual(len(executor.calls), 0)

    async def test_manual_only_weak_channel_escalates(self) -> None:
        service, gate, executor, _ = self._service()
        approval = (
            await service.submit_action(
                ActionRequest(
                    id="act-manual",
                    action_type="execute_order",
                    action_side="increase_risk",
                    target_type="portfolio",
                    target_id="portfolio-1",
                    risk_flags=("manual_only",),
                )
            )
        ).approval

        result = await service.submit_input(
            ApprovalInput(
                id="input-1",
                approval_id=approval.id,
                channel="approval_link",
                actor_ref="link:user",
                structured_payload={"intent": "approve"},
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.ESCALATED)
        self.assertEqual(len(gate.calls), 0)
        self.assertEqual(len(executor.calls), 0)

    async def test_blocked_action_does_not_call_policy_gate_or_executor(self) -> None:
        service, gate, executor, _ = self._service()
        result = await service.submit_action(
            ActionRequest(
                id="act-blocked",
                action_type="execute_order",
                action_side="increase_risk",
                target_type="portfolio",
                target_id="portfolio-1",
                risk_flags=("blocked",),
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.BLOCKED)
        self.assertEqual(len(gate.calls), 0)
        self.assertEqual(len(executor.calls), 0)

    async def test_execute_then_notify_uses_policy_gate_before_executor(self) -> None:
        service, gate, executor, _ = self._service()
        result = await service.submit_action(
            ActionRequest(
                id="act-reduce",
                action_type="reduce_position",
                action_side="reduce_risk",
                target_type="portfolio",
                target_id="portfolio-1",
                urgency="urgent",
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.EXECUTION_REQUESTED)
        self.assertEqual(len(gate.calls), 1)
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(len(self.notifications.seen), 1)

    async def test_no_approval_notify_only_publishes_notification_without_execution(self) -> None:
        service, gate, executor, _ = self._service()
        result = await service.submit_action(
            ActionRequest(
                id="act-notify",
                action_type="notify",
                action_side="neutral",
                target_type="portfolio",
                target_id="portfolio-1",
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.NOT_REQUIRED)
        self.assertEqual(len(gate.calls), 0)
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(len(self.notifications.seen), 1)
        self.assertEqual(len(self.completed.seen), 1)
        self.assertEqual(self.notifications.seen[0].payload["approval_id"], result.approval.id)
        self.assertEqual(self.completed.seen[0].payload["status"], "not_required")

    async def test_policy_gate_denial_blocks_executor(self) -> None:
        service, gate, executor, _ = self._service(gate_allowed=False)
        approval = (await service.submit_action(_approval_required_action())).approval

        result = await service.submit_input(
            ApprovalInput(
                id="input-1",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "approve"},
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.POLICY_BLOCKED)
        self.assertEqual(len(gate.calls), 1)
        self.assertEqual(len(executor.calls), 0)

    async def test_missing_policy_gate_blocks_executor(self) -> None:
        service, _, executor, _ = self._service(include_gate=False)
        approval = (await service.submit_action(_approval_required_action())).approval

        result = await service.submit_input(
            ApprovalInput(
                id="input-1",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "approve"},
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.POLICY_GATE_FAILED)
        self.assertEqual(len(executor.calls), 0)

    async def test_duplicate_input_does_not_repeat_executor(self) -> None:
        service, gate, executor, _ = self._service()
        approval = (await service.submit_action(_approval_required_action())).approval
        user_input = ApprovalInput(
            id="input-1",
            approval_id=approval.id,
            channel="web",
            actor_ref="user:test",
            structured_payload={"intent": "approve"},
        )

        first = await service.submit_input(user_input)
        second = await service.submit_input(user_input)

        self.assertIs(first.decision, second.decision)
        self.assertEqual(len(gate.calls), 1)
        self.assertEqual(len(executor.calls), 1)

    async def test_terminal_input_is_ignored(self) -> None:
        service, _, executor, repository = self._service()
        approval = (await service.submit_action(_approval_required_action())).approval
        await service.submit_input(
            ApprovalInput(
                id="input-1",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "reject"},
            )
        )

        result = await service.submit_input(
            ApprovalInput(
                id="input-2",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "approve"},
            )
        )

        self.assertEqual(result.decision.status, ApprovalDecisionStatus.IGNORED)
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(repository.latest_decision(approval.id).status, ApprovalDecisionStatus.REJECTED)

    async def test_timeout_actions(self) -> None:
        cases = {
            "expire_reject": ApprovalDecisionStatus.REJECTED,
            "expire_approve": ApprovalDecisionStatus.EXECUTION_REQUESTED,
            "expire_notify_only": ApprovalDecisionStatus.EXPIRED,
            "expire_reanalysis": ApprovalDecisionStatus.REANALYSIS_REQUESTED,
            "escalate": ApprovalDecisionStatus.ESCALATED,
        }
        for expiration_action, expected_status in cases.items():
            with self.subTest(expiration_action=expiration_action):
                service, _, _, _ = self._service()
                approval = (
                    await service.submit_action(
                        ActionRequest(
                            id=f"act-{expiration_action}",
                            action_type="execute_order",
                            action_side="increase_risk",
                            target_type="portfolio",
                            target_id="portfolio-1",
                            urgency="time_sensitive",
                            user_policy={
                                "mode": "approval_with_timeout",
                                "expiration_action": expiration_action,
                            },
                        )
                    )
                ).approval
                result = await service.expire_approval(approval.id)
                self.assertEqual(result.decision.status, expected_status)

    async def test_missing_action_input_persists_blocked_and_publishes_completed(self) -> None:
        service, _, _, repository = self._service()
        approval = ApprovalRequest(
            id="approval-orphan",
            action_request_id="missing-action",
            target_type="strategy",
            target_id="strategy-1",
            action_type="adjust_strategy",
            action_side="increase_risk",
            risk_level="high",
            urgency="normal",
            summary="orphan approval",
            required_confirmation_level=ConfirmationLevel.SOFT_CONFIRM,
            expiration_action=ExpirationAction.EXPIRE_REJECT,
            status=ApprovalRequestStatus.PENDING,
            allowed_channels=("web",),
        )
        repository.save_approval_request(approval)

        result = await service.submit_input(
            ApprovalInput(
                id="input-orphan",
                approval_id=approval.id,
                channel="web",
                actor_ref="user:test",
                structured_payload={"intent": "approve"},
            )
        )

        self.assertEqual(result.approval.status, ApprovalRequestStatus.BLOCKED)
        self.assertEqual(result.decision.status, ApprovalDecisionStatus.BLOCKED)
        self.assertEqual(repository.get_approval_request(approval.id).status, ApprovalRequestStatus.BLOCKED)
        self.assertEqual(len(self.completed.seen), 1)
        self.assertEqual(self.completed.seen[0].payload["status"], "blocked")

    async def test_missing_action_expiration_persists_blocked_and_publishes_completed(self) -> None:
        service, _, _, repository = self._service()
        approval = ApprovalRequest(
            id="approval-expire-orphan",
            action_request_id="missing-action",
            target_type="strategy",
            target_id="strategy-1",
            action_type="adjust_strategy",
            action_side="increase_risk",
            risk_level="high",
            urgency="time_sensitive",
            summary="orphan approval",
            required_confirmation_level=ConfirmationLevel.SOFT_CONFIRM,
            expiration_action=ExpirationAction.EXPIRE_REJECT,
            status=ApprovalRequestStatus.PENDING,
            allowed_channels=("web",),
        )
        repository.save_approval_request(approval)

        result = await service.expire_approval(approval.id)

        self.assertEqual(result.approval.status, ApprovalRequestStatus.BLOCKED)
        self.assertEqual(result.decision.status, ApprovalDecisionStatus.BLOCKED)
        self.assertEqual(repository.get_approval_request(approval.id).status, ApprovalRequestStatus.BLOCKED)
        self.assertEqual(len(self.completed.seen), 1)
        self.assertEqual(self.completed.seen[0].payload["status"], "blocked")

    async def test_action_execution_result_rejects_unknown_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "execution_status must be one of"):
            ActionExecutionResult(execution_status="live_order_sent", reason_summary="invalid status")

    def _service(
        self,
        *,
        gate_allowed: bool = True,
        include_gate: bool = True,
    ) -> tuple[ApprovalOrchestrationService, FakePolicyGate, FakeActionExecutor, InMemoryApprovalRepository]:
        repository = InMemoryApprovalRepository()
        gate = FakePolicyGate(allowed=gate_allowed, reason_summary="fake gate result")
        executor = FakeActionExecutor()
        return (
            ApprovalOrchestrationService(
                repository=repository,
                event_publisher=ApprovalEventPublisher(self.bus),
                policy_gate=gate if include_gate else None,
                executor=executor,
                id_factory=_fixed_id,
            ),
            gate,
            executor,
            repository,
        )


def _approval_required_action() -> ActionRequest:
    return ActionRequest(
        id="act-approval",
        action_type="adjust_strategy",
        action_side="increase_risk",
        target_type="strategy",
        target_id="strategy-1",
    )


def _fixed_id(prefix: str) -> str:
    return f"{prefix}-fixed"


if __name__ == "__main__":
    unittest.main()
