from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from quantagent.api.errors import BadRequestError
from quantagent.api.responses import ApiResponse


router = APIRouter(prefix="/debug", tags=["debug"])


class DebugValidationRequest(BaseModel):
    """用于演示校验错误响应格式的最小请求体。"""

    name: str


@router.get("/success", response_model=ApiResponse[dict[str, str]])
def success() -> ApiResponse[dict[str, str]]:
    """用于手工验证成功响应包裹格式的示例接口。"""
    return ApiResponse.success({"status": "ok"})


@router.get("/error")
def error() -> None:
    """主动抛出业务异常，方便本地查看错误处理效果。"""
    raise BadRequestError("参数错误")


@router.post("/validation", response_model=ApiResponse[dict[str, str]])
def validation(_: DebugValidationRequest) -> ApiResponse[dict[str, str]]:
    """先触发 FastAPI 请求体验证，再返回正常响应。"""
    return ApiResponse.success({"status": "ok"})
