from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from quantagent.api.auth import CurrentActor, RUNTIME_INSPECT_CAPABILITY, require_capability
from quantagent.api.db import get_db_session
from quantagent.api.http.errors import BadRequestError
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.raw_events import RawEventDetailResponse, RawEventListResponse
from quantagent.api.services.raw_event_api import RawEventQueryService


router = APIRouter(prefix="/raw-events", tags=["runtime"])


@router.get("", response_model=ApiResponse[RawEventListResponse])
def list_raw_events(
    request: Request,
    source_plugin_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[RawEventListResponse]:
    service = RawEventQueryService(session=session, request=request)
    try:
        items, next_cursor = service.list_raw_events(
            source_plugin_id=source_plugin_id,
            cursor=cursor,
            limit=limit,
        )
    except ValueError as exc:
        raise BadRequestError("Invalid raw event query", details={"reason": str(exc)}) from exc
    return ApiResponse.success(RawEventListResponse(items=items, next_cursor=next_cursor))


@router.get("/{raw_event_id}", response_model=ApiResponse[RawEventDetailResponse])
def get_raw_event(
    raw_event_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[RawEventDetailResponse]:
    service = RawEventQueryService(session=session, request=request)
    return ApiResponse.success(service.get_raw_event(raw_event_id))
