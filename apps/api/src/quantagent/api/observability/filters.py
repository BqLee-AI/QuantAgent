from __future__ import annotations

from collections.abc import Mapping
import logging
import re
from typing import Any

from quantagent.api.observability.context import get_current_request_context


_REDACTED = "[REDACTED]"
_SENSITIVE_KEYWORDS = (
    "authorization",
    "cookie",
    "csrf",
    "password",
    "token",
    "secret",
    "session",
    "api_key",
    "apikey",
    "database_url",
    "database-url",
    "dsn",
)
_DATABASE_URL_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]+")
_STANDARD_RECORD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__.keys())


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS)


def redact_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, str) and _DATABASE_URL_RE.search(value):
        return _DATABASE_URL_RE.sub(_REDACTED, value)
    if isinstance(value, Mapping):
        return {nested_key: redact_value(str(nested_key), nested_value) for nested_key, nested_value in value.items()}
    if isinstance(value, list):
        return [redact_value(key, item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(key, item) for item in value)
    return value


class ContextInjectionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = get_current_request_context()
        structured = getattr(record, "structured_data", None)
        if not isinstance(structured, dict):
            structured = {}

        if context is not None:
            structured.setdefault("request_id", context.request_id)
            structured.setdefault("trace_id", context.trace_id)
            if context.actor_type:
                structured.setdefault("actor_type", context.actor_type)
            if context.actor_id and getattr(record, "stream", "app") in {"security", "audit"}:
                structured.setdefault("actor_id", context.actor_id)
            if context.method:
                structured.setdefault("method", context.method)
            if context.path:
                structured.setdefault("path", context.path)
            if context.route:
                structured.setdefault("route", context.route)

        record.structured_data = structured
        record.request_id = structured.get("request_id")
        record.trace_id = structured.get("trace_id")
        return True


class SensitiveDataRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        structured = getattr(record, "structured_data", None)
        if isinstance(structured, dict):
            record.structured_data = {
                key: redact_value(str(key), value)
                for key, value in structured.items()
            }

        for key, value in list(record.__dict__.items()):
            if key in _STANDARD_RECORD_ATTRS or key in {"structured_data"}:
                continue
            record.__dict__[key] = redact_value(key, value)

        return True
