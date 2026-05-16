import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from quantagent.api.db import get_db_session
from quantagent.api.errors import ServiceUnavailableError
from quantagent.api.responses import ApiResponse

router = APIRouter()
logger = logging.getLogger("quantagent.api")


@router.get("/health")
def health() -> ApiResponse[dict[str, str]]:
    return ApiResponse.success({"status": "ok"})


@router.get("/ready")
def ready(session: Session = Depends(get_db_session)) -> ApiResponse[dict[str, str]]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Database readiness check failed: %s", exc.__class__.__name__)
        raise ServiceUnavailableError("Database not ready") from exc
    return ApiResponse.success({"status": "ready"})
