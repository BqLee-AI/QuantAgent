from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_SRC = REPO_ROOT / "packages" / "core" / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from quantagent.core.registry import PluginStatus, RegistryScanner
from quantagent.core.sources import SourceOutput


PLUGIN_ROOT = REPO_ROOT / "plugins" / "sources" / "readability-source"
PLUGIN_MODULE_PATH = PLUGIN_ROOT / "src" / "readability_source.py"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "readability_article.html"


class ReadabilitySourcePluginTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("readability_source", PLUGIN_MODULE_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("Failed to load readability_source module")
        module = importlib.util.module_from_spec(spec)
        sys.modules["readability_source"] = module
        spec.loader.exec_module(module)
        cls.module = module

    def test_registry_scans_official_readability_plugin(self) -> None:
        records = RegistryScanner(
            official_root=REPO_ROOT / "plugins",
            runtime_root=REPO_ROOT / "runtime" / "plugins",
        ).scan()

        by_id = {record.id: record for record in records}
        record = by_id["quantagent.official.source.readability"]
        self.assertEqual(record.status, PluginStatus.VALID)
        self.assertEqual(record.manifest.capabilities, ("source.fetch",))
        self.assertEqual(record.manifest.entrypoint, "readability_source:plugin")

    def test_fetch_extracts_article_content_from_controlled_html(self) -> None:
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        fake_response = _FakeHTTPResponse(html)

        with patch.object(self.module, "urlopen", return_value=fake_response):
            outputs = self.module.plugin.fetch(
                None,
                {
                    "url": "https://example.com/articles/storage-breakthrough",
                    "headers": {"User-Agent": "QuantAgentTest/1.0"},
                    "timeout_seconds": 3,
                    "min_text_length": 80,
                },
            )

        self.assertEqual(len(outputs), 1)
        output = outputs[0]
        self.assertIsInstance(output, SourceOutput)
        self.assertEqual(output.source_plugin_id, "quantagent.official.source.readability")
        self.assertEqual(output.source_type, "readability")
        self.assertEqual(output.title, "Markets Rally On Storage Breakthrough")
        self.assertEqual(output.canonical_url, "https://example.com/articles/storage-breakthrough")
        self.assertEqual(output.author, "Alex Chen")
        self.assertIsNotNone(output.published_at)
        self.assertIn("Battery storage suppliers climbed", output.content or "")
        self.assertIn("Quant Daily", str(output.metadata))

    def test_fetch_rejects_missing_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "url must be a non-empty string"):
            self.module.plugin.fetch(None, {})

    def test_readme_documents_plugin_boundary(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("只提供 `source.fetch` 能力，不暴露 `tool.read_url`", readme)
        self.assertIn("不负责 `RawEvent` 入库、去重、`SourceBinding`、`Event Bus`、权限或生命周期", readme)


class _FakeHeaders:
    def get_content_charset(self) -> str:
        return "utf-8"


class _FakeHTTPResponse:
    def __init__(self, html: str) -> None:
        self._body = html.encode("utf-8")
        self.headers = _FakeHeaders()

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
