from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiErrorDetail(BaseModel):
    code: str
    request_id: str
    trace_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class ApiResponse(BaseModel, Generic[T]):
    code: int
    data: T | None = None
    msg: str
    error: ApiErrorDetail | None = None

    @classmethod
    def success(cls, data: T | None = None, msg: str = "ok") -> "ApiResponse[T]":
        return cls(code=0, data=data, msg=msg, error=None)
