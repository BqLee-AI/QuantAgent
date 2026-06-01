from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
import os
from collections.abc import Mapping
from typing import Any

from quantagent.api.observability.filters import redact_value


_RESERVED_PAYLOAD_KEYS = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "service",
        "env",
        "instance_id",
        "pid",
        "stream",
        "event",
        "request_id",
        "trace_id",
        "message",
    }
)


class JsonLinesFormatter(logging.Formatter):
    def __init__(self, *, service: str, env: str, instance_id: str, pid: int | None = None) -> None:
        super().__init__()
        self._service = service
        self._env = env
        self._instance_id = instance_id
        self._pid = pid if pid is not None else os.getpid()

    def format(self, record: logging.LogRecord) -> str:
        structured = getattr(record, "structured_data", None)
        if not isinstance(structured, dict):
            structured = {}

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "service": self._service,
            "env": self._env,
            "instance_id": self._instance_id,
            "pid": self._pid,
            "stream": getattr(record, "stream", "app"),
            "event": getattr(record, "event", f"log.{record.levelname.lower()}"),
            "request_id": structured.get("request_id"),
            "trace_id": structured.get("trace_id"),
        }

        message = _get_redacted_message(record)
        if message and message != payload["event"]:
            payload["message"] = message

        payload.update(
            {
                key: _json_safe_value(str(key), value)
                for key, value in structured.items()
                if key not in _RESERVED_PAYLOAD_KEYS
            }
        )
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _get_redacted_message(record: logging.LogRecord) -> str:
    try:
        message = record.getMessage()
    except Exception:
        # 第三方 logger 可能使用非标准 msg/args 组合；结构化日志不能因此中断 API 启动或请求处理。
        message = str(record.msg)
    return redact_value("message", message)


def _json_safe_value(key: str, value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return redact_value(key, value)
    if isinstance(value, Mapping):
        return {str(nested_key): _json_safe_value(str(nested_key), nested_value) for nested_key, nested_value in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe_value(key, item) for item in value]

    # 日志字段来自错误 details 或第三方 extra 时可能带对象；统一降级成脱敏字符串，避免 handler 抛错打断请求。
    return redact_value(key, str(value))
