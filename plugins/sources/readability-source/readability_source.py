from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from quantagent.plugin_sdk import (
    BasePlugin,
    PluginInvokeResult,
    SourceFetchInput,
    SourceFetchResult,
    SourceItemDraft,
)


class ReadabilitySourcePlugin(BasePlugin):
    async def invoke(self, request) -> PluginInvokeResult:
        fetch_input = SourceFetchInput.from_mapping(request.input)
        normalized = self._validate_config(self.context.config, fetch_input=fetch_input)
        request = Request(
            normalized["url"],
            headers={
                "User-Agent": "QuantAgent Readability Source/0.1",
                **normalized["headers"],
            },
        )
        with urlopen(request, timeout=normalized["timeout_seconds"]) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type")

        html = _decode_body(body, content_type)
        extracted = _ReadableDocument.from_html(html, normalized["url"])
        content = extracted.best_content(normalized["min_text_length"])
        if not content:
            raise ValueError("readability source could not extract meaningful content")

        result = SourceFetchResult(
            items=(
                SourceItemDraft(
                    external_id=extracted.canonical_url or normalized["url"],
                    url=normalized["url"],
                    title=extracted.title or "(untitled)",
                    content=content,
                    author=extracted.author,
                    published_at=_stringify_datetime(_parse_datetime(extracted.published_at)),
                    raw_payload={
                        "requested_url": normalized["url"],
                        "title": extracted.title,
                        "canonical_url": extracted.canonical_url,
                        "author": extracted.author,
                        "published_at": extracted.published_at,
                        "content_length": len(content),
                    },
                    metadata={
                        "reader": "readability",
                        "requested_url": normalized["url"],
                        "canonical_url": extracted.canonical_url or normalized["url"],
                    },
                ),
            ),
            metadata={"source": "readability"},
        )
        return PluginInvokeResult(output=result.to_mapping())

    def _validate_config(self, config: Mapping[str, Any], *, fetch_input: SourceFetchInput) -> dict[str, Any]:
        if not isinstance(config, Mapping):
            raise ValueError("Readability source config must be an object.")

        url = fetch_input.query or config.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("url scheme must be http or https")

        headers = config.get("headers", {})
        if not isinstance(headers, dict):
            raise ValueError("headers must be an object")
        normalized_headers: dict[str, str] = {}
        for key, value in headers.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("header names must be non-empty strings")
            if not isinstance(value, str):
                raise ValueError("header values must be strings")
            normalized_headers[key] = value

        timeout_seconds = int(config.get("timeout_seconds", 10))
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")
        if timeout_seconds > 60:
            raise ValueError("timeout_seconds must be <= 60")

        min_text_length = int(config.get("min_text_length", 120))
        if min_text_length < 1:
            raise ValueError("min_text_length must be >= 1")

        return {
            "url": url.strip(),
            "headers": normalized_headers,
            "timeout_seconds": timeout_seconds,
            "min_text_length": min_text_length,
        }


class _ReadableHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.current_meta: dict[str, str] = {}
        self.in_title = False
        self.in_ignored_tag = False
        self.article_depth = 0
        self.body_depth = 0
        self.article_parts: list[str] = []
        self.body_parts: list[str] = []
        self.canonical_url: str | None = None
        self.author: str | None = None
        self.published_at: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): (value or "") for name, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        if tag in {"script", "style", "noscript"}:
            self.in_ignored_tag = True
            return
        if tag == "meta":
            self._capture_meta(attr_map)
        elif tag == "link":
            self._capture_link(attr_map)
        elif tag == "article":
            self.article_depth += 1
        elif tag == "body":
            self.body_depth += 1
        elif tag == "time" and not self.published_at:
            datetime_value = attr_map.get("datetime", "").strip()
            if datetime_value:
                self.published_at = datetime_value

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag in {"script", "style", "noscript"}:
            self.in_ignored_tag = False
        elif tag == "article" and self.article_depth > 0:
            self.article_depth -= 1
        elif tag == "body" and self.body_depth > 0:
            self.body_depth -= 1

    def handle_data(self, data: str) -> None:
        text = _normalize_text(data)
        if not text or self.in_ignored_tag:
            return
        if self.in_title:
            self.title_parts.append(text)
        if self.article_depth > 0:
            self.article_parts.append(text)
        elif self.body_depth > 0:
            self.body_parts.append(text)

    def _capture_link(self, attrs: dict[str, str]) -> None:
        rel = attrs.get("rel", "").lower()
        href = attrs.get("href", "").strip()
        if rel == "canonical" and href:
            self.canonical_url = urljoin(self.base_url, href)

    def _capture_meta(self, attrs: dict[str, str]) -> None:
        key = (attrs.get("property") or attrs.get("name") or "").lower().strip()
        content = attrs.get("content", "").strip()
        if not key or not content:
            return
        if key in {"og:title", "twitter:title"} and not self.title_parts:
            self.title_parts.append(content)
        elif key in {"author", "article:author"} and not self.author:
            self.author = content
        elif key in {"article:published_time", "og:published_time", "pubdate"} and not self.published_at:
            self.published_at = content


class _ReadableDocument:
    def __init__(
        self,
        *,
        title: str | None,
        canonical_url: str | None,
        author: str | None,
        published_at: str | None,
        article_text: str | None,
        body_text: str | None,
    ) -> None:
        self.title = title
        self.canonical_url = canonical_url
        self.author = author
        self.published_at = published_at
        self.article_text = article_text
        self.body_text = body_text

    @classmethod
    def from_html(cls, html: str, base_url: str) -> _ReadableDocument:
        parser = _ReadableHTMLParser(base_url)
        parser.feed(html)
        return cls(
            title=_collapse(parser.title_parts),
            canonical_url=parser.canonical_url,
            author=parser.author,
            published_at=parser.published_at,
            article_text=_collapse(parser.article_parts),
            body_text=_collapse(parser.body_parts),
        )

    def best_content(self, min_text_length: int) -> str | None:
        candidates = [self.article_text, self.body_text]
        for candidate in candidates:
            if candidate and len(candidate) >= min_text_length:
                return candidate
        return max((candidate for candidate in candidates if candidate), key=len, default=None)


def _collapse(parts: list[str]) -> str | None:
    text = " ".join(part for part in parts if part)
    collapsed = " ".join(text.split())
    return collapsed or None


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _detect_charset(content_type: str | None) -> str:
    if not content_type:
        return "utf-8"
    for piece in content_type.split(";"):
        key, _, value = piece.partition("=")
        if key.strip().lower() == "charset" and value.strip():
            return value.strip().strip("\"'")
    return "utf-8"


def _decode_body(body: bytes, content_type: str | None) -> str:
    primary_charset = _detect_charset(content_type)
    for charset in (primary_charset, "utf-8"):
        try:
            return body.decode(charset, errors="replace")
        except LookupError:
            continue
    return body.decode("utf-8", errors="replace")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed


def _stringify_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


plugin = ReadabilitySourcePlugin
