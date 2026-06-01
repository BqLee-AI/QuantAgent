from __future__ import annotations

import asyncio
import unittest
from importlib import util
from pathlib import Path
from unittest.mock import patch

from quantagent.core.plugins.manifest import load_plugin_manifest
from quantagent.plugin_sdk import PluginInvokeRequest, RuntimeContext


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class JinaSourcePluginTestCase(unittest.TestCase):
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
        self.plugin = self.module.JinaSourcePlugin()
        self.plugin_id = "quantagent.official.source.jina"
        self._run_async(
            self.plugin.load(
                RuntimeContext(
                    plugin_id=self.plugin_id,
                    plugin_version="0.1.0",
                    request_id="req-load",
                    logger=__import__("logging").getLogger("test.jina"),
                    config={
                        "url": "https://example.test/news/oil",
                        "endpoint": "https://reader.test/{url}",
                    },
                )
            )
        )
        self._run_async(self.plugin.start())

    def tearDown(self) -> None:
        self._run_async(self.plugin.stop())

    def _run_async(self, value):
        return asyncio.run(value)

    def test_fetch_extracts_jina_text_to_source_result(self) -> None:
        response = _FakeHTTPResponse(
            body=b"# Quarterly Oil Update\n\nOil inventories fell for the third consecutive week.\n",
            headers={"Content-Type": "text/plain; charset=utf-8"},
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
        self.assertEqual(item["external_id"], "https://example.test/news/oil")
        self.assertEqual(item["title"], "Quarterly Oil Update")
        self.assertIn("Oil inventories fell for the third consecutive week.", item["content"])
        self.assertEqual(item["metadata"]["reader"], "jina")
        self.assertEqual(item["metadata"]["reader_url"], "https://reader.test/https://example.test/news/oil")
        self.assertEqual(result.output["metadata"]["source"], "jina")

    def test_manifest_entrypoint_resolves_plugin_export(self) -> None:
        exported = getattr(self.module, self.entrypoint_attribute)

        self.assertIs(exported, self.module.plugin)
        self.assertIs(exported, self.module.JinaSourcePlugin)

    def test_fetch_rejects_private_or_local_urls(self) -> None:
        for bad_url in (
            "http://localhost/article",
            "http://127.0.0.1/article",
            "http://10.1.2.3/article",
            "http://192.168.0.8/article",
            "http://service.local/article",
        ):
            with self.subTest(url=bad_url):
                with self.assertRaisesRegex(ValueError, "private or local urls must not be sent to external reader"):
                    self._run_async(
                        self.plugin.invoke(
                            PluginInvokeRequest(
                                capability="source.fetch",
                                request_id="req-private",
                                input={"query": bad_url},
                            )
                        )
                    )

    def test_fetch_rejects_missing_or_blank_url(self) -> None:
        self._run_async(
            self.plugin.load(
                RuntimeContext(
                    plugin_id=self.plugin_id,
                    plugin_version="0.1.0",
                    request_id="req-missing-load",
                    logger=__import__("logging").getLogger("test.jina"),
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
        with self.assertRaisesRegex(ValueError, "url must be a non-empty string"):
            self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(capability="source.fetch", request_id="req-empty", input={"query": ""})
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
                    logger=__import__("logging").getLogger("test.jina"),
                    config={
                        "url": "https://example.test/news/oil",
                        "timeout_seconds": 61,
                    },
                )
            )
        )
        with self.assertRaisesRegex(ValueError, "timeout_seconds must be <= 60"):
            self._run_async(
                self.plugin.invoke(
                    PluginInvokeRequest(capability="source.fetch", request_id="req-timeout", input={})
                )
            )

    def test_fetch_fails_on_empty_reader_response(self) -> None:
        response = _FakeHTTPResponse(
            body=b"   \n\n",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

        with patch.object(self.module, "urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "jina source returned empty content"):
                self._run_async(
                    self.plugin.invoke(
                        PluginInvokeRequest(
                            capability="source.fetch",
                            request_id="req-empty-response",
                            input={},
                        )
                    )
                )

    def test_fetch_falls_back_to_utf8_when_charset_is_unknown(self) -> None:
        response = _FakeHTTPResponse(
            body="# Quarterly Oil Update\n\nText body.".encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=unknown-charset"},
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

        self.assertEqual(result.output["items"][0]["title"], "Quarterly Oil Update")

    def test_readme_documents_boundaries(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("只提供 `source.fetch` 能力，不暴露 `tool.read_url`。", readme)  # noqa: RUF001
        self.assertIn("当前实现默认拒绝 `localhost`、环回地址、私网地址、链路本地地址和 `.local` 域名。", readme)


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
