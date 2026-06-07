from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any

from quantagent.core.events.envelope import EventEnvelope
from quantagent.core.events.errors import EventBusError
from quantagent.plugin_sdk.io import JsonObject, JsonValue, freeze_json_mapping, to_json_value

SENSITIVE_KEYWORDS = frozenset(
    {
        "api_key",
        "authorization",
        "chain_of_thought",
        "cookie",
        "password",
        "prompt",
        "provider_raw_response",
        "raw_response",
        "reasoning",
        "secret",
        "session",
        "token",
    }
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)(token|secret|password|cookie|authorization|api[_-]?key)\s*[:=]\s*[^,\s]+"
)
LOCAL_PATH_PATTERN = re.compile(r"(/(?:home|tmp|var|Users)/[^\s,;]+|[A-Za-z]:\\[^\s,;]+)")
REDACTED = "[REDACTED]"


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(keyword in lowered for keyword in SENSITIVE_KEYWORDS)


def sanitize_string(value: str) -> str:
    return LOCAL_PATH_PATTERN.sub(REDACTED, SENSITIVE_VALUE_PATTERN.sub(REDACTED, value))


def sanitize_json_value(value: Any, *, key: str | None = None) -> JsonValue:
    if key is not None and is_sensitive_key(key):
        return REDACTED
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return f"[NON_FINITE_FLOAT:{value!r}]"
    if isinstance(value, str):
        return sanitize_string(value)
    if isinstance(value, Mapping):
        return {str(child_key): sanitize_json_value(child_value, key=str(child_key)) for child_key, child_value in value.items()}
    if isinstance(value, list | tuple):
        return tuple(sanitize_json_value(item, key=key) for item in value)
    return f"[UNSERIALIZABLE:{value.__class__.__name__}]"


def sanitize_mapping(value: Mapping[str, Any]) -> JsonObject:
    return freeze_json_mapping(
        {str(key): sanitize_json_value(item, key=str(key)) for key, item in value.items()},
        stage="publish",
    )


def error_to_summary(error: EventBusError) -> JsonObject:
    return freeze_json_mapping(
        {
            "code": error.code,
            "message": sanitize_string(error.message),
            "stage": error.stage,
            "retryable": error.retryable,
            "details": to_json_value(sanitize_mapping(error.details)),
        },
        stage=error.stage,
    )


class EventBusCodec:
    def encode(self, envelope: EventEnvelope) -> bytes:
        payload = {
            "id": envelope.id,
            "topic": envelope.topic,
            "payload": to_json_value(envelope.payload),
            "producer": envelope.producer,
            "created_at": envelope.created_at,
            "correlation_id": envelope.correlation_id,
            "causation_id": envelope.causation_id,
            "headers": to_json_value(envelope.headers),
            "retry_count": envelope.retry_count,
            "schema_version": envelope.schema_version,
        }
        return json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")

    def decode(self, message: bytes | str | Mapping[str, Any]) -> EventEnvelope:
        try:
            if isinstance(message, bytes):
                payload = json.loads(message.decode("utf-8"))
            elif isinstance(message, str):
                payload = json.loads(message)
            elif isinstance(message, Mapping):
                payload = dict(message)
            else:
                raise TypeError(f"Unsupported message type: {type(message).__name__}")
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            raise EventBusError(
                code="EVENT_CODEC_DECODE_FAILED",
                message="Event envelope could not be decoded.",
                stage="decode",
                details={"error_type": exc.__class__.__name__},
            ) from exc

        if not isinstance(payload, dict):
            raise EventBusError(
                code="EVENT_CODEC_MESSAGE_INVALID",
                message="Event envelope payload must decode into an object.",
                stage="decode",
            )

        try:
            return EventEnvelope(
                id=str(payload["id"]),
                topic=str(payload["topic"]),
                payload=freeze_json_mapping(payload.get("payload", {}), stage="decode"),
                producer=str(payload["producer"]),
                created_at=str(payload["created_at"]),
                correlation_id=_optional_string(payload.get("correlation_id")),
                causation_id=_optional_string(payload.get("causation_id")),
                headers=freeze_json_mapping(payload.get("headers", {}), stage="decode"),
                retry_count=int(payload.get("retry_count", 0)),
                schema_version=int(payload.get("schema_version", 1)),
            )
        except KeyError as exc:
            raise EventBusError(
                code="EVENT_CODEC_FIELD_MISSING",
                message="Event envelope is missing a required field.",
                stage="decode",
                details={"field": str(exc)},
            ) from exc
        except (TypeError, ValueError) as exc:
            raise EventBusError(
                code="EVENT_CODEC_FIELD_INVALID",
                message="Event envelope contains an invalid field.",
                stage="decode",
                details={"error_type": exc.__class__.__name__},
            ) from exc


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
