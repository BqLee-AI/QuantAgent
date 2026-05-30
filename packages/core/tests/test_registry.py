from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from quantagent.core.registry import PluginRegistry, PluginSource, PluginStatus, PluginType, RegistryScanner


class PluginRegistryScannerTestCase(unittest.TestCase):
    def test_scans_valid_official_broker_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            runtime_root = root / "missing-runtime"
            self._write_plugin(
                official_root / "brokers" / "mock",
                plugin_type="broker",
                plugin_id="quantagent.official.broker.mock",
            )

            records = RegistryScanner(official_root=official_root, runtime_root=runtime_root).scan()

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.source, PluginSource.OFFICIAL)
        self.assertEqual(record.status, PluginStatus.VALID)
        self.assertIsNotNone(record.manifest)
        self.assertEqual(record.manifest.type, PluginType.BROKER)
        self.assertEqual(record.config_schema_path.name, "config.schema.json")

    def test_legacy_executor_and_trade_executor_types_normalize_to_broker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            runtime_root = root / "missing-runtime"
            self._write_plugin(
                official_root / "legacy" / "executor",
                plugin_type="executor",
                plugin_id="quantagent.official.legacy.executor",
            )
            self._write_plugin(
                official_root / "legacy" / "trade-executor",
                plugin_type="trade_executor",
                plugin_id="quantagent.official.legacy.trade_executor",
            )

            records = RegistryScanner(official_root=official_root, runtime_root=runtime_root).scan()

        self.assertEqual(len(records), 2)
        self.assertTrue(all(record.status == PluginStatus.VALID for record in records))
        self.assertTrue(all(record.manifest and record.manifest.type == PluginType.BROKER for record in records))

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
            bad_encoding_dir = runtime_root / "bad-encoding"
            bad_encoding_dir.mkdir(parents=True)
            (bad_encoding_dir / "plugin.yaml").write_bytes(b"\xff\xfe\xfa")
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
            self._write_raw_manifest(
                runtime_root / "bad-required-type",
                (
                    "id: runtime.bad_required_type\nname: Bad Required Type\ntype: source\nversion:\n"
                    "  major: 0\nentrypoint: bad_required_type:plugin\ncapabilities:\n"
                    "  - source.fetch\nconfig_schema: config.schema.json\n"
                ),
            )

            records = RegistryScanner(official_root=official_root, runtime_root=runtime_root).scan()

        by_id = {record.id: record for record in records}
        self.assertEqual(by_id["quantagent.official.source.valid"].status, PluginStatus.VALID)
        self.assertEqual(by_id["runtime.missing"].last_error.code, "PLUGIN_MANIFEST_REQUIRED_FIELD_MISSING")
        self.assertEqual(by_id["runtime.bad_required_type"].last_error.code, "PLUGIN_MANIFEST_FIELD_INVALID")
        self.assertEqual(by_id["runtime.unknown"].last_error.code, "PLUGIN_TYPE_UNKNOWN")
        self.assertEqual(by_id["runtime.missing_schema"].last_error.code, "PLUGIN_CONFIG_SCHEMA_NOT_FOUND")
        self.assertTrue(any(record.last_error and record.last_error.code == "PLUGIN_MANIFEST_YAML_INVALID" for record in records))
        self.assertTrue(any(record.last_error and record.last_error.code == "PLUGIN_MANIFEST_READ_FAILED" for record in records))
        synthetic_ids = [record.id for record in records if record.id.startswith("invalid:runtime:")]
        self.assertTrue(synthetic_ids)
        self.assertTrue(all(Path(tmpdir).name not in plugin_id for plugin_id in synthetic_ids))

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

    def test_duplicate_plugin_ids_include_invalid_manifest_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            runtime_root = root / "runtime" / "plugins"
            self._write_plugin(official_root / "sources" / "valid", plugin_id="duplicate.invalid")
            self._write_raw_manifest(
                runtime_root / "sources" / "invalid",
                (
                    "id: duplicate.invalid\nname: Duplicate Invalid\ntype: source\nversion: 0.1.0\n"
                    "entrypoint: invalid:plugin\ncapabilities:\n  - source.fetch\nconfig_schema: missing.json\n"
                ),
            )

            records = RegistryScanner(official_root=official_root, runtime_root=runtime_root).scan()

        self.assertEqual(len(records), 2)
        self.assertTrue(all(record.status == PluginStatus.INVALID for record in records))
        self.assertTrue(all(record.last_error and record.last_error.code == "PLUGIN_ID_DUPLICATE" for record in records))

    def test_registry_does_not_read_config_schema_for_invalid_duplicate_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            runtime_root = root / "runtime" / "plugins"
            self._write_plugin(official_root / "sources" / "one", plugin_id="duplicate.schema")
            self._write_plugin(runtime_root / "sources" / "two", plugin_id="duplicate.schema")
            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=runtime_root))

            schema = registry.read_config_schema("duplicate.schema")

        self.assertIsNone(schema)

    def test_symlinked_manifest_file_outside_root_is_marked_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            external_root = root / "external"
            self._write_plugin(external_root / "outside", plugin_id="outside.root")
            linked_plugin_dir = official_root / "linked"
            linked_plugin_dir.mkdir(parents=True)
            (linked_plugin_dir / "plugin.yaml").symlink_to(external_root / "outside" / "plugin.yaml")

            records = RegistryScanner(official_root=official_root, runtime_root=root / "runtime" / "plugins").scan()

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.status, PluginStatus.INVALID)
        self.assertIsNone(record.manifest)
        self.assertEqual(record.last_error.code, "PLUGIN_MANIFEST_OUTSIDE_ROOT")
        self.assertTrue(record.id.startswith("invalid:official:"))
        self.assertNotIn(Path(tmpdir).name, record.id)

    def test_outside_root_synthetic_ids_use_root_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            external_root = root / "external"
            self._write_plugin(external_root / "one", plugin_id="outside.one")
            self._write_plugin(external_root / "two", plugin_id="outside.two")
            for parent, target in (("a", "one"), ("b", "two")):
                linked_plugin_dir = official_root / parent / "linked"
                linked_plugin_dir.mkdir(parents=True)
                (linked_plugin_dir / "plugin.yaml").symlink_to(external_root / target / "plugin.yaml")

            records = RegistryScanner(official_root=official_root, runtime_root=root / "runtime" / "plugins").scan()

        self.assertEqual(len(records), 2)
        self.assertTrue(all(record.status == PluginStatus.INVALID for record in records))
        self.assertEqual(len({record.id for record in records}), 2)
        self.assertTrue(all(record.id.startswith("invalid:official:") for record in records))
        self.assertTrue(all(Path(tmpdir).name not in record.id for record in records))

    def test_registry_reads_config_schema_for_valid_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            self._write_plugin(official_root / "sources" / "valid", plugin_id="valid.schema")
            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))

            schema = registry.read_config_schema("valid.schema")

        self.assertEqual(schema["title"], "Plugin Config")

    def test_registry_returns_none_for_invalid_json_config_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            self._write_plugin(official_root / "sources" / "invalid-json", plugin_id="invalid.json.schema")
            (official_root / "sources" / "invalid-json" / "config.schema.json").write_text("{", encoding="utf-8")
            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))

            schema = registry.read_config_schema("invalid.json.schema")

        self.assertIsNone(schema)

    def test_registry_returns_none_for_non_utf8_config_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            self._write_plugin(official_root / "sources" / "non-utf8-json", plugin_id="non.utf8.schema")
            (official_root / "sources" / "non-utf8-json" / "config.schema.json").write_bytes(b"\xff\xfe\xfa")
            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))

            schema = registry.read_config_schema("non.utf8.schema")

        self.assertIsNone(schema)

    def test_registry_records_do_not_expose_mutable_nested_mappings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            self._write_plugin(official_root / "sources" / "valid", plugin_id="immutable.record")
            plugin_dir = official_root / "sources" / "valid"
            manifest_text = (plugin_dir / "plugin.yaml").read_text(encoding="utf-8")
            (plugin_dir / "plugin.yaml").write_text(
                manifest_text + "dependencies:\n  quantagent-core: '>=0.1.0'\n",
                encoding="utf-8",
            )

            records = RegistryScanner(official_root=official_root, runtime_root=root / "runtime").scan()

        manifest = records[0].manifest
        self.assertIsNotNone(manifest)
        with self.assertRaises(TypeError):
            manifest.dependencies["new"] = "value"  # type: ignore[index]

    def test_scans_official_discord_plugin_from_repo(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        registry = PluginRegistry(
            RegistryScanner(
                official_root=repo_root / "plugins",
                runtime_root=repo_root / "runtime" / "plugins",
            )
        )

        records = registry.list_plugins()
        by_id = {record.id: record for record in records}

        self.assertIn("quantagent.official.notification.discord", by_id)
        self.assertEqual(by_id["quantagent.official.notification.discord"].status, PluginStatus.VALID)
        self.assertEqual(
            by_id["quantagent.official.notification.discord"].config_schema_path.name,
            "config.schema.json",
        )

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
