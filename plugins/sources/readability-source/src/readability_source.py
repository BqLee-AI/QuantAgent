from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from quantagent.plugin_sdk import (
    BasePlugin,
    PluginInvokeRequest,
    PluginInvokeResult,
    PluginRuntimeError,
    SourceFetchResult,
    SourceItemDraft,
)


PLUGIN_ID = "quantagent.official.source.readability"
_DEFAULT_URLOPEN = urlopen


class ReadabilitySourcePlugin(BasePlugin):
    opener = staticmethod(_DEFAULT_URLOPEN)

    async def invoke(self, request: PluginInvokeRequest) -> PluginInvokeResult:
        if request.capability != "source.fetch":
            raise PluginRuntimeError(
                code="PLUGIN_CAPABILITY_NOT_IMPLEMENTED",
                message="Readability source only implements source.fetch.",
                stage="invoke",
                details={"capability": request.capability},
            )

        config = _merge_effective_config(self.context.config, request.input)
        url = _require_string(config, "url")
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError(f"Only http and https schemes are allowed, got: {parsed_url.scheme or '<empty>'}")
        headers = _coerce_headers(config.get("headers"))
        timeout_seconds = _coerce_timeout(config.get("timeout_seconds"))
        min_text_length = _coerce_min_text_length(config.get("min_text_length"))

        request_obj = Request(url, headers=headers)
        with self.opener(request_obj, timeout=timeout_seconds) as response:
            body = response.read()
            content_type = response.headers.get_content_charset() or "utf-8"
        html = _decode_html(body, content_type)
        output = SourceFetchResult(
            items=(_extract_source_item(html, url, min_text_length=min_text_length),),
            metadata={"source": "readability"},
        )
        return PluginInvokeResult(output=output.to_mapping())


plugin = ReadabilitySourcePlugin


class _ParsedDocument:
    def __init__(self) -> None:
        self.title: str | None = None
        self.canonical_url: str | None = None
        self.site_name: str | None = None
        self.author: str | None = None
        self.published_at: datetime | None = None
        self.article_chunks: list[str] = []
        self.body_chunks: list[str] = []


class _ReadableHTMLParser(HTMLParser):
    _BLOCKED_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.document = _ParsedDocument()
        self._title_buffer: list[str] = []
        self._tag_stack: list[str] = []
        self._skip_depth = 0
        self._inside_title = False
        self._article_depth = 0
        self._body_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs}
        self._tag_stack.append(tag)
        if tag in self._BLOCKED_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._inside_title = True
        if tag == "article":
            self._article_depth += 1
        if tag == "body":
            self._body_depth += 1
        if tag == "link" and (attr_map.get("rel") or "").lower() == "canonical":
            self.document.canonical_url = attr_map.get("href")
        if tag == "meta":
            self._consume_meta(attr_map)

    def handle_endtag(self, tag: str) -> None:
        if self._tag_stack:
            self._tag_stack.pop()
        if tag in self._BLOCKED_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._inside_title = False
            title = _normalize_text(" ".join(self._title_buffer))
            if title:
                self.document.title = title
            self._title_buffer.clear()
        if tag == "article" and self._article_depth > 0:
            self._article_depth -= 1
        if tag == "body" and self._body_depth > 0:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = _normalize_text(data)
        if not text:
            return
        if self._inside_title:
            self._title_buffer.append(text)
            return
        if self._article_depth > 0 and self.document.article_chunks is not None:
            self.document.article_chunks.append(text)
        if self._body_depth > 0 and self.document.body_chunks is not None:
            self.document.body_chunks.append(text)

    def _consume_meta(self, attrs: Mapping[str, str | None]) -> None:
        name = (attrs.get("name") or attrs.get("property") or "").strip().lower()
        content = _normalize_text(attrs.get("content"))
        if not name or not content:
            return
        if name in {"og:title", "twitter:title"} and not self.document.title:
            self.document.title = content
        elif name in {"og:site_name"} and not self.document.site_name:
            self.document.site_name = content
        elif name in {"author", "article:author"} and not self.document.author:
            self.document.author = content
        elif name in {"article:published_time", "og:published_time", "pubdate"} and not self.document.published_at:
            self.document.published_at = _parse_datetime(content)


def _extract_source_item(html: str, url: str, *, min_text_length: int) -> SourceItemDraft:
    parser = _ReadableHTMLParser()
    parser.feed(html)
    document = parser.document
    content = _pick_content(document, min_text_length=min_text_length)
    title = document.title or _fallback_title(url)
    metadata = {
        "reader": "stdlib-readability",
        "site_name": document.site_name,
        "content_length": len(content) if content else 0,
    }
    return SourceItemDraft(
        title=title,
        url=url,
        content=content,
        author=document.author,
        published_at=document.published_at.isoformat() if document.published_at is not None else None,
        raw_payload={"html": html},
        metadata={
            "plugin_id": PLUGIN_ID,
            "canonical_url": document.canonical_url or url,
            **{key: value for key, value in metadata.items() if value not in (None, "")},
        },
    )


def _pick_content(document: _ParsedDocument, *, min_text_length: int) -> str | None:
    article_text = _join_chunks(document.article_chunks or [])
    body_text = _join_chunks(document.body_chunks or [])
    if article_text and len(article_text) >= min_text_length:
        return article_text
    if body_text:
        return body_text
    return article_text or None


def _join_chunks(chunks: list[str]) -> str | None:
    if not chunks:
        return None
    return _normalize_text(" ".join(chunks))


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    collapsed = " ".join(unescape(value).split())
    return collapsed.strip()


def _parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None


def _fallback_title(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or url


def _require_string(config: Mapping[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _merge_effective_config(
    context_config: Mapping[str, Any],
    request_input: Mapping[str, Any],
) -> dict[str, Any]:
    # 平台传入的 request input 表示本次调用覆盖；插件只消费合并后的有效配置，不保存配置状态。
    return {**context_config, **request_input}


def _coerce_headers(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("headers must be an object of string pairs")
    headers: dict[str, str] = {}
    for key, header_value in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("header names must be non-empty strings")
        if not isinstance(header_value, str):
            raise ValueError("header values must be strings")
        headers[key.strip()] = header_value
    return headers


def _coerce_timeout(value: object) -> float:
    if value is None:
        return 10.0
    if not isinstance(value, (int, float)) or value <= 0 or value > 30:
        raise ValueError("timeout_seconds must be a positive number no greater than 30")
    return float(value)


def _coerce_min_text_length(value: object) -> int:
    if value is None:
        return 140
    if not isinstance(value, int) or value < 0:
        raise ValueError("min_text_length must be a non-negative integer")
    return value


def _decode_html(body: bytes, content_type: str) -> str:
    try:
        return body.decode(content_type, errors="replace")
    except (LookupError, UnicodeError):
        return body.decode("utf-8", errors="replace")
