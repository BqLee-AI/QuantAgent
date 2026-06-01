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
