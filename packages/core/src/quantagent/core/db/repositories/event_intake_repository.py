from __future__ import annotations

from sqlalchemy import Select, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantagent.core.db.models.event_intake import EventIntakeRoutedEventORM


class EventIntakeRoutedEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_event_id(self, event_id: str) -> EventIntakeRoutedEventORM | None:
        statement: Select[tuple[EventIntakeRoutedEventORM]] = (
            select(EventIntakeRoutedEventORM)
            .where(EventIntakeRoutedEventORM.event_id == event_id)
            .limit(1)
        )
        return self._session.scalars(statement).first()

    def create_once(self, routed_event: EventIntakeRoutedEventORM) -> tuple[EventIntakeRoutedEventORM, bool]:
        existing = self.get_by_event_id(routed_event.event_id)
        if existing is not None:
            return existing, False
        try:
            # event_id 是 event bus message identity；并发重复消费时只保留第一条审计事实。
            with self._session.begin_nested():
                self._session.add(routed_event)
                self._session.flush()
            return routed_event, True
        except IntegrityError:
            existing = self.get_by_event_id(routed_event.event_id)
            if existing is None:
                raise
            return existing, False

    def list_latest_by_raw_event_ids(
        self,
        raw_event_ids: list[str],
    ) -> dict[str, EventIntakeRoutedEventORM]:
        if not raw_event_ids:
            return {}
        statement: Select[tuple[EventIntakeRoutedEventORM]] = (
            select(EventIntakeRoutedEventORM)
            .where(EventIntakeRoutedEventORM.raw_event_id.in_(raw_event_ids))
            .order_by(
                EventIntakeRoutedEventORM.raw_event_id.asc(),
                desc(EventIntakeRoutedEventORM.created_at),
                desc(EventIntakeRoutedEventORM.id),
            )
        )
        latest: dict[str, EventIntakeRoutedEventORM] = {}
        for item in self._session.scalars(statement).all():
            if item.raw_event_id and item.raw_event_id not in latest:
                latest[item.raw_event_id] = item
        return latest
