from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import hashlib
import json

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping, to_json_value

_MASKED = "[masked]"
_SENSITIVE_KEYWORDS = (
    "api_key",
    "authorization",
    "broker_credential",
    "cookie",
    "credential",
    "password",
    "private_policy",
    "prompt",
    "raw_response",
    "secret",
    "token",
)


class EventIdentityKind(StrEnum):
    RAW_EVENT_ID = "raw_event_id"
    ROUTED_EVENT_ID = "routed_event_id"
    EXTERNAL = "external"


class EventCurrentStatus(StrEnum):
    CAPTURED = "captured"
    ROUTED = "routed"
    ANALYZING = "analyzing"
    SCORED = "scored"
    DECISION_READY = "decision_ready"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"
    DISCARDED = "discarded"


class EventAnalysisStatus(StrEnum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    SCORED = "scored"
    DECISION_READY = "decision_ready"
    PENDING_APPROVAL = "pending_approval"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"
    UNAVAILABLE = "unavailable"


class EventCredibility(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class EventSourceType(StrEnum):
    RSS = "rss"
    API = "api"
    WEBHOOK = "webhook"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class EventRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class EventRiskDirection(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class EventSectionStatus(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class EventSortMode(StrEnum):
    MIXED = "mixed"
    LATEST = "latest"
    PRIORITY = "priority"


class EventTimeRange(StrEnum):
    TODAY = "today"
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"

    def resolve_start(self, *, now: datetime) -> datetime:
        resolved_now = now.astimezone(UTC)
        if self is EventTimeRange.TODAY:
            return resolved_now.replace(hour=0, minute=0, second=0, microsecond=0)
        if self is EventTimeRange.LAST_24H:
            return resolved_now - timedelta(hours=24)
        if self is EventTimeRange.LAST_7D:
            return resolved_now - timedelta(days=7)
        return resolved_now - timedelta(days=30)


@dataclass(frozen=True)
class EventSummaryBuckets:
    new_count: int
    featured_count: int
    analyzing_count: int
    failed_or_review_count: int
    pending_approval_count: int | None = None


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    schema_version: str
    title: str
    summary: str | None
    source_name: str | None
    source_type: str | None
    source_url: str | None
    source_authority: str | None
    published_at: datetime | None
    captured_at: datetime
    current_status: str
    analysis_status: str
    credibility: str | None
    priority_score: float | None
    recommendation_score: float | None
    confidence: float | None
    risk_level: str | None
    risk_direction: str | None
    industries: tuple[str, ...] = field(default_factory=tuple)
    entities: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    featured_reason: str | None = None
    is_featured: bool = False
    raw_event_id: str | None = None
    routed_event_id: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    identity_kind: str = EventIdentityKind.EXTERNAL.value
    identity_value: str = ""
    version: int = 1
    latest_agent_run_id: str | None = None
    latest_tool_invocation_id: str | None = None
    approval_id: str | None = None
    degradation_notices: tuple[JsonObject, ...] = field(default_factory=tuple)
    evidence_summary: JsonObject = field(default_factory=dict)
    industry_impact_summary: JsonObject = field(default_factory=dict)
    best_action_summary: JsonObject = field(default_factory=dict)
    audit_refs: tuple[JsonObject, ...] = field(default_factory=tuple)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class EventStateTransitionRecord:
    transition_id: str
    event_id: str
    from_status: str | None
    to_status: str
    reason_code: str | None
    reason_summary: str | None
    actor_type: str
    actor_id: str | None
    source_ref: JsonObject = field(default_factory=dict)
    request_id: str | None = None
    trace_id: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class EventStateSummaryView:
    current_status: str
    analysis_status: str
    version: int
    transitions: tuple[EventStateTransitionRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EventDetailView:
    event: EventRecord
    state_summary: EventStateSummaryView


@dataclass(frozen=True)
class EventDashboardSnapshot:
    featured_events: tuple[EventRecord, ...]
    entry_metrics: EventSummaryBuckets
    generated_at: datetime


@dataclass(frozen=True)
class EventListQuery:
    time_range: EventTimeRange = EventTimeRange.LAST_24H
    industries: tuple[str, ...] = field(default_factory=tuple)
    credibility: str | None = None
    analysis_status: str | None = None
    source_type: str | None = None
    sort: EventSortMode = EventSortMode.MIXED
    cursor: str | None = None
    limit: int = 20
    captured_from: datetime | None = None


@dataclass(frozen=True)
class EventListPage:
    items: tuple[EventRecord, ...]
    next_cursor: str | None
    buckets: EventSummaryBuckets
    generated_at: datetime


@dataclass(frozen=True)
class EventMaterializationInput:
    identity_kind: EventIdentityKind
    identity_value: str
    title: str
    current_status: EventCurrentStatus
    analysis_status: EventAnalysisStatus
    schema_version: str = "event_read_model.v1"
    summary: str | None = None
    source_name: str | None = None
    source_type: EventSourceType | None = None
    source_url: str | None = None
    source_authority: str | None = None
    published_at: datetime | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    credibility: EventCredibility | None = None
    priority_score: float | None = None
    recommendation_score: float | None = None
    confidence: float | None = None
    risk_level: EventRiskLevel | None = None
    risk_direction: EventRiskDirection | None = None
    industries: tuple[str, ...] = field(default_factory=tuple)
    entities: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    featured_reason: str | None = None
    is_featured: bool = False
    raw_event_id: str | None = None
    routed_event_id: str | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    latest_agent_run_id: str | None = None
    latest_tool_invocation_id: str | None = None
    approval_id: str | None = None
    degradation_notices: tuple[JsonObject, ...] = field(default_factory=tuple)
    evidence_summary: JsonObject = field(default_factory=dict)
    industry_impact_summary: JsonObject = field(default_factory=dict)
    best_action_summary: JsonObject = field(default_factory=dict)
    audit_refs: tuple[JsonObject, ...] = field(default_factory=tuple)
    reason_code: str | None = None
    reason_summary: str | None = None
    actor_type: str = "system"
    actor_id: str | None = None
    source_ref: JsonObject = field(default_factory=dict)
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not self.identity_value.strip():
            raise ValueError("identity_value must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        object.__setattr__(self, "source_ref", _freeze_public_mapping(self.source_ref))
        object.__setattr__(self, "evidence_summary", _freeze_public_mapping(self.evidence_summary))
        object.__setattr__(self, "industry_impact_summary", _freeze_public_mapping(self.industry_impact_summary))
        object.__setattr__(self, "best_action_summary", _freeze_public_mapping(self.best_action_summary))
        object.__setattr__(
            self,
            "degradation_notices",
            tuple(_freeze_public_mapping(item) for item in self.degradation_notices),
        )
        object.__setattr__(self, "audit_refs", tuple(_freeze_public_mapping(item) for item in self.audit_refs))
        object.__setattr__(self, "industries", tuple(item.strip() for item in self.industries if item and item.strip()))
        object.__setattr__(self, "entities", tuple(item.strip() for item in self.entities if item and item.strip()))
        object.__setattr__(self, "tags", tuple(item.strip() for item in self.tags if item and item.strip()))


@dataclass(frozen=True)
class EventMaterializationResult:
    event_id: str
    created: bool
    previous_status: str | None
    current_status: str
    transition_id: str | None
    degradation_notices: tuple[JsonObject, ...] = field(default_factory=tuple)


def derive_event_id(*, identity_kind: EventIdentityKind, identity_value: str) -> str:
    stable_key = f"{identity_kind.value}:{identity_value.strip()}".encode("utf-8")
    return f"evt_{hashlib.sha256(stable_key).hexdigest()[:24]}"


def encode_event_cursor(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_event_cursor(cursor: str | None) -> dict[str, object] | None:
    if cursor is None:
        return None
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("event cursor is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("event cursor is invalid")
    return payload


def freeze_public_json_sequence(values: Sequence[Mapping[str, object]]) -> tuple[JsonObject, ...]:
    return tuple(_freeze_public_mapping(item) for item in values)


def _freeze_public_mapping(payload: Mapping[str, object]) -> JsonObject:
    redacted = _redact_public_json(to_json_value(freeze_json_mapping(payload, stage="event_read_model")))
    return redacted if isinstance(redacted, dict) else {}


def _redact_public_json(value: object, *, key: str | None = None) -> object:
    if key is not None and _is_sensitive_key(key):
        return _MASKED
    if isinstance(value, Mapping):
        return {
            str(item_key): _redact_public_json(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_public_json(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(item in normalized for item in _SENSITIVE_KEYWORDS)
