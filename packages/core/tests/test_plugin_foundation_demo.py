from __future__ import annotations

import unittest
from pathlib import Path

from quantagent.core.registry import PluginRegistry, PluginStatus, PluginType
from quantagent.core.registry.scanner import RegistryScanner
from quantagent.core.runtime import PluginRuntimeService


READABILITY_PLUGIN_ID = "quantagent.official.source.readability"
JINA_PLUGIN_ID = "quantagent.official.source.jina"


class PluginFoundationReadabilityTestCase(unittest.IsolatedAsyncioTestCase):
    def test_registry_discovers_readability_manifest(self) -> None:
        registry = self._registry()

        record = registry.get_plugin(READABILITY_PLUGIN_ID)

        self.assertIsNotNone(record)
        self.assertEqual(record.status, PluginStatus.VALID)
        self.assertEqual(record.path, Path("plugins/sources/readability-source").resolve())
        self.assertIsNotNone(record.manifest)
        self.assertEqual(record.manifest.type, PluginType.SOURCE)
        self.assertEqual(record.manifest.entrypoint, "readability_source:plugin")
        self.assertEqual(record.manifest.capabilities, ("source.fetch",))

    async def test_runtime_loads_readability_entrypoint_from_plugin_path(self) -> None:
        record = self._placeholder_record()

        invocation = await PluginRuntimeService().invoke(
            record,
            capability="source.fetch",
            request_id="req-readability-runtime",
            config={"url": "https://example.test/news/oil"},
            input={"query": "https://example.test/news/oil"},
            metadata={"origin": "readability-runtime"},
        )

        self.assertFalse(invocation.ok)
        self.assertIsNotNone(invocation.error)
        self.assertEqual(invocation.error.stage, "invoke")
        self.assertIn(invocation.error.code, {"PLUGIN_INVOKE_FAILED", "PLUGIN_LOAD_FAILED", "PLUGIN_START_FAILED"})

    def _registry(self) -> PluginRegistry:
        return PluginRegistry(
            RegistryScanner(
                official_root=Path("plugins"),
                runtime_root=Path("runtime/plugin-foundation-demo-missing"),
            )
        )

    def _placeholder_record(self):
        record = self._registry().get_plugin(READABILITY_PLUGIN_ID)
        assert record is not None
        return record


class PluginFoundationJinaTestCase(unittest.IsolatedAsyncioTestCase):
    def test_registry_discovers_jina_manifest(self) -> None:
        registry = self._registry()

        record = registry.get_plugin(JINA_PLUGIN_ID)

        self.assertIsNotNone(record)
        self.assertEqual(record.status, PluginStatus.VALID)
        self.assertEqual(record.path, Path("plugins/sources/jina-source").resolve())
        self.assertIsNotNone(record.manifest)
        self.assertEqual(record.manifest.type, PluginType.SOURCE)
        self.assertEqual(record.manifest.entrypoint, "jina_source:plugin")
        self.assertEqual(record.manifest.capabilities, ("source.fetch",))

    async def test_runtime_loads_jina_entrypoint_from_plugin_path(self) -> None:
        record = self._jina_record()

        invocation = await PluginRuntimeService().invoke(
            record,
            capability="source.fetch",
            request_id="req-jina-runtime",
            config={
                "url": "https://example.test/news/oil",
                "endpoint": "https://reader.test/{url}",
            },
            input={"query": "https://example.test/news/oil"},
            metadata={"origin": "jina-runtime"},
        )

        self.assertFalse(invocation.ok)
        self.assertIsNotNone(invocation.error)
        self.assertIn(invocation.error.stage, {"load", "invoke", "start"})

    def _registry(self) -> PluginRegistry:
        return PluginRegistry(
            RegistryScanner(
                official_root=Path("plugins"),
                runtime_root=Path("runtime/plugin-foundation-demo-missing"),
            )
        )

    def _jina_record(self):
        record = self._registry().get_plugin(JINA_PLUGIN_ID)
        assert record is not None
        return record


if __name__ == "__main__":
    unittest.main()
