from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from quantagent.core.db.models.source_binding import SourceBindingORM

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200


class SourceBindingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, binding: SourceBindingORM) -> SourceBindingORM:
        self._session.add(binding)
        self._session.flush()
        return binding

    def get(self, binding_id: str) -> SourceBindingORM | None:
        return self._session.get(SourceBindingORM, binding_id)

    def list_due_bindings(self, *, now: datetime, limit: int = DEFAULT_LIST_LIMIT) -> list[SourceBindingORM]:
        statement: Select[tuple[SourceBindingORM]] = (
            select(SourceBindingORM)
            .where(SourceBindingORM.status == "active")
            .where(SourceBindingORM.next_run_at.is_not(None))
            .where(SourceBindingORM.next_run_at <= now)
            .order_by(SourceBindingORM.next_run_at.asc(), SourceBindingORM.binding_id.asc())
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())

    def list_by_owner(
        self,
        *,
        owner_type: str,
        owner_id: str,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> list[SourceBindingORM]:
        statement = (
            select(SourceBindingORM)
            .where(SourceBindingORM.owner_type == owner_type)
            .where(SourceBindingORM.owner_id == owner_id)
            .order_by(SourceBindingORM.updated_at.desc(), SourceBindingORM.binding_id.asc())
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())

    def list_by_plugin(
        self,
        *,
        source_plugin_id: str,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> list[SourceBindingORM]:
        statement = (
            select(SourceBindingORM)
            .where(SourceBindingORM.source_plugin_id == source_plugin_id)
            .order_by(SourceBindingORM.updated_at.desc(), SourceBindingORM.binding_id.asc())
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())

    def save(self, binding: SourceBindingORM) -> SourceBindingORM:
        self._session.add(binding)
        self._session.flush()
        return binding

    def list_for_api(
        self,
        *,
        owner_type: str | None = None,
        owner_id: str | None = None,
        source_plugin_id: str | None = None,
        status: str | None = None,
        cursor: dict[str, str] | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> tuple[list[SourceBindingORM], dict[str, str] | None]:
        bounded_limit = _bounded_limit(limit)
        statement: Select[tuple[SourceBindingORM]] = select(SourceBindingORM)
        if owner_type is not None:
            statement = statement.where(SourceBindingORM.owner_type == owner_type)
        if owner_id is not None:
            statement = statement.where(SourceBindingORM.owner_id == owner_id)
        if source_plugin_id is not None:
            statement = statement.where(SourceBindingORM.source_plugin_id == source_plugin_id)
        if status is not None:
            statement = statement.where(SourceBindingORM.status == status)
        if cursor is not None:
            cursor_updated_at, cursor_binding_id = _parse_source_binding_cursor(cursor)
            statement = statement.where(
                or_(
                    SourceBindingORM.updated_at < cursor_updated_at,
                    and_(
                        SourceBindingORM.updated_at == cursor_updated_at,
                        SourceBindingORM.binding_id < cursor_binding_id,
                    ),
                )
            )
        statement = statement.order_by(SourceBindingORM.updated_at.desc(), SourceBindingORM.binding_id.desc()).limit(
            bounded_limit + 1
        )
        items = list(self._session.scalars(statement).all())
        next_cursor = None
        if len(items) > bounded_limit:
            last = items[bounded_limit - 1]
            next_cursor = {
                "updated_at": last.updated_at.astimezone(UTC).isoformat(),
                "binding_id": last.binding_id,
            }
            items = items[:bounded_limit]
        return items, next_cursor


def _bounded_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    return min(limit, MAX_LIST_LIMIT)


def _parse_source_binding_cursor(cursor: dict[str, str]) -> tuple[datetime, str]:
    if not isinstance(cursor, dict):
        raise ValueError("source binding cursor must be an object")
    if "updated_at" not in cursor:
        raise ValueError("source binding cursor missing updated_at")
    if "binding_id" not in cursor:
        raise ValueError("source binding cursor missing binding_id")
    updated_at_raw = cursor["updated_at"]
    binding_id = cursor["binding_id"]
    try:
        updated_at = datetime.fromisoformat(updated_at_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("source binding cursor has invalid updated_at") from exc
    if not binding_id:
        raise ValueError("source binding cursor has invalid binding_id")
    return updated_at, binding_id
