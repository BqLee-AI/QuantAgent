import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from quantagent.api.db import get_db_session
from quantagent.api.http.errors import ServiceUnavailableError
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.system import ProbeStatusResponse

router = APIRouter(tags=["system"])
logger = logging.getLogger("quantagent.api")


@router.get("/health", response_model=ApiResponse[ProbeStatusResponse])
def health() -> ApiResponse[ProbeStatusResponse]:
    """存活探针，即使依赖退化也应尽量保持可用。"""
    return ApiResponse.success(ProbeStatusResponse(status="ok"))


@router.get("/ready", response_model=ApiResponse[ProbeStatusResponse])
def ready(session: Session = Depends(get_db_session)) -> ApiResponse[ProbeStatusResponse]:
    """就绪探针，确认已配置的数据库当前可以正常响应查询。"""
    try:
        # 用最轻量的一次往返确认数据库可达，避免探针依赖具体业务表结构。
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Database readiness check failed: %s", exc.__class__.__name__)
        raise ServiceUnavailableError("Database not ready") from exc
    return ApiResponse.success(ProbeStatusResponse(status="ready"))

