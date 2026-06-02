from __future__ import annotations

import asyncio
from http.client import RemoteDisconnected
import json
import logging
import sys
import time
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
from quantagent.plugin_sdk import PluginInvokeRequest, PluginRuntimeError, RuntimeContext, SourceFetchResult


PLUGIN_ID = "quantagent.official.source.rss"
PLUGIN_ROOT = REPO_ROOT / "plugins" / "sources" / "rss-source"
RSS_FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "rss_feed.xml"
ATOM_FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "atom_feed.xml"
THOMSON_REUTERS_FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "thomson_reuters_news_releases.xml"


class RSSSourcePluginTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        plugin, error = asyncio.run(
            PluginRuntimeService().load_plugin(
                _rss_record(),
                request_id="req-rss-test-load",
                config={},
                metadata={"origin": "rss-plugin-test"},
            )
        )
        if error is not None or plugin is None:
            raise AssertionError(f"Failed to load RSS plugin through runtime: {error}")
        cls.plugin = plugin

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "plugin"):
            asyncio.run(
                PluginRuntimeService().stop_plugin(
                    cls.plugin,
                    plugin_id=PLUGIN_ID,
                )
            )
            del cls.plugin

    def test_fetch_parses_rss_feed(self) -> None:
        rss_xml = RSS_FIXTURE.read_text(encoding="utf-8")
        responses = {
            "https://feeds.example.com/rss.xml": _FakeHTTPResponse(rss_xml),
        }

        _set_plugin_config(self.plugin, {"feeds": ["https://feeds.example.com/rss.xml"]})
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-fetch-rss",
                    )
                )
            )

        output = SourceFetchResult.from_mapping(result.output)
        self.assertEqual(output.metadata["source"], "rss")
        self.assertEqual(output.metadata["feed_count"], 1)
        self.assertEqual(len(output.items), 2)

        first_item = output.items[0]
        self.assertEqual(first_item.external_id, "rss-item-1")
        self.assertEqual(first_item.url, "https://example.com/articles/battery-rally")
        self.assertEqual(first_item.title, "Battery Storage Rally Extends")
        self.assertIn("Battery storage suppliers climbed", first_item.content or "")
        self.assertEqual(first_item.author, "Alex Chen")
        self.assertIsNotNone(first_item.published_at)
        self.assertIsNotNone(first_item.captured_at)
        self.assertEqual(first_item.metadata["plugin_id"], PLUGIN_ID)
        self.assertEqual(first_item.metadata["feed_url"], "https://feeds.example.com/rss.xml")
        self.assertEqual(first_item.metadata["feed_title"], "Quant Daily RSS")
        self.assertEqual(first_item.metadata["entry_id"], "rss-item-1")
        self.assertEqual(first_item.metadata["content_type"], "application/rss+xml")

    def test_fetch_parses_atom_feed(self) -> None:
        atom_xml = ATOM_FIXTURE.read_text(encoding="utf-8")
        responses = {
            "https://feeds.example.com/atom.xml": _FakeHTTPResponse(atom_xml),
        }

        _set_plugin_config(self.plugin, {"feeds": ["https://feeds.example.com/atom.xml"]})
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-fetch-atom",
                    )
                )
            )

        output = SourceFetchResult.from_mapping(result.output)
        self.assertEqual(len(output.items), 1)
        item = output.items[0]
        self.assertEqual(item.external_id, "atom-entry-1")
        self.assertEqual(item.url, "https://example.com/articles/memory-pricing")
        self.assertEqual(item.title, "Memory Pricing Turns Up")
        self.assertIn("Spot prices moved higher", item.content or "")
        self.assertEqual(item.author, "Taylor Lin")
        self.assertEqual(item.metadata["content_type"], "application/atom+xml")
        self.assertEqual(item.metadata["feed_title"], "Quant Atom Feed")

    def test_request_input_cannot_override_runtime_config(self) -> None:
        rss_xml = RSS_FIXTURE.read_text(encoding="utf-8")
        responses = {
            "https://feeds.example.com/configured.xml": _FakeHTTPResponse(rss_xml),
        }
        runtime = _RuntimeServiceWithResponses(responses)

        invocation = asyncio.run(
            runtime.invoke(
                _rss_record(),
                capability="source.fetch",
                request_id="req-rss-config-boundary",
                config={"feeds": ["https://feeds.example.com/configured.xml"]},
                input={"feeds": ["https://feeds.example.com/overridden.xml"]},
            )
        )

        self.assertTrue(invocation.ok)
        output = SourceFetchResult.from_mapping(invocation.result.output)
        self.assertEqual(output.items[0].metadata["feed_url"], "https://feeds.example.com/configured.xml")

    def test_fetch_parses_thomson_reuters_fixture(self) -> None:
        feed_xml = THOMSON_REUTERS_FIXTURE.read_text(encoding="utf-8")
        feed_url = "https://ir.thomsonreuters.com/rss/news-releases.xml?items=15"
        responses = {
            feed_url: _FakeHTTPResponse(feed_xml),
        }

        _set_plugin_config(self.plugin, {"feeds": [feed_url], "max_items_per_feed": 5})
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-fetch-thomson-reuters",
                    )
                )
            )

        output = SourceFetchResult.from_mapping(result.output)
        self.assertEqual(len(output.items), 5)
        self.assertEqual(output.metadata["feed_count"], 1)
        self.assertEqual(output.metadata["item_count"], 5)

        first_item = output.items[0]
        self.assertEqual(first_item.external_id, "32166")
        self.assertEqual(
            first_item.title,
            "Thomson Reuters to Present at CIBC Technology & Innovation Conference",
        )
        self.assertEqual(
            first_item.url,
            "https://ir.thomsonreuters.com/news-releases/news-release-details/thomson-reuters-present-cibc-technology-innovation-conference-2",
        )
        self.assertEqual(first_item.author, "Thomson Reuters News Releases")
        self.assertEqual(first_item.published_at, "2026-05-18T11:00:00-04:00")
        self.assertIn("Steve Assie", first_item.content or "")
        self.assertEqual(first_item.metadata["feed_title"], "Thomson Reuters News Releases")
        self.assertEqual(first_item.metadata["entry_id"], "32166")
        self.assertEqual(first_item.metadata["content_type"], "application/rss+xml")

    def test_missing_feeds_raises_plugin_runtime_error(self) -> None:
        _set_plugin_config(self.plugin, {})
        with self.assertRaises(PluginRuntimeError) as raised:
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-missing-feeds",
                    )
                )
            )
        self.assertEqual(raised.exception.code, "PLUGIN_INVALID_INPUT")
        self.assertIn("feeds must be an array of non-empty feed URLs", raised.exception.message)

    def test_invalid_feed_content_raises_plugin_runtime_error(self) -> None:
        responses = {
            "https://feeds.example.com/bad.xml": _FakeHTTPResponse("<rss><channel><title>broken"),
        }

        _set_plugin_config(self.plugin, {"feeds": ["https://feeds.example.com/bad.xml"]})
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            with self.assertRaises(PluginRuntimeError) as raised:
                asyncio.run(
                    self.plugin.invoke(
                        PluginInvokeRequest(
                            capability="source.fetch",
                            request_id="req-rss-bad-feed",
                        )
                    )
                )

        self.assertEqual(raised.exception.code, "PLUGIN_PARSE_FAILED")

    def test_rdf_feed_returns_explicit_not_supported_error(self) -> None:
        rdf_xml = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/">
  <channel><title>RDF Feed</title></channel>
  <item><title>hello</title></item>
