"""Tavily Source Tool 插件单元测试。

完全照搬 readability-source 的测试模式:
- 通过 PluginRuntimeService 加载插件
- 使用 patch.object 注入 fake HTTP 请求
- 测试正常流程、边界条件、错误处理
"""

from __future__ import annotations

import asyncio
import json
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
from quantagent.plugin_sdk import PluginInvokeRequest, PluginRuntimeError

PLUGIN_ROOT = REPO_ROOT / "plugins" / "sources" / "tavily-source"
SEARCH_FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "tavily_search_response.json"
EXTRACT_FIXTURE = PLUGIN_ROOT / "tests" / "fixtures" / "tavily_extract_response.json"
PLUGIN_ID = "quantagent.official.source.tavily"


class TavilySourcePluginTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        plugin, error = asyncio.run(
            PluginRuntimeService().load_plugin(
                _tavily_record(),
                request_id="req-tavily-test-load",
                config={"api_key_ref": "test-key-12345"},
                metadata={"origin": "tavily-plugin-test"},
            )
        )
        if error is not None or plugin is None:
            raise AssertionError(f"Failed to load tavily plugin through runtime: {error}")
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

    def test_search_returns_structured_results(self) -> None:
        """测试 source.search 返回结构化结果。"""
        fixture_data = json.loads(SEARCH_FIXTURE.read_text(encoding="utf-8"))

        with patch.object(type(self.plugin), "http_request", staticmethod(_fake_http(fixture_data))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.search",
                        request_id="req-tavily-test-search",
                        input={"query": "battery storage breakthrough 2026"},
                    )
                )
            )

        self.assertIsNotNone(result.output)
        self.assertEqual(result.output["query"], "battery storage breakthrough 2026")
        self.assertEqual(len(result.output["results"]), 2)
        self.assertEqual(result.output["metadata"]["provider"], "tavily")
        self.assertEqual(result.output["metadata"]["result_count"], 2)

        # 验证第一条结果的结构
        first_result = result.output["results"][0]
        self.assertEqual(first_result["title"], "Grid-Scale Battery Storage Breakthrough Reported in East Asia")
        self.assertEqual(first_result["url"], "https://example.com/articles/storage-breakthrough")
        self.assertIn("Battery storage suppliers climbed", first_result["snippet"])
        self.assertEqual(first_result["score"], 0.92)
        self.assertEqual(first_result["source"], "tavily")

    def test_extract_returns_structured_content(self) -> None:
        """测试 source.extract 返回结构化内容。"""
        fixture_data = json.loads(EXTRACT_FIXTURE.read_text(encoding="utf-8"))

        with patch.object(type(self.plugin), "http_request", staticmethod(_fake_http(fixture_data))):
            result = asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.extract",
                        request_id="req-tavily-test-extract",
                        input={"url": "https://example.com/articles/storage-breakthrough"},
                    )
                )
            )

        self.assertIsNotNone(result.output)
        self.assertEqual(result.output["url"], "https://example.com/articles/storage-breakthrough")
        self.assertIn("Battery storage suppliers climbed", result.output["content"])
        self.assertEqual(result.output["metadata"]["provider"], "tavily")
        self.assertGreater(result.output["metadata"]["content_length"], 0)

    def test_runtime_invokes_manifest_entrypoint(self) -> None:
        """测试通过 PluginRuntimeService 端到端调用。"""
        fixture_data = json.loads(SEARCH_FIXTURE.read_text(encoding="utf-8"))
        runtime = _RuntimeServiceWithFakeHttp(fixture_data)

        invocation = asyncio.run(
            runtime.invoke(
                _tavily_record(),
                capability="source.search",
                request_id="req-tavily-runtime",
                config={"api_key_ref": "test-key-12345"},
                input={"query": "battery storage breakthrough 2026"},
            )
        )

        self.assertTrue(invocation.ok)
        self.assertIsNotNone(invocation.result)
        self.assertEqual(invocation.result.output["query"], "battery storage breakthrough 2026")
        self.assertEqual(len(invocation.result.output["results"]), 2)

    def test_search_rejects_missing_query(self) -> None:
        """测试 source.search 缺失 query 参数时报错。"""
        with self.assertRaisesRegex(PluginRuntimeError, "query must be a non-empty string"):
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.search",
                        request_id="req-tavily-missing-query",
                        input={},
                    )
                )
            )

    def test_extract_rejects_missing_url(self) -> None:
        """测试 source.extract 缺失 url 参数时报错。"""
        with self.assertRaisesRegex(PluginRuntimeError, "url must be a non-empty string"):
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.extract",
                        request_id="req-tavily-missing-url",
                        input={},
                    )
                )
            )

    def test_rejects_unsupported_capability(self) -> None:
        """测试不支持的 capability 报错。"""
        with self.assertRaisesRegex(PluginRuntimeError, "PLUGIN_CAPABILITY_NOT_IMPLEMENTED"):
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.fetch",
                        request_id="req-tavily-unsupported-cap",
                        input={"query": "test"},
                    )
                )
            )

    def test_rejects_missing_api_key(self) -> None:
        """测试缺失 API key 配置时报错。"""
        with self.assertRaisesRegex(PluginRuntimeError, "PLUGIN_CONFIG_MISSING"):
            asyncio.run(
                self.plugin.invoke(
                    PluginInvokeRequest(
                        capability="source.search",
                        request_id="req-tavily-missing-key",
                        input={"query": "test"},
                    )
                )
            )

    def test_upstream_401_is_wrapped_and_desensitized(self) -> None:
        """测试上游 401 错误被正确包装且脱敏。"""
        def _fake_401(request, timeout=10.0):
            import urllib.error
            raise urllib.error.HTTPError(
                url="https://api.tavily.com/search",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=None,
            )

        with patch.object(type(self.plugin), "http_request", staticmethod(_fake_401)):
            with self.assertRaisesRegex(PluginRuntimeError, "TAVILY_AUTH_FAILED"):
                asyncio.run(
                    self.plugin.invoke(
                        PluginInvokeRequest(
                            capability="source.search",
                            request_id="req-tavily-401",
                            input={"query": "test"},
                        )
                    )
                )

    def test_upstream_timeout_is_wrapped(self) -> None:
        """测试上游超时错误被正确包装。"""
        def _fake_timeout(request, timeout=10.0):
            raise TimeoutError("Request timed out")

        with patch.object(type(self.plugin), "http_request", staticmethod(_fake_timeout)):
            with self.assertRaisesRegex(PluginRuntimeError, "TAVILY_TIMEOUT"):
                asyncio.run(
                    self.plugin.invoke(
                        PluginInvokeRequest(
                            capability="source.search",
                            request_id="req-tavily-timeout",
                            input={"query": "test"},
                        )
                    )
                )

    def test_readme_documents_plugin_boundary(self) -> None:
        """测试 README 说明插件边界。"""
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("source.search", readme)
        self.assertIn("source.extract", readme)
        self.assertIn("不负责", readme)


def _tavily_record():
    """扫描注册表获取 Tavily 插件记录。"""
    records = RegistryScanner(
        official_root=REPO_ROOT / "plugins",
        runtime_root=REPO_ROOT / "runtime" / "plugins",
    ).scan()
    return {item.id: item for item in records}[PLUGIN_ID]


def _fake_http(json_response):
    """创建 fake HTTP 请求函数，返回预设的 JSON 响应。"""
    encoded = json.dumps(json_response).encode("utf-8")

    class _FakeResponse:
        def read(self):
            return encoded

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def _http(request, timeout=10.0):
        return _FakeResponse()

    return _http


class _RuntimeServiceWithFakeHttp(PluginRuntimeService):
    """带 fake HTTP 注入的 RuntimeService，用于端到端测试。"""

    def __init__(self, json_response) -> None:
        super().__init__()
        self._json_response = json_response

    def _load_plugin_module(self, module_name: str, *, plugin_path: Path | None = None):
        module = super()._load_plugin_module(module_name, plugin_path=plugin_path)
        module.TavilySourcePlugin.http_request = staticmethod(_fake_http(self._json_response))
        return module


if __name__ == "__main__":
    unittest.main()
