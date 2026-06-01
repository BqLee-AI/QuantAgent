from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from quantagent.core.db.models.source_binding import SourceBindingORM


class SourceBindingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, binding: SourceBindingORM) -> SourceBindingORM:
        self._session.add(binding)
        self._session.flush()
        return binding

    def get(self, binding_id: str) -> SourceBindingORM | None:
        return self._session.get(SourceBindingORM, binding_id)

    def list_due_bindings(self, *, now: datetime, limit: int) -> list[SourceBindingORM]:
        statement: Select[tuple[SourceBindingORM]] = (
            select(SourceBindingORM)
            .where(SourceBindingORM.status == "active")
            .where(SourceBindingORM.next_run_at.is_not(None))
            .where(SourceBindingORM.next_run_at <= now)
            .order_by(SourceBindingORM.next_run_at.asc(), SourceBindingORM.binding_id.asc())
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())

    def list_by_owner(self, *, owner_type: str, owner_id: str) -> list[SourceBindingORM]:
        statement = (
            select(SourceBindingORM)
            .where(SourceBindingORM.owner_type == owner_type)
            .where(SourceBindingORM.owner_id == owner_id)
            .order_by(SourceBindingORM.updated_at.desc(), SourceBindingORM.binding_id.asc())
        )
        return list(self._session.scalars(statement).all())

    def list_by_plugin(self, *, source_plugin_id: str) -> list[SourceBindingORM]:
        statement = (
            select(SourceBindingORM)
            .where(SourceBindingORM.source_plugin_id == source_plugin_id)
            .order_by(SourceBindingORM.updated_at.desc(), SourceBindingORM.binding_id.asc())
        )
        return list(self._session.scalars(statement).all())

    def save(self, binding: SourceBindingORM) -> SourceBindingORM:
        self._session.add(binding)
        self._session.flush()
        return binding
