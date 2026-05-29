from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[4]
for src_root in (
    REPO_ROOT / "packages" / "core" / "src",
    REPO_ROOT / "packages" / "plugin-sdk" / "src",
):
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

from quantagent.core.registry import RegistryScanner
from quantagent.core.runtime import PluginRuntimeService
from quantagent.plugin_sdk import PluginInvokeRequest, SourceFetchResult


PLUGIN_ROOT = REPO_ROOT / "plugins" / "sources" / "readability-source"
FIXTURE_PATH = PLUGIN_ROOT / "tests" / "fixtures" / "readability_article.html"


class ReadabilitySourcePluginTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        plugin, error = asyncio.run(
            PluginRuntimeService().load_plugin(
                _readability_record(),
                request_id="req-readability-test-load",
                config={},
                metadata={"origin": "readability-plugin-test"},
            )
        )
        if error is not None or plugin is None:
            raise AssertionError(f"Failed to load readability plugin through runtime: {error}")
        cls.plugin = plugin

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "plugin"):
            asyncio.run(
                PluginRuntimeService().stop_plugin(
                    cls.plugin,
                    plugin_id="quantagent.official.source.readability",
                )
            )
            del cls.plugin

    def test_fetch_extracts_article_content_from_controlled_html(self) -> None:
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        fake_response = _FakeHTTPResponse(html)

        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(fake_response))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-readability-test-fetch",
                        input={
                            "url": "https://example.com/articles/storage-breakthrough",
                            "headers": {"User-Agent": "QuantAgentTest/1.0"},
                            "timeout_seconds": 3,
                            "min_text_length": 80,
                        },
                    )
                )
            )

        output = SourceFetchResult.from_mapping(result.output)
        self.assertEqual(len(output.items), 1)
        item = output.items[0]
        self.assertEqual(item.metadata["plugin_id"], "quantagent.official.source.readability")
        self.assertEqual(output.metadata["source"], "readability")
        self.assertEqual(item.title, "Markets Rally On Storage Breakthrough")
        self.assertEqual(item.url, "https://example.com/articles/storage-breakthrough")
        self.assertEqual(item.metadata["canonical_url"], "https://example.com/articles/storage-breakthrough")
        self.assertEqual(item.author, "Alex Chen")
        self.assertIsNotNone(item.published_at)
        self.assertIn("Battery storage suppliers climbed", item.content or "")
        self.assertIn("Quant Daily", str(item.metadata))

    def test_runtime_invokes_manifest_entrypoint(self) -> None:
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        fake_response = _FakeHTTPResponse(html)

        runtime = _RuntimeServiceWithOpener(fake_response)
        invocation = asyncio.run(
            runtime.invoke(
                _readability_record(),
                capability="source.fetch",
                request_id="req-readability-runtime",
                config={
                    "url": "https://example.com/articles/storage-breakthrough",
                    "min_text_length": 80,
                },
                input={},
            )
        )

        self.assertTrue(invocation.ok)
        self.assertIsNotNone(invocation.result)
        output = SourceFetchResult.from_mapping(invocation.result.output)
        self.assertEqual(output.items[0].title, "Markets Rally On Storage Breakthrough")

    def test_fetch_rejects_missing_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "url must be a non-empty string"):
            asyncio.run(self.plugin.invoke(PluginInvokeRequest(capability="source.fetch", request_id="req-missing-url")))

    def test_fetch_rejects_empty_or_blank_url(self) -> None:
        for bad in ("", "   "):
            with self.subTest(url=bad):
                with self.assertRaisesRegex(ValueError, "url must be a non-empty string"):
                    asyncio.run(
                        self.plugin.invoke(
                            PluginInvokeRequest(
                                capability="source.fetch",
                                request_id="req-blank-url",
                                input={"url": bad},
                            )
                        )
                    )

    def test_fetch_rejects_non_http_schemes(self) -> None:
        with self.assertRaisesRegex(ValueError, "Only http and https schemes are allowed"):
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-file-url",
                        input={"url": "file:///tmp/test.html"},
                    )
                )
            )

    def test_fetch_rejects_timeout_over_schema_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "timeout_seconds must be a positive number no greater than 30"):
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-timeout",
                        input={"url": "https://example.com", "timeout_seconds": 31},
                    )
                )
            )

    def test_fetch_falls_back_to_utf8_for_unknown_charset(self) -> None:
        html = FIXTURE_PATH.read_text(encoding="utf-8")
        fake_response = _FakeHTTPResponse(html, charset="x-unknown-charset")

        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(fake_response))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-unknown-charset",
                        input={"url": "https://example.com/articles/storage-breakthrough"},
                    )
                )
            )

        output = SourceFetchResult.from_mapping(result.output)
        self.assertEqual(len(output.items), 1)
        self.assertEqual(output.items[0].title, "Markets Rally On Storage Breakthrough")

    def test_readme_documents_plugin_boundary(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("只提供 `source.fetch` 能力，不暴露 `tool.read_url`", readme)  # noqa: RUF001
        self.assertIn("不负责 `RawEvent` 入库、去重、`SourceBinding`、`Event Bus`、权限或生命周期", readme)


def _readability_record():
    records = RegistryScanner(
        official_root=REPO_ROOT / "plugins",
        runtime_root=REPO_ROOT / "runtime" / "plugins",
    ).scan()
    return {item.id: item for item in records}["quantagent.official.source.readability"]


def _fake_opener(response):
    def opener(*_args, **_kwargs):
        return response

    return opener


class _RuntimeServiceWithOpener(PluginRuntimeService):
    def __init__(self, response) -> None:
        super().__init__()
        self._response = response

    def _load_plugin_module(self, module_name: str, *, plugin_path: Path | None = None):
        module = super()._load_plugin_module(module_name, plugin_path=plugin_path)
        module.ReadabilitySourcePlugin.opener = staticmethod(_fake_opener(self._response))
        return module


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
