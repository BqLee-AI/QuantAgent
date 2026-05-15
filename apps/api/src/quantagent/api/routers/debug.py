from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from quantagent.api.errors import BadRequestError
from quantagent.api.responses import ApiResponse


router = APIRouter(prefix="/debug", tags=["debug"])


class DebugValidationRequest(BaseModel):
    name: str


@router.get("/success", response_model=ApiResponse[dict[str, str]])
def success() -> ApiResponse[dict[str, str]]:
    return ApiResponse.success({"status": "ok"})


@router.get("/error")
def error() -> None:
    raise BadRequestError("参数错误")


@router.post("/validation", response_model=ApiResponse[dict[str, str]])
def validation(_: DebugValidationRequest) -> ApiResponse[dict[str, str]]:
    return ApiResponse.success({"status": "ok"})
