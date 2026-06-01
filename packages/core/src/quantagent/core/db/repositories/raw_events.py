from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantagent.core.db.models.sources import RawEvent
from quantagent.core.events.dedupe import build_dedupe_identity
from quantagent.core.events.dto import RawEventDraft, StoredRawEvent


@dataclass(frozen=True)
class StoreRawEventResult:
    is_duplicate: bool
    event: StoredRawEvent | None = None
    dedupe_reason: str | None = None


class RawEventRepository:
    def __init__(self, session: Session):
        self._session = session

    def store_if_new(self, draft: RawEventDraft) -> StoreRawEventResult:
        identity = build_dedupe_identity(draft)
        existing = self._session.scalar(select(RawEvent).where(RawEvent.dedupe_key == identity.key))
        if existing is not None:
            return StoreRawEventResult(
                is_duplicate=True,
                event=_to_stored_event(existing),
                dedupe_reason=existing.dedupe_reason,
            )

        raw_event = RawEvent(
            source_plugin_id=draft.source_plugin_id,
            source_type=draft.source_type,
            external_id=draft.external_id,
            url=draft.url,
            canonical_url=identity.canonical_url or draft.canonical_url,
            title=draft.title,
            content=draft.content,
            author=draft.author,
            published_at=draft.published_at,
            captured_at=draft.captured_at,
            raw_payload=draft.raw_payload,
            metadata_=draft.metadata,
            content_hash=identity.content_hash,
            dedupe_key=identity.key,
            dedupe_reason=identity.reason,
        )
        try:
            with self._session.begin_nested():
                self._session.add(raw_event)
                self._session.flush()
        except IntegrityError:
            existing_after_conflict = self._session.scalar(
                select(RawEvent).where(RawEvent.dedupe_key == identity.key)
            )
            if existing_after_conflict is None:
                raise
            return StoreRawEventResult(
                is_duplicate=True,
                event=_to_stored_event(existing_after_conflict),
                dedupe_reason=identity.reason,
            )

        return StoreRawEventResult(
            is_duplicate=False,
            event=_to_stored_event(raw_event),
            dedupe_reason=identity.reason,
        )


def _to_stored_event(raw_event: RawEvent) -> StoredRawEvent:
    return StoredRawEvent(
        id=raw_event.id,
        source_plugin_id=raw_event.source_plugin_id,
        source_type=raw_event.source_type,
        title=raw_event.title,
        external_id=raw_event.external_id,
        url=raw_event.url,
        canonical_url=raw_event.canonical_url,
        content_hash=raw_event.content_hash,
        dedupe_key=raw_event.dedupe_key,
        captured_at=raw_event.captured_at,
    )
