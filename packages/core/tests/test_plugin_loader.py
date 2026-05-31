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

    def test_loads_entrypoint_with_sibling_module_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            plugin_dir = official_root / "sources" / "package-like"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "plugin.yaml").write_text(
                (
                    "id: quantagent.official.source.package_like\n"
                    "name: Package Like Plugin\n"
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
            (plugin_dir / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
            (plugin_dir / "plugin_impl.py").write_text(
                "import helper\nplugin = {'value': helper.VALUE}\n",
                encoding="utf-8",
            )

            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))
            record = registry.get_plugin("quantagent.official.source.package_like")
            assert record is not None
            plugin = load_plugin_entrypoint(record)

        self.assertEqual(plugin, {"value": 42})

    def test_loads_package_entrypoint_with_relative_import_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            plugin_dir = official_root / "sources" / "package-entrypoint"
            package_dir = plugin_dir / "src"
            package_dir.mkdir(parents=True)
            (plugin_dir / "plugin.yaml").write_text(
                (
                    "id: quantagent.official.source.package_entrypoint\n"
                    "name: Package Entrypoint Plugin\n"
                    "type: source\n"
                    "version: 0.1.0\n"
                    "entrypoint: src.plugin_impl:plugin\n"
                    "capabilities:\n"
                    "  - source.receive\n"
                    "config_schema: config.schema.json\n"
                ),
                encoding="utf-8",
            )
            (plugin_dir / "config.schema.json").write_text('{"type":"object"}', encoding="utf-8")
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
            (package_dir / "helper.py").write_text("VALUE = 7\n", encoding="utf-8")
            (package_dir / "plugin_impl.py").write_text(
                "from .helper import VALUE\nplugin = {'value': VALUE}\n",
                encoding="utf-8",
            )

            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))
            record = registry.get_plugin("quantagent.official.source.package_entrypoint")
            assert record is not None
            plugin = load_plugin_entrypoint(record)

        self.assertEqual(plugin, {"value": 7})

    def test_plugin_sibling_modules_are_isolated_between_entrypoint_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"

            first_plugin_dir = official_root / "sources" / "first"
            first_plugin_dir.mkdir(parents=True)
            (first_plugin_dir / "plugin.yaml").write_text(
                (
                    "id: quantagent.official.source.first\n"
                    "name: First Plugin\n"
                    "type: source\n"
                    "version: 0.1.0\n"
                    "entrypoint: plugin_impl:plugin\n"
                    "capabilities:\n"
                    "  - source.receive\n"
                    "config_schema: config.schema.json\n"
                ),
                encoding="utf-8",
            )
            (first_plugin_dir / "config.schema.json").write_text('{"type":"object"}', encoding="utf-8")
            (first_plugin_dir / "helper.py").write_text("VALUE = 'first'\n", encoding="utf-8")
            (first_plugin_dir / "plugin_impl.py").write_text("import helper\nplugin = {'value': helper.VALUE}\n", encoding="utf-8")

            second_plugin_dir = official_root / "sources" / "second"
            second_plugin_dir.mkdir(parents=True)
            (second_plugin_dir / "plugin.yaml").write_text(
                (
                    "id: quantagent.official.source.second\n"
                    "name: Second Plugin\n"
                    "type: source\n"
                    "version: 0.1.0\n"
                    "entrypoint: plugin_impl:plugin\n"
                    "capabilities:\n"
                    "  - source.receive\n"
                    "config_schema: config.schema.json\n"
                ),
                encoding="utf-8",
            )
            (second_plugin_dir / "config.schema.json").write_text('{"type":"object"}', encoding="utf-8")
            (second_plugin_dir / "helper.py").write_text("VALUE = 'second'\n", encoding="utf-8")
            (second_plugin_dir / "plugin_impl.py").write_text("import helper\nplugin = {'value': helper.VALUE}\n", encoding="utf-8")

            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))
            first_record = registry.get_plugin("quantagent.official.source.first")
            second_record = registry.get_plugin("quantagent.official.source.second")
            assert first_record is not None
            assert second_record is not None

            first_plugin = load_plugin_entrypoint(first_record)
            second_plugin = load_plugin_entrypoint(second_record)

        self.assertEqual(first_plugin, {"value": "first"})
        self.assertEqual(second_plugin, {"value": "second"})

    def test_rejects_entrypoint_outside_plugin_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            official_root = root / "plugins"
            plugin_dir = official_root / "sources" / "escape"
            plugin_dir.mkdir(parents=True)
            (root / "outside.py").write_text("plugin = {'escaped': True}\n", encoding="utf-8")
            (plugin_dir / "plugin.yaml").write_text(
                (
                    "id: quantagent.official.source.escape\n"
                    "name: Escape Plugin\n"
                    "type: source\n"
                    "version: 0.1.0\n"
                    "entrypoint: ...outside:plugin\n"
                    "capabilities:\n"
                    "  - source.receive\n"
                    "config_schema: config.schema.json\n"
                ),
                encoding="utf-8",
            )
            (plugin_dir / "config.schema.json").write_text('{"type":"object"}', encoding="utf-8")
            registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=root / "runtime"))
            record = registry.get_plugin("quantagent.official.source.escape")

        assert record is not None
        with self.assertRaises(PluginEntrypointLoadError):
            load_plugin_entrypoint(record)


if __name__ == "__main__":
    unittest.main()
