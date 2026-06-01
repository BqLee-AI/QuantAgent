from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RawEventDedupeStrategy(StrEnum):
    EXTERNAL_ID = "external_id"
    CANONICAL_URL_CONTENT = "canonical_url_content"
    SOURCE_HINT = "source_hint"


@dataclass(frozen=True)
class RawEventRecord:
    raw_event_id: str
    source_plugin_id: str
    source_binding_id: str | None
    scheduler_run_id: str | None
    external_id: str | None
    canonical_url: str | None
    title: str | None
    content: str | None
    author: str | None
    published_at: datetime | None
    captured_at: datetime
    last_seen_at: datetime
    raw_payload: dict[str, object]
    metadata: dict[str, object]
    dedupe_key: str
    dedupe_strategy: RawEventDedupeStrategy
    content_hash: str | None
    duplicate_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RawEventPersistResult:
    raw_event: RawEventRecord
    created: bool


@dataclass(frozen=True)
class PersistSourceFetchResultSummary:
    items: tuple[RawEventPersistResult, ...]

    @property
    def created_count(self) -> int:
        return sum(1 for item in self.items if item.created)

    @property
    def duplicate_count(self) -> int:
        return len(self.items) - self.created_count
