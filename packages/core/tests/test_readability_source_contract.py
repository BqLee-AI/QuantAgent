from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_SRC = REPO_ROOT / "packages" / "core" / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from quantagent.core.registry import PluginStatus, RegistryScanner


class ReadabilitySourcePluginContractTestCase(unittest.TestCase):
    def test_registry_scans_official_readability_plugin(self) -> None:
        records = RegistryScanner(
            official_root=REPO_ROOT / "plugins",
            runtime_root=REPO_ROOT / "runtime" / "plugins",
        ).scan()

        by_id = {record.id: record for record in records}
        record = by_id["quantagent.official.source.readability"]
        self.assertEqual(record.status, PluginStatus.VALID)
        self.assertIsNotNone(record.manifest)
        self.assertEqual(record.manifest.capabilities, ("source.fetch",))
        self.assertEqual(record.manifest.entrypoint, "readability_source:plugin")

    def test_plugin_schema_declares_minimal_reader_config(self) -> None:
        records = RegistryScanner(
            official_root=REPO_ROOT / "plugins",
            runtime_root=REPO_ROOT / "runtime" / "plugins",
        ).scan()
        record = {item.id: item for item in records}["quantagent.official.source.readability"]
        schema_text = record.config_schema_path.read_text(encoding="utf-8")
        schema = json.loads(schema_text)
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        self.assertIn("url", properties)
        self.assertIn("headers", properties)
        self.assertIn("timeout_seconds", properties)
        self.assertIn("min_text_length", properties)
        self.assertIn("url", required)


if __name__ == "__main__":
    unittest.main()
