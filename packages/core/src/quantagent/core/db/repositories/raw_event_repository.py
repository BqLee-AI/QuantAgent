from __future__ import annotations

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from quantagent.core.db.models.raw_event import RawEventORM

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200


class RawEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, raw_event: RawEventORM) -> RawEventORM:
        self._session.add(raw_event)
        self._session.flush()
        return raw_event

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

    def list_by_binding(self, *, source_binding_id: str, limit: int = DEFAULT_LIST_LIMIT) -> list[RawEventORM]:
        statement: Select[tuple[RawEventORM]] = (
            select(RawEventORM)
            .where(RawEventORM.first_binding_id == source_binding_id)
            .order_by(desc(RawEventORM.first_captured_at), desc(RawEventORM.raw_event_id))
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())

    def list_by_run(self, *, scheduler_run_id: str, limit: int = DEFAULT_LIST_LIMIT) -> list[RawEventORM]:
        statement: Select[tuple[RawEventORM]] = (
            select(RawEventORM)
            .where(RawEventORM.first_run_id == scheduler_run_id)
            .order_by(desc(RawEventORM.first_captured_at), desc(RawEventORM.raw_event_id))
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())


def _bounded_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    return min(limit, MAX_LIST_LIMIT)
