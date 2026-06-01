from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping


class WorkerRouteStatus(StrEnum):
    ROUTED = "routed"
    IGNORED = "ignored"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class ConsumerDisposition(StrEnum):
    ACK_AND_RECORD_FAILURE = "ack_and_record_failure"
    ACK_AND_RECORD_IGNORED = "ack_and_record_ignored"
    ACK_AND_RECORD_DUPLICATE = "ack_and_record_duplicate"
    NACK_OR_SCHEDULE_RETRY = "nack_or_schedule_retry"
    ACK_AND_RECORD_ROUTED = "ack_and_record_routed"


@dataclass(frozen=True)
class CapturedSourceEventInput:
    message_id: str
    topic: str
    binding_id: str | None
    request_id: str | None
    plugin_id: str | None
    item_count: int
    correlation_id: str | None
    causation_id: str | None
    payload: JsonObject = field(default_factory=dict)
    headers: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze_json_mapping(self.payload, stage="decode"))
        object.__setattr__(self, "headers", freeze_json_mapping(self.headers, stage="decode"))


@dataclass(frozen=True)
class IndustryEntrypointRef:
    owner_type: str
    owner_id: str
    binding_id: str


@dataclass(frozen=True)
class IndustryGatewayResult:
    status: str
    reason_code: str | None
    target_ref: str
    attempted_at: str
    error_summary: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "error_summary", freeze_json_mapping(self.error_summary, stage="publish"))


@dataclass(frozen=True)
class WorkerRouteResult:
    message_id: str
    binding_id: str | None
    status: WorkerRouteStatus
    consumer_disposition: ConsumerDisposition
    retryable: bool
    audit_required: bool
    reason_code: str | None
    owner_type: str | None = None
    owner_id: str | None = None
    route_target: str | None = None
    request_id: str | None = None
    plugin_id: str | None = None
    audit_payload: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "audit_payload", freeze_json_mapping(self.audit_payload, stage="publish"))


@dataclass(frozen=True)
class WorkerRouteAuditEntry:
    message_id: str
    binding_id: str | None
    status: WorkerRouteStatus
    consumer_disposition: ConsumerDisposition
    retryable: bool
    reason_code: str | None
    payload: JsonObject
    recorded_at: str


def build_audit_entry(result: WorkerRouteResult) -> WorkerRouteAuditEntry:
    return WorkerRouteAuditEntry(
        message_id=result.message_id,
        binding_id=result.binding_id,
        status=result.status,
        consumer_disposition=result.consumer_disposition,
        retryable=result.retryable,
        reason_code=result.reason_code,
        payload=result.audit_payload,
        recorded_at=datetime.now(UTC).isoformat(),
    )
