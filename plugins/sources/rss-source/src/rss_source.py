from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from quantagent.core.events.dto import RawEventDraft
from quantagent.core.sources.protocols import RuntimeContext


class RssSourcePlugin:
    id = "quantagent.official.source.rss"

    def __init__(self) -> None:
        self._loaded = False
        self._started = False

    def load(self, context: RuntimeContext) -> None:
        if context.plugin_id != self.id:
            raise ValueError(f"runtime context plugin_id mismatch: {context.plugin_id}")
        self._loaded = True

    def start(self) -> None:
        if not self._loaded:
            raise RuntimeError("RSS source must be loaded before start.")
        self._started = True

    def stop(self) -> None:
        self._started = False

    def reload(self, config: dict[str, Any]) -> None:
        self._validate_config(config)

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "plugin_id": self.id, "started": self._started}

    def fetch(self, cursor: str | None, config: dict[str, Any]) -> list[RawEventDraft]:
        del cursor
        if not self._started:
            raise RuntimeError("RSS source must be started before fetch.")
        self._validate_config(config)

        max_items = int(config.get("max_items", 50))
        events: list[RawEventDraft] = []
        for feed_url in config["feeds"]:
            body = self._read_feed(feed_url, config)
            events.extend(_parse_feed(body, feed_url, max_items=max_items - len(events)))
            if len(events) >= max_items:
                break
        return events

    def _read_feed(self, feed_url: str, config: dict[str, Any]) -> bytes:
        request = Request(
            feed_url,
            headers={"User-Agent": str(config.get("user_agent", "QuantAgent RSS Source/0.1"))},
        )
        with urlopen(request, timeout=int(config.get("timeout_seconds", 10))) as response:
            return response.read()

    def _validate_config(self, config: dict[str, Any]) -> None:
        feeds = config.get("feeds")
        if not isinstance(feeds, list) or not feeds:
            raise ValueError("RSS source config requires a non-empty feeds list.")
        if any(not isinstance(feed, str) or not feed for feed in feeds):
            raise ValueError("RSS source feeds must be non-empty strings.")


def _parse_feed(body: bytes, feed_url: str, *, max_items: int) -> list[RawEventDraft]:
    if max_items <= 0:
        return []
    root = ElementTree.fromstring(body)
    if _strip_namespace(root.tag) == "rss":
        channel = root.find("channel")
        items = [] if channel is None else list(channel.findall("item"))
        return [_rss_item_to_event(item, feed_url) for item in items[:max_items]]
    if _strip_namespace(root.tag) == "feed":
        entries = [child for child in list(root) if _strip_namespace(child.tag) == "entry"]
        return [_atom_entry_to_event(entry, feed_url) for entry in entries[:max_items]]
    raise ValueError("Unsupported feed format.")


def _rss_item_to_event(item: ElementTree.Element, feed_url: str) -> RawEventDraft:
    title = _child_text(item, "title") or "(untitled)"
    link = _child_text(item, "link")
    guid = _child_text(item, "guid")
    published_at = _parse_datetime(_child_text(item, "pubDate"))
    content = _child_text(item, "description")
    author = _child_text(item, "author")
    external_id = guid or link
    return RawEventDraft(
        source_plugin_id=RssSourcePlugin.id,
        source_type="rss",
        external_id=external_id,
        url=link,
        canonical_url=link,
        title=title,
        content=content,
        author=author,
        published_at=published_at,
        raw_payload={
            "feed_url": feed_url,
            "guid": guid,
            "link": link,
            "title": title,
        },
        metadata={"feed_url": feed_url},
    )


def _atom_entry_to_event(entry: ElementTree.Element, feed_url: str) -> RawEventDraft:
    title = _child_text(entry, "title") or "(untitled)"
    link = _atom_link(entry)
    external_id = _child_text(entry, "id") or link
    published_at = _parse_datetime(_child_text(entry, "published") or _child_text(entry, "updated"))
    content = _child_text(entry, "summary") or _child_text(entry, "content")
    return RawEventDraft(
        source_plugin_id=RssSourcePlugin.id,
        source_type="rss",
        external_id=external_id,
        url=link,
        canonical_url=link,
        title=title,
        content=content,
        published_at=published_at,
        raw_payload={
            "feed_url": feed_url,
            "id": external_id,
            "link": link,
            "title": title,
        },
        metadata={"feed_url": feed_url, "format": "atom"},
    )


def _child_text(parent: ElementTree.Element, local_name: str) -> str | None:
    for child in list(parent):
        if _strip_namespace(child.tag) == local_name and child.text:
            return child.text.strip()
    return None


def _atom_link(entry: ElementTree.Element) -> str | None:
    for child in list(entry):
        if _strip_namespace(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return None


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


plugin = RssSourcePlugin()