</rdf:RDF>
"""
        responses = {
            "https://feeds.example.com/rdf.xml": _FakeHTTPResponse(rdf_xml),
        }

        _set_plugin_config(self.plugin, {"feeds": ["https://feeds.example.com/rdf.xml"]})
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            with self.assertRaises(PluginRuntimeError) as raised:
                asyncio.run(
                    self.plugin.invoke(
                        PluginInvokeRequest(
                            capability="source.fetch",
                            request_id="req-rss-rdf-feed",
                        )
                    )
                )

        self.assertEqual(raised.exception.code, "PLUGIN_PARSE_FAILED")
        self.assertIn("Feed content", raised.exception.message)

    def test_max_items_per_feed_is_enforced(self) -> None:
        rss_xml = RSS_FIXTURE.read_text(encoding="utf-8")
        responses = {
            "https://feeds.example.com/rss.xml": _FakeHTTPResponse(rss_xml),
        }

        _set_plugin_config(self.plugin, {"feeds": ["https://feeds.example.com/rss.xml"], "max_items_per_feed": 1})
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-max-items",
                    )
                )
            )

        output = SourceFetchResult.from_mapping(result.output)
        self.assertEqual(len(output.items), 1)
        self.assertEqual(output.items[0].external_id, "rss-item-1")

    def test_rejects_feed_count_over_limit(self) -> None:
        too_many = [f"https://feeds.example.com/{index}.xml" for index in range(21)]
        _set_plugin_config(self.plugin, {"feeds": too_many})
        with self.assertRaisesRegex(PluginRuntimeError, "feeds must contain no more than 20 URLs"):
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-too-many-feeds",
                    )
                )
            )

    def test_rejects_sensitive_headers_in_config(self) -> None:
        _set_plugin_config(
            self.plugin,
            {
                "feeds": ["https://feeds.example.com/rss.xml"],
                "headers": {"Authorization": "Bearer secret"},
            },
        )
        with self.assertRaisesRegex(PluginRuntimeError, "sensitive header 'Authorization' is not allowed"):
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-sensitive-header",
                    )
                )
            )

    def test_rejects_feed_response_over_size_limit(self) -> None:
        body = "<rss><channel><title>x</title>" + ("a" * 3000) + "</channel></rss>"
        responses = {
            "https://feeds.example.com/large.xml": _FakeHTTPResponse(body),
        }

        _set_plugin_config(
            self.plugin,
            {
                "feeds": ["https://feeds.example.com/large.xml"],
                "max_response_bytes": 1024,
            },
        )
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            with self.assertRaises(PluginRuntimeError) as raised:
                asyncio.run(
                    self.plugin.invoke(
                        PluginInvokeRequest(
                            capability="source.fetch",
                            request_id="req-rss-large-feed",
                        )
                    )
                )

        self.assertEqual(raised.exception.code, "PLUGIN_FETCH_TOO_LARGE")

    def test_truncates_content_to_configured_limit(self) -> None:
        long_content = "x" * 5000
        rss_xml = f"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Long</title>
<item><title>Long item</title><link>https://example.com/long</link><guid>long-1</guid><description>{long_content}</description></item>
</channel></rss>"""
        responses = {
            "https://feeds.example.com/long.xml": _FakeHTTPResponse(rss_xml),
        }

        _set_plugin_config(
            self.plugin,
            {
                "feeds": ["https://feeds.example.com/long.xml"],
                "max_content_chars": 256,
            },
        )
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-truncate-content",
                    )
                )
            )

        output = SourceFetchResult.from_mapping(result.output)
        self.assertEqual(len(output.items[0].content or ""), 256)

    def test_keywords_filter_keeps_only_matching_entries(self) -> None:
        rss_xml = RSS_FIXTURE.read_text(encoding="utf-8")
        responses = {
            "https://feeds.example.com/rss.xml": _FakeHTTPResponse(rss_xml),
        }

        _set_plugin_config(
            self.plugin,
            {
                "feeds": ["https://feeds.example.com/rss.xml"],
                "keywords": ["battery"],
            },
        )
        with patch.object(type(self.plugin), "opener", staticmethod(_fake_opener(responses))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-rss-keywords",
                    )
                )
            )

        output = SourceFetchResult.from_mapping(result.output)
        self.assertEqual(len(output.items), 1)
        self.assertEqual(output.items[0].external_id, "rss-item-1")

    def test_remote_disconnect_maps_to_fetch_failed(self) -> None:
        def failing_opener(*_args, **_kwargs):
            raise RemoteDisconnected("Remote end closed connection without response")

        _set_plugin_config(self.plugin, {"feeds": ["https://feeds.example.com/rss.xml"]})
        with patch.object(type(self.plugin), "opener", staticmethod(failing_opener)):
            with self.assertRaises(PluginRuntimeError) as raised:
                asyncio.run(
                    self.plugin.invoke(
                        PluginInvokeRequest(
                            capability="source.fetch",
                            request_id="req-rss-remote-disconnect",
                        )
                    )
                )

        self.assertEqual(raised.exception.code, "PLUGIN_FETCH_FAILED")

    def test_invoke_offloads_blocking_fetch_from_event_loop(self) -> None:
        rss_xml = RSS_FIXTURE.read_text(encoding="utf-8")

        def slow_opener(*_args, **_kwargs):
            time.sleep(0.05)
            return _FakeHTTPResponse(rss_xml)

        async def main():
            ticked = False

            async def tick():
                nonlocal ticked
                await asyncio.sleep(0.01)
                ticked = True

            _set_plugin_config(self.plugin, {"feeds": ["https://feeds.example.com/rss.xml"]})
            with patch.object(type(self.plugin), "opener", staticmethod(slow_opener)):
                invoke_task = asyncio.create_task(
                    self.plugin.invoke(
                        PluginInvokeRequest(
                            capability="source.fetch",
                            request_id="req-rss-offload",
                        )
                    )
                )
                tick_task = asyncio.create_task(tick())
                await asyncio.gather(invoke_task, tick_task)
            return ticked

        self.assertTrue(asyncio.run(main()))

    def test_runtime_invocation_roundtrips_source_fetch_result(self) -> None:
        rss_xml = RSS_FIXTURE.read_text(encoding="utf-8")
        atom_xml = ATOM_FIXTURE.read_text(encoding="utf-8")
        runtime = _RuntimeServiceWithResponses(
            {
                "https://feeds.example.com/rss.xml": _FakeHTTPResponse(rss_xml),
                "https://feeds.example.com/atom.xml": _FakeHTTPResponse(atom_xml),
            }
        )

        invocation = asyncio.run(
            runtime.invoke(
                _rss_record(),
                capability="source.fetch",
                request_id="req-rss-runtime",
                config={
                    "feeds": [
                        "https://feeds.example.com/rss.xml",
                        "https://feeds.example.com/atom.xml",
                    ],
                    "max_items_per_feed": 2,
                },
                input={},
            )
        )

        self.assertTrue(invocation.ok)
        self.assertIsNotNone(invocation.result)
        output = SourceFetchResult.from_mapping(invocation.result.output)
        reconstructed = SourceFetchResult.from_mapping(output.to_mapping())
        self.assertEqual(len(reconstructed.items), 3)
        self.assertEqual(reconstructed.metadata["plugin_id"], PLUGIN_ID)

    def test_manifest_schema_and_readme_document_boundary(self) -> None:
        record = _rss_record()
        self.assertEqual(record.manifest.capabilities, ("source.fetch",))
        self.assertEqual(record.manifest.entrypoint, "src.rss_source:plugin")

        schema = json.loads(record.config_schema_path.read_text(encoding="utf-8"))
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in ("feeds", "timeout_seconds", "headers", "user_agent", "max_items_per_feed", "include_content"):
            self.assertIn(key, properties)
        self.assertIn("feeds", required)
        self.assertEqual(properties["feeds"]["maxItems"], 20)
        self.assertIn("max_response_bytes", properties)
        self.assertIn("max_content_chars", properties)
        self.assertIn("keywords", properties)

        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("不负责 `RawEvent` 入库", readme)
        self.assertIn("不是内嵌关系", readme)
        self.assertIn("不是完整 source ingestion 主链路", readme)
        self.assertIn("uv run python", readme)
        self.assertIn("当前不支持 RSS 1.0 / RDF", readme)


