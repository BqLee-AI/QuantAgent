from __future__ import annotations

import unittest
from pathlib import Path

from quantagent.core.notifications import (
    InMemoryNotificationApprovalHandoff,
    InMemoryNotificationIngressAuditSink,
    InMemoryNotificationReceiveFactRepository,
)
from quantagent.core.notifications.ingress import (
    NotificationIngressService,
    NotificationIngressServiceUnavailableError,
)
from quantagent.core.registry import PluginManifest, PluginRecord, PluginSource, PluginStatus, PluginType
from quantagent.plugin_sdk import NotificationReceiveInput, NotificationReceiveItem, NotificationReceiveResult


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


class _FailingHandoff:
    async def handoff(self, _request):
        raise RuntimeError("handoff unavailable")


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
        repository = InMemoryNotificationReceiveFactRepository()
        audit_sink = InMemoryNotificationIngressAuditSink()
        handoff = InMemoryNotificationApprovalHandoff()
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
        service = NotificationIngressService(
            registry=_StubRegistry(_valid_record()),
            runtime=runtime,
            repository=repository,
            audit_sink=audit_sink,
            approval_handoff=handoff,
        )

        result = await service.receive(
            plugin_id="quantagent.official.notification.discord",
            request_id="req-1",
            config={},
            receive_input=NotificationReceiveInput(transport="http.webhook"),
        )

        self.assertTrue(result.accepted)
        self.assertIsNone(result.receive_result.item)
        self.assertIsNone(result.receive_fact)
        self.assertIsNone(result.approval_handoff)
        self.assertEqual(list(repository.list()), [])
        self.assertEqual(list(audit_sink.list()), [])
        self.assertEqual(list(handoff.list()), [])

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

    async def test_receive_records_fact_and_calls_handoff_when_item_exists(self) -> None:
        repository = InMemoryNotificationReceiveFactRepository()
        audit_sink = InMemoryNotificationIngressAuditSink()
        handoff = InMemoryNotificationApprovalHandoff()
        runtime = _StubRuntime(
            result=type(
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
                            interaction_id="int-1",
                            source_id="discord.interaction:app-1",
                            text="approve this action",
                            payload_summary={"command_name": "approve"},
                            guild_id="guild-1",
                            channel_id="channel-1",
                            author_id="user-1",
                            metadata={"plugin_id": "quantagent.official.notification.discord"},
                        ),
                        retryable=False,
                        metadata={"receive_stage": "validated"},
                    ).to_mapping()
                },
            )()
        )
        service = NotificationIngressService(
            registry=_StubRegistry(_valid_record()),
            runtime=runtime,
            repository=repository,
            audit_sink=audit_sink,
            approval_handoff=handoff,
        )

        result = await service.receive(
            plugin_id="quantagent.official.notification.discord",
            request_id="req-42",
            config={},
            receive_input=NotificationReceiveInput(
                transport="http.webhook",
                request_metadata={"request_id": "req-42", "correlation_id": "corr-42"},
            ),
        )

        assert result.receive_fact is not None
        assert result.approval_handoff is not None
        self.assertEqual(result.receive_fact.request_id, "req-42")
        self.assertEqual(result.receive_fact.correlation_id, "corr-42")
        self.assertEqual(result.receive_fact.interaction_id, "int-1")
        self.assertEqual(result.receive_fact.text, "approve this action")
        self.assertEqual(result.approval_handoff.status, "queued")

        facts = list(repository.list())
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].fact_id, result.receive_fact.fact_id)

        handoff_requests = list(handoff.list())
        self.assertEqual(len(handoff_requests), 1)
        self.assertEqual(handoff_requests[0].fact_id, result.receive_fact.fact_id)
        self.assertEqual(handoff_requests[0].correlation_id, "corr-42")

        audit_entries = list(audit_sink.list())
        self.assertEqual([entry.event_type for entry in audit_entries], [
            "notification.receive.recorded",
            "notification.receive.approval_handoff",
        ])
        self.assertEqual(audit_entries[0].details["fact_id"], result.receive_fact.fact_id)
        self.assertEqual(audit_entries[1].details["handoff_status"], "queued")

    async def test_receive_does_not_record_fact_or_handoff_when_not_accepted(self) -> None:
        repository = InMemoryNotificationReceiveFactRepository()
        audit_sink = InMemoryNotificationIngressAuditSink()
        handoff = InMemoryNotificationApprovalHandoff()
        runtime = _StubRuntime(
            result=type(
                "PluginResult",
                (),
                {
                    "output": NotificationReceiveResult(
                        accepted=False,
                        code="SIGNATURE_INVALID",
                        message="bad signature",
                        response_status_code=401,
                        response={"error": "SIGNATURE_INVALID"},
                        item=NotificationReceiveItem(
                            interaction_id="int-1",
                            source_id="discord.interaction:app-1",
                            text="should not persist",
                            payload_summary={},
                            metadata={},
                        ),
                        retryable=False,
                    ).to_mapping()
                },
            )()
        )
        service = NotificationIngressService(
            registry=_StubRegistry(_valid_record()),
            runtime=runtime,
            repository=repository,
            audit_sink=audit_sink,
            approval_handoff=handoff,
        )

        result = await service.receive(
            plugin_id="quantagent.official.notification.discord",
            request_id="req-5",
            config={},
            receive_input=NotificationReceiveInput(transport="http.webhook"),
        )

        self.assertFalse(result.accepted)
        self.assertIsNone(result.receive_fact)
        self.assertIsNone(result.approval_handoff)
        self.assertEqual(list(repository.list()), [])
        self.assertEqual(list(audit_sink.list()), [])
        self.assertEqual(list(handoff.list()), [])

    async def test_receive_keeps_fact_and_audits_failure_when_handoff_raises(self) -> None:
        repository = InMemoryNotificationReceiveFactRepository()
        audit_sink = InMemoryNotificationIngressAuditSink()
        runtime = _StubRuntime(
            result=type(
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
                            interaction_id="int-2",
                            source_id="discord.interaction:app-1",
                            text="handoff should fail",
                            payload_summary={"command_name": "approve"},
                            metadata={},
                        ),
                        retryable=False,
                    ).to_mapping()
                },
            )()
        )
        service = NotificationIngressService(
            registry=_StubRegistry(_valid_record()),
            runtime=runtime,
            repository=repository,
            audit_sink=audit_sink,
            approval_handoff=_FailingHandoff(),
        )

        result = await service.receive(
            plugin_id="quantagent.official.notification.discord",
            request_id="req-6",
            config={},
            receive_input=NotificationReceiveInput(
                transport="http.webhook",
                request_metadata={"correlation_id": "corr-6"},
            ),
        )

        assert result.receive_fact is not None
        assert result.approval_handoff is not None
        self.assertEqual(result.approval_handoff.status, "failed")
        self.assertEqual(len(list(repository.list())), 1)

        audit_entries = list(audit_sink.list())
        self.assertEqual([entry.event_type for entry in audit_entries], [
            "notification.receive.recorded",
            "notification.receive.approval_handoff_failed",
        ])
        self.assertEqual(audit_entries[1].details["fact_id"], result.receive_fact.fact_id)
        self.assertEqual(audit_entries[1].details["handoff_status"], "failed")
        self.assertEqual(audit_entries[1].details["error_type"], "RuntimeError")
