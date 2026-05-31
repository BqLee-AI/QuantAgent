"""Tavily Source Tool 插件入口。

设计关键:
- 顶部 sys.path 操作使 sibling tavily_client.py 可直接 import
- 类属性 http_request 作为测试注入点（seam），与 readability 的 opener 模式一致
- 合并平台配置与请求输入，请求输入优先级更高
- 所有 TavilyClientError 统一转换为 PluginRuntimeError
- 中文注释说明非显然边界决策
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# 修改 sys.path 使 sibling tavily_client.py 可 import
_src_dir = str(Path(__file__).parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from tavily_client import TavilyClient, TavilyClientError, default_http_request

from quantagent.plugin_sdk import (
    BasePlugin,
    PluginInvokeRequest,
    PluginInvokeResult,
    PluginRuntimeError,
    SourceFetchResult,
    SourceItemDraft,
)


PLUGIN_ID = "quantagent.official.source.tavily"
SUPPORTED_CAPABILITIES = frozenset({"source.fetch", "source.search", "source.extract"})


class TavilySourcePlugin(BasePlugin):
    """Tavily Source Tool 插件。

    提供 source.search 和 source.extract 两个能力。
    """

    # 类属性 seam，测试时注入 mock HTTP 实现
    http_request = staticmethod(default_http_request)

    async def invoke(self, request: PluginInvokeRequest) -> PluginInvokeResult:
        """处理插件调用请求。

        Args:
            request: 包含 capability、input、metadata 的调用请求

        Returns:
            PluginInvokeResult 包含标准化输出

        Raises:
            PluginRuntimeError: 能力不支持、配置缺失、上游调用失败等
        """
        # 1. 检查能力是否支持
        if request.capability not in SUPPORTED_CAPABILITIES:
            raise PluginRuntimeError(
                code="PLUGIN_CAPABILITY_NOT_IMPLEMENTED",
                message=f"Tavily source only implements {', '.join(sorted(SUPPORTED_CAPABILITIES))}",
                stage="invoke",
                details={"capability": request.capability, "supported": list(SUPPORTED_CAPABILITIES)},
            )

        # 2. 合并有效配置（平台配置 + 请求输入）
        config = _merge_effective_config(self.context.config, request.input)

        # 3. 获取 API key（必需配置）
        api_key = config.get("api_key_ref")
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            raise PluginRuntimeError(
                code="PLUGIN_CONFIG_MISSING",
                message="Missing or invalid api_key_ref in config",
                stage="invoke",
                details={"config_key": "api_key_ref"},
            )

        # 4. 构建客户端（注入测试 seam）
        timeout = _coerce_timeout(config.get("timeout_seconds"))
        client = TavilyClient(api_key.strip(), timeout=timeout, http_request=self.http_request)

        # 5. 按 capability 分发处理
        try:
            if request.capability == "source.search":
                result_dict = self._handle_search(client, config)
            elif request.capability == "source.extract":
                result_dict = self._handle_extract(client, config)
            else:
                result_dict = self._handle_fetch(client, config)

            return PluginInvokeResult(output=result_dict.to_mapping())

        except TavilyClientError as e:
            # 上游错误统一转为 PluginRuntimeError
            raise PluginRuntimeError(
                code=e.code,
                message=e.message,
                stage="invoke",
                retryable=e.retryable,
                details=e.details,
            )
        except ValueError as e:
            # 参数验证错误
            raise PluginRuntimeError(
                code="PLUGIN_INVALID_INPUT",
                message=str(e),
                stage="invoke",
                details={"reason": str(e)},
            )
        except Exception as e:
            # 未预期错误：原始信息只记日志，不泄露给调用方
            self.logger.error("Unexpected error in invoke: %s: %s", type(e).__name__, e)
            raise PluginRuntimeError(
                code="PLUGIN_INTERNAL_ERROR",
                message="An internal error occurred",
                stage="invoke",
                details={"error_type": type(e).__name__},
            )

    def _handle_search(self, client: TavilyClient, config: Mapping[str, Any]) -> SourceFetchResult:
        """处理 source.search 能力。

        Args:
            client: Tavily 客户端实例
            config: 合并后的有效配置

        Returns:
            标准化搜索结果字典
        """
        query = _require_string(config, "query")

        # 提取搜索参数：请求级参数优先，fallback 到平台配置级默认值
        max_results = _coerce_max_results(config.get("max_results") or config.get("default_max_results"))
        search_depth = _coerce_search_depth(config.get("search_depth") or config.get("default_search_depth"))
        include_raw_content = _coerce_bool(config.get("include_raw_content"), key="include_raw_content", default=False)
        include_favicon = _coerce_bool(config.get("include_favicon"), key="include_favicon", default=False)

        # 可选的高级参数
        topic = config.get("topic")
        include_domains = config.get("include_domains")
        exclude_domains = config.get("exclude_domains")

        raw_result = client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
            include_favicon=include_favicon,
            topic=topic,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
        return _build_search_fetch_result(raw_result)

    def _handle_extract(self, client: TavilyClient, config: Mapping[str, Any]) -> SourceFetchResult:
        """处理 source.extract 能力。

        Args:
            client: Tavily 客户端实例
            config: 合并后的有效配置

        Returns:
            标准化提取结果字典
        """
        url = _require_string(config, "url")

        # 提取参数
        extract_depth = _coerce_search_depth(config.get("extract_depth"))
        include_raw_content = _coerce_bool(config.get("include_raw_content"), key="include_raw_content", default=False)
        include_favicon = _coerce_bool(config.get("include_favicon"), key="include_favicon", default=False)
        query = config.get("query")  # 可选的提取上下文

        raw_result = client.extract(
            urls=[url],
            extract_depth=extract_depth,
            include_raw_content=include_raw_content,
            include_favicon=include_favicon,
            query=query,
        )
        return _build_extract_fetch_result(raw_result)

    def _handle_fetch(self, client: TavilyClient, config: Mapping[str, Any]) -> SourceFetchResult:
        """兼容 source.fetch 契约。

        为什么这样做：
        - 最新 gate 已把 source 插件的默认能力收口到 source.fetch + SourceFetchResult。
        - Tavily 仍保留 search/extract 两种调用语义，但通过 fetch 作为统一入口，避免插件类型与 DTO 契约继续漂移。
        """
        if isinstance(config.get("url"), str) and config.get("url", "").strip():
            return self._handle_extract(client, config)
        return self._handle_search(client, config)


# 插件入口
plugin = TavilySourcePlugin


# 辅助函数

def _merge_effective_config(
    context_config: Mapping[str, Any],
    request_input: Mapping[str, Any],
) -> dict[str, Any]:
    """合并平台配置与请求输入。

    平台传入的 request.input 表示本次调用覆盖；插件只消费合并后的有效配置，不保存配置状态。
    请求输入优先级高于平台配置。
    """
    return {**context_config, **request_input}


def _require_string(config: Mapping[str, Any], key: str) -> str:
    """获取必需的字符串配置项。

    Args:
        config: 配置字典
        key: 配置键

    Returns:
        非空字符串值

    Raises:
        ValueError: 配置缺失或无效
    """
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _coerce_timeout(value: Any) -> float:
    """强制转换超时配置为有效浮点数。

    Args:
        value: 配置值

    Returns:
        有效的超时时间（秒）

    Raises:
        ValueError: 配置无效
    """
    if value is None:
        return 10.0
    if not isinstance(value, (int, float)):
        raise ValueError("timeout_seconds must be a number")
    if value <= 0 or value > 30:
        raise ValueError("timeout_seconds must be between 0 and 30")
    return float(value)


def _coerce_max_results(value: Any) -> int:
    """强制转换最大结果数配置为有效整数。

    Args:
        value: 配置值

    Returns:
        有效的最大结果数

    Raises:
        ValueError: 配置无效
    """
    if value is None:
        return 5
    if not isinstance(value, int):
        raise ValueError("default_max_results must be an integer")
    if value < 1 or value > 20:
        raise ValueError("default_max_results must be between 1 and 20")
    return int(value)


def _coerce_search_depth(value: Any) -> str:
    """强制转换搜索深度配置为有效枚举值。

    Args:
        value: 配置值

    Returns:
        有效的搜索深度（"basic" 或 "advanced"）

    Raises:
        ValueError: 配置无效
    """
    if value is None:
        return "basic"
    if not isinstance(value, str):
        raise ValueError("default_search_depth must be a string")
    depth = value.lower()
    if depth not in {"basic", "advanced"}:
        raise ValueError('default_search_depth must be "basic" or "advanced"')
    return depth


def _coerce_bool(value: Any, *, key: str, default: bool) -> bool:
    """严格解析布尔配置，避免字符串 false/0 被 Python bool() 误判为 True。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValueError(f"{key} must be a boolean")


