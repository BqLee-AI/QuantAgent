from __future__ import annotations

import unittest
from pathlib import Path

from quantagent.core.notifications.ingress import (
    NotificationIngressService,
    NotificationIngressServiceUnavailableError,
)
from quantagent.core.registry import PluginManifest, PluginRecord, PluginSource, PluginStatus, PluginType
from quantagent.plugin_sdk import NotificationReceiveInput, NotificationReceiveResult


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


def _valid_record() -> PluginRecord:
    return PluginRecord(
        id="quantagent.official.notification.discord",
        source=PluginSource.OFFICIAL,
        path=Path("/tmp/fake-plugin"),
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


class NotificationIngressServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_receive_passes_typed_input_mapping_to_runtime(self) -> None:
        runtime = _StubRuntime(
            result=type(
                "PluginResult",
                (),
                {
                    "output": NotificationReceiveResult(
                        accepted=True,
                        code="PING",
                        message="ok",
                        response={"type": 1},
                        retryable=False,
                    ).to_mapping()
                },
            )()
        )
        service = NotificationIngressService(registry=_StubRegistry(_valid_record()), runtime=runtime)
        receive_input = NotificationReceiveInput(
            transport="http.webhook",
            headers={"X-Signature-Ed25519": "abcd"},
            body_text='{"type":1}',
            request_metadata={"request_id": "req-1"},
        )

        result = await service.receive(
            plugin_id="quantagent.official.notification.discord",
            request_id="req-1",
            config={"public_key": "a" * 64},
            receive_input=receive_input,
        )

        self.assertTrue(result.accepted)
        self.assertEqual(runtime.last_call["input"]["transport"], "http.webhook")
        self.assertEqual(runtime.last_call["metadata"]["transport"], "http.webhook")

    async def test_receive_rejects_missing_capability(self) -> None:
        record = _valid_record()
        assert record.manifest is not None
        record = PluginRecord(
            id=record.id,
            source=record.source,
            path=record.path,
            status=record.status,
            manifest=PluginManifest(
                id=record.manifest.id,
                name=record.manifest.name,
                type=record.manifest.type,
                version=record.manifest.version,
                entrypoint=record.manifest.entrypoint,
                capabilities=("notification.send",),
                config_schema=record.manifest.config_schema,
            ),
        )
        service = NotificationIngressService(registry=_StubRegistry(record), runtime=_StubRuntime())

        with self.assertRaises(NotificationIngressServiceUnavailableError):
            await service.receive(
                plugin_id=record.id,
                request_id="req-1",
                config={},
                receive_input=NotificationReceiveInput(transport="http.webhook"),
            )

    async def test_receive_rejects_invalid_result_payload(self) -> None:
        runtime = _StubRuntime(
            result=type(
                "PluginResult",
                (),
                {"output": {"accepted": True, "code": "PING", "message": "ok", "response": "invalid", "retryable": False}},
            )()
        )
        service = NotificationIngressService(registry=_StubRegistry(_valid_record()), runtime=runtime)

        with self.assertRaises(NotificationIngressServiceUnavailableError):
            await service.receive(
                plugin_id="quantagent.official.notification.discord",
                request_id="req-1",
                config={},
                receive_input=NotificationReceiveInput(transport="http.webhook"),
            )

    async def test_receive_accepts_response_only_success_without_item(self) -> None:
        runtime = _StubRuntime(
            result=type(
                "PluginResult",
                (),
                {
                    "output": NotificationReceiveResult(
                        accepted=True,
                        code="CHALLENGE",
                        message="ok",
                        response_status_code=200,
                        response={"challenge": "token"},
                        item=None,
                        retryable=False,
                    ).to_mapping()
                },
            )()
        )
        service = NotificationIngressService(registry=_StubRegistry(_valid_record()), runtime=runtime)

        result = await service.receive(
            plugin_id="quantagent.official.notification.discord",
            request_id="req-1",
            config={},
            receive_input=NotificationReceiveInput(transport="http.webhook"),
        )

        self.assertTrue(result.accepted)
        self.assertIsNone(result.receive_result.item)

    async def test_receive_rejects_invalid_http_status_code(self) -> None:
        runtime = _StubRuntime(
            result=type(
                "PluginResult",
                (),
                {
                    "output": NotificationReceiveResult(
                        accepted=False,
                        code="BAD_REQUEST",
                        message="bad",
                        response_status_code=999,
                        response={"error": "BAD_REQUEST", "message": "bad"},
                        retryable=False,
                    ).to_mapping()
                },
            )()
        )
        service = NotificationIngressService(registry=_StubRegistry(_valid_record()), runtime=runtime)

        with self.assertRaises(NotificationIngressServiceUnavailableError):
            await service.receive(
                plugin_id="quantagent.official.notification.discord",
                request_id="req-1",
                config={},
                receive_input=NotificationReceiveInput(transport="http.webhook"),
            )
