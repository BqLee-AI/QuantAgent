from __future__ import annotations

import re
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_MAX_LENGTH = 128
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def generate_request_id() -> str:
    """当客户端未提供请求 ID 时，生成一个兜底值。"""
    return uuid.uuid4().hex


def normalize_request_id(request_id: str | None) -> str:
    """接受合法的客户端请求 ID，不合法时替换为系统生成的值。"""
    if request_id and len(request_id) <= REQUEST_ID_MAX_LENGTH and REQUEST_ID_PATTERN.fullmatch(request_id):
        return request_id
    return generate_request_id()


def get_request_id(request: Request) -> str:
    """读取缓存的请求 ID；若尚未写入，则按需补算并缓存。"""
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id

    normalized = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = normalized
    return normalized


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 将规范化后的请求 ID 回写给客户端，便于日志和响应按同一标识串联排查。
        request.state.request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response
