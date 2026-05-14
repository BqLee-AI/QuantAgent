from __future__ import annotations

import re
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_MAX_LENGTH = 128
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def generate_request_id() -> str:
    return uuid.uuid4().hex


def normalize_request_id(request_id: str | None) -> str:
    if request_id and len(request_id) <= REQUEST_ID_MAX_LENGTH and REQUEST_ID_PATTERN.fullmatch(request_id):
        return request_id
    return generate_request_id()


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id

    normalized = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = normalized
    return normalized


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response
