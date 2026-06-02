from __future__ import annotations

import unittest
from pathlib import Path

from quantagent.core.approval import (
    ActionRequest,
    ApprovalEventPublisher,
    ApprovalNotificationHandoffAdapter,
    ApprovalOrchestrationService,
    FakeActionExecutor,
    FakePolicyGate,
    InMemoryApprovalRepository,
)
from quantagent.core.events import EventEnvelope, InMemoryEventBus
from quantagent.core.notifications import (
    InMemoryNotificationApprovalHandoff,
    NotificationDispatchService,
    NotificationEventPublisher,
    NotificationRequestedHandler,
)
from quantagent.core.notifications.ingress import NotificationIngressService
from quantagent.core.registry import PluginManifest, PluginRecord, PluginSource, PluginStatus, PluginType
from quantagent.plugin_sdk import NotificationReceiveInput, NotificationReceiveItem, NotificationReceiveResult, NotificationSendResult


class _RecordingHandler:
    def __init__(self) -> None:
        self.seen: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.seen.append(envelope)


class _StubRegistry:
    def get_plugin(self, _plugin_id: str) -> PluginRecord:
        return PluginRecord(
            id="quantagent.official.notification.discord",
            source=PluginSource.OFFICIAL,
            path=Path("/tmp/fake-discord"),
            status=PluginStatus.VALID,
            manifest=PluginManifest(
                id="quantagent.official.notification.discord",
                name="Discord Notification",
                type=PluginType.NOTIFICATION,
                version="0.1.0",
                entrypoint="discord_plugin:plugin",
                capabilities=("notification.send", "notification.receive"),
                config_schema="config.schema.json",
            ),
        )


class _LoopRuntime:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def invoke(self, _record, **kwargs):
        self.calls.append(kwargs)
        capability = kwargs["capability"]
        if capability == "notification.send":
            return type(
                "Invocation",
                (),
                {
                    "error": None,
                    "result": type(
                        "PluginResult",
                        (),
                        {"output": NotificationSendResult(accepted=True, retryable=False, metadata={"code": "SENT", "message": "sent"}).to_mapping()},
                    )(),
                },
            )()
        if capability == "notification.receive":
            return type(
                "Invocation",
                (),
                {
                    "error": None,
                    "result": type(
                        "PluginResult",
                        (),
                        {
                            "output": NotificationReceiveResult(
                                accepted=True,
                                code="RECEIVED",
                                message="ok",
                                response_status_code=200,
                                response={"type": 4},
                                item=NotificationReceiveItem(
                                    interaction_id="interaction-1",
                                    source_id="discord.interaction:app-1",
                                    text="approval_id: approval-fixed approve",
                                    payload_summary={"approval_id": "approval-fixed"},
                                    author_id="user-1",
                                ),
                                retryable=False,
                            ).to_mapping()
                        },
                    )(),
                },
            )()
        raise AssertionError(f"unexpected capability: {capability}")


class NotificationApprovalLoopTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_notification_requested_to_send_to_completed_and_receive_handoff(self) -> None:
        bus = InMemoryEventBus()
        completed = _RecordingHandler()
        await bus.subscribe(topics=("notification.completed",), group_id="test", handler=completed)
        runtime = _LoopRuntime()
        registry = _StubRegistry()
        dispatch_service = NotificationDispatchService(registry=registry, runtime=runtime)
        await bus.subscribe(
            topics=("notification.requested",),
            group_id="notification-dispatch",
            handler=NotificationRequestedHandler(
                dispatch_service=dispatch_service,
                event_publisher=NotificationEventPublisher(bus),
                plugin_id="quantagent.official.notification.discord",
            ),
        )
        repository = InMemoryApprovalRepository()
        executor = FakeActionExecutor()
        approval_service = ApprovalOrchestrationService(
            repository=repository,
            event_publisher=ApprovalEventPublisher(bus),
            policy_gate=FakePolicyGate(allowed=True),
            executor=executor,
            id_factory=lambda prefix: f"{prefix}-fixed",
        )

        action_result = await approval_service.submit_action(
            ActionRequest(
                id="action-1",
                action_type="adjust_strategy",
                action_side="increase_risk",
                target_type="strategy",
                target_id="strategy-1",
                correlation_id="corr-1",
            )
        )

        self.assertEqual(action_result.approval.id, "approval-fixed")
        self.assertEqual(len(completed.seen), 1)
        payload = completed.seen[0].payload
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["approval_id"], "approval-fixed")
        self.assertEqual(payload["action_request_id"], "action-1")
        self.assertNotIn("decision_status", payload)
        self.assertEqual(runtime.calls[0]["capability"], "notification.send")
        self.assertIn("approval_id: approval-fixed", runtime.calls[0]["input"]["text"])

        ingress = NotificationIngressService(
            registry=registry,
            runtime=runtime,
            approval_handoff=ApprovalNotificationHandoffAdapter(service=approval_service),
        )
        receive = await ingress.receive(
            plugin_id="quantagent.official.notification.discord",
            request_id="req-receive-1",
            config={},
            receive_input=NotificationReceiveInput(
                transport="discord",
                request_metadata={"correlation_id": "corr-1"},
            ),
        )

        self.assertTrue(receive.accepted)
        self.assertEqual(receive.approval_handoff.status, "completed")
        decision = repository.latest_decision("approval-fixed")
        self.assertEqual(decision.status.value, "escalated")
        self.assertEqual(len(executor.calls), 0)

    async def test_ingress_can_use_noop_handoff_without_claiming_approval_input(self) -> None:
        ingress = NotificationIngressService(
            registry=_StubRegistry(),
            runtime=_LoopRuntime(),
            approval_handoff=InMemoryNotificationApprovalHandoff(),
        )

        receive = await ingress.receive(
            plugin_id="quantagent.official.notification.discord",
            request_id="req-receive-2",
            config={},
            receive_input=NotificationReceiveInput(transport="discord"),
        )

        self.assertTrue(receive.accepted)
        self.assertEqual(receive.approval_handoff.status, "queued")


if __name__ == "__main__":
    unittest.main()
