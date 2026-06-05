from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy.orm import Session

from quantagent.api.http.errors import NotFoundError
from quantagent.api.schemas.events import (
    EventBestActionResponse,
    EventDetailResponse,
    EventListFiltersResponse,
    EventListItemResponse,
    EventListResponse,
    EventRefResponse,
    EventSourceResponse,
    EventStateSummaryResponse,
    EventStateTransitionResponse,
    EventSummaryBucketsResponse,
)
from quantagent.core.db.repositories.event_repository import SqlAlchemyEventReadModelRepository
from quantagent.core.event_read_model import (
    EventListQuery,
    EventReadModelNotFoundError,
    EventReadModelService,
    EventSortMode,
    EventTimeRange,
)


class EventApiService:
    def __init__(self, *, session: Session, request: Request) -> None:
        self._service = EventReadModelService(
            repository=SqlAlchemyEventReadModelRepository(session),
            now_factory=lambda: datetime.now(UTC),
        )
        self._request = request

    def list_events(
        self,
        *,
        time_range: str,
        industries: list[str],
        credibility: str | None,
        analysis_status: str | None,
        source_type: str | None,
        sort: str,
        cursor: str | None,
        limit: int,
    ) -> EventListResponse:
        page = self._service.list_events(
            EventListQuery(
                time_range=EventTimeRange(time_range),
                industries=tuple(industries),
                credibility=credibility,
                analysis_status=analysis_status,
                source_type=source_type,
                sort=EventSortMode(sort),
                cursor=cursor,
                limit=limit,
            )
        )
        return EventListResponse(
            items=[_to_list_item(item) for item in page.items],
            next_cursor=page.next_cursor,
            filters=EventListFiltersResponse(
                time_range=time_range, industry=industries, credibility=credibility, analysis_status=analysis_status, source_type=source_type, sort=sort, limit=limit, cursor=cursor
            ),
            summary_buckets=EventSummaryBucketsResponse(
                new_count=page.buckets.new_count,
                featured_count=page.buckets.featured_count,
                analyzing_count=page.buckets.analyzing_count,
                failed_or_review_count=page.buckets.failed_or_review_count,
                pending_approval_count=page.buckets.pending_approval_count,
            ),
            generated_at=page.generated_at,
        )

    def get_event(self, event_id: str) -> EventDetailResponse:
        try:
            detail = self._service.get_event_detail(event_id)
        except EventReadModelNotFoundError as exc:
            raise NotFoundError("Event not found", details={"event_id": exc.event_id}) from exc

        recommendation_score = _float_value(detail.event.best_action_summary.get("recommendation_score"))
        confidence = _float_value(detail.event.best_action_summary.get("confidence"))
        risk_level = _string_value(detail.event.best_action_summary.get("risk_level")) or detail.event.risk_level
        risk_direction = _string_value(detail.event.best_action_summary.get("risk_direction")) or detail.event.risk_direction
        approval_ref = _approval_ref(detail.event.approval_id)
        return EventDetailResponse(
            event_id=detail.event.event_id,
            fact_summary={
                "title": detail.event.title,
                "summary": detail.event.summary,
                "source_name": detail.event.source_name,
                "source_url": detail.event.source_url,
                "published_at": detail.event.published_at,
                "captured_at": detail.event.captured_at,
            },
            score_summary={
                "credibility": detail.event.credibility,
                "priority_score": detail.event.priority_score,
                "recommendation_score": detail.event.recommendation_score,
                "confidence": detail.event.confidence,
                "risk_level": detail.event.risk_level,
                "risk_direction": detail.event.risk_direction,
            },
            industry_impact=dict(detail.event.industry_impact_summary),
            best_action=EventBestActionResponse(
                title=_string_value(detail.event.best_action_summary.get("title")),
                action_hint=_string_value(detail.event.best_action_summary.get("action_hint")),
                recommendation_score=recommendation_score,
                confidence=confidence,
                risk_level=risk_level,
                risk_direction=risk_direction,
                approval_ref=approval_ref,
                status=_string_value(detail.event.best_action_summary.get("status")),
                unavailable_reason=_string_value(detail.event.best_action_summary.get("unavailable_reason")),
            ),
            approval_ref=approval_ref,
            runtime_summary={
                "latest_agent_run_id": detail.event.latest_agent_run_id,
                "latest_tool_invocation_id": detail.event.latest_tool_invocation_id,
                "trace_id": detail.event.trace_id,
                "correlation_id": detail.event.correlation_id,
            },
            evidence_summary=dict(detail.event.evidence_summary),
            degradation_notices=[dict(item) for item in detail.event.degradation_notices],
            audit_refs=[dict(item) for item in detail.event.audit_refs],
            state_summary=EventStateSummaryResponse(
                current_status=detail.state_summary.current_status,
                analysis_status=detail.state_summary.analysis_status,
                version=detail.state_summary.version,
                transitions=[
                    EventStateTransitionResponse(
                        transition_id=item.transition_id,
                        from_status=item.from_status,
                        to_status=item.to_status,
                        reason_code=item.reason_code,
                        reason_summary=item.reason_summary,
                        actor_type=item.actor_type,
                        actor_id=item.actor_id,
                        request_id=item.request_id,
                        trace_id=item.trace_id,
                        created_at=item.created_at,
                    )
                    for item in detail.state_summary.transitions
                ],
            ),
        )


def _to_list_item(item) -> EventListItemResponse:
    return EventListItemResponse(
        event_id=item.event_id,
        title=item.title,
        summary=item.summary,
        source=EventSourceResponse(name=item.source_name, authority=item.source_authority),
        source_type=item.source_type,
        source_url=item.source_url,
        published_at=item.published_at,
        captured_at=item.captured_at,
        current_status=item.current_status,
        analysis_status=item.analysis_status,
        credibility=item.credibility,
        priority_score=item.priority_score,
        recommendation_score=item.recommendation_score,
        confidence=item.confidence,
        risk_level=item.risk_level,
        risk_direction=item.risk_direction,
        industries=list(item.industries),
        featured_reason=item.featured_reason,
        trace_ref=EventRefResponse(kind="trace", id=item.trace_id) if item.trace_id else None,
        raw_event_ref=EventRefResponse(kind="raw_event", id=item.raw_event_id) if item.raw_event_id else None,
        routed_event_ref=EventRefResponse(kind="routed_event", id=item.routed_event_id) if item.routed_event_id else None,
        degradation_notices=[dict(value) for value in item.degradation_notices],
    )


def _approval_ref(approval_id: str | None) -> EventRefResponse | None:
    if approval_id is None:
        return None
    return EventRefResponse(kind="approval", id=approval_id)


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _float_value(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None
