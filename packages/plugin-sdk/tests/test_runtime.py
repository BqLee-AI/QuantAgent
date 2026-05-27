from __future__ import annotations

import logging
import unittest

from quantagent.plugin_sdk import (
    BasePlugin,
    HealthCheckResult,
    PluginInvokeRequest,
    PluginRuntimeError,
    RuntimeContext,
    RuntimePlugin,
)


class PluginSdkRuntimeTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_base_plugin_loads_context_and_defaults_health_check(self) -> None:
        context = RuntimeContext(
            plugin_id="quantagent.test",
            plugin_version="0.1.0",
            request_id="req-1",
            logger=logging.getLogger("test.plugin"),
            config={"enabled": True},
        )
        plugin = BasePlugin()

        await plugin.load(context)
        await plugin.start()
        health = await plugin.health_check()
        await plugin.stop()

        self.assertIs(plugin.context, context)
        self.assertIs(plugin.logger, context.logger)
        self.assertEqual(health, HealthCheckResult())

    async def test_base_plugin_default_invoke_returns_structured_error(self) -> None:
        plugin = BasePlugin()
        request = PluginInvokeRequest(capability="source.fetch", request_id="req-1")

        with self.assertRaises(PluginRuntimeError) as raised:
            await plugin.invoke(request)

        self.assertEqual(raised.exception.code, "PLUGIN_CAPABILITY_NOT_IMPLEMENTED")
        self.assertEqual(raised.exception.stage, "invoke")
        self.assertEqual(raised.exception.details["capability"], "source.fetch")

    def test_runtime_dtos_expose_read_only_mappings(self) -> None:
        context = RuntimeContext(
            plugin_id="quantagent.test",
            plugin_version="0.1.0",
            request_id="req-1",
            logger=logging.getLogger("test.plugin"),
            config={"token": "secret-ref"},
            metadata={"mode": "test"},
        )

        with self.assertRaises(TypeError):
            context.config["new"] = "value"  # type: ignore[index]
        with self.assertRaises(TypeError):
            context.metadata["new"] = "value"  # type: ignore[index]

    def test_base_plugin_satisfies_runtime_protocol(self) -> None:
        self.assertIsInstance(BasePlugin(), RuntimePlugin)


if __name__ == "__main__":
    unittest.main()
