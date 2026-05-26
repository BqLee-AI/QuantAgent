from __future__ import annotations

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
        plugin = PlainRuntimePlugin()
        self._install_module("test_runtime_plain", plugin)
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
        self._install_module("test_runtime_capability", PlainRuntimePlugin())
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

    def _install_module(self, module_name: str, plugin) -> None:
        module = types.ModuleType(module_name)
        module.plugin = plugin
        sys.modules[module_name] = module
        self._module_names.append(module_name)

    def _record(
        self,
        *,
        entrypoint: str = "test_runtime_plugin:plugin",
        status: PluginStatus = PluginStatus.VALID,
    ) -> PluginRecord:
        return PluginRecord(
            id="quantagent.test.runtime",
            source=PluginSource.OFFICIAL,
            path=Path(tempfile.gettempdir()),
            status=status,
            manifest=PluginManifest(
                id="quantagent.test.runtime",
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
