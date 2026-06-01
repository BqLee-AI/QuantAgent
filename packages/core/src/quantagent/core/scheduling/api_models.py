from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping

from quantagent.core.scheduling.binding_models import SourceBindingStatus
from quantagent.core.scheduling.models import PluginRunStatus, PluginTriggerType


@dataclass(frozen=True)
class CursorPage:
    items: tuple[object, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class SourceBindingQuery:
    owner_type: str | None = None
    owner_id: str | None = None
    source_plugin_id: str | None = None
    status: SourceBindingStatus | None = None
    cursor: str | None = None
    limit: int = 50


@dataclass(frozen=True)
class SchedulerRunQuery:
    binding_id: str | None = None
    status: PluginRunStatus | None = None
    trigger_mode: PluginTriggerType | None = None
    started_after: datetime | None = None
    started_before: datetime | None = None
    cursor: str | None = None
    limit: int = 50


@dataclass(frozen=True)
class SourceBindingRunRef:
    run_id: str
    status: PluginRunStatus
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class EffectiveConfigSummary:
    values: JsonObject = field(default_factory=dict)
    secret_fields_masked: tuple[str, ...] = ()
    last_validated_at: str | None = None
    config_source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", freeze_json_mapping(self.values, stage="config"))
        object.__setattr__(self, "secret_fields_masked", tuple(self.secret_fields_masked))
        object.__setattr__(self, "config_source_refs", tuple(self.config_source_refs))


@dataclass(frozen=True)
class SourceBindingSummaryView:
    id: str
    source_plugin_id: str
    owner_type: str
    owner_id: str
    status: SourceBindingStatus
    blocked_reason: str | None
    schedule_summary: JsonObject
    last_run_ref: SourceBindingRunRef | None
    next_run_at: datetime | None
    health_summary: JsonObject
    allowed_actions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "schedule_summary", freeze_json_mapping(self.schedule_summary, stage="schedule_precheck"))
        object.__setattr__(self, "health_summary", freeze_json_mapping(self.health_summary, stage="schedule_precheck"))
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))


@dataclass(frozen=True)
class SourceBindingDetailView:
    summary: SourceBindingSummaryView
    effective_config_summary: EffectiveConfigSummary
    config_version: str
    config_validation_status: str
    rate_limit_policy_summary: JsonObject
    retry_policy_summary: JsonObject
    last_error_summary: JsonObject
    audit_refs: tuple[str, ...]
    recent_run_refs: tuple[SourceBindingRunRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rate_limit_policy_summary", freeze_json_mapping(self.rate_limit_policy_summary, stage="schedule_precheck"))
        object.__setattr__(self, "retry_policy_summary", freeze_json_mapping(self.retry_policy_summary, stage="schedule_precheck"))
        object.__setattr__(self, "last_error_summary", freeze_json_mapping(self.last_error_summary, stage="invoke"))
        object.__setattr__(self, "audit_refs", tuple(self.audit_refs))
        object.__setattr__(self, "recent_run_refs", tuple(self.recent_run_refs))


@dataclass(frozen=True)
class SchedulerRunSummaryView:
    id: str
    binding_id: str
    source_plugin_id: str
    trigger_mode: PluginTriggerType
    status: PluginRunStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    attempt_index: int | None
    captured_count: int | None
    failure_summary: JsonObject

    def __post_init__(self) -> None:
        object.__setattr__(self, "failure_summary", freeze_json_mapping(self.failure_summary, stage="invoke"))


@dataclass(frozen=True)
class SchedulerRunDetailView:
    summary: SchedulerRunSummaryView
    request_id: str
    actor: JsonObject
    correlation_id: str | None
    binding_snapshot_ref: str
    output_summary: JsonObject
    error_code: str | None
    error_stage: str | None
    error_retryable: bool | None
    audit_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor", freeze_json_mapping(self.actor, stage="schedule_precheck"))
        object.__setattr__(self, "output_summary", freeze_json_mapping(self.output_summary, stage="invoke"))


@dataclass(frozen=True)
class SourceBindingStateActionAccepted:
    binding_id: str
    target_state: SourceBindingStatus
    already_in_target_state: bool
    accepted_at: datetime
    audit_ref: str


@dataclass(frozen=True)
class SourceBindingRunNowAccepted:
    binding_id: str
    accepted_at: datetime
    request_id: str
    requested_run_ref: str
    audit_ref: str


def page_items(page: CursorPage, item_type: type) -> tuple[object, ...]:
    return tuple(item for item in page.items if isinstance(item, item_type))


def build_recent_run_refs(items: Sequence[SchedulerRunSummaryView]) -> tuple[SourceBindingRunRef, ...]:
    return tuple(
        SourceBindingRunRef(
            run_id=item.id,
            status=item.status,
            started_at=item.started_at,
            finished_at=item.finished_at,
        )
        for item in items
    )
