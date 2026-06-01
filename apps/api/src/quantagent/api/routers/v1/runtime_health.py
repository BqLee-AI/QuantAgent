from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from quantagent.api.auth import RUNTIME_INSPECT_CAPABILITY, CurrentActor, require_capability
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.runtime_inspect import RuntimeHealthSummary
from quantagent.api.services.runtime_inspect import RuntimeInspectService
from quantagent.api.services.runtime_inspect_session import get_optional_db_session


router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/health", response_model=ApiResponse[RuntimeHealthSummary])
def get_runtime_health(
    request: Request,
    session: Session | None = Depends(get_optional_db_session),
    _actor: CurrentActor = Depends(require_capability(RUNTIME_INSPECT_CAPABILITY)),
) -> ApiResponse[RuntimeHealthSummary]:
    service = RuntimeInspectService(session=session, request=request)
    return ApiResponse.success(service.get_runtime_health())
