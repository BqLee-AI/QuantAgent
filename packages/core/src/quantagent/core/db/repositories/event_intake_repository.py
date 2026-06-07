from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, String, and_, cast, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantagent.core.db.models.event_intake import EventIntakeRoutedEventORM
from quantagent.core.db.models.raw_event import RawEventORM


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

    def get_latest_by_raw_event_id(self, raw_event_id: str) -> EventIntakeRoutedEventORM | None:
        statement: Select[tuple[EventIntakeRoutedEventORM]] = (
            select(EventIntakeRoutedEventORM)
            .where(EventIntakeRoutedEventORM.raw_event_id == raw_event_id)
            .order_by(desc(EventIntakeRoutedEventORM.created_at), desc(EventIntakeRoutedEventORM.id))
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

    def list_for_events_read_model(
        self,
        *,
        decisions: frozenset[str],
        binding_id: str | None = None,
        source_plugin_id: str | None = None,
        industry_id: str | None = None,
        keyword: str | None = None,
        target_topic: str | None = None,
        priority: str | None = None,
        relationship: str | None = None,
        status: str | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
        sort: str = "routed_at_desc",
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        cursor_sort_at: datetime | None = None,
        cursor_id: int | None = None,
        limit: int = 20,
    ) -> list[EventIntakeRoutedEventORM]:
        safe_limit = min(max(limit, 1), 100)
        statement: Select[tuple[EventIntakeRoutedEventORM]] = select(EventIntakeRoutedEventORM).where(
            EventIntakeRoutedEventORM.raw_event_id.is_not(None)
        )
        sort_expr = EventIntakeRoutedEventORM.created_at
        if sort == "published_at_desc":
            statement = statement.outerjoin(RawEventORM, RawEventORM.raw_event_id == EventIntakeRoutedEventORM.raw_event_id)
            sort_expr = func.coalesce(RawEventORM.published_at, EventIntakeRoutedEventORM.created_at)
        if decisions:
            statement = statement.where(EventIntakeRoutedEventORM.decision.in_(sorted(decisions)))
        if binding_id:
            statement = statement.where(EventIntakeRoutedEventORM.binding_id == binding_id)
        if source_plugin_id:
            statement = statement.where(
                or_(
                    EventIntakeRoutedEventORM.raw_event_id.in_(
                        select(RawEventORM.raw_event_id).where(RawEventORM.source_plugin_id == source_plugin_id)
                    ),
                    _json_string(EventIntakeRoutedEventORM.source_snapshot, "plugin_id") == source_plugin_id,
                )
            )
        if industry_id:
            # 中文注释：行业包筛选优先使用 routed read model 的 owner_id，避免把某个行业的 topic 硬编码成全局筛选项。
            statement = statement.where(EventIntakeRoutedEventORM.owner_id == industry_id)
        if keyword:
            pattern = f"%{keyword.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(EventIntakeRoutedEventORM.summary).like(pattern),
                    func.lower(EventIntakeRoutedEventORM.raw_event_id).like(pattern),
                    func.lower(EventIntakeRoutedEventORM.request_id).like(pattern),
                    func.lower(EventIntakeRoutedEventORM.correlation_id).like(pattern),
                    EventIntakeRoutedEventORM.raw_event_id.in_(
                        select(RawEventORM.raw_event_id).where(
                            or_(
                                func.lower(RawEventORM.title).like(pattern),
                                func.lower(RawEventORM.canonical_url).like(pattern),
                                func.lower(RawEventORM.source_plugin_id).like(pattern),
                            )
                        )
                    ),
                )
            )
        if status:
            statement = statement.where(EventIntakeRoutedEventORM.status == status)
        if target_topic:
            # JSON array membership across SQLite/Postgres is not uniform here；使用 read model JSON 文本预筛选，
            # 避免分页后再过滤导致第一页遗漏后续匹配项。
            topic_pattern = f'%"{target_topic}"%'
            statement = statement.where(cast(EventIntakeRoutedEventORM.key_fields, String).like(topic_pattern))
        if priority:
            statement = statement.where(
                or_(
                    _json_string(EventIntakeRoutedEventORM.key_fields, "priority") == priority,
                    _json_string(EventIntakeRoutedEventORM.output_json["routing"], "priority") == priority,
                )
            )
        if relationship:
            relationship_pattern = f"% / {relationship} / %"
            statement = statement.where(
                or_(
                    _json_string(EventIntakeRoutedEventORM.key_fields, "relationship") == relationship,
                    _json_string(EventIntakeRoutedEventORM.key_fields, "relevance").like(relationship_pattern),
                    cast(EventIntakeRoutedEventORM.output_json, String).like(f'%"relationship": "{relationship}"%'),
                )
            )
        if trace_id:
            statement = statement.where(EventIntakeRoutedEventORM.correlation_id == trace_id)
        if request_id:
            statement = statement.where(EventIntakeRoutedEventORM.request_id == request_id)
        if time_from:
            statement = statement.where(EventIntakeRoutedEventORM.created_at >= time_from)
        if time_to:
            statement = statement.where(EventIntakeRoutedEventORM.created_at <= time_to)
        if cursor_sort_at is not None and cursor_id is not None:
            statement = statement.where(
                or_(
                    sort_expr < cursor_sort_at,
                    and_(
                        sort_expr == cursor_sort_at,
                        EventIntakeRoutedEventORM.id < cursor_id,
                    ),
                )
            )
        statement = statement.order_by(desc(sort_expr), desc(EventIntakeRoutedEventORM.id)).limit(safe_limit + 1)
        return list(self._session.scalars(statement).all())


def _json_string(column: object, key: str) -> object:
    return column[key].as_string()  # type: ignore[index, no-any-return]
