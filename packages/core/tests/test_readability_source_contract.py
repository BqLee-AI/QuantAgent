from __future__ import annotations

import json
import unittest
from pathlib import Path

from quantagent.core.plugins.manifest import discover_plugin_manifests, load_plugin_manifest


class ReadabilitySourceContractTestCase(unittest.TestCase):
    def test_readability_manifest_is_discoverable(self) -> None:
        root = Path(__file__).resolve().parents[3]
        plugin_root = root / "plugins" / "sources" / "readability-source"

        manifest = load_plugin_manifest(plugin_root)
        module_name, _, attribute_name = manifest.entrypoint.partition(":")

        self.assertEqual(manifest.id, "quantagent.official.source.readability")
        self.assertEqual(manifest.type, "source")
        self.assertEqual(manifest.execution_mode, "pull")
        self.assertIn("source.fetch", manifest.capabilities)
        self.assertTrue(module_name)
        self.assertEqual(attribute_name, "plugin")
        self.assertTrue((plugin_root / "README.md").is_file())
        self.assertTrue((plugin_root / f"{module_name}.py").is_file())
        self.assertTrue((plugin_root / "config.schema.json").is_file())

        source_manifests = discover_plugin_manifests(root / "plugins" / "sources", plugin_type="source")
        self.assertIn("quantagent.official.source.readability", {item.id for item in source_manifests})

    def test_readability_config_schema_declares_minimum_fields(self) -> None:
        root = Path(__file__).resolve().parents[3]
        schema_path = root / "plugins" / "sources" / "readability-source" / "config.schema.json"

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        properties = schema.get("properties", {})

        self.assertIn("url", properties)
        self.assertIn("headers", properties)
        self.assertIn("timeout_seconds", properties)
        self.assertIn("min_text_length", properties)
        self.assertIn("url", schema.get("required", []))


if __name__ == "__main__":
    unittest.main()
