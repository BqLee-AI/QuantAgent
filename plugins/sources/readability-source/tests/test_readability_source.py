from __future__ import annotations

import asyncio
import unittest
from importlib import util
from pathlib import Path
from unittest.mock import patch

from quantagent.core.plugins.manifest import load_plugin_manifest
from quantagent.plugin_sdk import PluginInvokeRequest, RuntimeContext


FIXTURE_PATH = Path(__file__).resolve().parents[4] / "packages" / "core" / "tests" / "fixtures" / "readability_article.html"
PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class ReadabilitySourcePluginTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest = load_plugin_manifest(PLUGIN_ROOT)
        module_name, _, attribute_name = manifest.entrypoint.partition(":")
        if not module_name or not attribute_name:
            raise RuntimeError(f"Invalid plugin entrypoint: {manifest.entrypoint}")
        module_path = PLUGIN_ROOT / f"{module_name}.py"
        spec = util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load plugin module from entrypoint: {manifest.entrypoint}")
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.module = module
        cls.entrypoint_attribute = attribute_name

    def setUp(self) -> None:
        self.plugin = self.module.ReadabilitySourcePlugin()
        self.plugin_id = "quantagent.official.source.readability"
        self._run_async(
            self.plugin.load(
                RuntimeContext(
                    plugin_id=self.plugin_id,
                    plugin_version="0.1.0",
                    request_id="req-load",
                    logger=__import__("logging").getLogger("test.readability"),
                    config={"url": "https://example.test/news/oil"},
                )
            )
        )
        self._run_async(self.plugin.start())

    def tearDown(self) -> None:
        self._run_async(self.plugin.stop())

    def _run_async(self, value):
        return asyncio.run(value)

    def test_fetch_extracts_article_to_raw_event_draft(self) -> None:
        html = FIXTURE_PATH.read_bytes()
        response = _FakeHTTPResponse(
            body=html,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

        with patch.object(self.module, "urlopen", return_value=response) as mocked_urlopen:
            result = self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-fetch",
                        input={},
                    )
                )
            )

        mocked_urlopen.assert_called_once()
        self.assertEqual(len(result.output["items"]), 1)
        item = result.output["items"][0]
        self.assertEqual(item["external_id"], "https://example.test/reports/oil-quarterly")
        self.assertEqual(item["title"], "Quarterly Oil Update")
        self.assertEqual(item["author"], "Quant Analyst")
        self.assertEqual(item["published_at"], "2026-05-26T08:30:00+00:00")
        self.assertIn("Oil inventories fell for the third consecutive week", item["content"])
        self.assertEqual(item["metadata"]["reader"], "readability")
        self.assertEqual(result.output["metadata"]["source"], "readability")

    def test_manifest_entrypoint_resolves_plugin_export(self) -> None:
        exported = getattr(self.module, self.entrypoint_attribute)

        self.assertIs(exported, self.module.plugin)
        self.assertIs(exported, self.module.ReadabilitySourcePlugin)

    def test_fetch_rejects_missing_or_blank_url(self) -> None:
        self._run_async(
            self.plugin.load(
                RuntimeContext(
                    plugin_id=self.plugin_id,
                    plugin_version="0.1.0",
                    request_id="req-missing-load",
                    logger=__import__("logging").getLogger("test.readability"),
                    config={},
                )
            )
        )
        with self.assertRaisesRegex(ValueError, "url must be a non-empty string"):
            self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(capability="source.fetch", request_id="req-missing", input={})
                )
            )
        self._run_async(
            self.plugin.load(
                RuntimeContext(
                    plugin_id=self.plugin_id,
                    plugin_version="0.1.0",
                    request_id="req-reload",
                    logger=__import__("logging").getLogger("test.readability"),
                    config={},
                )
            )
        )
        with self.assertRaisesRegex(ValueError, "url must be a non-empty string"):
            self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(capability="source.fetch", request_id="req-empty", input={"query": ""})
                )
            )
        with self.assertRaisesRegex(ValueError, "url must be a non-empty string"):
            self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(capability="source.fetch", request_id="req-blank", input={"query": "   "})
                )
            )

    def test_fetch_rejects_non_http_scheme(self) -> None:
        with self.assertRaisesRegex(ValueError, "url scheme must be http or https"):
            self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-file",
                        input={"query": "file:///tmp/test.html"},
                    )
                )
            )

    def test_fetch_rejects_timeout_above_schema_maximum(self) -> None:
        self._run_async(
            self.plugin.load(
                RuntimeContext(
                    plugin_id=self.plugin_id,
                    plugin_version="0.1.0",
                    request_id="req-timeout",
                    logger=__import__("logging").getLogger("test.readability"),
                    config={"url": "https://example.test/news/oil", "timeout_seconds": 61},
                )
            )
        )
        with self.assertRaisesRegex(ValueError, "timeout_seconds must be <= 60"):
            self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(capability="source.fetch", request_id="req-timeout", input={})
                )
            )

    def test_fetch_falls_back_to_utf8_when_charset_is_unknown(self) -> None:
        html = FIXTURE_PATH.read_bytes()
        response = _FakeHTTPResponse(
            body=html,
            headers={"Content-Type": "text/html; charset=unknown-charset"},
        )

        with patch.object(self.module, "urlopen", return_value=response):
            result = self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-charset",
                        input={},
                    )
                )
            )

        self.assertEqual(len(result.output["items"]), 1)
        self.assertEqual(result.output["items"][0]["title"], "Quarterly Oil Update")

    def test_readme_documents_boundaries(self) -> None:
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")

        self.assertIn("只提供 `source.fetch` 能力，不暴露 `tool.read_url`。", readme)  # noqa: RUF001
        self.assertIn("不负责 Registry 扫描、API 接入、Runtime 无感接入、Scheduler、SourceBinding、RawEvent 入库或 Event Bus 发布。", readme)


class _FakeHTTPResponse:
    def __init__(self, *, body: bytes, headers: dict[str, str]) -> None:
        self._body = body
        self.headers = headers

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        return None


if __name__ == "__main__":
    unittest.main()
