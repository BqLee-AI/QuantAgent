from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

from quantagent.core.registry import PluginManifest, PluginRecord, PluginSource, PluginStatus, PluginType
from quantagent.core.runtime import PluginRuntimeService
from quantagent.plugin_sdk import BasePlugin, PluginInvokeResult, PluginRuntimeError


class PlainRuntimePlugin:
    def __init__(self) -> None:
        self.loaded_config = None
        self.started = False
        self.stopped = False

    async def load(self, context):
        self.loaded_config = context.config

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    async def health_check(self):
        from quantagent.plugin_sdk import HealthCheckResult

        return HealthCheckResult(status="ok")

    async def invoke(self, request):
        return PluginInvokeResult(output={"capability": request.capability, "configured": self.loaded_config["enabled"]})


class BaseRuntimePlugin(BasePlugin):
    async def invoke(self, request):
        return PluginInvokeResult(output={"base": True, "request_id": request.request_id})


class PluginRuntimeServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._module_names: list[str] = []

    async def asyncTearDown(self) -> None:
        for module_name in self._module_names:
            sys.modules.pop(module_name, None)

    async def test_invokes_protocol_plugin_without_base_class(self) -> None:
        created_plugins = []

        def create_plugin():
            plugin = PlainRuntimePlugin()
            created_plugins.append(plugin)
            return plugin

        self._install_module("test_runtime_plain", create_plugin)
        record = self._record(entrypoint="test_runtime_plain:plugin")

        invocation = await PluginRuntimeService().invoke(
            record,
            capability="source.fetch",
            request_id="req-1",
            config={"enabled": True},
        )

        self.assertTrue(invocation.ok)
        self.assertEqual(invocation.result.output["capability"], "source.fetch")
        self.assertTrue(invocation.result.output["configured"])
        plugin = created_plugins[0]
        self.assertTrue(plugin.started)
        self.assertTrue(plugin.stopped)

    async def test_invokes_base_plugin_and_default_lifecycle(self) -> None:
        self._install_module("test_runtime_base", BaseRuntimePlugin)
        record = self._record(entrypoint="test_runtime_base:plugin")

        invocation = await PluginRuntimeService().invoke(
            record,
            capability="source.fetch",
            request_id="req-2",
        )

        self.assertTrue(invocation.ok)
        self.assertEqual(invocation.result.output["base"], True)
        self.assertEqual(invocation.result.output["request_id"], "req-2")

    async def test_invalid_record_is_rejected_before_loading(self) -> None:
        record = self._record(status=PluginStatus.INVALID)

        plugin, error = await PluginRuntimeService().load_plugin(record, request_id="req-1")

        self.assertIsNone(plugin)
        self.assertEqual(error.code, "PLUGIN_RECORD_NOT_LOADABLE")
        self.assertEqual(error.stage, "load")

    async def test_entrypoint_load_failure_returns_structured_error(self) -> None:
        record = self._record(entrypoint="missing_runtime_module:plugin")

        plugin, error = await PluginRuntimeService().load_plugin(record, request_id="req-1")

        self.assertIsNone(plugin)
        self.assertEqual(error.stage, "load")
        self.assertEqual(error.code, "PLUGIN_LOAD_FAILED")
        self.assertEqual(error.details["error_type"], "ModuleNotFoundError")

    async def test_missing_capability_returns_invoke_error(self) -> None:
        self._install_module("test_runtime_capability", PlainRuntimePlugin)
        record = self._record(entrypoint="test_runtime_capability:plugin")

        invocation = await PluginRuntimeService().invoke(record, capability="source.search", request_id="req-1")

        self.assertFalse(invocation.ok)
        self.assertEqual(invocation.error.code, "PLUGIN_CAPABILITY_UNAVAILABLE")
        self.assertEqual(invocation.error.stage, "invoke")

    async def test_plugin_exception_is_wrapped_as_structured_error(self) -> None:
        class FailingPlugin(BasePlugin):
            async def invoke(self, request):
                raise RuntimeError("secret token should not leak")

        self._install_module("test_runtime_failing", FailingPlugin)
        record = self._record(entrypoint="test_runtime_failing:plugin")

        invocation = await PluginRuntimeService().invoke(record, capability="source.fetch", request_id="req-1")

        self.assertFalse(invocation.ok)
        self.assertEqual(invocation.error.code, "PLUGIN_INVOKE_FAILED")
        self.assertEqual(invocation.error.stage, "invoke")
        self.assertEqual(invocation.error.details["error_type"], "RuntimeError")
        self.assertNotIn("secret token", invocation.error.message)

    async def test_runtime_context_does_not_expose_host_internals(self) -> None:
        captured = {}

        class InspectingPlugin(BasePlugin):
            async def invoke(self, request):
                captured["context"] = self.context
                return PluginInvokeResult()

        self._install_module("test_runtime_context", InspectingPlugin)
        record = self._record(entrypoint="test_runtime_context:plugin")

        invocation = await PluginRuntimeService().invoke(record, capability="source.fetch", request_id="req-1")

        self.assertTrue(invocation.ok)
        context = captured["context"]
        for forbidden in ("db", "session", "scheduler", "event_bus", "service", "secret_resolver"):
            self.assertFalse(hasattr(context, forbidden))

    async def test_validated_config_is_injected_into_runtime_context(self) -> None:
        captured = {}

        class ConfigPlugin(BasePlugin):
            async def invoke(self, request):
                captured["config"] = self.context.config
                return PluginInvokeResult(output={"configured": self.context.config["enabled"]})

        self._install_module("test_runtime_config", ConfigPlugin)
        record = self._record(entrypoint="test_runtime_config:plugin")

        invocation = await PluginRuntimeService().invoke(
            record,
            capability="source.fetch",
            request_id="req-1",
            config={"enabled": True},
        )

        self.assertTrue(invocation.ok)
        self.assertTrue(invocation.result.output["configured"])
        with self.assertRaises(TypeError):
            captured["config"]["enabled"] = False

    async def test_async_lifecycle_methods_are_awaited_in_order(self) -> None:
        events = []

        class AsyncLifecyclePlugin(BasePlugin):
            async def load(self, context):
                await asyncio.sleep(0)
                await super().load(context)
                events.append(("load", context.request_id))

            async def start(self):
                await asyncio.sleep(0)
                events.append(("start", self.context.request_id))

            async def invoke(self, request):
                await asyncio.sleep(0)
                events.append(("invoke", request.request_id))
                return PluginInvokeResult(output={"request_id": request.request_id})

            async def stop(self):
                await asyncio.sleep(0)
                events.append(("stop", self.context.request_id))

        self._install_module("test_runtime_async_lifecycle", AsyncLifecyclePlugin)
        record = self._record(entrypoint="test_runtime_async_lifecycle:plugin")

        invocation = await PluginRuntimeService().invoke(record, capability="source.fetch", request_id="req-async")

        self.assertTrue(invocation.ok)
        self.assertEqual(
            events,
            [
                ("load", "req-async"),
                ("start", "req-async"),
                ("invoke", "req-async"),
                ("stop", "req-async"),
            ],
        )

    async def test_concurrent_class_entrypoint_invocations_keep_context_isolated(self) -> None:
        class ConcurrentPlugin(BasePlugin):
            async def invoke(self, request):
                before_sleep = self.context.request_id
                await asyncio.sleep(0.01)
                return PluginInvokeResult(
                    output={
                        "request_id": request.request_id,
                        "context_request_id": self.context.request_id,
                        "before_sleep": before_sleep,
                    }
                )

        self._install_module("test_runtime_concurrent", ConcurrentPlugin)
        record = self._record(entrypoint="test_runtime_concurrent:plugin")
        runtime = PluginRuntimeService()

        first, second = await asyncio.gather(
            runtime.invoke(record, capability="source.fetch", request_id="req-a"),
            runtime.invoke(record, capability="source.fetch", request_id="req-b"),
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(first.result.output["request_id"], "req-a")
        self.assertEqual(first.result.output["context_request_id"], "req-a")
        self.assertEqual(first.result.output["before_sleep"], "req-a")
        self.assertEqual(second.result.output["request_id"], "req-b")
        self.assertEqual(second.result.output["context_request_id"], "req-b")
        self.assertEqual(second.result.output["before_sleep"], "req-b")

    async def test_concurrent_factory_entrypoint_invocations_keep_context_isolated(self) -> None:
        class ConcurrentFactoryPlugin(BasePlugin):
            async def invoke(self, request):
                before_sleep = self.context.request_id
                await asyncio.sleep(0.01)
                return PluginInvokeResult(
                    output={
                        "request_id": request.request_id,
                        "context_request_id": self.context.request_id,
                        "before_sleep": before_sleep,
                    }
                )

        self._install_module("test_runtime_concurrent_factory", lambda: ConcurrentFactoryPlugin())
        record = self._record(entrypoint="test_runtime_concurrent_factory:plugin")
        runtime = PluginRuntimeService()

        first, second = await asyncio.gather(
            runtime.invoke(record, capability="source.fetch", request_id="req-factory-a"),
            runtime.invoke(record, capability="source.fetch", request_id="req-factory-b"),
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(first.result.output["context_request_id"], "req-factory-a")
        self.assertEqual(first.result.output["before_sleep"], "req-factory-a")
        self.assertEqual(second.result.output["context_request_id"], "req-factory-b")
        self.assertEqual(second.result.output["before_sleep"], "req-factory-b")

    async def test_plugin_path_entrypoint_loads_same_module_name_in_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_plugin_dir = root / "first"
            second_plugin_dir = root / "second"
            self._write_plugin_module(first_plugin_dir, origin="first")
            self._write_plugin_module(second_plugin_dir, origin="second")

            runtime = PluginRuntimeService()
            first, second = await asyncio.gather(
                runtime.invoke(
                    self._record(plugin_id="quantagent.test.runtime.first", entrypoint="plugin:plugin", path=first_plugin_dir),
                    capability="source.fetch",
                    request_id="req-first",
                ),
                runtime.invoke(
                    self._record(plugin_id="quantagent.test.runtime.second", entrypoint="plugin:plugin", path=second_plugin_dir),
                    capability="source.fetch",
                    request_id="req-second",
                ),
            )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(first.result.output["origin"], "first")
        self.assertEqual(second.result.output["origin"], "second")
        self.assertNotIn("plugin", sys.modules)
        self.assertFalse(any(module_name.startswith("_quantagent_plugin_") for module_name in sys.modules))

    async def test_plugin_path_entrypoint_does_not_leak_synthetic_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugin"
            self._write_plugin_module(plugin_dir, origin="leak-check")

            invocation = await PluginRuntimeService().invoke(
                self._record(entrypoint="plugin:plugin", path=plugin_dir),
                capability="source.fetch",
                request_id="req-leak",
            )

        self.assertTrue(invocation.ok)
        self.assertFalse(any(module_name.startswith("_quantagent_plugin_") for module_name in sys.modules))

    async def test_plugin_path_entrypoint_does_not_depend_on_current_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            plugin_dir = root / "plugins" / "cwd-safe"
            other_cwd = root / "other"
            other_cwd.mkdir()
            self._write_plugin_module(plugin_dir, origin="cwd-safe")
            old_cwd = Path.cwd()
            try:
                os.chdir(other_cwd)
                invocation = await PluginRuntimeService().invoke(
                    self._record(entrypoint="plugin:plugin", path=plugin_dir.resolve()),
                    capability="source.fetch",
                    request_id="req-cwd",
                )
            finally:
                os.chdir(old_cwd)

        self.assertTrue(invocation.ok)
        self.assertEqual(invocation.result.output["origin"], "cwd-safe")

    async def test_singleton_object_entrypoint_is_rejected_to_avoid_context_races(self) -> None:
        self._install_module("test_runtime_singleton", PlainRuntimePlugin())
        record = self._record(entrypoint="test_runtime_singleton:plugin")

        plugin, error = await PluginRuntimeService().load_plugin(record, request_id="req-singleton")

        self.assertIsNone(plugin)
        self.assertEqual(error.code, "PLUGIN_ENTRYPOINT_NOT_FACTORY")
        self.assertEqual(error.stage, "load")

    async def test_start_failure_still_stops_loaded_plugin(self) -> None:
        stopped = {"value": False}

        class StartFailingPlugin(BasePlugin):
            async def start(self):
                raise PluginRuntimeError(
                    code="PLUGIN_START_FAILED_BY_TEST",
                    message="Plugin start failed by test.",
                    stage="start",
                )

            async def stop(self):
                stopped["value"] = True

        self._install_module("test_runtime_start_failure", StartFailingPlugin)
        record = self._record(entrypoint="test_runtime_start_failure:plugin")

        invocation = await PluginRuntimeService().invoke(record, capability="source.fetch", request_id="req-start")

        self.assertFalse(invocation.ok)
        self.assertEqual(invocation.error.code, "PLUGIN_START_FAILED_BY_TEST")
        self.assertEqual(invocation.error.stage, "start")
        self.assertTrue(stopped["value"])

    async def test_start_failure_exposes_cleanup_error_when_stop_fails(self) -> None:
        class StartAndStopFailingPlugin(BasePlugin):
            async def start(self):
                raise PluginRuntimeError(
                    code="PLUGIN_START_FAILED_BY_TEST",
                    message="Plugin start failed by test.",
                    stage="start",
                )

            async def stop(self):
                raise PluginRuntimeError(
                    code="PLUGIN_STOP_FAILED_BY_TEST",
                    message="Plugin stop failed by test.",
                    stage="stop",
                )

        self._install_module("test_runtime_start_stop_failure", StartAndStopFailingPlugin)
        record = self._record(entrypoint="test_runtime_start_stop_failure:plugin")

        invocation = await PluginRuntimeService().invoke(record, capability="source.fetch", request_id="req-start-stop")

        self.assertFalse(invocation.ok)
        self.assertEqual(invocation.error.code, "PLUGIN_START_FAILED_BY_TEST")
        self.assertIsNotNone(invocation.cleanup_error)
        self.assertEqual(invocation.cleanup_error.code, "PLUGIN_STOP_FAILED_BY_TEST")
        self.assertEqual(invocation.cleanup_error.stage, "stop")

    async def test_successful_invoke_exposes_cleanup_error_when_stop_fails(self) -> None:
        class StopFailingPlugin(BasePlugin):
            async def invoke(self, request):
                return PluginInvokeResult(output={"ok": True})

            async def stop(self):
                raise PluginRuntimeError(
                    code="PLUGIN_STOP_FAILED_BY_TEST",
                    message="Plugin stop failed by test.",
                    stage="stop",
                )

        self._install_module("test_runtime_stop_failure", StopFailingPlugin)
        record = self._record(entrypoint="test_runtime_stop_failure:plugin")

        invocation = await PluginRuntimeService().invoke(record, capability="source.fetch", request_id="req-stop")

        self.assertTrue(invocation.ok)
        self.assertEqual(invocation.result.output["ok"], True)
        self.assertIsNotNone(invocation.cleanup_error)
        self.assertEqual(invocation.cleanup_error.code, "PLUGIN_STOP_FAILED_BY_TEST")

    async def test_cancelled_invoke_waits_for_stop_cleanup(self) -> None:
        stopped = asyncio.Event()

        class SlowPlugin(BasePlugin):
            async def invoke(self, request):
                await asyncio.sleep(10)
                return PluginInvokeResult(output={"done": True})

            async def stop(self):
                await asyncio.sleep(0.02)
                stopped.set()

        self._install_module("test_runtime_cancelled_cleanup", SlowPlugin)
        record = self._record(entrypoint="test_runtime_cancelled_cleanup:plugin")
        task = asyncio.create_task(PluginRuntimeService().invoke(record, capability="source.fetch", request_id="req-cancel"))
        await asyncio.sleep(0)

        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertTrue(stopped.is_set())

    async def test_plugin_runtime_error_message_and_details_are_sanitized(self) -> None:
        class SensitiveErrorPlugin(BasePlugin):
            async def invoke(self, request):
                raise PluginRuntimeError(
                    code="PLUGIN_SENSITIVE_ERROR",
                    message="token=abc123 failed at /home/xxs/private.env",
                    stage="invoke",
                    details={
                        "token": "abc123",
                        "nested": {"cookie": "session=value"},
                        "path": "/home/xxs/private.env",
                        "safe": "visible",
                    },
                )

        self._install_module("test_runtime_sensitive_error", SensitiveErrorPlugin)
        record = self._record(entrypoint="test_runtime_sensitive_error:plugin")

        invocation = await PluginRuntimeService().invoke(record, capability="source.fetch", request_id="req-sensitive")

        self.assertFalse(invocation.ok)
        self.assertEqual(invocation.error.code, "PLUGIN_SENSITIVE_ERROR")
        self.assertNotIn("abc123", invocation.error.message)
        self.assertNotIn("/home/xxs", invocation.error.message)
        self.assertEqual(invocation.error.details["token"], "[REDACTED]")
        self.assertEqual(invocation.error.details["nested"]["cookie"], "[REDACTED]")
        self.assertEqual(invocation.error.details["path"], "[REDACTED]")
        self.assertEqual(invocation.error.details["safe"], "visible")

    def _install_module(self, module_name: str, plugin) -> None:
        module = types.ModuleType(module_name)
        module.plugin = plugin
        sys.modules[module_name] = module
        self._module_names.append(module_name)

    def _write_plugin_module(self, plugin_dir: Path, *, origin: str) -> None:
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.py").write_text(
            "\n".join(
                [
                    "from quantagent.plugin_sdk import BasePlugin, PluginInvokeResult",
                    "",
                    "class TestPlugin(BasePlugin):",
                    "    async def invoke(self, request):",
                    f"        return PluginInvokeResult(output={{'origin': {origin!r}, 'request_id': request.request_id}})",
                    "",
                    "plugin = TestPlugin",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _record(
        self,
        *,
        plugin_id: str = "quantagent.test.runtime",
        entrypoint: str = "test_runtime_plugin:plugin",
        path: Path | None = None,
        status: PluginStatus = PluginStatus.VALID,
    ) -> PluginRecord:
        return PluginRecord(
            id=plugin_id,
            source=PluginSource.OFFICIAL,
            path=path or Path(tempfile.gettempdir()),
            status=status,
            manifest=PluginManifest(
                id=plugin_id,
                name="Runtime Test",
                type=PluginType.SOURCE,
                version="0.1.0",
                entrypoint=entrypoint,
                capabilities=("source.fetch",),
                config_schema="config.schema.json",
            ),
        )


if __name__ == "__main__":
    unittest.main()
