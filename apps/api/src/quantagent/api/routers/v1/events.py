from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from quantagent.api.auth import CurrentActor, RUNTIME_INSPECT_CAPABILITY, require_capability
from quantagent.api.db import get_db_session
from quantagent.api.http.errors import BadRequestError
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.events import EventDetailResponse, EventListResponse
from quantagent.api.services.event_api import EventApiService


router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=ApiResponse[EventListResponse])
def list_events(
    request: Request,
    time_range: str = Query(default="24h"),
    industry: list[str] = Query(default_factory=list),
    credibility: str | None = Query(default=None),
    analysis_status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    sort: str = Query(default="mixed"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[EventListResponse]:
    service = EventApiService(session=session, request=request)
    try:
        payload = service.list_events(
            time_range=time_range,
            industries=industry,
            credibility=credibility,
            analysis_status=analysis_status,
            source_type=source_type,
            sort=sort,
            cursor=cursor,
            limit=limit,
        )
    except ValueError as exc:
        raise BadRequestError("Invalid event query", details={"reason": str(exc)}) from exc
    return ApiResponse.success(payload)


@router.get("/{event_id}", response_model=ApiResponse[EventDetailResponse])
def get_event(
    event_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[EventDetailResponse]:
    service = EventApiService(session=session, request=request)
    return ApiResponse.success(service.get_event(event_id))
