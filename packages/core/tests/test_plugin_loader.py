from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from quantagent.core.plugins import PluginEntrypointLoadError, load_plugin_entrypoint
from quantagent.core.registry import PluginRegistry, PluginStatus, RegistryScanner


class PluginEntrypointLoaderTestCase(unittest.TestCase):
    def test_loads_plugin_object_from_valid_manifest_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            plugin_dir = official_root / "sources" / "valid"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "plugin.yaml").write_text(
                (
                    "id: quantagent.official.source.test\n"
                    "name: Test Plugin\n"
                    "type: source\n"
                    "version: 0.1.0\n"
                    "entrypoint: plugin_impl:plugin\n"
                    "capabilities:\n"
                    "  - source.receive\n"
                    "config_schema: config.schema.json\n"
                ),
                encoding="utf-8",
            )
            (plugin_dir / "config.schema.json").write_text('{"type":"object"}', encoding="utf-8")
            (plugin_dir / "plugin_impl.py").write_text("plugin = {'ok': True}\n", encoding="utf-8")

            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))
            record = registry.get_plugin("quantagent.official.source.test")
            assert record is not None
            plugin = load_plugin_entrypoint(record)

        self.assertEqual(plugin, {"ok": True})

    def test_rejects_invalid_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            plugin_dir = official_root / "sources" / "invalid"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "plugin.yaml").write_text("id: only-id\n", encoding="utf-8")
            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))
            record = registry.list_plugins()[0]

        self.assertEqual(record.status, PluginStatus.INVALID)
        with self.assertRaises(PluginEntrypointLoadError):
            load_plugin_entrypoint(record)

    def test_rejects_missing_entrypoint_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            plugin_dir = official_root / "sources" / "missing"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "plugin.yaml").write_text(
                (
                    "id: quantagent.official.source.missing\n"
                    "name: Missing Module\n"
                    "type: source\n"
                    "version: 0.1.0\n"
                    "entrypoint: missing_impl:plugin\n"
                    "capabilities:\n"
                    "  - source.receive\n"
                    "config_schema: config.schema.json\n"
                ),
                encoding="utf-8",
            )
            (plugin_dir / "config.schema.json").write_text('{"type":"object"}', encoding="utf-8")
            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))
            record = registry.get_plugin("quantagent.official.source.missing")

        assert record is not None
        with self.assertRaises(PluginEntrypointLoadError):
            load_plugin_entrypoint(record)


if __name__ == "__main__":
    unittest.main()
