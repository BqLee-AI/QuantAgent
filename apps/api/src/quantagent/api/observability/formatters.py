from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
import os
from typing import Any


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

        message = record.getMessage()
        if message and message != payload["event"]:
            payload["message"] = message

        payload.update(structured)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
