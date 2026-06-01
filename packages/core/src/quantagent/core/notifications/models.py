from __future__ import annotations

from dataclasses import dataclass, field

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping


@dataclass(frozen=True)
class NotificationReceiveFact:
    fact_id: str
    plugin_id: str
    transport: str
    request_id: str
    correlation_id: str
    interaction_id: str
    source_id: str
    text: str
    payload_summary: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)
    received_at: str = ""
    guild_id: str | None = None
    channel_id: str | None = None
    author_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("fact_id", self.fact_id)
        _require_non_empty("plugin_id", self.plugin_id)
        _require_non_empty("transport", self.transport)
        _require_non_empty("request_id", self.request_id)
        _require_non_empty("correlation_id", self.correlation_id)
        _require_non_empty("interaction_id", self.interaction_id)
        _require_non_empty("source_id", self.source_id)
        _require_non_empty("text", self.text)
        _require_non_empty("received_at", self.received_at)
        object.__setattr__(self, "payload_summary", freeze_json_mapping(self.payload_summary, stage="invoke"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="invoke"))


@dataclass(frozen=True)
class NotificationIngressAuditEntry:
    audit_id: str
    event_type: str
    plugin_id: str
    request_id: str
    correlation_id: str
    recorded_at: str
    details: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("audit_id", self.audit_id)
        _require_non_empty("event_type", self.event_type)
        _require_non_empty("plugin_id", self.plugin_id)
        _require_non_empty("request_id", self.request_id)
        _require_non_empty("correlation_id", self.correlation_id)
        _require_non_empty("recorded_at", self.recorded_at)
        object.__setattr__(self, "details", freeze_json_mapping(self.details, stage="invoke"))


@dataclass(frozen=True)
class NotificationApprovalHandoffRequest:
    handoff_id: str
    fact_id: str
    plugin_id: str
    transport: str
    request_id: str
    correlation_id: str
    interaction_id: str
    source_id: str
    text: str
    payload_summary: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)
    received_at: str = ""
    guild_id: str | None = None
    channel_id: str | None = None
    author_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("handoff_id", self.handoff_id)
        _require_non_empty("fact_id", self.fact_id)
        _require_non_empty("plugin_id", self.plugin_id)
        _require_non_empty("transport", self.transport)
        _require_non_empty("request_id", self.request_id)
        _require_non_empty("correlation_id", self.correlation_id)
        _require_non_empty("interaction_id", self.interaction_id)
        _require_non_empty("source_id", self.source_id)
        _require_non_empty("text", self.text)
        _require_non_empty("received_at", self.received_at)
        object.__setattr__(self, "payload_summary", freeze_json_mapping(self.payload_summary, stage="invoke"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="invoke"))


@dataclass(frozen=True)
class NotificationApprovalHandoffResult:
    status: str
    message: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("status", self.status)
        _require_non_empty("message", self.message)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="invoke"))


def _require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
