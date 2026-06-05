from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from quantagent.api.auth import CurrentActor, RUNTIME_INSPECT_CAPABILITY, require_capability
from quantagent.api.db import get_db_session
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.dashboard import DashboardSummaryResponse
from quantagent.api.services.dashboard_api import DashboardApiService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=ApiResponse[DashboardSummaryResponse])
def get_dashboard_summary(
    request: Request,
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[DashboardSummaryResponse]:
    service = DashboardApiService(session=session, request=request)
    return ApiResponse.success(service.get_summary())
