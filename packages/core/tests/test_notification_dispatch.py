from __future__ import annotations

import unittest
from pathlib import Path

from quantagent.core.notifications import (
    NotificationDispatchRequest,
    NotificationDispatchService,
    build_discord_approval_notification_text,
)
from quantagent.core.registry import PluginManifest, PluginRecord, PluginSource, PluginStatus, PluginType
from quantagent.plugin_sdk import NotificationSendResult


class _StubRegistry:
    def __init__(self, record: PluginRecord | None) -> None:
        self._record = record

    def get_plugin(self, _plugin_id: str) -> PluginRecord | None:
        return self._record


class _StubRuntime:
    def __init__(self, *, result=None, error=None) -> None:
        self._result = result
        self._error = error
        self.last_call = None

    async def invoke(self, record, **kwargs):
        self.last_call = {"record": record, **kwargs}
        return type("Invocation", (), {"result": self._result, "error": self._error})()


def _record(*, capabilities: tuple[str, ...] = ("notification.send", "notification.receive")) -> PluginRecord:
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
            capabilities=capabilities,
            config_schema="config.schema.json",
        ),
    )


def _request() -> NotificationDispatchRequest:
    return NotificationDispatchRequest(
        request_id="notif-1",
        plugin_id="quantagent.official.notification.discord",
        correlation_id="corr-1",
        causation_id="approval-1",
        approval_id="approval-1",
        action_request_id="action-1",
        channel="discord",
        text="approval_id: approval-1",
        metadata={"approval_id": "approval-1", "action_request_id": "action-1"},
    )


class NotificationDispatchServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_dispatch_invokes_notification_send(self) -> None:
        runtime = _StubRuntime(
            result=type(
                "PluginResult",
                (),
                {
                    "output": NotificationSendResult(
                        accepted=True,
                        retryable=False,
                        provider_message_id="msg-1",
                        metadata={"code": "DISCORD_SENT", "message": "sent"},
                    ).to_mapping()
                },
            )()
        )
        service = NotificationDispatchService(registry=_StubRegistry(_record()), runtime=runtime, config={"webhook_secret_ref": "env:DISCORD_WEBHOOK_URL"})

        result = await service.dispatch(_request())

        self.assertTrue(result.accepted)
        self.assertFalse(result.retryable)
        self.assertEqual(result.code, "DISCORD_SENT")
        self.assertEqual(runtime.last_call["capability"], "notification.send")
        self.assertEqual(runtime.last_call["request_id"], "notif-1")
        self.assertEqual(runtime.last_call["input"]["channel"], "discord")
        self.assertEqual(runtime.last_call["input"]["metadata"]["approval_id"], "approval-1")
        self.assertEqual(runtime.last_call["config"]["webhook_secret_ref"], "env:DISCORD_WEBHOOK_URL")

    async def test_dispatch_disabled_does_not_call_runtime(self) -> None:
        runtime = _StubRuntime()
        service = NotificationDispatchService(registry=_StubRegistry(_record()), runtime=runtime, enabled=False)

        result = await service.dispatch(_request())

        self.assertFalse(result.accepted)
        self.assertEqual(result.code, "NOTIFICATION_DISPATCH_DISABLED")
        self.assertIsNone(runtime.last_call)

    async def test_dispatch_rejects_missing_plugin_or_capability(self) -> None:
        cases = [
            None,
            _record(capabilities=("notification.receive",)),
        ]
        for record in cases:
            with self.subTest(record=record):
                runtime = _StubRuntime()
                service = NotificationDispatchService(registry=_StubRegistry(record), runtime=runtime)

                result = await service.dispatch(_request())

                self.assertFalse(result.accepted)
                self.assertEqual(result.code, "PLUGIN_UNAVAILABLE")
                self.assertIsNone(runtime.last_call)

    async def test_dispatch_preserves_retryable_runtime_failure_without_secret_leak(self) -> None:
        error = type(
            "PluginError",
            (),
            {
                "code": "PLUGIN_INVOKE_FAILED",
                "message": "token=secret123 failed at /home/user/plugin",
                "retryable": True,
                "stage": "invoke",
                "details": {"webhook_secret_ref": "env:DISCORD_WEBHOOK_URL", "path": "/home/user/plugin"},
            },
        )()
        service = NotificationDispatchService(registry=_StubRegistry(_record()), runtime=_StubRuntime(error=error))

        result = await service.dispatch(_request())

        self.assertFalse(result.accepted)
        self.assertTrue(result.retryable)
        rendered = str(result.to_delivery_summary().to_mapping())
        self.assertNotIn("secret123", rendered)
        self.assertNotIn("/home/user/plugin", rendered)

    async def test_dispatch_rejects_invalid_plugin_output(self) -> None:
        service = NotificationDispatchService(
            registry=_StubRegistry(_record()),
            runtime=_StubRuntime(result=type("PluginResult", (), {"output": {"accepted": True}})()),
        )

        result = await service.dispatch(_request())

        self.assertFalse(result.accepted)
        self.assertTrue(result.retryable)
        self.assertEqual(result.code, "PLUGIN_RESULT_INVALID")


class NotificationApprovalMessageTestCase(unittest.TestCase):
    def test_message_contains_approval_id_and_omits_sensitive_payload(self) -> None:
        text = build_discord_approval_notification_text(
            {
                "approval_id": "approval-1",
                "action_request_id": "action-1",
                "summary": "Review strategy adjustment token=secret123",
                "risk_direction": "increase_risk",
                "required_confirmation_level": "soft_confirm",
                "expires_at": "2026-06-02T12:00:00Z",
                "proposed_payload": {"prompt": "full prompt", "broker_credential": "broker-secret"},
                "private_policy": "do not leak",
                "cookie": "session-cookie",
            }
        )

        self.assertIn("approval_id: approval-1", text)
        self.assertIn("action_request_id: action-1", text)
        self.assertIn("risk: increase_risk", text)
        self.assertIn("confirmation: soft_confirm", text)
        rendered = text.lower()
        self.assertNotIn("secret123", rendered)
        self.assertNotIn("full prompt", rendered)
        self.assertNotIn("broker-secret", rendered)
        self.assertNotIn("session-cookie", rendered)
        self.assertNotIn("private_policy", rendered)


if __name__ == "__main__":
    unittest.main()
