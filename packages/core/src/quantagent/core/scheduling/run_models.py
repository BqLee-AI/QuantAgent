from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping

from quantagent.core.scheduling.models import PluginRunStatus, PluginTriggerType


@dataclass(frozen=True)
class SchedulerRunRecord:
    run_id: str
    binding_id: str
    source_plugin_id: str
    source_plugin_version: str | None
    trigger_mode: PluginTriggerType
    request_id: str
    status: PluginRunStatus
    attempt_index: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    timeout_ms: int | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failure_stage: str | None = None
    retryable: bool | None = None
    output_summary: JsonObject = field(default_factory=dict)
    captured_count: int | None = None
    metadata: JsonObject = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty("run_id", self.run_id)
        _require_non_empty("binding_id", self.binding_id)
        _require_non_empty("source_plugin_id", self.source_plugin_id)
        _require_non_empty("request_id", self.request_id)
        if self.attempt_index is not None and self.attempt_index < 0:
            raise ValueError("attempt_index must not be negative.")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must not be negative.")
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than zero when provided.")
        object.__setattr__(self, "output_summary", freeze_json_mapping(self.output_summary, stage="invoke"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="schedule_precheck"))


def _require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
