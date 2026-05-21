from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiErrorDetail(BaseModel):
    """接口失败时返回的结构化错误元信息。"""

    code: str
    request_id: str
    trace_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class ApiResponse(BaseModel, Generic[T]):
    """成功和失败响应共用的统一包裹结构。"""

    code: int
    data: T | None = None
    msg: str
    error: ApiErrorDetail | None = None

    @classmethod
    def success(cls, data: T | None = None, msg: str = "ok") -> "ApiResponse[T]":
        """构造标准成功响应。"""
        return cls(code=0, data=data, msg=msg, error=None)

