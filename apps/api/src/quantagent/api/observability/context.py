from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, replace
import re
import uuid


REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"
REQUEST_ID_MAX_LENGTH = 128
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
TRACE_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")
TRACEPARENT_PATTERN = re.compile(r"^[\da-fA-F]{2}-([\da-fA-F]{32})-([\da-fA-F]{16})-[\da-fA-F]{2}$")


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    trace_id: str
    method: str | None = None
    path: str | None = None
    route: str | None = None
    actor_type: str | None = None
    actor_id: str | None = None


_REQUEST_CONTEXT: ContextVar[RequestContext | None] = ContextVar("quantagent_api_request_context", default=None)


def generate_request_id() -> str:
    return uuid.uuid4().hex


def normalize_request_id(request_id: str | None) -> str:
    if request_id and len(request_id) <= REQUEST_ID_MAX_LENGTH and REQUEST_ID_PATTERN.fullmatch(request_id):
        return request_id
    return generate_request_id()


def generate_trace_id() -> str:
    return uuid.uuid4().hex


def normalize_trace_id(trace_id: str | None) -> str | None:
    if trace_id and TRACE_ID_PATTERN.fullmatch(trace_id):
        return trace_id.lower()
    return None


def resolve_trace_id(traceparent: str | None, trace_id: str | None) -> str:
    if traceparent:
        match = TRACEPARENT_PATTERN.fullmatch(traceparent.strip())
        if match is not None:
            return match.group(1).lower()
    normalized = normalize_trace_id(trace_id)
    return normalized or generate_trace_id()


def set_request_context(
    *,
    request_id: str,
    trace_id: str,
    method: str | None = None,
    path: str | None = None,
    route: str | None = None,
) -> Token[RequestContext | None]:
    return _REQUEST_CONTEXT.set(
        RequestContext(
            request_id=request_id,
            trace_id=trace_id,
            method=method,
            path=path,
            route=route,
        )
    )


def clear_request_context(token: Token[RequestContext | None]) -> None:
    _REQUEST_CONTEXT.reset(token)


def get_current_request_context() -> RequestContext | None:
    return _REQUEST_CONTEXT.get()


def get_request_id_from_context() -> str | None:
    context = get_current_request_context()
    return None if context is None else context.request_id


def get_trace_id_from_context() -> str | None:
    context = get_current_request_context()
    return None if context is None else context.trace_id


def set_actor_context(*, actor_type: str | None, actor_id: str | None = None) -> None:
    context = get_current_request_context()
    if context is None:
        return
    _REQUEST_CONTEXT.set(replace(context, actor_type=actor_type, actor_id=actor_id))
