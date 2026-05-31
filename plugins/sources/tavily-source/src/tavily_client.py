"""Tavily HTTP 适配器 - 纯 urllib 实现，零外部依赖。

设计关键:
- TavilyClient 接受 http_request 注入，便于测试时 mock HTTP 响应
- 所有错误脱敏处理，不泄露 API key 或原始响应体
- 防御性响应解析，使用 .get() 避免 KeyError
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Mapping, Optional


def default_http_request(request: urllib.request.Request, timeout: float = 10.0):
    """默认 HTTP 请求实现，使用 urllib.request.urlopen。

    作为模块级函数而非类方法，方便测试时注入 mock 实现。
    不使用下划线前缀，因为 tavily_source.py 需要显式引用它作为类属性默认值。
    """
    return urllib.request.urlopen(request, timeout=timeout)


class TavilyClientError(Exception):
    """Tavily API 调用错误。

    所有异常统一通过此类封装，错误码标准化:
    - TAVILY_AUTH_FAILED: API key 无效或过期 (401)
    - TAVILY_RATE_LIMITED: 超出速率限制 (429)，可重试
    - TAVILY_CLIENT_ERROR: 客户端请求错误 (4xx 其他)
    - TAVILY_SERVER_ERROR: 服务端错误 (5xx)，可重试
    - TAVILY_TIMEOUT: 请求超时
    - TAVILY_NETWORK_ERROR: 网络连接错误
    """

    def __init__(
        self,
        code: str,
        message: str,
        retryable: bool = False,
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)


class TavilyClient:
    """Tavily API 客户端。

    提供 search 和 extract 两个核心方法，返回标准化的响应格式。
    """

    BASE_URL = "https://api.tavily.com"

    def __init__(
        self,
        api_key: str,
        timeout: float = 10.0,
        *,
        http_request: Callable[[urllib.request.Request, float], Any] = default_http_request,
    ) -> None:
        """初始化 Tavily 客户端。

        Args:
            api_key: Tavily API key
            timeout: 请求超时时间（秒）
            http_request: HTTP 请求函数（测试注入点）
        """
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.timeout = timeout
        self.http_request = http_request

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        search_depth: str = "basic",
        include_raw_content: bool = False,
        include_favicon: bool = False,
        topic: Optional[str] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """执行搜索查询。

        Args:
            query: 搜索查询字符串
            max_results: 返回结果数量（1-20）
            search_depth: 搜索深度（"basic" 或 "advanced"）
            include_raw_content: 是否包含原始内容
            include_favicon: 是否包含网站图标
            topic: 搜索主题（可选）
            include_domains: 仅包含指定域名列表（可选）
            exclude_domains: 排除指定域名列表（可选）

        Returns:
            标准化的搜索响应字典，包含 query、results 和 metadata

        Raises:
            TavilyClientError: API 调用失败
        """
        if not query:
            raise ValueError("query is required")

        body = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": include_raw_content,
            "include_favicon": include_favicon,
        }

        # 可选参数仅在非 None/空时添加
        if topic:
            body["topic"] = topic
        if include_domains:
            body["include_domains"] = include_domains
        if exclude_domains:
            body["exclude_domains"] = exclude_domains

        raw_response = self._post(f"{self.BASE_URL}/search", body)
        return self._normalize_search_response(raw_response)

    def extract(
        self,
        urls: List[str],
        *,
        extract_depth: str = "basic",
        include_raw_content: bool = False,
        include_favicon: bool = False,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """提取网页内容。

        Args:
            urls: 要提取的 URL 列表
            extract_depth: 提取深度（"basic" 或 "advanced"）
            include_raw_content: 是否包含原始 HTML 内容
            include_favicon: 是否包含网站图标
            query: 提取时的查询上下文（可选）

        Returns:
            标准化的提取响应字典，包含 url、title、content 和 metadata

        Raises:
            TavilyClientError: API 调用失败
        """
        if not urls:
            raise ValueError("urls is required")

        body = {
            "api_key": self.api_key,
            "urls": urls,
            "extract_depth": extract_depth,
            "include_raw_content": include_raw_content,
            "include_favicon": include_favicon,
        }

        if query:
            body["query"] = query

        raw_response = self._post(f"{self.BASE_URL}/extract", body)
        return self._normalize_extract_response(raw_response)

    def _post(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """执行 POST 请求并返回 JSON 响应。

        Args:
            url: 请求 URL
            body: 请求体字典

        Returns:
            解码后的 JSON 响应字典

        Raises:
            TavilyClientError: HTTP 错误或 JSON 解析错误
        """
        encoded_body = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=encoded_body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            response = self.http_request(request, timeout=self.timeout)
            response_body = response.read().decode("utf-8")
            return json.loads(response_body)
        except urllib.error.HTTPError as e:
            self._handle_http_error(e)
            raise AssertionError("unreachable: _handle_http_error always raises")  # 类型安全
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise TavilyClientError(
                    code="TAVILY_TIMEOUT",
                    message=f"Request timed out after {self.timeout}s",
                    retryable=True,
                    details={"timeout": self.timeout},
                )
            raise TavilyClientError(
                code="TAVILY_NETWORK_ERROR",
                message=f"Network error: {e.reason}",
                retryable=True,
                details={"reason": str(e.reason)},
            )
        except TimeoutError:
            raise TavilyClientError(
                code="TAVILY_TIMEOUT",
                message=f"Request timed out after {self.timeout}s",
                retryable=True,
                details={"timeout": self.timeout},
            )
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
            raise TavilyClientError(
                code="TAVILY_INVALID_RESPONSE",
                message=f"Failed to parse response: {e}",
                details={"error": str(e)},
            )

    def _handle_http_error(self, error: urllib.error.HTTPError) -> None:
        """处理 HTTP 错误并抛出相应的 TavilyClientError。"""
        status_code = error.code

        # 只记录状态码，不读取响应体——响应体可能含敏感信息，不放进 error details
        error_details = {"status_code": status_code}

        if status_code == 401:
            raise TavilyClientError(
                code="TAVILY_AUTH_FAILED",
                message="Invalid or expired API key",
                details=error_details,
            )
        elif status_code == 429:
            raise TavilyClientError(
                code="TAVILY_RATE_LIMITED",
                message="Rate limit exceeded, please retry later",
                retryable=True,
                details=error_details,
            )
        elif 400 <= status_code < 500:
            raise TavilyClientError(
                code="TAVILY_CLIENT_ERROR",
                message=f"Client error: {status_code}",
                details=error_details,
            )
        elif 500 <= status_code < 600:
            raise TavilyClientError(
                code="TAVILY_SERVER_ERROR",
                message=f"Server error: {status_code}",
                retryable=True,
                details=error_details,
            )
        else:
            raise TavilyClientError(
                code="TAVILY_UNKNOWN_ERROR",
                message=f"Unexpected HTTP status: {status_code}",
                details=error_details,
            )

    def _normalize_search_response(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """规范化搜索响应格式。

        将 Tavily API 的原生响应转换为插件标准格式。
        使用防御性 .get() 避免 KeyError。
        """
        results = raw.get("results", [])
        normalized_results = []

        for item in results:
            normalized_item = {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0.0),
                "source": "tavily",
                "published_at": None,  # Tavily search 不直接提供发布时间
                "favicon_url": item.get("favicon"),
                "raw_payload": item,
            }
            normalized_results.append(normalized_item)

        return {
            "query": raw.get("query", ""),
            "results": normalized_results,
            "metadata": {
                "provider": "tavily",
                "result_count": len(normalized_results),
                "search_depth": raw.get("auto_parameters", {}).get("search_depth", "basic"),
            },
        }

    def _normalize_extract_response(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """规范化提取响应格式。

        将 Tavily Extract API 的原生响应转换为插件标准格式。
        如果成功，返回第一个结果的内容；如果失败，返回错误信息。
        """
        results = raw.get("results", [])
        failed_results = raw.get("failed_results", [])

        if not results and failed_results:
            # 所有 URL 都提取失败
            first_error = failed_results[0]
            return {
                "url": first_error.get("url", ""),
                "title": None,
                "content": None,
                "raw_content": None,
                "favicon_url": None,
                "metadata": {
                    "provider": "tavily",
                    "content_length": 0,
                    "extraction_source": "tavily-extract",
                    "error": "Extraction failed",
                    "error_details": first_error.get("error", "Unknown error"),
                },
            }

        if not results:
            # 上游返回空结果时，降级为受控空响应，避免被包装成内部错误。
            return {
                "url": "",
                "title": None,
                "content": None,
                "raw_content": None,
                "favicon_url": None,
                "metadata": {
                    "provider": "tavily",
                    "content_length": 0,
                    "extraction_source": "tavily-extract",
                    "error": "Extraction returned empty result",
                },
            }

        # 返回第一个成功的结果
        first_result = results[0]
        content = first_result.get("content") or first_result.get("raw_content", "")
        raw_content = first_result.get("raw_content")

        return {
            "url": first_result.get("url", ""),
            "title": None,  # Tavily extract 不直接返回标题
            "content": content,
            "raw_content": raw_content,
            "metadata": {
                "provider": "tavily",
                "content_length": len(content),
                "extraction_source": "tavily-extract",
            },
            "favicon_url": first_result.get("favicon"),
            "raw_payload": first_result,
        }
