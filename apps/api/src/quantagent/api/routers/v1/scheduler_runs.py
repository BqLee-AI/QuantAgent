from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from quantagent.api.auth import RUNTIME_INSPECT_CAPABILITY, CurrentActor, require_capability
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.runtime_inspect import RuntimeListResponse, SchedulerRunDetail, SchedulerRunSummary
from quantagent.api.services.runtime_inspect import RuntimeInspectListFilters, RuntimeInspectService
from quantagent.api.services.runtime_inspect_session import get_optional_db_session


router = APIRouter(prefix="/scheduler-runs", tags=["runtime"])


@router.get("", response_model=ApiResponse[RuntimeListResponse[SchedulerRunSummary]])
def list_scheduler_runs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    event_id: str | None = None,
    trace_id: str | None = None,
    plugin_id: str | None = None,
    status: str | None = None,
    time_from: datetime | None = None,
    time_to: datetime | None = None,
    trigger_type: str | None = None,
    session: Session | None = Depends(get_optional_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[RuntimeListResponse[SchedulerRunSummary]]:
    service = RuntimeInspectService(session=session, request=request)
    filters = RuntimeInspectListFilters(
        page=page,
        page_size=page_size,
        event_id=event_id,
        trace_id=trace_id,
        plugin_id=plugin_id,
        status=status,
        time_from=time_from,
        time_to=time_to,
    )
    return ApiResponse.success(service.list_scheduler_runs(filters=filters, trigger_type=trigger_type))


@router.get("/{run_id}", response_model=ApiResponse[SchedulerRunDetail])
def get_scheduler_run(
    run_id: str,
    request: Request,
    session: Session | None = Depends(get_optional_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[SchedulerRunDetail]:
    service = RuntimeInspectService(session=session, request=request)
    return ApiResponse.success(service.get_scheduler_run(run_id))
