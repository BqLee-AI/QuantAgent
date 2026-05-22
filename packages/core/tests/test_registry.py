from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from quantagent.core.registry import PluginRegistry, PluginSource, PluginStatus, PluginType, RegistryScanner


class PluginRegistryScannerTestCase(unittest.TestCase):
    def test_scans_valid_official_plugin_and_normalizes_executor_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            runtime_root = root / "missing-runtime"
            self._write_plugin(
                official_root / "executors" / "mock",
                plugin_type="executor",
                plugin_id="quantagent.official.executor.mock",
            )

            records = RegistryScanner(official_root=official_root, runtime_root=runtime_root).scan()

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.source, PluginSource.OFFICIAL)
        self.assertEqual(record.status, PluginStatus.VALID)
        self.assertIsNotNone(record.manifest)
        self.assertEqual(record.manifest.type, PluginType.TRADE_EXECUTOR)
        self.assertEqual(record.config_schema_path.name, "config.schema.json")

    def test_missing_runtime_root_is_empty_and_directories_without_manifest_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            (official_root / "sources" / "no-manifest").mkdir(parents=True)

            records = RegistryScanner(official_root=official_root, runtime_root=root / "runtime" / "plugins").scan()

        self.assertEqual(records, [])

    def test_invalid_manifest_cases_do_not_block_valid_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            runtime_root = root / "runtime" / "plugins"
            self._write_plugin(
                official_root / "sources" / "valid",
                plugin_id="quantagent.official.source.valid",
            )
            self._write_raw_manifest(
                runtime_root / "bad-yaml",
                "id: runtime.bad\ncapabilities:\n  - source.fetch\n  - [",
            )
            self._write_raw_manifest(
                runtime_root / "missing-field",
                "id: runtime.missing\nname: Missing Field\ntype: source\nversion: 0.1.0\nentrypoint: missing:plugin\n",
            )
            self._write_raw_manifest(
                runtime_root / "unknown-type",
                (
                    "id: runtime.unknown\nname: Unknown Type\ntype: mystery\nversion: 0.1.0\n"
                    "entrypoint: unknown:plugin\ncapabilities:\n  - source.fetch\nconfig_schema: config.schema.json\n"
                ),
            )
            self._write_raw_manifest(
                runtime_root / "missing-schema",
                (
                    "id: runtime.missing_schema\nname: Missing Schema\ntype: source\nversion: 0.1.0\n"
                    "entrypoint: missing_schema:plugin\ncapabilities:\n  - source.fetch\nconfig_schema: missing.json\n"
                ),
            )

            records = RegistryScanner(official_root=official_root, runtime_root=runtime_root).scan()

        by_id = {record.id: record for record in records}
        self.assertEqual(by_id["quantagent.official.source.valid"].status, PluginStatus.VALID)
        self.assertEqual(by_id["runtime.missing"].last_error.code, "PLUGIN_MANIFEST_REQUIRED_FIELD_MISSING")
        self.assertEqual(by_id["runtime.unknown"].last_error.code, "PLUGIN_TYPE_UNKNOWN")
        self.assertEqual(by_id["runtime.missing_schema"].last_error.code, "PLUGIN_CONFIG_SCHEMA_NOT_FOUND")
        self.assertTrue(any(record.last_error and record.last_error.code == "PLUGIN_MANIFEST_YAML_INVALID" for record in records))

    def test_duplicate_plugin_ids_are_marked_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            runtime_root = root / "runtime" / "plugins"
            self._write_plugin(official_root / "sources" / "one", plugin_id="duplicate.plugin")
            self._write_plugin(runtime_root / "sources" / "two", plugin_id="duplicate.plugin")

            records = RegistryScanner(official_root=official_root, runtime_root=runtime_root).scan()

        self.assertEqual(len(records), 2)
        self.assertTrue(all(record.status == PluginStatus.INVALID for record in records))
        self.assertTrue(all(record.last_error and record.last_error.code == "PLUGIN_ID_DUPLICATE" for record in records))

    def test_registry_reads_config_schema_for_valid_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            self._write_plugin(official_root / "sources" / "valid", plugin_id="valid.schema")
            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))

            schema = registry.read_config_schema("valid.schema")

        self.assertEqual(schema["title"], "Plugin Config")

    def _write_plugin(
        self,
        plugin_dir: Path,
        *,
        plugin_id: str = "quantagent.official.source.test",
        plugin_type: str = "source",
    ) -> None:
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.yaml").write_text(
            (
                f"id: {plugin_id}\n"
                "name: Test Plugin\n"
                f"type: {plugin_type}\n"
                "version: 0.1.0\n"
                "entrypoint: does_not_exist:plugin\n"
                "capabilities:\n"
                "  - source.fetch\n"
                "config_schema: config.schema.json\n"
            ),
            encoding="utf-8",
        )
        (plugin_dir / "config.schema.json").write_text(
            '{"title": "Plugin Config", "type": "object", "properties": {}}',
            encoding="utf-8",
        )

    def _write_raw_manifest(self, plugin_dir: Path, content: str) -> None:
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.yaml").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
