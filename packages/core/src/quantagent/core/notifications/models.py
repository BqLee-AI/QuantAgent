from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping, to_json_value


@dataclass(frozen=True)
class NotificationDispatchRequest:
    request_id: str
    plugin_id: str
    correlation_id: str
    causation_id: str
    approval_id: str
    action_request_id: str
    channel: str
    text: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "plugin_id",
            "correlation_id",
            "causation_id",
            "approval_id",
            "action_request_id",
            "channel",
            "text",
        ):
            _require_non_empty(field_name, getattr(self, field_name))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="invoke"))


@dataclass(frozen=True)
class NotificationDispatchResult:
    request_id: str
    plugin_id: str
    accepted: bool
    retryable: bool
    code: str
    message: str
    correlation_id: str
    causation_id: str
    approval_id: str
    action_request_id: str
    channel: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "plugin_id",
            "code",
            "message",
            "correlation_id",
            "causation_id",
            "approval_id",
            "action_request_id",
            "channel",
        ):
            _require_non_empty(field_name, getattr(self, field_name))
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted must be a bool.")
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be a bool.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="invoke"))

    def to_delivery_summary(self) -> "NotificationDeliverySummary":
        return NotificationDeliverySummary(
            notification_request_id=self.request_id,
            plugin_id=self.plugin_id,
            accepted=self.accepted,
            retryable=self.retryable,
            code=self.code,
            message=self.message,
            approval_id=self.approval_id,
            action_request_id=self.action_request_id,
            channel=self.channel,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class NotificationDeliverySummary:
    notification_request_id: str
    plugin_id: str
    accepted: bool
    retryable: bool
    code: str
    message: str
    approval_id: str
    action_request_id: str
    channel: str
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "notification_request_id",
            "plugin_id",
            "code",
            "message",
            "approval_id",
            "action_request_id",
            "channel",
        ):
            _require_non_empty(field_name, getattr(self, field_name))
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted must be a bool.")
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be a bool.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="publish"))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "notification_request_id": self.notification_request_id,
            "plugin_id": self.plugin_id,
            "accepted": self.accepted,
            "retryable": self.retryable,
            "code": self.code,
            "message": self.message,
            "approval_id": self.approval_id,
            "action_request_id": self.action_request_id,
            "channel": self.channel,
            "metadata": to_json_value(self.metadata),
        }

    @classmethod
    def from_dispatch_result(cls, result: NotificationDispatchResult) -> "NotificationDeliverySummary":
        return result.to_delivery_summary()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "NotificationDeliverySummary":
        return cls(
            notification_request_id=_required_string(payload, "notification_request_id"),
            plugin_id=_required_string(payload, "plugin_id"),
            accepted=_required_bool(payload, "accepted"),
            retryable=_required_bool(payload, "retryable"),
            code=_required_string(payload, "code"),
            message=_required_string(payload, "message"),
            approval_id=_required_string(payload, "approval_id"),
            action_request_id=_required_string(payload, "action_request_id"),
            channel=_required_string(payload, "channel"),
            metadata=freeze_json_mapping(_optional_mapping(payload.get("metadata")), stage="publish"),
        )


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


def _required_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _required_bool(payload: Mapping[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a bool.")
    return value


def _optional_mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be a JSON object.")
    return value
