from __future__ import annotations

from sqlalchemy import Select, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantagent.core.db.models.raw_event_capture import RawEventCaptureORM
from quantagent.core.db.repositories.raw_event_repository import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT, _bounded_limit


class RawEventCaptureRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, capture: RawEventCaptureORM) -> RawEventCaptureORM:
        self._session.add(capture)
        self._session.flush()
        return capture

    def get_or_create_by_capture_dedupe_key(self, capture: RawEventCaptureORM) -> tuple[RawEventCaptureORM, bool]:
        existing = self.get_by_capture_dedupe_key(capture.capture_dedupe_key)
        if existing is not None:
            return existing, False
        try:
            # capture ledger 以唯一键保证幂等；冲突后回读已存在 ownership 行。
            with self._session.begin_nested():
                self._session.add(capture)
                self._session.flush()
            return capture, True
        except IntegrityError:
            existing = self.get_by_capture_dedupe_key(capture.capture_dedupe_key)
            if existing is None:
                raise
            return existing, False

    def save(self, capture: RawEventCaptureORM) -> RawEventCaptureORM:
        self._session.add(capture)
        self._session.flush()
        return capture

    def get(self, capture_id: str) -> RawEventCaptureORM | None:
        return self._session.get(RawEventCaptureORM, capture_id)

    def get_by_capture_dedupe_key(self, capture_dedupe_key: str) -> RawEventCaptureORM | None:
        statement: Select[tuple[RawEventCaptureORM]] = (
            select(RawEventCaptureORM).where(RawEventCaptureORM.capture_dedupe_key == capture_dedupe_key).limit(1)
        )
        return self._session.scalars(statement).first()

    def get_by_run_and_raw_event(self, *, scheduler_run_id: str, raw_event_id: str) -> RawEventCaptureORM | None:
        statement: Select[tuple[RawEventCaptureORM]] = (
            select(RawEventCaptureORM)
            .where(
                RawEventCaptureORM.scheduler_run_id == scheduler_run_id,
                RawEventCaptureORM.raw_event_id == raw_event_id,
            )
            .limit(1)
        )
        return self._session.scalars(statement).first()

    def list_by_binding(
        self,
        *,
        source_binding_id: str,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> list[RawEventCaptureORM]:
        statement: Select[tuple[RawEventCaptureORM]] = (
            select(RawEventCaptureORM)
            .where(RawEventCaptureORM.source_binding_id == source_binding_id)
            .order_by(desc(RawEventCaptureORM.captured_at), desc(RawEventCaptureORM.capture_id))
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())

    def list_by_run(
        self,
        *,
        scheduler_run_id: str,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> list[RawEventCaptureORM]:
        statement: Select[tuple[RawEventCaptureORM]] = (
            select(RawEventCaptureORM)
            .where(RawEventCaptureORM.scheduler_run_id == scheduler_run_id)
            .order_by(desc(RawEventCaptureORM.captured_at), desc(RawEventCaptureORM.capture_id))
            .limit(_bounded_limit(limit))
        )
        return list(self._session.scalars(statement).all())
