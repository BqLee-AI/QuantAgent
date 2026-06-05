from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from uuid import uuid4

from sqlalchemy import Select, Text, and_, case, cast, desc, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantagent.core.db.models.event import EventORM, EventStateTransitionORM
from quantagent.core.event_read_model.models import (
    EventCurrentStatus,
    EventDetailView,
    EventListPage,
    EventListQuery,
    EventMaterializationInput,
    EventMaterializationResult,
    EventRecord,
    EventSortMode,
    EventStateSummaryView,
    EventStateTransitionRecord,
    EventSummaryBuckets,
    decode_event_cursor,
    derive_event_id,
    encode_event_cursor,
)
from quantagent.core.event_read_model.repository import EventReadModelRepository

_NEW_STATUSES = frozenset(
    {
        EventCurrentStatus.CAPTURED.value,
        EventCurrentStatus.ROUTED.value,
        EventCurrentStatus.ANALYZING.value,
    }
)
_FAILED_OR_REVIEW_STATUSES = frozenset(
    {
        EventCurrentStatus.FAILED.value,
        EventCurrentStatus.REVIEW_REQUIRED.value,
    }
)
_STATUS_ORDER = {
    EventCurrentStatus.CAPTURED.value: 10,
    EventCurrentStatus.ROUTED.value: 20,
    EventCurrentStatus.ANALYZING.value: 30,
    EventCurrentStatus.SCORED.value: 40,
    EventCurrentStatus.DECISION_READY.value: 50,
    EventCurrentStatus.PENDING_APPROVAL.value: 60,
    EventCurrentStatus.APPROVED.value: 70,
    EventCurrentStatus.REJECTED.value: 70,
    EventCurrentStatus.FAILED.value: 70,
    EventCurrentStatus.REVIEW_REQUIRED.value: 70,
    EventCurrentStatus.DISCARDED.value: 80,
}


