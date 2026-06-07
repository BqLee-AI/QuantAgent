from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from quantagent.api.auth import EVENT_INSPECT_CAPABILITY, CurrentActor, require_capability
from quantagent.api.db import get_db_session
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.events import EventDetailResponse, EventListResponse, EventRouterOutputResponse
from quantagent.api.services.events import EventReadModelQueryService


router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=ApiResponse[EventListResponse])
def list_events(
    keyword: str | None = None,
    decision: str | None = None,
    include_discard: bool = False,
    binding_id: str | None = None,
    source_plugin_id: str | None = None,
    industry_id: str | None = None,
    target_topic: str | None = None,
    priority: str | None = None,
    relationship: str | None = None,
    status: str | None = None,
    trace_id: str | None = None,
    request_id: str | None = None,
    sort: str = "routed_at_desc",
    time_from: datetime | None = None,
    time_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(EVENT_INSPECT_CAPABILITY)),
) -> ApiResponse[EventListResponse]:
    service = EventReadModelQueryService(session=session)
    return ApiResponse.success(
        service.list_events(
            keyword=keyword,
            decision=decision,
            include_discard=include_discard,
            binding_id=binding_id,
            source_plugin_id=source_plugin_id,
            industry_id=industry_id,
            target_topic=target_topic,
            priority=priority,
            relationship=relationship,
            status=status,
            trace_id=trace_id,
            request_id=request_id,
            sort=sort,
            time_from=time_from,
            time_to=time_to,
            cursor=cursor,
            limit=limit,
        )
    )


@router.get("/{raw_event_id}", response_model=ApiResponse[EventDetailResponse])
def get_event_detail(
    raw_event_id: str,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(EVENT_INSPECT_CAPABILITY)),
) -> ApiResponse[EventDetailResponse]:
    return ApiResponse.success(EventReadModelQueryService(session=session).get_event_detail(raw_event_id))


@router.get("/{raw_event_id}/router-output", response_model=ApiResponse[EventRouterOutputResponse])
def get_event_router_output(
    raw_event_id: str,
    routed_event_id: str | None = None,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(EVENT_INSPECT_CAPABILITY)),
) -> ApiResponse[EventRouterOutputResponse]:
    return ApiResponse.success(
        EventReadModelQueryService(session=session).get_router_output(
            raw_event_id=raw_event_id,
            routed_event_id=routed_event_id,
        )
    )
