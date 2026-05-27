from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_SRC = REPO_ROOT / "packages" / "core" / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from quantagent.core.sources import SourceOutput


PLUGIN_ROOT = REPO_ROOT / "plugins" / "sources" / "readability-source"
PLUGIN_MODULE_PATH = PLUGIN_ROOT / "src" / "readability_source.py"
FIXTURE_PATH = REPO_ROOT / "packages" / "core" / "tests" / "fixtures" / "readability_article.html"


class ReadabilitySourcePluginTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._module_name = "readability_source"
        cls._previous_module = sys.modules.get(cls._module_name)
        spec = importlib.util.spec_from_file_location(cls._module_name, PLUGIN_MODULE_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("Failed to load readability_source module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[cls._module_name] = module
        spec.loader.exec_module(module)
        cls.module = module

    @classmethod
    def tearDownClass(cls) -> None:
        sys.modules.pop(getattr(cls, "_module_name", "readability_source"), None)
        previous = getattr(cls, "_previous_module", None)
        if previous is not None:
            sys.modules[cls._module_name] = previous
        if hasattr(cls, "module"):
            del cls.module

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

    def test_fetch_rejects_empty_or_blank_url(self) -> None:
        for bad in ("", "   "):
            with self.subTest(url=bad):
                with self.assertRaisesRegex(ValueError, "url must be a non-empty string"):
                    self.module.plugin.fetch(None, {"url": bad})

    def test_fetch_rejects_non_http_schemes(self) -> None:
        with self.assertRaisesRegex(ValueError, "Only http and https schemes are allowed"):
            self.module.plugin.fetch(None, {"url": "file:///tmp/test.html"})

    def test_fetch_rejects_timeout_over_schema_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "timeout_seconds must be a positive number no greater than 30"):
            self.module.plugin.fetch(None, {"url": "https://example.com", "timeout_seconds": 31})

    def test_fetch_falls_back_to_utf8_for_unknown_charset(self) -> None:
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        fake_response = _FakeHTTPResponse(html, charset="x-unknown-charset")

        with patch.object(self.module, "urlopen", return_value=fake_response):
            outputs = self.module.plugin.fetch(
                None,
                {
                    "url": "https://example.com/articles/storage-breakthrough",
                },
            )

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].title, "Markets Rally On Storage Breakthrough")

    def test_readme_documents_plugin_boundary(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("只提供 `source.fetch` 能力，不暴露 `tool.read_url`", readme)  # noqa: RUF001
        self.assertIn("不负责 `RawEvent` 入库、去重、`SourceBinding`、`Event Bus`、权限或生命周期", readme)


class _FakeHeaders:
    def __init__(self, charset: str = "utf-8") -> None:
        self._charset = charset

    def get_content_charset(self) -> str:
        return self._charset


class _FakeHTTPResponse:
    def __init__(self, html: str, *, charset: str = "utf-8") -> None:
        self._body = html.encode("utf-8")
        self.headers = _FakeHeaders(charset=charset)

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
