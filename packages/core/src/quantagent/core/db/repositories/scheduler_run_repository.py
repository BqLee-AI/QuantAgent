from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, and_, desc, or_, select
from sqlalchemy.orm import Session

from quantagent.core.db.models.scheduler_run import SchedulerRunORM

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200


class SchedulerRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, run: SchedulerRunORM) -> SchedulerRunORM:
        self._session.add(run)
        self._session.flush()
        return run

    def get(self, run_id: str) -> SchedulerRunORM | None:
        return self._session.get(SchedulerRunORM, run_id)

    def save(self, run: SchedulerRunORM) -> SchedulerRunORM:
        self._session.add(run)
        self._session.flush()
        return run

    def list_runs(
        self,
        *,
        status: str | None = None,
        source_plugin_id: str | None = None,
        request_id: str | None = None,
        trigger_mode: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
        offset: int = 0,
    ) -> list[SchedulerRunORM]:
        conditions = []
        if status is not None:
            conditions.append(SchedulerRunORM.status == status)
        if source_plugin_id is not None:
            conditions.append(SchedulerRunORM.source_plugin_id == source_plugin_id)
        if request_id is not None:
            conditions.append(SchedulerRunORM.request_id == request_id)
        if trigger_mode is not None:
            conditions.append(SchedulerRunORM.trigger_mode == trigger_mode)
        if started_from is not None:
            conditions.append(SchedulerRunORM.started_at >= started_from)
        if started_to is not None:
            conditions.append(SchedulerRunORM.started_at <= started_to)

        statement: Select[tuple[SchedulerRunORM]] = select(SchedulerRunORM)
        if conditions:
            statement = statement.where(and_(*conditions))

        statement = (
            statement.order_by(desc(SchedulerRunORM.created_at), desc(SchedulerRunORM.run_id))
            .offset(_bounded_offset(offset))
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())

    def list_by_binding(self, *, binding_id: str, limit: int = DEFAULT_LIST_LIMIT) -> list[SchedulerRunORM]:
        statement: Select[tuple[SchedulerRunORM]] = (
            select(SchedulerRunORM)
            .where(SchedulerRunORM.binding_id == binding_id)
            .order_by(desc(SchedulerRunORM.created_at), desc(SchedulerRunORM.run_id))
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())

    def list_by_request(self, *, request_id: str, limit: int = DEFAULT_LIST_LIMIT) -> list[SchedulerRunORM]:
        statement = (
            select(SchedulerRunORM)
            .where(SchedulerRunORM.request_id == request_id)
            .order_by(SchedulerRunORM.created_at.asc(), SchedulerRunORM.run_id.asc())
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())

    def list_for_api(
        self,
        *,
        binding_id: str | None = None,
        status: str | None = None,
        trigger_mode: str | None = None,
        started_after: datetime | None = None,
        started_before: datetime | None = None,
        cursor: dict[str, str] | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> tuple[list[SchedulerRunORM], dict[str, str] | None]:
        bounded_limit = _bounded_limit(limit)
        statement: Select[tuple[SchedulerRunORM]] = select(SchedulerRunORM)
        if binding_id is not None:
            statement = statement.where(SchedulerRunORM.binding_id == binding_id)
        if status is not None:
            statement = statement.where(SchedulerRunORM.status == status)
        if trigger_mode is not None:
            statement = statement.where(SchedulerRunORM.trigger_mode == trigger_mode)
        if started_after is not None:
            statement = statement.where(SchedulerRunORM.started_at.is_not(None)).where(SchedulerRunORM.started_at >= started_after)
        if started_before is not None:
            statement = statement.where(SchedulerRunORM.started_at.is_not(None)).where(SchedulerRunORM.started_at <= started_before)
        if cursor is not None:
            cursor_created_at, cursor_run_id = _parse_scheduler_run_cursor(cursor)
            statement = statement.where(
                or_(
                    SchedulerRunORM.created_at < cursor_created_at,
                    and_(
                        SchedulerRunORM.created_at == cursor_created_at,
                        SchedulerRunORM.run_id < cursor_run_id,
                    ),
                )
            )
        statement = statement.order_by(desc(SchedulerRunORM.created_at), desc(SchedulerRunORM.run_id)).limit(
            bounded_limit + 1
        )
        items = list(self._session.scalars(statement).all())
        next_cursor = None
        if len(items) > bounded_limit:
            last = items[bounded_limit - 1]
            next_cursor = {
                "created_at": last.created_at.astimezone(UTC).isoformat(),
                "run_id": last.run_id,
            }
            items = items[:bounded_limit]
        return items, next_cursor


def _bounded_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    return min(limit, MAX_LIST_LIMIT)


def _parse_scheduler_run_cursor(cursor: dict[str, str]) -> tuple[datetime, str]:
    if not isinstance(cursor, dict):
        raise ValueError("scheduler run cursor must be an object")
    if "created_at" not in cursor:
        raise ValueError("scheduler run cursor missing created_at")
    if "run_id" not in cursor:
        raise ValueError("scheduler run cursor missing run_id")
    created_at_raw = cursor["created_at"]
    run_id = cursor["run_id"]
    try:
        created_at = datetime.fromisoformat(created_at_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("scheduler run cursor has invalid created_at") from exc
    if not run_id:
        raise ValueError("scheduler run cursor has invalid run_id")
    return created_at, run_id


def _bounded_offset(offset: int) -> int:
    if offset < 0:
        raise ValueError("offset must not be negative.")
    return offset