def _build_search_fetch_result(raw_result: Mapping[str, Any]) -> SourceFetchResult:
    items = []
    for item in raw_result.get("results", []):
        items.append(
            SourceItemDraft(
                external_id=item.get("url"),
                url=item.get("url"),
                title=item.get("title"),
                content=item.get("content"),
                raw_payload=item.get("raw_payload") or {},
                metadata={
                    "plugin_id": PLUGIN_ID,
                    "provider": "tavily",
                    "score": item.get("score"),
                    "source": item.get("source"),
                    "favicon_url": item.get("favicon_url"),
                    "query": raw_result.get("query"),
                    "search_depth": raw_result.get("metadata", {}).get("search_depth"),
                },
            )
        )
    return SourceFetchResult(
        items=tuple(items),
        metadata={
            "provider": raw_result.get("metadata", {}).get("provider", "tavily"),
            "result_count": raw_result.get("metadata", {}).get("result_count", len(items)),
            "query": raw_result.get("query"),
            "capability": "source.search",
        },
    )


def _build_extract_fetch_result(raw_result: Mapping[str, Any]) -> SourceFetchResult:
    content = raw_result.get("content")
    item = SourceItemDraft(
        external_id=raw_result.get("url") or None,
        url=raw_result.get("url") or None,
        title=raw_result.get("title"),
        content=content,
        raw_payload=raw_result.get("raw_payload") or {},
        metadata={
            "plugin_id": PLUGIN_ID,
            "provider": raw_result.get("metadata", {}).get("provider", "tavily"),
            "favicon_url": raw_result.get("favicon_url"),
            "raw_content": raw_result.get("raw_content"),
            "extraction_source": raw_result.get("metadata", {}).get("extraction_source"),
            "error": raw_result.get("metadata", {}).get("error"),
            "error_details": raw_result.get("metadata", {}).get("error_details"),
        },
    )
    items = () if item.url is None and content is None else (item,)
    return SourceFetchResult(
        items=items,
        metadata={
            "provider": raw_result.get("metadata", {}).get("provider", "tavily"),
            "content_length": raw_result.get("metadata", {}).get("content_length", 0),
            "capability": "source.extract",
            **(
                {"error": raw_result.get("metadata", {}).get("error")}
                if raw_result.get("metadata", {}).get("error")
                else {}
            ),
        },
    )
