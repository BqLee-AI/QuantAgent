from __future__ import annotations

import logging
import unittest

from quantagent.plugin_sdk import (
    BasePlugin,
    HealthCheckResult,
    PluginInvokeRequest,
    PluginInvokeResult,
    PluginRuntimeError,
    RuntimeContext,
)


class PluginSdkRuntimeTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_base_plugin_keeps_loaded_context_read_only(self) -> None:
        plugin = BasePlugin()
        context = RuntimeContext(
            plugin_id="quantagent.test.plugin",
            plugin_version="0.1.0",
            request_id="req-1",
            logger=logging.getLogger("test.plugin"),
            config={"enabled": True},
            metadata={"origin": "unit-test"},
        )

        await plugin.load(context)

        self.assertEqual(plugin.context.plugin_id, "quantagent.test.plugin")
        self.assertEqual(plugin.context.config["enabled"], True)
        self.assertEqual(plugin.context.metadata["origin"], "unit-test")
        with self.assertRaises(TypeError):
            plugin.context.config["enabled"] = False  # type: ignore[index]

    async def test_base_plugin_default_lifecycle_and_health_check_are_noops(self) -> None:
        plugin = BasePlugin()
        context = RuntimeContext(
            plugin_id="quantagent.test.plugin",
            plugin_version="0.1.0",
            request_id="req-2",
            logger=logging.getLogger("test.plugin"),
        )

        await plugin.load(context)
        await plugin.start()
        health = await plugin.health_check()
        await plugin.stop()

        self.assertEqual(health, HealthCheckResult(status="ok"))

    async def test_base_plugin_invoke_raises_structured_not_implemented_error(self) -> None:
        plugin = BasePlugin()
        await plugin.load(
            RuntimeContext(
                plugin_id="quantagent.test.plugin",
                plugin_version="0.1.0",
                request_id="req-3",
                logger=logging.getLogger("test.plugin"),
            )
        )

        with self.assertRaises(PluginRuntimeError) as raised:
            await plugin.invoke(PluginInvokeRequest(capability="source.fetch", request_id="req-3"))

        self.assertEqual(raised.exception.code, "PLUGIN_CAPABILITY_NOT_IMPLEMENTED")
        self.assertEqual(raised.exception.stage, "invoke")
        self.assertEqual(raised.exception.details["capability"], "source.fetch")

    def test_plugin_invoke_result_and_request_freeze_nested_mappings(self) -> None:
        request = PluginInvokeRequest(
            capability="source.fetch",
            request_id="req-4",
            input={"query": "oil"},
            metadata={"origin": "unit-test"},
        )
        result = PluginInvokeResult(output={"count": 1}, metadata={"source": "demo"})

        with self.assertRaises(TypeError):
            request.input["query"] = "gas"  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.output["count"] = 2  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