def _rss_record():
    records = RegistryScanner(
        official_root=REPO_ROOT / "plugins",
        runtime_root=REPO_ROOT / "runtime" / "plugins",
    ).scan()
    return {item.id: item for item in records}[PLUGIN_ID]


def _fake_opener(responses):
    def opener(request, *_args, **_kwargs):
        url = getattr(request, "full_url", None) or request.get_full_url()
        if url not in responses:
            raise AssertionError(f"Unexpected URL requested: {url}")
        return responses[url]

    return opener


def _set_plugin_config(plugin, config):
    current = plugin.context
    plugin._context = RuntimeContext(
        plugin_id=current.plugin_id,
        plugin_version=current.plugin_version,
        request_id=current.request_id,
        logger=logging.getLogger(f"rss-plugin-test.{current.plugin_id}"),
        config=config,
        runtime_mode=current.runtime_mode,
        metadata=current.metadata,
    )


class _RuntimeServiceWithResponses(PluginRuntimeService):
    def __init__(self, responses) -> None:
        super().__init__()
        self._responses = responses

    def _load_plugin_module(self, module_name: str, *, plugin_path: Path | None = None):
        module = super()._load_plugin_module(module_name, plugin_path=plugin_path)
        module.RSSSourcePlugin.opener = staticmethod(_fake_opener(self._responses))
        return module


class _FakeHeaders:
    def __init__(self, charset: str = "utf-8") -> None:
        self._charset = charset

    def get_content_charset(self) -> str:
        return self._charset


class _FakeHTTPResponse:
    def __init__(self, body: str, *, charset: str = "utf-8") -> None:
        self._body = body.encode("utf-8")
        self.headers = _FakeHeaders(charset=charset)

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            return self._body
        return self._body[:size]

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
