from __future__ import annotations

from fastapi import Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from quantagent.api.observability.context import (
    REQUEST_ID_HEADER,
    REQUEST_ID_MAX_LENGTH,
    REQUEST_ID_PATTERN,
    TRACE_ID_HEADER,
    clear_request_context,
    generate_request_id,
    get_request_id_from_context,
    get_trace_id_from_context,
    normalize_request_id,
    resolve_trace_id,
    set_request_context,
)
from quantagent.api.observability.logging import RequestTiming, log_access_event


def get_request_id(request: Request) -> str:
    """读取缓存的请求 ID；若尚未写入，则按需补算并缓存。"""
    request_id = get_request_id_from_context()
    if isinstance(request_id, str) and request_id:
        return request_id

    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id

    normalized = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = normalized
    return normalized


def get_trace_id(request: Request) -> str:
    trace_id = get_trace_id_from_context()
    if isinstance(trace_id, str) and trace_id:
        return trace_id

    request_trace_id = getattr(request.state, "trace_id", None)
    if isinstance(request_trace_id, str) and request_trace_id:
        return request_trace_id

    normalized = resolve_trace_id(request.headers.get("traceparent"), request.headers.get(TRACE_ID_HEADER))
    request.state.trace_id = normalized
    return normalized


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        trace_id = resolve_trace_id(request.headers.get("traceparent"), request.headers.get(TRACE_ID_HEADER))
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        timing = RequestTiming()
        token = set_request_context(
            request_id=request_id,
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
            route=getattr(request.scope.get("route"), "path", None),
        )

        async def send_with_context_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                scope["_quantagent_status_code"] = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                headers[TRACE_ID_HEADER] = trace_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_context_headers)
        except Exception:
            log_access_event(request, status_code=500, duration_ms=timing.duration_ms())
            raise
        else:
            log_access_event(request, status_code=int(scope.get("_quantagent_status_code", 200)), duration_ms=timing.duration_ms())
        finally:
            clear_request_context(token)


RequestIdMiddleware = RequestContextMiddleware
