from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from quantagent.api.auth import RUNTIME_INSPECT_CAPABILITY, CurrentActor, require_capability
from quantagent.api.db import get_db_session
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.runtime_audit import RuntimeAuditNewsListResponse
from quantagent.api.services.runtime_audit import RuntimeAuditNewsQueryService


router = APIRouter(prefix="/runtime/audit", tags=["runtime"])


@router.get("/news", response_model=ApiResponse[RuntimeAuditNewsListResponse])
def list_runtime_audit_news(
    request: Request,
    keyword: str | None = None,
    binding_id: str | None = None,
    source_plugin_id: str | None = None,
    status: str | None = None,
    current_stage: str | None = None,
    trace_id: str | None = None,
    request_id: str | None = None,
    time_from: datetime | None = None,
    time_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[RuntimeAuditNewsListResponse]:
    service = RuntimeAuditNewsQueryService(session=session, request=request)
    return ApiResponse.success(
        service.list_news(
            keyword=keyword,
            binding_id=binding_id,
            source_plugin_id=source_plugin_id,
            status=status,
            current_stage=current_stage,
            trace_id=trace_id,
            request_id=request_id,
            time_from=time_from,
            time_to=time_to,
            cursor=cursor,
            limit=limit,
        )
    )
