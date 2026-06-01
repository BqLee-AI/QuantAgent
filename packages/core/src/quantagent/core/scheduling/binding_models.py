from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping

from quantagent.core.scheduling.models import PluginRunStatus


class SourceBindingStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass(frozen=True)
class CreateSourceBindingInput:
    binding_id: str
    owner_type: str
    owner_id: str
    source_plugin_id: str
    source_plugin_version: str | None = None
    effective_config_snapshot: JsonObject = field(default_factory=dict)
    schedule_policy: JsonObject = field(default_factory=dict)
    retry_policy: JsonObject = field(default_factory=dict)
    rate_limit_policy: JsonObject = field(default_factory=dict)
    status: SourceBindingStatus = SourceBindingStatus.ACTIVE
    next_run_at: datetime | None = None
    created_by: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("binding_id", self.binding_id)
        _require_non_empty("owner_type", self.owner_type)
        _require_non_empty("owner_id", self.owner_id)
        _require_non_empty("source_plugin_id", self.source_plugin_id)
        object.__setattr__(self, "effective_config_snapshot", freeze_json_mapping(self.effective_config_snapshot, stage="config"))
        object.__setattr__(self, "schedule_policy", freeze_json_mapping(self.schedule_policy, stage="schedule_precheck"))
        object.__setattr__(self, "retry_policy", freeze_json_mapping(self.retry_policy, stage="schedule_precheck"))
        object.__setattr__(self, "rate_limit_policy", freeze_json_mapping(self.rate_limit_policy, stage="schedule_precheck"))


@dataclass(frozen=True)
class SourceBindingRecord:
    binding_id: str
    owner_type: str
    owner_id: str
    source_plugin_id: str
    source_plugin_version: str | None
    effective_config_snapshot: JsonObject
    schedule_policy: JsonObject
    retry_policy: JsonObject
    rate_limit_policy: JsonObject
    status: SourceBindingStatus
    last_run_id: str | None
    last_run_status: PluginRunStatus | None
    last_run_at: datetime | None
    last_success_at: datetime | None
    next_run_at: datetime | None
    last_heartbeat_at: datetime | None
    consecutive_failure_count: int
    disabled_reason: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None


def _require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
