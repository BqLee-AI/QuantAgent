from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, and_, desc, select
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


def _bounded_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    return min(limit, MAX_LIST_LIMIT)


def _bounded_offset(offset: int) -> int:
    if offset < 0:
        raise ValueError("offset must not be negative.")
    return offset
