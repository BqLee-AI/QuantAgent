from __future__ import annotations

from dataclasses import dataclass, field

from quantagent.core.events.topics import DEFAULT_EVENT_SCHEMA_VERSION
from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping


def _require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


@dataclass(frozen=True)
class EventEnvelope:
    id: str
    topic: str
    payload: JsonObject = field(default_factory=dict)
    producer: str = ""
    created_at: str = ""
    correlation_id: str | None = None
    causation_id: str | None = None
    headers: JsonObject = field(default_factory=dict)
    retry_count: int = 0
    schema_version: int = DEFAULT_EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_non_empty("id", self.id)
        _require_non_empty("topic", self.topic)
        _require_non_empty("producer", self.producer)
        _require_non_empty("created_at", self.created_at)
        if self.correlation_id is not None:
            _require_non_empty("correlation_id", self.correlation_id)
        if self.causation_id is not None:
            _require_non_empty("causation_id", self.causation_id)
        if self.retry_count < 0:
            raise ValueError("retry_count must not be negative.")
        if self.schema_version <= 0:
            raise ValueError("schema_version must be greater than zero.")
        object.__setattr__(self, "payload", freeze_json_mapping(self.payload, stage="publish"))
        object.__setattr__(self, "headers", freeze_json_mapping(self.headers, stage="publish"))
