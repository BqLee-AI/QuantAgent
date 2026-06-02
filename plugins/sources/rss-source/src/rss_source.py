from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from http.client import RemoteDisconnected
import asyncio
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from quantagent.plugin_sdk import (
    BasePlugin,
    PluginInvokeRequest,
    PluginInvokeResult,
    PluginRuntimeError,
    SourceFetchResult,
    SourceItemDraft,
)


PLUGIN_ID = "quantagent.official.source.rss"
DEFAULT_USER_AGENT = "QuantAgentRSSSource/0.1"
DEFAULT_ACCEPT = "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8"
SUPPORTED_CAPABILITIES = frozenset({"source.fetch"})
MAX_FEEDS = 20
DEFAULT_MAX_RESPONSE_BYTES = 262144
DEFAULT_MAX_CONTENT_CHARS = 4000
MAX_RESPONSE_BYTES_LIMIT = 1048576
MAX_CONTENT_CHARS_LIMIT = 20000
SENSITIVE_HEADER_NAMES = frozenset(
    {
        "api-key",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "proxy-authorization",
        "set-cookie",
        "x-api-key",
    }
)
_DEFAULT_URLOPEN = urlopen


class RSSSourcePlugin(BasePlugin):
    opener = staticmethod(_DEFAULT_URLOPEN)

    async def invoke(self, request: PluginInvokeRequest) -> PluginInvokeResult:
        if request.capability not in SUPPORTED_CAPABILITIES:
            raise PluginRuntimeError(
                code="PLUGIN_CAPABILITY_NOT_IMPLEMENTED",
                message="RSS source only implements source.fetch.",
                stage="invoke",
                details={"capability": request.capability},
            )

        try:
            config = _read_effective_config(self.context.config)
            feeds = _coerce_feeds(config.get("feeds"))
            timeout_seconds = _coerce_timeout(config.get("timeout_seconds"))
            max_items_per_feed = _coerce_max_items_per_feed(config.get("max_items_per_feed"))
            max_response_bytes = _coerce_max_response_bytes(config.get("max_response_bytes"))
            max_content_chars = _coerce_max_content_chars(config.get("max_content_chars"))
            include_content = _coerce_bool(config.get("include_content"), key="include_content", default=True)
            keywords = _coerce_keywords(config.get("keywords"))
            headers = _coerce_headers(config.get("headers"), user_agent=config.get("user_agent"))
            captured_at = datetime.now(UTC).isoformat()

            items: list[SourceItemDraft] = []
            feed_summaries: list[dict[str, Any]] = []
            for feed_url in feeds:
                parsed_feed = await asyncio.to_thread(
                    self._fetch_and_parse_feed,
                    feed_url,
                    headers,
                    timeout_seconds,
                    max_response_bytes,
                )
                feed_summaries.append(
                    {
                        "feed_url": parsed_feed.feed_url,
                        "feed_title": parsed_feed.feed_title,
                        "content_type": parsed_feed.content_type,
                        "item_count": min(len(parsed_feed.entries), max_items_per_feed),
                    }
                )
                items.extend(
                    _build_source_items(
                        parsed_feed,
                        captured_at=captured_at,
                        include_content=include_content,
                        max_items_per_feed=max_items_per_feed,
                        max_content_chars=max_content_chars,
                        keywords=keywords,
                    )
                )

            output = SourceFetchResult(
                items=tuple(items),
                metadata={
                    "source": "rss",
                    "plugin_id": PLUGIN_ID,
                    "feed_count": len(feeds),
                    "item_count": len(items),
                    "feeds": tuple(feed_summaries),
                },
            )
            return PluginInvokeResult(output=output.to_mapping())
        except PluginRuntimeError:
            raise
        except ValueError as exc:
            raise PluginRuntimeError(
                code="PLUGIN_INVALID_INPUT",
                message=str(exc),
                stage="invoke",
                details={"reason": str(exc)},
            ) from exc
        except Exception as exc:
            self.logger.error("Unexpected error in RSS source: %s: %s", type(exc).__name__, exc)
            raise PluginRuntimeError(
                code="PLUGIN_INTERNAL_ERROR",
                message="An internal error occurred.",
                stage="invoke",
                details={"error_type": type(exc).__name__},
            ) from exc

    def _fetch_and_parse_feed(
        self,
        feed_url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> "_ParsedFeed":
        parsed_url = urlparse(feed_url)
        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError(f"feed URLs must use http or https, got: {parsed_url.scheme or '<empty>'}")

        request = Request(feed_url, headers=dict(headers))
        try:
            with self.opener(request, timeout=timeout_seconds) as response:
                body = response.read(max_response_bytes + 1)
                charset = response.headers.get_content_charset() or "utf-8"
        except HTTPError as exc:
            raise PluginRuntimeError(
                code="PLUGIN_FETCH_FAILED",
                message=f"Failed to fetch feed: HTTP {exc.code}",
                stage="invoke",
                retryable=500 <= exc.code < 600,
                details={"feed_url": feed_url, "status_code": exc.code},
            ) from exc
        except URLError as exc:
            raise PluginRuntimeError(
                code="PLUGIN_FETCH_FAILED",
                message="Failed to fetch feed due to a network error.",
                stage="invoke",
                retryable=True,
                details={"feed_url": feed_url, "reason": str(exc.reason)},
            ) from exc
        except TimeoutError as exc:
            raise PluginRuntimeError(
                code="PLUGIN_FETCH_TIMEOUT",
                message=f"Feed request timed out after {timeout_seconds}s.",
                stage="invoke",
                retryable=True,
                details={"feed_url": feed_url, "timeout_seconds": timeout_seconds},
            ) from exc
        except (RemoteDisconnected, ssl.SSLError, OSError) as exc:
            raise PluginRuntimeError(
                code="PLUGIN_FETCH_FAILED",
                message="Failed to fetch feed due to a connection error.",
                stage="invoke",
                retryable=True,
                details={"feed_url": feed_url, "reason": str(exc)},
            ) from exc

        if len(body) > max_response_bytes:
            raise PluginRuntimeError(
                code="PLUGIN_FETCH_TOO_LARGE",
                message="Feed response exceeded the configured size limit.",
                stage="invoke",
                details={"feed_url": feed_url, "max_response_bytes": max_response_bytes},
            )

        xml_text = _decode_text(body, charset)
        return _parse_feed(xml_text, feed_url=feed_url)


plugin = RSSSourcePlugin


class _ParsedEntry:
    def __init__(
        self,
        *,
        entry_id: str | None,
        url: str | None,
        title: str | None,
        content: str | None,
        author: str | None,
        published_at: str | None,
        raw_payload: Mapping[str, Any],
    ) -> None:
        self.entry_id = entry_id
        self.url = url
        self.title = title
        self.content = content
        self.author = author
        self.published_at = published_at
        self.raw_payload = raw_payload


class _ParsedFeed:
    def __init__(
        self,
        *,
        feed_url: str,
        feed_title: str | None,
        content_type: str,
        entries: tuple[_ParsedEntry, ...],
    ) -> None:
        self.feed_url = feed_url
        self.feed_title = feed_title
        self.content_type = content_type
        self.entries = entries


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        text = _collapse_text(data)
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        return _collapse_text(" ".join(self._chunks))


def _read_effective_config(context_config: Mapping[str, Any]) -> dict[str, Any]:
    # 插件只消费平台给出的 effective config；不允许 request.input 覆盖受平台治理的配置字段。
    return dict(context_config)


def _coerce_feeds(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise ValueError("feeds must be an array of non-empty feed URLs")
    feeds = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if not feeds:
        raise ValueError("feeds must contain at least one non-empty URL")
    if len(feeds) > MAX_FEEDS:
        raise ValueError(f"feeds must contain no more than {MAX_FEEDS} URLs")
    return feeds


def _coerce_timeout(value: Any) -> float:
    if value is None:
        return 10.0
    if not isinstance(value, (int, float)) or value <= 0 or value > 30:
        raise ValueError("timeout_seconds must be a positive number no greater than 30")
    return float(value)


def _coerce_max_items_per_feed(value: Any) -> int:
    if value is None:
        return 20
    if not isinstance(value, int) or value < 1 or value > 100:
        raise ValueError("max_items_per_feed must be an integer between 1 and 100")
    return value


def _coerce_max_response_bytes(value: Any) -> int:
    if value is None:
        return DEFAULT_MAX_RESPONSE_BYTES
    if not isinstance(value, int) or value < 1024 or value > MAX_RESPONSE_BYTES_LIMIT:
        raise ValueError(f"max_response_bytes must be an integer between 1024 and {MAX_RESPONSE_BYTES_LIMIT}")
    return value


def _coerce_max_content_chars(value: Any) -> int:
    if value is None:
        return DEFAULT_MAX_CONTENT_CHARS
    if not isinstance(value, int) or value < 128 or value > MAX_CONTENT_CHARS_LIMIT:
        raise ValueError(f"max_content_chars must be an integer between 128 and {MAX_CONTENT_CHARS_LIMIT}")
    return value


def _coerce_bool(value: Any, *, key: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{key} must be a boolean")


def _coerce_keywords(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise ValueError("keywords must be an array of non-empty strings")
    keywords = tuple(item.strip().lower() for item in value if isinstance(item, str) and item.strip())
    if not keywords:
        raise ValueError("keywords must contain at least one non-empty string when provided")
    return keywords


def _coerce_headers(value: Any, *, user_agent: Any) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": DEFAULT_ACCEPT}
    if value is not None:
        if not isinstance(value, Mapping):
            raise ValueError("headers must be an object of string pairs")
        for key, header_value in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("header names must be non-empty strings")
            if not isinstance(header_value, str):
                raise ValueError("header values must be strings")
            normalized_key = key.strip()
            if normalized_key.lower() in SENSITIVE_HEADER_NAMES:
                raise ValueError(f"sensitive header {normalized_key!r} is not allowed in plugin config")
            headers[normalized_key] = header_value

    resolved_user_agent = DEFAULT_USER_AGENT if user_agent is None else user_agent
    if not isinstance(resolved_user_agent, str) or not resolved_user_agent.strip():
        raise ValueError("user_agent must be a non-empty string")
    headers.setdefault("User-Agent", resolved_user_agent.strip())
    return headers


def _decode_text(body: bytes, charset: str) -> str:
    try:
        return body.decode(charset, errors="replace")
    except (LookupError, UnicodeError):
        return body.decode("utf-8", errors="replace")


def _parse_feed(xml_text: str, *, feed_url: str) -> _ParsedFeed:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise PluginRuntimeError(
            code="PLUGIN_PARSE_FAILED",
            message="Feed content is not valid XML.",
            stage="invoke",
            details={"feed_url": feed_url},
        ) from exc

    root_name = _local_name(root.tag)
    if root_name == "feed":
        return _parse_atom_feed(root, feed_url=feed_url)
    if root_name == "rss":
        return _parse_rss_feed(root, feed_url=feed_url)
    if root_name == "rdf":
        raise PluginRuntimeError(
            code="PLUGIN_PARSE_FAILED",
            message="RSS 1.0 / RDF feeds are not supported in RSS Source V0.1.",
            stage="invoke",
            details={"feed_url": feed_url, "root_tag": root_name},
        )
    raise PluginRuntimeError(
        code="PLUGIN_PARSE_FAILED",
        message="Feed content must be RSS or Atom XML.",
        stage="invoke",
        details={"feed_url": feed_url, "root_tag": root_name},
    )


def _parse_rss_feed(root: ElementTree.Element, *, feed_url: str) -> _ParsedFeed:
    channel = _first_child(root, "channel")
    if channel is None:
        channel = root
    feed_title = _normalize_field(_child_text(channel, "title"))
    entries: list[_ParsedEntry] = []
    for item in _iter_children(channel, "item"):
        title = _normalize_field(_child_text(item, "title"))
        url = _normalize_field(_child_text(item, "link"))
        entry_id = _normalize_field(_child_text(item, "guid")) or url
        raw_content = (
            _child_text(item, "description")
            or _child_text(item, "encoded")
            or _child_text(item, "summary")
        )
        entries.append(
            _ParsedEntry(
                entry_id=entry_id,
                url=url,
                title=title,
                content=_normalize_content(raw_content),
                author=_normalize_field(_child_text(item, "author") or _child_text(item, "creator")),
                published_at=_parse_datetime(
                    _child_text(item, "pubDate")
                    or _child_text(item, "published")
                    or _child_text(item, "updated")
                ),
                raw_payload={
                    "feed_url": feed_url,
                    "entry_type": "rss",
                    "guid": entry_id,
                    "link": url,
                    "title": title,
                    "description": _normalize_field(_child_text(item, "description")),
                    "content": _normalize_field(_child_text(item, "encoded")),
                    "author": _normalize_field(_child_text(item, "author") or _child_text(item, "creator")),
                    "published_at": _normalize_field(_child_text(item, "pubDate")),
                },
            )
        )
    return _ParsedFeed(
        feed_url=feed_url,
        feed_title=feed_title,
        content_type="application/rss+xml",
        entries=tuple(entries),
    )


def _parse_atom_feed(root: ElementTree.Element, *, feed_url: str) -> _ParsedFeed:
    feed_title = _normalize_field(_child_text(root, "title"))
    feed_author = _extract_atom_author(root)
    entries: list[_ParsedEntry] = []
    for entry in _iter_children(root, "entry"):
        entry_id = _normalize_field(_child_text(entry, "id"))
        url = _extract_atom_link(entry)
        title = _normalize_field(_child_text(entry, "title"))
        raw_content = _child_text(entry, "summary") or _child_text(entry, "content")
        entries.append(
            _ParsedEntry(
                entry_id=entry_id or url,
                url=url,
                title=title,
                content=_normalize_content(raw_content),
                author=_extract_atom_author(entry) or feed_author,
                published_at=_parse_datetime(_child_text(entry, "published") or _child_text(entry, "updated")),
                raw_payload={
                    "feed_url": feed_url,
                    "entry_type": "atom",
                    "id": entry_id,
                    "link": url,
                    "title": title,
                    "summary": _normalize_field(_child_text(entry, "summary")),
                    "content": _normalize_field(_child_text(entry, "content")),
                    "author": _extract_atom_author(entry) or feed_author,
                    "published_at": _normalize_field(_child_text(entry, "published")),
                    "updated_at": _normalize_field(_child_text(entry, "updated")),
                },
            )
        )
    return _ParsedFeed(
        feed_url=feed_url,
        feed_title=feed_title,
        content_type="application/atom+xml",
        entries=tuple(entries),
    )


def _build_source_items(
    parsed_feed: _ParsedFeed,
    *,
    captured_at: str,
    include_content: bool,
    max_items_per_feed: int,
    max_content_chars: int,
    keywords: tuple[str, ...],
) -> list[SourceItemDraft]:
    items: list[SourceItemDraft] = []
    for index, entry in enumerate(parsed_feed.entries[:max_items_per_feed], start=1):
        if keywords and not _matches_keywords(entry=entry, keywords=keywords):
            continue
        external_id = entry.entry_id or entry.url or _fallback_external_id(parsed_feed.feed_url, index=index, title=entry.title)
        # 只保证 feed 自带 summary/content 片段，不保证正文完整；正文抓取应由平台决定是否再协作 reader 插件。
        content = _truncate_content(entry.content, max_content_chars=max_content_chars) if include_content else None
        items.append(
            SourceItemDraft(
                external_id=external_id,
                url=entry.url,
                title=entry.title,
                content=content,
                author=entry.author,
                published_at=entry.published_at,
                captured_at=captured_at,
                raw_payload=entry.raw_payload,
                metadata={
                    "plugin_id": PLUGIN_ID,
                    "feed_url": parsed_feed.feed_url,
                    "feed_title": parsed_feed.feed_title or parsed_feed.feed_url,
                    "entry_id": entry.entry_id or external_id,
                    "content_type": parsed_feed.content_type,
                },
            )
        )
    return items


def _matches_keywords(*, entry: _ParsedEntry, keywords: tuple[str, ...]) -> bool:
    haystack = " ".join(
        item.strip().lower()
        for item in (entry.title, entry.content, entry.url)
        if isinstance(item, str) and item.strip()
    )
    return any(keyword in haystack for keyword in keywords)


def _fallback_external_id(feed_url: str, *, index: int, title: str | None) -> str:
    normalized_title = title or "untitled"
    return f"{feed_url}#{index}:{normalized_title}"


def _first_child(element: ElementTree.Element, local_name: str) -> ElementTree.Element | None:
    for child in element:
        if _local_name(child.tag) == local_name:
            return child
    return None


def _iter_children(element: ElementTree.Element, local_name: str) -> Iterable[ElementTree.Element]:
    for child in element:
        if _local_name(child.tag) == local_name:
            yield child


def _child_text(element: ElementTree.Element, local_name: str) -> str | None:
    child = _first_child(element, local_name)
    if child is None:
        return None
    return _element_text(child)


def _element_text(element: ElementTree.Element) -> str | None:
    text = "".join(element.itertext())
    normalized = _collapse_text(text)
    return normalized or None


def _extract_atom_author(element: ElementTree.Element) -> str | None:
    author_node = _first_child(element, "author")
    if author_node is None:
        return None
    return _normalize_field(_child_text(author_node, "name") or _element_text(author_node))


def _extract_atom_link(element: ElementTree.Element) -> str | None:
    fallback_url: str | None = None
    for child in _iter_children(element, "link"):
        href = child.attrib.get("href")
        if not href:
            continue
        relation = (child.attrib.get("rel") or "alternate").strip().lower()
        if relation == "alternate":
            return href.strip()
        if fallback_url is None:
            fallback_url = href.strip()
    return fallback_url


def _parse_datetime(value: str | None) -> str | None:
    normalized = _normalize_field(value)
    if normalized is None:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(normalized)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.isoformat()


def _normalize_field(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _collapse_text(value)
    return normalized or None


def _normalize_content(value: str | None) -> str | None:
    normalized = _normalize_field(value)
    if normalized is None:
        return None
    if "<" not in normalized and ">" not in normalized:
        return normalized
    extractor = _HTMLTextExtractor()
    extractor.feed(unescape(normalized))
    text = extractor.text()
    return text or normalized


def _truncate_content(value: str | None, *, max_content_chars: int) -> str | None:
    if value is None or len(value) <= max_content_chars:
        return value
    return value[:max_content_chars].rstrip()


def _collapse_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(unescape(value).split()).strip()


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
