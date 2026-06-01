from __future__ import annotations

from sqlalchemy import Select, desc, select
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
