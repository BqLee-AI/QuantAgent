from __future__ import annotations

from sqlalchemy import Select, desc, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantagent.core.db.models.raw_event import RawEventORM
from quantagent.core.db.models.raw_event_capture import RawEventCaptureORM

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200


class RawEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, raw_event: RawEventORM) -> RawEventORM:
        self._session.add(raw_event)
        self._session.flush()
        return raw_event

    def get_or_create_by_canonical_identity(self, raw_event: RawEventORM) -> tuple[RawEventORM, bool]:
        existing = self.get_by_canonical_identity(
            source_plugin_id=raw_event.source_plugin_id,
            canonical_dedupe_key=raw_event.canonical_dedupe_key,
        )
        if existing is not None:
            return existing, False
        try:
            # canonical identity 由数据库唯一键兜底；并发 loser 回读 winner 行，避免 IntegrityError 冒泡。
            with self._session.begin_nested():
                self._session.add(raw_event)
                self._session.flush()
            return raw_event, True
        except IntegrityError:
            existing = self.get_by_canonical_identity(
                source_plugin_id=raw_event.source_plugin_id,
                canonical_dedupe_key=raw_event.canonical_dedupe_key,
            )
            if existing is None:
                raise
            return existing, False

    def get(self, raw_event_id: str) -> RawEventORM | None:
        return self._session.get(RawEventORM, raw_event_id)

    def get_by_canonical_identity(self, *, source_plugin_id: str, canonical_dedupe_key: str) -> RawEventORM | None:
        statement: Select[tuple[RawEventORM]] = (
            select(RawEventORM)
            .where(
                RawEventORM.source_plugin_id == source_plugin_id,
                RawEventORM.canonical_dedupe_key == canonical_dedupe_key,
            )
            .limit(1)
        )
        return self._session.scalars(statement).first()

    def save(self, raw_event: RawEventORM) -> RawEventORM:
        self._session.add(raw_event)
        self._session.flush()
        return raw_event

    def increment_duplicate_capture_count(self, raw_event: RawEventORM) -> RawEventORM:
        self._session.execute(
            update(RawEventORM)
            .where(RawEventORM.raw_event_id == raw_event.raw_event_id)
            .values(duplicate_capture_count=RawEventORM.duplicate_capture_count + 1)
        )
        self._session.flush()
        self._session.refresh(raw_event)
        return raw_event

    def list_by_binding(self, *, source_binding_id: str, limit: int = DEFAULT_LIST_LIMIT) -> list[RawEventORM]:
        statement: Select[tuple[RawEventORM]] = (
            select(RawEventORM)
            .join(RawEventCaptureORM, RawEventCaptureORM.raw_event_id == RawEventORM.raw_event_id)
            .where(RawEventCaptureORM.source_binding_id == source_binding_id)
            .order_by(desc(RawEventCaptureORM.captured_at), desc(RawEventORM.raw_event_id))
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).unique().all())

    def list_by_run(self, *, scheduler_run_id: str, limit: int = DEFAULT_LIST_LIMIT) -> list[RawEventORM]:
        statement: Select[tuple[RawEventORM]] = (
            select(RawEventORM)
            .join(RawEventCaptureORM, RawEventCaptureORM.raw_event_id == RawEventORM.raw_event_id)
            .where(RawEventCaptureORM.scheduler_run_id == scheduler_run_id)
            .order_by(desc(RawEventCaptureORM.captured_at), desc(RawEventORM.raw_event_id))
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).unique().all())


def _bounded_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    return min(limit, MAX_LIST_LIMIT)
