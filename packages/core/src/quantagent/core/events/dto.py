from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RawEventDraft:
    source_plugin_id: str
    source_type: str
    title: str
    external_id: str | None = None
    url: str | None = None
    canonical_url: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    captured_at: datetime = field(default_factory=utc_now)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    dedupe_hint: str | None = None


@dataclass(frozen=True)
class StoredRawEvent:
    id: str
    source_plugin_id: str
    source_type: str
    title: str
    external_id: str | None
    url: str | None
    canonical_url: str | None
    content_hash: str | None
    dedupe_key: str
    captured_at: datetime