@dataclass
class SqlAlchemyEventReadModelRepository(EventReadModelRepository):
    session: Session

    def materialize(self, input_data: EventMaterializationInput) -> EventMaterializationResult:
        event_id = derive_event_id(identity_kind=input_data.identity_kind, identity_value=input_data.identity_value)
        existing = self._get_existing_for_input(input_data, event_id=event_id)
        if existing is None:
            return self._create_event(input_data, event_id=event_id)
        return self._update_event(existing, input_data)

    def get_event(self, event_id: str) -> EventRecord | None:
        row = self.session.get(EventORM, event_id)
        return _to_event_record(row) if row is not None else None

    def get_event_detail(self, event_id: str) -> EventDetailView | None:
        row = self.session.get(EventORM, event_id)
        if row is None:
            return None
        transitions = self.list_state_transitions(event_id)
        return EventDetailView(
            event=_to_event_record(row),
            state_summary=EventStateSummaryView(
                current_status=row.current_status,
                analysis_status=row.analysis_status,
                version=row.version,
                transitions=transitions,
            ),
        )

    def list_events(self, query: EventListQuery) -> EventListPage:
        cursor = decode_event_cursor(query.cursor)
        statement = self._apply_filters(select(EventORM), query)
        statement = self._apply_sort(statement, query.sort, cursor=cursor)
        limit = min(max(query.limit, 1), 100)
        rows = list(self.session.scalars(statement.limit(limit + 1)).all())
        next_cursor = None
        if len(rows) > limit:
            next_cursor = _build_cursor(rows[limit - 1], sort=query.sort)
            rows = rows[:limit]
        return EventListPage(
            items=tuple(_to_event_record(row) for row in rows),
            next_cursor=next_cursor,
            buckets=self.get_summary_buckets(query),
            generated_at=datetime.now(UTC),
        )

    def list_featured_events(self, query: EventListQuery, *, limit: int) -> tuple[EventRecord, ...]:
        statement = self._apply_filters(select(EventORM), query)
        statement: Select[tuple[EventORM]] = (
            statement.where(EventORM.is_featured.is_(True))
            .order_by(
                desc(func.coalesce(EventORM.priority_score, -1.0)),
                desc(EventORM.captured_at),
                desc(EventORM.event_id),
            )
            .limit(max(limit, 1))
        )
        return tuple(_to_event_record(row) for row in self.session.scalars(statement).all())

    def get_summary_buckets(self, query: EventListQuery) -> EventSummaryBuckets:
        statement = self._apply_filters(select(EventORM), query)
        subquery = statement.subquery()
        aggregate = select(
            func.count().label("total"),
            func.sum(case((subquery.c.current_status.in_(_NEW_STATUSES), 1), else_=0)).label("new_count"),
            func.sum(case((subquery.c.is_featured.is_(True), 1), else_=0)).label("featured_count"),
            func.sum(case((subquery.c.analysis_status == "analyzing", 1), else_=0)).label("analyzing_count"),
            func.sum(
                case(
                    (
                        or_(
                            subquery.c.current_status.in_(_FAILED_OR_REVIEW_STATUSES),
                            subquery.c.analysis_status.in_(("failed", "review_required")),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("failed_or_review_count"),
            func.sum(
                case(
                    (
                        or_(
                            subquery.c.current_status == EventCurrentStatus.PENDING_APPROVAL.value,
                            subquery.c.analysis_status == "pending_approval",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("pending_approval_count"),
        )
        row = self.session.execute(aggregate).one()
        return EventSummaryBuckets(
            new_count=int(row.new_count or 0),
            featured_count=int(row.featured_count or 0),
            analyzing_count=int(row.analyzing_count or 0),
            failed_or_review_count=int(row.failed_or_review_count or 0),
            pending_approval_count=int(row.pending_approval_count or 0),
        )

    def list_state_transitions(self, event_id: str) -> tuple[EventStateTransitionRecord, ...]:
        statement: Select[tuple[EventStateTransitionORM]] = (
            select(EventStateTransitionORM)
            .where(EventStateTransitionORM.event_id == event_id)
            .order_by(EventStateTransitionORM.created_at.asc(), EventStateTransitionORM.transition_id.asc())
        )
        return tuple(_to_transition_record(row) for row in self.session.scalars(statement).all())

    def _create_event(self, input_data: EventMaterializationInput, *, event_id: str) -> EventMaterializationResult:
        now = datetime.now(UTC)
        row = EventORM(
            event_id=event_id,
            schema_version=input_data.schema_version,
            title=input_data.title,
            summary=input_data.summary,
            source_name=input_data.source_name,
            source_type=input_data.source_type.value if input_data.source_type else None,
            source_url=input_data.source_url,
            source_authority=input_data.source_authority,
            published_at=input_data.published_at,
            captured_at=input_data.captured_at,
            current_status=input_data.current_status.value,
            analysis_status=input_data.analysis_status.value,
            credibility=input_data.credibility.value if input_data.credibility else None,
            priority_score=input_data.priority_score,
            recommendation_score=input_data.recommendation_score,
            confidence=input_data.confidence,
            risk_level=input_data.risk_level.value if input_data.risk_level else None,
            risk_direction=input_data.risk_direction.value if input_data.risk_direction else None,
            industries=list(input_data.industries),
            entities=list(input_data.entities),
            tags=list(input_data.tags),
            featured_reason=input_data.featured_reason,
            is_featured=input_data.is_featured,
            raw_event_id=input_data.raw_event_id,
            routed_event_id=input_data.routed_event_id,
            trace_id=input_data.trace_id,
            correlation_id=input_data.correlation_id,
            identity_kind=input_data.identity_kind.value,
            identity_value=input_data.identity_value,
            version=1,
            latest_agent_run_id=input_data.latest_agent_run_id,
            latest_tool_invocation_id=input_data.latest_tool_invocation_id,
            approval_id=input_data.approval_id,
            degradation_notices=list(input_data.degradation_notices),
            evidence_summary=dict(input_data.evidence_summary),
            industry_impact_summary=dict(input_data.industry_impact_summary),
            best_action_summary=dict(input_data.best_action_summary),
            audit_refs=list(input_data.audit_refs),
            created_at=now,
            updated_at=now,
        )
        transition = self._build_transition(
            event_id=event_id,
            from_status=None,
            input_data=input_data,
            created_at=now,
        )
        try:
            with self.session.begin_nested():
                self.session.add(row)
                self.session.add(transition)
                self.session.flush()
        except IntegrityError:
            existing = self._get_existing_for_input(input_data, event_id=event_id)
            if existing is None:
                raise
            return self._update_event(existing, input_data)
        return EventMaterializationResult(
            event_id=event_id,
            created=True,
            previous_status=None,
            current_status=input_data.current_status.value,
            transition_id=transition.transition_id,
            degradation_notices=input_data.degradation_notices,
        )

    def _update_event(self, row: EventORM, input_data: EventMaterializationInput) -> EventMaterializationResult:
        latest_transition = self._latest_transition(row.event_id)
        if _is_duplicate_transition(latest_transition, input_data):
            self._merge_mutable_fields(row, input_data, update_status=False)
            self.session.flush()
            return EventMaterializationResult(
                event_id=row.event_id,
                created=False,
                previous_status=row.current_status,
                current_status=row.current_status,
                transition_id=latest_transition.transition_id if latest_transition is not None else None,
                degradation_notices=input_data.degradation_notices,
            )

        if _is_backward_transition(row.current_status, input_data.current_status.value) and not input_data.reason_code:
            raise ValueError("backward status transition requires reason_code")

        previous_status = row.current_status
        updated_at = datetime.now(UTC)
        current_version = row.version

        # SQLite 测试方言不支持稳定的 FOR UPDATE；这里用 version 条件更新保证并发写入不会静默覆盖状态。
        values = self._materialized_values(input_data, version=current_version + 1, updated_at=updated_at)
        result = self.session.execute(
            update(EventORM)
            .where(EventORM.event_id == row.event_id, EventORM.version == current_version)
            .values(**values)
        )
        if result.rowcount != 1:
            self.session.expire_all()
            fresh = self.session.get(EventORM, row.event_id)
            if fresh is None:
                raise ValueError(f"event disappeared during update: {row.event_id}")
            return self._update_event(fresh, input_data)

        transition_id = None
        if previous_status != input_data.current_status.value:
            transition = self._build_transition(
                event_id=row.event_id,
                from_status=previous_status,
                input_data=input_data,
                created_at=updated_at,
            )
            self.session.add(transition)
            transition_id = transition.transition_id

        self.session.flush()
        refreshed = self.session.get(EventORM, row.event_id)
        if refreshed is None:
            raise ValueError(f"event disappeared after update: {row.event_id}")
        return EventMaterializationResult(
            event_id=row.event_id,
            created=False,
            previous_status=previous_status,
            current_status=refreshed.current_status,
            transition_id=transition_id,
            degradation_notices=input_data.degradation_notices,
        )

    def _materialized_values(
        self,
        input_data: EventMaterializationInput,
        *,
        version: int,
        updated_at: datetime,
    ) -> dict[str, object]:
        return {
            "schema_version": input_data.schema_version,
            "title": input_data.title,
            "summary": input_data.summary,
            "source_name": input_data.source_name,
            "source_type": input_data.source_type.value if input_data.source_type else None,
            "source_url": input_data.source_url,
            "source_authority": input_data.source_authority,
            "published_at": input_data.published_at,
            "captured_at": input_data.captured_at,
            "current_status": input_data.current_status.value,
            "analysis_status": input_data.analysis_status.value,
            "credibility": input_data.credibility.value if input_data.credibility else None,
            "priority_score": input_data.priority_score,
            "recommendation_score": input_data.recommendation_score,
            "confidence": input_data.confidence,
            "risk_level": input_data.risk_level.value if input_data.risk_level else None,
            "risk_direction": input_data.risk_direction.value if input_data.risk_direction else None,
            "industries": list(input_data.industries),
            "entities": list(input_data.entities),
            "tags": list(input_data.tags),
            "featured_reason": input_data.featured_reason,
            "is_featured": input_data.is_featured,
            "raw_event_id": input_data.raw_event_id,
            "routed_event_id": input_data.routed_event_id,
            "trace_id": input_data.trace_id,
            "correlation_id": input_data.correlation_id,
            "latest_agent_run_id": input_data.latest_agent_run_id,
            "latest_tool_invocation_id": input_data.latest_tool_invocation_id,
            "approval_id": input_data.approval_id,
            "degradation_notices": list(input_data.degradation_notices),
            "evidence_summary": dict(input_data.evidence_summary),
            "industry_impact_summary": dict(input_data.industry_impact_summary),
            "best_action_summary": dict(input_data.best_action_summary),
            "audit_refs": list(input_data.audit_refs),
            "version": version,
            "updated_at": updated_at,
        }

    def _merge_mutable_fields(self, row: EventORM, input_data: EventMaterializationInput, *, update_status: bool) -> None:
        row.schema_version = input_data.schema_version
        row.title = input_data.title
        row.summary = input_data.summary
        row.source_name = input_data.source_name
        row.source_type = input_data.source_type.value if input_data.source_type else None
        row.source_url = input_data.source_url
        row.source_authority = input_data.source_authority
        row.published_at = input_data.published_at
        row.captured_at = input_data.captured_at
        if update_status:
            row.current_status = input_data.current_status.value
        row.analysis_status = input_data.analysis_status.value
        row.credibility = input_data.credibility.value if input_data.credibility else None
        row.priority_score = input_data.priority_score
        row.recommendation_score = input_data.recommendation_score
        row.confidence = input_data.confidence
        row.risk_level = input_data.risk_level.value if input_data.risk_level else None
        row.risk_direction = input_data.risk_direction.value if input_data.risk_direction else None
        row.industries = list(input_data.industries)
        row.entities = list(input_data.entities)
        row.tags = list(input_data.tags)
        row.featured_reason = input_data.featured_reason
        row.is_featured = input_data.is_featured
        row.raw_event_id = input_data.raw_event_id
        row.routed_event_id = input_data.routed_event_id
        row.trace_id = input_data.trace_id
        row.correlation_id = input_data.correlation_id
        row.latest_agent_run_id = input_data.latest_agent_run_id
        row.latest_tool_invocation_id = input_data.latest_tool_invocation_id
        row.approval_id = input_data.approval_id
        row.degradation_notices = list(input_data.degradation_notices)
        row.evidence_summary = dict(input_data.evidence_summary)
        row.industry_impact_summary = dict(input_data.industry_impact_summary)
        row.best_action_summary = dict(input_data.best_action_summary)
        row.audit_refs = list(input_data.audit_refs)

    def _build_transition(
        self,
        *,
        event_id: str,
        from_status: str | None,
        input_data: EventMaterializationInput,
        created_at: datetime,
    ) -> EventStateTransitionORM:
        return EventStateTransitionORM(
            transition_id=f"evtst_{uuid4().hex[:24]}",
            event_id=event_id,
            from_status=from_status,
            to_status=input_data.current_status.value,
            reason_code=input_data.reason_code,
            reason_summary=input_data.reason_summary,
            actor_type=input_data.actor_type,
            actor_id=input_data.actor_id,
            source_ref=dict(input_data.source_ref),
            request_id=input_data.request_id,
            trace_id=input_data.trace_id,
            created_at=created_at,
        )

    def _latest_transition(self, event_id: str) -> EventStateTransitionORM | None:
        statement: Select[tuple[EventStateTransitionORM]] = (
            select(EventStateTransitionORM)
            .where(EventStateTransitionORM.event_id == event_id)
            .order_by(EventStateTransitionORM.created_at.desc(), EventStateTransitionORM.transition_id.desc())
            .limit(1)
        )
        return self.session.scalars(statement).first()

    def _get_existing_for_input(self, input_data: EventMaterializationInput, *, event_id: str) -> EventORM | None:
        by_identity = self.session.scalars(
            select(EventORM)
            .where(
                EventORM.identity_kind == input_data.identity_kind.value,
                EventORM.identity_value == input_data.identity_value,
            )
            .limit(1)
        ).first()
        if by_identity is not None:
            return by_identity
        if input_data.raw_event_id:
            by_raw_event = self.session.scalars(
                select(EventORM).where(EventORM.raw_event_id == input_data.raw_event_id).limit(1)
            ).first()
            if by_raw_event is not None:
                return by_raw_event
        if input_data.routed_event_id:
            by_routed_event = self.session.scalars(
                select(EventORM).where(EventORM.routed_event_id == input_data.routed_event_id).limit(1)
            ).first()
            if by_routed_event is not None:
                return by_routed_event
        return self.session.get(EventORM, event_id)

    def _apply_filters(self, statement: Select[tuple[EventORM]], query: EventListQuery) -> Select[tuple[EventORM]]:
        if query.captured_from is not None:
            statement = statement.where(EventORM.captured_at >= query.captured_from)
        if query.credibility is not None:
            statement = statement.where(EventORM.credibility == query.credibility)
        if query.analysis_status is not None:
            statement = statement.where(EventORM.analysis_status == query.analysis_status)
        if query.source_type is not None:
            statement = statement.where(EventORM.source_type == query.source_type)
        for industry in query.industries:
            statement = statement.where(cast(EventORM.industries, Text).like(f'%"{industry}"%'))
        return statement

    def _apply_sort(
        self,
        statement: Select[tuple[EventORM]],
        sort: EventSortMode,
        *,
        cursor: dict[str, object] | None,
    ) -> Select[tuple[EventORM]]:
        effective_published_at = func.coalesce(EventORM.published_at, EventORM.captured_at)
        priority_value = func.coalesce(EventORM.priority_score, -1.0)
        featured_rank = case((EventORM.is_featured.is_(True), 1), else_=0)

        if sort is EventSortMode.LATEST:
            if cursor is not None:
                published_at = _cursor_datetime(cursor, "published_at")
                captured_at = _cursor_datetime(cursor, "captured_at")
                event_id = _cursor_string(cursor, "event_id")
                statement = statement.where(
                    or_(
                        effective_published_at < published_at,
                        and_(
                            effective_published_at == published_at,
                            or_(
                                EventORM.captured_at < captured_at,
                                and_(EventORM.captured_at == captured_at, EventORM.event_id < event_id),
                            ),
                        ),
                    )
                )
            return statement.order_by(desc(effective_published_at), desc(EventORM.captured_at), desc(EventORM.event_id))

        if sort is EventSortMode.PRIORITY:
            if cursor is not None:
                priority_score = _cursor_float(cursor, "priority_score")
                captured_at = _cursor_datetime(cursor, "captured_at")
                event_id = _cursor_string(cursor, "event_id")
                statement = statement.where(
                    or_(
                        priority_value < priority_score,
                        and_(
                            priority_value == priority_score,
                            or_(
                                EventORM.captured_at < captured_at,
                                and_(EventORM.captured_at == captured_at, EventORM.event_id < event_id),
                            ),
                        ),
                    )
                )
            return statement.order_by(desc(priority_value), desc(EventORM.captured_at), desc(EventORM.event_id))

        if cursor is not None:
            featured = _cursor_int(cursor, "featured_rank")
            priority_score = _cursor_float(cursor, "priority_score")
            captured_at = _cursor_datetime(cursor, "captured_at")
            event_id = _cursor_string(cursor, "event_id")
            statement = statement.where(
                or_(
                    featured_rank < featured,
                    and_(
                        featured_rank == featured,
                        or_(
                            priority_value < priority_score,
                            and_(
                                priority_value == priority_score,
                                or_(
                                    EventORM.captured_at < captured_at,
                                    and_(EventORM.captured_at == captured_at, EventORM.event_id < event_id),
                                ),
                            ),
                        ),
                    ),
                )
            )
        return statement.order_by(desc(featured_rank), desc(priority_value), desc(EventORM.captured_at), desc(EventORM.event_id))


def _build_cursor(row: EventORM, *, sort: EventSortMode) -> str:
    if sort is EventSortMode.LATEST:
        return encode_event_cursor(
            {
                "sort": sort.value,
                "published_at": (row.published_at or row.captured_at).astimezone(UTC).isoformat(),
                "captured_at": row.captured_at.astimezone(UTC).isoformat(),
                "event_id": row.event_id,
            }
        )
    if sort is EventSortMode.PRIORITY:
        return encode_event_cursor(
            {
                "sort": sort.value,
                "priority_score": float(row.priority_score or -1.0),
                "captured_at": row.captured_at.astimezone(UTC).isoformat(),
                "event_id": row.event_id,
            }
        )
    return encode_event_cursor(
        {
            "sort": sort.value,
            "featured_rank": 1 if row.is_featured else 0,
            "priority_score": float(row.priority_score or -1.0),
            "captured_at": row.captured_at.astimezone(UTC).isoformat(),
            "event_id": row.event_id,
        }
    )


def _to_event_record(row: EventORM) -> EventRecord:
    return EventRecord(
        event_id=row.event_id,
        schema_version=row.schema_version,
        title=row.title,
        summary=row.summary,
        source_name=row.source_name,
        source_type=row.source_type,
        source_url=row.source_url,
        source_authority=row.source_authority,
        published_at=row.published_at,
        captured_at=row.captured_at,
        current_status=row.current_status,
        analysis_status=row.analysis_status,
        credibility=row.credibility,
        priority_score=_to_optional_float(row.priority_score),
        recommendation_score=_to_optional_float(row.recommendation_score),
        confidence=_to_optional_float(row.confidence),
        risk_level=row.risk_level,
        risk_direction=row.risk_direction,
        industries=tuple(str(item) for item in (row.industries or [])),
        entities=tuple(str(item) for item in (row.entities or [])),
        tags=tuple(str(item) for item in (row.tags or [])),
        featured_reason=row.featured_reason,
        is_featured=bool(row.is_featured),
        raw_event_id=row.raw_event_id,
        routed_event_id=row.routed_event_id,
        trace_id=row.trace_id,
        correlation_id=row.correlation_id,
        identity_kind=row.identity_kind,
        identity_value=row.identity_value,
        version=row.version,
        latest_agent_run_id=row.latest_agent_run_id,
        latest_tool_invocation_id=row.latest_tool_invocation_id,
        approval_id=row.approval_id,
        degradation_notices=tuple(_json_object(item) for item in (row.degradation_notices or [])),
        evidence_summary=_json_object(row.evidence_summary),
        industry_impact_summary=_json_object(row.industry_impact_summary),
        best_action_summary=_json_object(row.best_action_summary),
        audit_refs=tuple(_json_object(item) for item in (row.audit_refs or [])),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_transition_record(row: EventStateTransitionORM) -> EventStateTransitionRecord:
    return EventStateTransitionRecord(
        transition_id=row.transition_id,
        event_id=row.event_id,
        from_status=row.from_status,
        to_status=row.to_status,
        reason_code=row.reason_code,
        reason_summary=row.reason_summary,
        actor_type=row.actor_type,
        actor_id=row.actor_id,
        source_ref=_json_object(row.source_ref),
        request_id=row.request_id,
        trace_id=row.trace_id,
        created_at=row.created_at,
    )


def _json_object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


def _to_optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _cursor_datetime(cursor: dict[str, object], key: str) -> datetime:
    raw_value = _cursor_string(cursor, key)
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError("event cursor is invalid") from exc


def _cursor_float(cursor: dict[str, object], key: str) -> float:
    raw_value = cursor.get(key)
    if isinstance(raw_value, int | float):
        return float(raw_value)
    raise ValueError("event cursor is invalid")


def _cursor_int(cursor: dict[str, object], key: str) -> int:
    raw_value = cursor.get(key)
    if isinstance(raw_value, int):
        return raw_value
    raise ValueError("event cursor is invalid")


def _cursor_string(cursor: dict[str, object], key: str) -> str:
    raw_value = cursor.get(key)
    if isinstance(raw_value, str) and raw_value:
        return raw_value
    raise ValueError("event cursor is invalid")


def _is_backward_transition(previous_status: str, next_status: str) -> bool:
    return _STATUS_ORDER.get(next_status, 0) < _STATUS_ORDER.get(previous_status, 0)


def _is_duplicate_transition(
    latest_transition: EventStateTransitionORM | None,
    input_data: EventMaterializationInput,
) -> bool:
    if latest_transition is None:
        return False
    if latest_transition.to_status != input_data.current_status.value:
        return False
    if latest_transition.request_id != input_data.request_id:
        return False
    return json.dumps(latest_transition.source_ref or {}, sort_keys=True) == json.dumps(dict(input_data.source_ref), sort_keys=True)
