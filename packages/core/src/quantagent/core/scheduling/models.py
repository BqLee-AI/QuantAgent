from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping


class PluginTriggerType(StrEnum):
    MANUAL = "manual"
    INTERVAL = "interval"


class PluginRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class PluginTriggerRequest:
    plugin_id: str
    capability: str
    request_id: str
    trigger_type: PluginTriggerType
    input: JsonObject = field(default_factory=dict)
    effective_config: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)
    binding_id: str | None = None
    timeout_ms: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty("plugin_id", self.plugin_id)
        _require_non_empty("capability", self.capability)
        _require_non_empty("request_id", self.request_id)
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than zero when provided.")
        if self.binding_id is not None:
            _require_non_empty("binding_id", self.binding_id)
        object.__setattr__(self, "input", freeze_json_mapping(self.input, stage="invoke"))
        object.__setattr__(self, "effective_config", freeze_json_mapping(self.effective_config, stage="config"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="schedule_precheck"))


@dataclass(frozen=True)
class PluginRunRecord:
    run_id: str
    plugin_id: str
    plugin_version: str | None
    capability: str
    request_id: str
    trigger_type: PluginTriggerType
    status: PluginRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    timeout_ms: int | None = None
    output_summary: JsonObject = field(default_factory=dict)
    error_summary: JsonObject | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("run_id", self.run_id)
        _require_non_empty("plugin_id", self.plugin_id)
        _require_non_empty("capability", self.capability)
        _require_non_empty("request_id", self.request_id)
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than zero when provided.")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must not be negative.")
        object.__setattr__(self, "output_summary", freeze_json_mapping(self.output_summary, stage="invoke"))
        if self.error_summary is not None:
            object.__setattr__(self, "error_summary", freeze_json_mapping(self.error_summary, stage="invoke"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="schedule_precheck"))


@dataclass(frozen=True)
class IntervalSchedulePolicy:
    interval_seconds: int
    jitter_seconds: int = 0
    enabled: bool = True
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero.")
        if self.jitter_seconds < 0:
            raise ValueError("jitter_seconds must not be negative.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata, stage="schedule_precheck"))

    def next_run_at(self, reference_time: datetime, *, applied_jitter_seconds: int = 0) -> datetime | None:
        if not self.enabled:
            return None
        if applied_jitter_seconds < 0 or applied_jitter_seconds > self.jitter_seconds:
            raise ValueError("applied_jitter_seconds must be within the configured jitter window.")
        return reference_time + timedelta(seconds=self.interval_seconds + applied_jitter_seconds)

    def build_trigger_request(
        self,
        *,
        plugin_id: str,
        capability: str,
        request_id: str,
        effective_config: Mapping[str, object] | None = None,
        input_payload: Mapping[str, object] | None = None,
        metadata: Mapping[str, object] | None = None,
        binding_id: str | None = None,
        timeout_ms: int | None = None,
    ) -> PluginTriggerRequest:
        merged_metadata = dict(self.metadata)
        merged_metadata.update(metadata or {})
        return PluginTriggerRequest(
            plugin_id=plugin_id,
            capability=capability,
            request_id=request_id,
            trigger_type=PluginTriggerType.INTERVAL,
            input=input_payload or {},
            effective_config=effective_config or {},
            metadata=merged_metadata,
            binding_id=binding_id,
            timeout_ms=timeout_ms,
        )


def _require_non_empty(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
