from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

from quantagent.core.registry import PluginManifest, PluginRecord, PluginRegistry, PluginSource, PluginStatus, PluginType
from quantagent.core.registry.models import PluginError
from quantagent.core.runtime import PluginRuntimeService
from quantagent.core.scheduling import (
    FrozenSchedulingClock,
    InMemoryPluginRunRepository,
    IntervalSchedulePolicy,
    PluginRunStatus,
    PluginSchedulingService,
    PluginTriggerRequest,
    PluginTriggerType,
)
from quantagent.core.source_binding import EffectiveSourceConfigComposer, SecretValueRef, SourceBindingTemplate
from quantagent.core.events import InMemoryEventBus
from quantagent.plugin_sdk import BasePlugin, PluginInvokeResult, PluginRuntimeError


class StaticScanner:
    def __init__(self, records: list[PluginRecord]) -> None:
        self._records = records

    def scan(self) -> list[PluginRecord]:
        return list(self._records)


class _RecordingHandler:
    """订阅事件总线后收集收到的 envelope，供测试断言。"""

    def __init__(self) -> None:
        self.envelopes: list[object] = []

    async def handle(self, envelope) -> None:
        self.envelopes.append(envelope)


class PluginSchedulingServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._module_names: list[str] = []
        self.clock = FrozenSchedulingClock(datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc))
        self.repository = InMemoryPluginRunRepository()

    async def asyncTearDown(self) -> None:
        for module_name in self._module_names:
            sys.modules.pop(module_name, None)

    async def test_manual_trigger_success_records_succeeded_run(self) -> None:
        class SuccessPlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(
                    output={"items": [], "count": 0},
                    metadata={"trace_id": request.request_id},
                )

        self._install_module("test_scheduling_success", SuccessPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_success:plugin"))
        request = PluginTriggerRequest(
            plugin_id="quantagent.test.scheduling",
            capability="source.fetch",
            request_id="req-success",
            trigger_type=PluginTriggerType.MANUAL,
            input={"query": "oil"},
            effective_config={"enabled": True},
            metadata={"source": "manual-test"},
        )

        self.clock.advance(seconds=0.25)
        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(run.output_summary["items"], ())
        self.assertEqual(run.output_summary["count"], 0)
        self.assertEqual(run.metadata["source"], "manual-test")
        self.assertIsNone(run.error_summary)
        self.assertEqual(run.duration_ms, 0)
        history = self.repository.get_history(run.run_id)
        self.assertEqual([item.status for item in history], [PluginRunStatus.QUEUED, PluginRunStatus.RUNNING, PluginRunStatus.SUCCEEDED])

    async def test_runtime_structured_failure_records_failed_run(self) -> None:
        class StructuredFailingPlugin(BasePlugin):
            async def invoke(self, request):
                raise PluginRuntimeError(
                    code="PLUGIN_REMOTE_FAILED",
                    message="token=abc123 refused at /home/xxs/private.env",
                    stage="invoke",
                    retryable=True,
                    details={
                        "token": "abc123",
                        "path": "/home/xxs/private.env",
                        "nested": {"cookie": "session=value"},
                        "safe": "visible",
                    },
                )

        self._install_module("test_scheduling_failure", StructuredFailingPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_failure:plugin"))

        self.clock.advance(seconds=0.1)
        run = await service.trigger(self._request(request_id="req-fail"))

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_REMOTE_FAILED")
        self.assertEqual(run.error_summary["stage"], "invoke")
        self.assertEqual(run.error_summary["retryable"], True)
        self.assertNotIn("abc123", run.error_summary["message"])
        self.assertEqual(run.error_summary["details"]["token"], "[REDACTED]")
        self.assertEqual(run.error_summary["details"]["nested"]["cookie"], "[REDACTED]")
        self.assertEqual(run.error_summary["details"]["safe"], "visible")

    async def test_missing_plugin_records_failed_precheck_run(self) -> None:
        registry = PluginRegistry(StaticScanner([]))
        service = PluginSchedulingService(
            registry=registry,
            runtime=PluginRuntimeService(),
            repository=self.repository,
            clock=self.clock,
        )

        run = await service.trigger(self._request(request_id="req-missing"))

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_NOT_FOUND")
        self.assertEqual(run.error_summary["stage"], "schedule_precheck")

    async def test_invalid_plugin_record_is_failed_before_runtime_invoke(self) -> None:
        class NeverReachedPlugin(BasePlugin):
            async def invoke(self, request):
                raise AssertionError("runtime invoke should not be reached for invalid records")

        self._install_module("test_scheduling_invalid_record", NeverReachedPlugin)
        service = self._service(
            self._record(
                entrypoint="test_scheduling_invalid_record:plugin",
                status=PluginStatus.INVALID,
            )
        )

        run = await service.trigger(self._request(request_id="req-invalid-record"))

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_RECORD_NOT_LOADABLE")
        self.assertEqual(run.error_summary["stage"], "load")

    async def test_timeout_records_timeout_run(self) -> None:
        class SlowPlugin(BasePlugin):
            async def invoke(self, request):
                await asyncio.sleep(0.05)
                return PluginInvokeResult(output={"done": True})

        self._install_module("test_scheduling_timeout", SlowPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_timeout:plugin"))

        run = await service.trigger(self._request(request_id="req-timeout", timeout_ms=10))

        self.assertEqual(run.status, PluginRunStatus.TIMEOUT)
        self.assertEqual(run.timeout_ms, 10)
        self.assertEqual(run.error_summary["code"], "PLUGIN_INVOKE_TIMEOUT")
        self.assertEqual(run.error_summary["details"]["timeout_ms"], 10)
        self.assertIsNotNone(run.finished_at)
        self.assertIsNotNone(run.duration_ms)

    async def test_cleanup_failure_after_success_is_recorded_once_as_failed_run(self) -> None:
        class StopFailingPlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(output={"ok": True})

            async def stop(self):
                raise PluginRuntimeError(
                    code="PLUGIN_STOP_FAILED_BY_TEST",
                    message="Plugin stop failed by test.",
                    stage="stop",
                )

        self._install_module("test_scheduling_cleanup_failure", StopFailingPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_cleanup_failure:plugin"))

        run = await service.trigger(self._request(request_id="req-stop-failed"))

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_STOP_FAILED_BY_TEST")
        self.assertNotIn("cleanup_error", run.error_summary["details"])

    async def test_empty_result_is_succeeded_with_empty_summary(self) -> None:
        class EmptyPlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult()

        self._install_module("test_scheduling_empty", EmptyPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_empty:plugin"))

        run = await service.trigger(self._request(request_id="req-empty"))

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(dict(run.output_summary), {})
        self.assertIsNone(run.error_summary)

    async def test_interval_policy_builds_interval_trigger(self) -> None:
        policy = IntervalSchedulePolicy(
            interval_seconds=60,
            jitter_seconds=5,
            metadata={"schedule": "hourly"},
        )

        next_run = policy.next_run_at(self.clock.now(), applied_jitter_seconds=3)
        request = policy.build_trigger_request(
            plugin_id="quantagent.test.scheduling",
            capability="source.fetch",
            request_id="req-interval",
            effective_config={"enabled": True},
            input_payload={"cursor": "next"},
            metadata={"source": "policy"},
        )

        self.assertEqual(next_run, datetime(2026, 5, 28, 8, 1, 3, tzinfo=timezone.utc))
        self.assertEqual(request.trigger_type, PluginTriggerType.INTERVAL)
        self.assertEqual(request.metadata["schedule"], "hourly")
        self.assertEqual(request.metadata["source"], "policy")

    async def test_runtime_context_does_not_expose_scheduler_or_host_objects(self) -> None:
        captured = {}

        class InspectingPlugin(BasePlugin):
            async def invoke(self, request):
                captured["context"] = self.context
                captured["input"] = request.input
                return PluginInvokeResult(output={"ok": True})

        self._install_module("test_scheduling_context", InspectingPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_context:plugin"))

        run = await service.trigger(
            self._request(
                request_id="req-context",
                input_data={"query": "rss"},
                effective_config={"enabled": True},
                metadata={"origin": "test"},
            )
        )

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        context = captured["context"]
        for forbidden in ("db", "session", "scheduler", "event_bus", "service", "secret_resolver"):
            self.assertFalse(hasattr(context, forbidden))
        self.assertNotIn("scheduler", captured["input"])

    async def test_source_plugin_receives_flat_runtime_config_from_effective_config_snapshot(self) -> None:
        captured = {}

        class InspectingSourcePlugin(BasePlugin):
            async def invoke(self, request):
                captured["config"] = self.context.config
                return PluginInvokeResult(output={"ok": True, "feeds": self.context.config["feeds"]})

        self._install_module("test_scheduling_source_effective_config", InspectingSourcePlugin)
        service = self._service(self._record(entrypoint="test_scheduling_source_effective_config:plugin"))
        snapshot = EffectiveSourceConfigComposer().compose(
            template=SourceBindingTemplate(
                source_plugin_id="quantagent.test.scheduling",
                required=True,
                config_override={"feeds": ["https://feeds.example.com/runtime.xml"]},
            ),
            plugin_schema={
                "type": "object",
                "properties": {
                    "feeds": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["feeds"],
                "additionalProperties": False,
            },
        )

        run = await service.trigger(
            self._request(
                request_id="req-effective-config",
                effective_config=snapshot.to_mapping(),
            )
        )

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(captured["config"]["feeds"], ("https://feeds.example.com/runtime.xml",))
        self.assertNotIn("config_fingerprint", captured["config"])

    async def test_source_plugin_resolves_runtime_secret_refs_from_effective_config_snapshot(self) -> None:
        captured = {}

        class InspectingSourcePlugin(BasePlugin):
            async def invoke(self, request):
                captured["config"] = self.context.config
                return PluginInvokeResult(output={"ok": True})

        self._install_module("test_scheduling_source_secret_resolution", InspectingSourcePlugin)
        service = self._service(self._record(entrypoint="test_scheduling_source_secret_resolution:plugin"))
        snapshot = EffectiveSourceConfigComposer().compose(
            template=SourceBindingTemplate(
                source_plugin_id="quantagent.test.scheduling",
                required=True,
                config_override={
                    "api_key_ref": SecretValueRef(secret_ref="env://TAVILY_API_KEY").to_mapping(),
                    "timeout_seconds": 8,
                },
            ),
            plugin_schema={
                "type": "object",
                "properties": {
                    "api_key_ref": {
                        "type": "object",
                        "properties": {"secret_ref": {"type": "string"}, "metadata": {"type": "object"}},
                        "required": ["secret_ref"],
                        "additionalProperties": False,
                    },
                    "timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 30},
                },
                "required": ["api_key_ref"],
                "additionalProperties": False,
            },
        )

        old_value = os.environ.get("TAVILY_API_KEY")
        os.environ["TAVILY_API_KEY"] = "runtime-secret-value"
        try:
            run = await service.trigger(
                self._request(
                    request_id="req-effective-config-secret",
                    effective_config=snapshot.to_mapping(),
                )
            )
        finally:
            if old_value is None:
                os.environ.pop("TAVILY_API_KEY", None)
            else:
                os.environ["TAVILY_API_KEY"] = old_value

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(captured["config"]["api_key_ref"], "runtime-secret-value")
        self.assertEqual(captured["config"]["timeout_seconds"], 8)

    async def test_source_plugin_fails_when_effective_config_plugin_id_mismatches_manifest(self) -> None:
        class NeverReachedPlugin(BasePlugin):
            async def invoke(self, request):
                raise AssertionError("runtime invoke should not be reached for plugin id mismatch")

        self._install_module("test_scheduling_source_plugin_mismatch", NeverReachedPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_source_plugin_mismatch:plugin"))
        snapshot = EffectiveSourceConfigComposer().compose(
            template=SourceBindingTemplate(
                source_plugin_id="quantagent.official.source.other",
                required=True,
                config_override={"feeds": ["https://feeds.example.com/runtime.xml"]},
            ),
            plugin_schema={
                "type": "object",
                "properties": {
                    "feeds": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["feeds"],
                "additionalProperties": False,
            },
        )

        run = await service.trigger(
            self._request(
                request_id="req-effective-config-plugin-mismatch",
                effective_config=snapshot.to_mapping(),
            )
        )

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_EFFECTIVE_CONFIG_PLUGIN_MISMATCH")
        self.assertEqual(run.error_summary["stage"], "invoke")
        self.assertEqual(run.error_summary["details"]["plugin_id"], "quantagent.test.scheduling")
        self.assertEqual(run.error_summary["details"]["source_plugin_id"], "quantagent.official.source.other")

    async def test_concurrent_triggers_keep_run_state_isolated(self) -> None:
        release = asyncio.Event()

        class ConcurrentPlugin(BasePlugin):
            async def invoke(self, request):
                await release.wait()
                return PluginInvokeResult(
                    output={
                        "request_id": request.request_id,
                        "origin": request.metadata["origin"],
                        "query": request.input["query"],
                    }
                )

        self._install_module("test_scheduling_concurrent", ConcurrentPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_concurrent:plugin"))

        first_task = asyncio.create_task(
            service.trigger(
                self._request(
                    request_id="req-concurrent-a",
                    input_data={"query": "rss-a"},
                    metadata={"origin": "worker-a"},
                )
            )
        )
        second_task = asyncio.create_task(
            service.trigger(
                self._request(
                    request_id="req-concurrent-b",
                    input_data={"query": "rss-b"},
                    metadata={"origin": "worker-b"},
                )
            )
        )
        await asyncio.sleep(0)
        release.set()

        first, second = await asyncio.gather(first_task, second_task)

        self.assertNotEqual(first.run_id, second.run_id)
        self.assertEqual(first.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(second.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(first.request_id, "req-concurrent-a")
        self.assertEqual(second.request_id, "req-concurrent-b")
        self.assertEqual(first.metadata["origin"], "worker-a")
        self.assertEqual(second.metadata["origin"], "worker-b")
        self.assertEqual(first.output_summary["request_id"], "req-concurrent-a")
        self.assertEqual(second.output_summary["request_id"], "req-concurrent-b")
        self.assertEqual(first.output_summary["origin"], "worker-a")
        self.assertEqual(second.output_summary["origin"], "worker-b")
        self.assertEqual(first.output_summary["query"], "rss-a")
        self.assertEqual(second.output_summary["query"], "rss-b")
        self.assertEqual(
            [item.status for item in self.repository.get_history(first.run_id)],
            [PluginRunStatus.QUEUED, PluginRunStatus.RUNNING, PluginRunStatus.SUCCEEDED],
        )
        self.assertEqual(
            [item.status for item in self.repository.get_history(second.run_id)],
            [PluginRunStatus.QUEUED, PluginRunStatus.RUNNING, PluginRunStatus.SUCCEEDED],
        )
        self.assertEqual({record.run_id for record in self.repository.list()}, {first.run_id, second.run_id})

    async def test_non_json_safe_payload_is_failed_without_runtime_invoke(self) -> None:
        class NeverReachedPlugin(BasePlugin):
            async def invoke(self, request):
                raise AssertionError("runtime invoke should not be reached for invalid payloads")

        self._install_module("test_scheduling_invalid_payload", NeverReachedPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_invalid_payload:plugin"))
        request = self._request(request_id="req-invalid")
        object.__setattr__(request, "input", {"bad": object()})

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_DTO_VALIDATION_FAILED")
        self.assertEqual(run.error_summary["stage"], "invoke")

    async def test_non_json_safe_metadata_is_failed_without_escaping(self) -> None:
        class NeverReachedPlugin(BasePlugin):
            async def invoke(self, request):
                raise AssertionError("runtime invoke should not be reached for invalid metadata")

        self._install_module("test_scheduling_invalid_metadata", NeverReachedPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_invalid_metadata:plugin"))
        request = self._request(request_id="req-invalid-metadata")
        object.__setattr__(request, "metadata", {"scheduler": object()})

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_DTO_VALIDATION_FAILED")
        self.assertEqual(run.error_summary["stage"], "schedule_precheck")

    async def test_failed_precheck_run_duration_starts_when_run_enters_running(self) -> None:
        class ExplodingRegistry(PluginRegistry):
            def get_plugin(inner_self, plugin_id):
                self.clock.advance(seconds=2)
                raise RuntimeError("registry unavailable")

        service = PluginSchedulingService(
            registry=ExplodingRegistry(StaticScanner([])),
            runtime=PluginRuntimeService(),
            repository=self.repository,
            clock=self.clock,
        )

        self.clock.advance(seconds=0.25)
        run = await service.trigger(self._request(request_id="req-duration"))

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_SCHEDULING_FAILED")
        self.assertEqual(run.duration_ms, 0)

    async def test_error_summary_freeze_preserves_error_stage(self) -> None:
        class BadDetailPlugin(BasePlugin):
            async def invoke(self, request):
                raise PluginRuntimeError(
                    code="PLUGIN_BAD_DETAIL",
                    message="bad detail",
                    stage="load",
                    details={"bad": object()},
                )

        self._install_module("test_scheduling_bad_detail", BadDetailPlugin)
        service = self._service(self._record(entrypoint="test_scheduling_bad_detail:plugin"))

        run = await service.trigger(self._request(request_id="req-bad-detail"))

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.error_summary["code"], "PLUGIN_BAD_DETAIL")
        self.assertEqual(run.error_summary["stage"], "load")
        self.assertEqual(run.error_summary["details"]["bad"], "[UNSERIALIZABLE:object]")

    async def test_nested_cleanup_error_summary_preserves_cleanup_stage(self) -> None:
        summary = self._error_summary(
            PluginError(
                code="PLUGIN_INVOKE_FAILED_BY_TEST",
                message="invoke failed",
                stage="invoke",
            ),
            cleanup_error=PluginError(
                code="PLUGIN_STOP_FAILED_BY_TEST",
                message="stop failed",
                stage="stop",
            ),
        )

        self.assertEqual(summary["stage"], "invoke")
        self.assertEqual(summary["details"]["cleanup_error"]["stage"], "stop")

    async def test_frozen_clock_requires_timezone_aware_datetime(self) -> None:
        with self.assertRaises(ValueError):
            FrozenSchedulingClock(datetime(2026, 5, 28, 8, 0))

    async def test_identifier_fields_raise_value_error_for_non_strings(self) -> None:
        with self.assertRaises(ValueError):
            PluginTriggerRequest(
                plugin_id=object(),  # type: ignore[arg-type]
                capability="source.fetch",
                request_id="req-bad-id",
                trigger_type=PluginTriggerType.MANUAL,
            )

    async def test_tampered_identifier_is_failed_without_escaping(self) -> None:
        request = self._request(request_id="req-tampered-id")
        object.__setattr__(request, "plugin_id", object())
        service = self._service(self._record(entrypoint="missing_module:plugin"))

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.FAILED)
        self.assertEqual(run.plugin_id, "invalid-plugin-id")
        self.assertEqual(run.error_summary["code"], "PLUGIN_SCHEDULING_FAILED")

    # ── 事件发布桥接测试 ──

    def _service_with_publisher(self, record: PluginRecord, bus: InMemoryEventBus) -> PluginSchedulingService:
        registry = PluginRegistry(StaticScanner([record]))
        return PluginSchedulingService(
            registry=registry,
            runtime=PluginRuntimeService(),
            repository=self.repository,
            clock=self.clock,
            publisher=bus,
        )

    async def test_trigger_publishes_source_event_with_binding_when_publisher_provided(self) -> None:
        """有 publisher 且请求带 binding_id 时 source.fetch 成功 → 下游收到可路由事件。"""

        bus = InMemoryEventBus()
        handler = _RecordingHandler()
        await bus.subscribe(topics=["source.event.captured"], group_id="test-group", handler=handler)

        class SourcePlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(
                    output={"items": [{"external_id": "a1", "title": "Test"}], "metadata": {}},
                )

        self._install_module("test_publish_source", SourcePlugin)
        service = self._service_with_publisher(self._record(entrypoint="test_publish_source:plugin"), bus)
        request = self._request(request_id="req-publish-1", binding_id="binding-manual-001")

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(len(handler.envelopes), 1)
        envelope = handler.envelopes[0]
        self.assertEqual(envelope.topic, "source.event.captured")
        self.assertIn("plugin_id", envelope.payload)
        self.assertEqual(envelope.payload["plugin_id"], "quantagent.test.scheduling")
        self.assertEqual(envelope.payload["binding_id"], "binding-manual-001")
        self.assertEqual(envelope.headers["binding_id"], "binding-manual-001")

    async def test_trigger_does_not_publish_source_event_without_binding_id(self) -> None:
        """source.event.captured 缺 binding_id 会让 worker 走 missing-binding，生产侧必须拦住。"""

        bus = InMemoryEventBus()
        handler = _RecordingHandler()
        await bus.subscribe(topics=["source.event.captured"], group_id="test-group", handler=handler)

        class SourcePlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(
                    output={"items": [{"external_id": "a1", "title": "Test"}], "metadata": {}},
                )

        self._install_module("test_publish_source_without_binding", SourcePlugin)
        service = self._service_with_publisher(self._record(entrypoint="test_publish_source_without_binding:plugin"), bus)
        request = self._request(request_id="req-publish-no-binding")

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(len(handler.envelopes), 0)

    async def test_trigger_without_publisher_behaves_identically(self) -> None:
        """无 publisher 时行为不变"""

        class SuccessPlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(output={"items": []})

        self._install_module("test_no_publisher", SuccessPlugin)
        service = self._service(self._record(entrypoint="test_no_publisher:plugin"))
        request = self._request(request_id="req-no-pub-1")

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)

    async def test_trigger_does_not_publish_for_non_source_capability(self) -> None:
        """非 source.fetch capability 不发布事件"""

        bus = InMemoryEventBus()
        handler = _RecordingHandler()
        await bus.subscribe(topics=["source.event.captured"], group_id="test-group", handler=handler)

        class NotifyPlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(output={"accepted": True})

        self._install_module("test_notify_cap", NotifyPlugin)
        record = PluginRecord(
            id="quantagent.test.scheduling",
            source=PluginSource.OFFICIAL,
            path=Path(tempfile.gettempdir()),
            status=PluginStatus.VALID,
            manifest=PluginManifest(
                id="quantagent.test.scheduling",
                name="Notify Test",
                type=PluginType.SOURCE,
                version="0.1.0",
                entrypoint="test_notify_cap:plugin",
                capabilities=("notification.send",),
                config_schema="config.schema.json",
            ),
        )
        service = self._service_with_publisher(record, bus)
        request = PluginTriggerRequest(
            plugin_id="quantagent.test.scheduling",
            capability="notification.send",
            request_id="req-notify-1",
            trigger_type=PluginTriggerType.MANUAL,
            input={},
            effective_config={"enabled": True},
        )

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(len(handler.envelopes), 0)

    async def test_trigger_publish_failure_does_not_affect_run_record(self) -> None:
        """发布失败不影响 PluginRunRecord 状态"""

        class FailingPublisher:
            async def publish(self, envelope):
                raise RuntimeError("publish failed")

        class SourcePlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(output={"items": [{"external_id": "x"}]})

        self._install_module("test_publish_fail", SourcePlugin)
        registry = PluginRegistry(StaticScanner([self._record(entrypoint="test_publish_fail:plugin")]))
        service = PluginSchedulingService(
            registry=registry,
            runtime=PluginRuntimeService(),
            repository=self.repository,
            clock=self.clock,
            publisher=FailingPublisher(),
        )
        request = self._request(request_id="req-fail-pub-1")

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)

    async def test_trigger_publish_failure_on_invalid_output_does_not_affect_run_record(self) -> None:
        """插件返回非法 SourceFetchResult 结构时 from_mapping 抛异常，但不影响调度记录"""

        bus = InMemoryEventBus()
        handler = _RecordingHandler()
        await bus.subscribe(topics=["source.event.captured"], group_id="test-group", handler=handler)

        class BadOutputPlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(output={"items": "not_a_list"})

        self._install_module("test_bad_output_publish", BadOutputPlugin)
        service = self._service_with_publisher(self._record(entrypoint="test_bad_output_publish:plugin"), bus)
        request = self._request(request_id="req-bad-output-1")

        run = await service.trigger(request)

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        # from_mapping 对 items="not_a_list" 会抛异常，被 catch 吞掉，不发布任何事件
        self.assertEqual(len(handler.envelopes), 0)

    async def test_concurrent_triggers_with_publisher_publish_independently(self) -> None:
        """并发 trigger 带 publisher 时，各自独立发布事件且不交叉"""
        release = asyncio.Event()

        bus = InMemoryEventBus()
        handler = _RecordingHandler()
        await bus.subscribe(topics=["source.event.captured"], group_id="test-group", handler=handler)

        class SlowSourcePlugin(BasePlugin):
            async def invoke(self, request):
                await release.wait()
                return PluginInvokeResult(
                    output={"items": [{"external_id": request.request_id}]},
                )

        self._install_module("test_concurrent_publish", SlowSourcePlugin)
        service = self._service_with_publisher(self._record(entrypoint="test_concurrent_publish:plugin"), bus)

        first_task = asyncio.create_task(
            service.trigger(self._request(request_id="req-conc-a", binding_id="binding-conc-a"))
        )
        second_task = asyncio.create_task(
            service.trigger(self._request(request_id="req-conc-b", binding_id="binding-conc-b"))
        )
        await asyncio.sleep(0)
        release.set()

        first, second = await asyncio.gather(first_task, second_task)

        self.assertEqual(first.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(second.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(len(handler.envelopes), 2)
        event_plugin_ids = {e.payload["plugin_id"] for e in handler.envelopes}
        self.assertEqual(event_plugin_ids, {"quantagent.test.scheduling"})
        event_binding_ids = {e.payload["binding_id"] for e in handler.envelopes}
        self.assertEqual(event_binding_ids, {"binding-conc-a", "binding-conc-b"})

    def _service(self, record: PluginRecord) -> PluginSchedulingService:
        registry = PluginRegistry(StaticScanner([record]))
        return PluginSchedulingService(
            registry=registry,
            runtime=PluginRuntimeService(),
            repository=self.repository,
            clock=self.clock,
        )

    def _request(
        self,
        *,
        request_id: str,
        input_data: dict[str, object] | None = None,
        effective_config: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        binding_id: str | None = None,
        timeout_ms: int | None = None,
    ) -> PluginTriggerRequest:
        return PluginTriggerRequest(
            plugin_id="quantagent.test.scheduling",
            capability="source.fetch",
            request_id=request_id,
            trigger_type=PluginTriggerType.MANUAL,
            input=input_data or {},
            effective_config=effective_config or {"enabled": True},
            metadata=metadata or {},
            binding_id=binding_id,
            timeout_ms=timeout_ms,
        )

    def _install_module(self, module_name: str, plugin) -> None:
        module = types.ModuleType(module_name)
        module.plugin = plugin
        sys.modules[module_name] = module
        self._module_names.append(module_name)

    def _record(
        self,
        *,
        entrypoint: str,
        status: PluginStatus = PluginStatus.VALID,
    ) -> PluginRecord:
        return PluginRecord(
            id="quantagent.test.scheduling",
            source=PluginSource.OFFICIAL,
            path=Path(tempfile.gettempdir()),
            status=status,
            manifest=PluginManifest(
                id="quantagent.test.scheduling",
                name="Scheduling Test",
                type=PluginType.SOURCE,
                version="0.1.0",
                entrypoint=entrypoint,
                capabilities=("source.fetch",),
                config_schema="config.schema.json",
            ),
        )

    def _error_summary(
        self,
        error: PluginError,
        *,
        cleanup_error: PluginError | None = None,
    ):
        from quantagent.core.scheduling.service import _error_to_summary

        return _error_to_summary(error, cleanup_error=cleanup_error)


if __name__ == "__main__":
    unittest.main()
