from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class SectionAvailabilityState(StrEnum):
    READY = "ready"
    NOT_CONFIGURED = "not_configured"
    NOT_COLLECTED = "not_collected"
    FORBIDDEN = "forbidden"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class ConfigDisplayMode(StrEnum):
    PLAIN = "plain"
    MASKED = "masked"
    REFERENCE = "reference"
    UNSET = "unset"


class DependencyKind(StrEnum):
    PLUGIN = "plugin"
    PYTHON = "python"
    SYSTEM = "system"
    REVERSE_PLUGIN = "reverse_plugin"


class DependencyResolvedState(StrEnum):
    RESOLVED = "resolved"
    MISSING = "missing"
    BLOCKED = "blocked"
    NOT_COLLECTED = "not_collected"


class CapabilityRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    NOT_COLLECTED = "not_collected"
    UNAVAILABLE = "unavailable"


class ConfigState(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    MISSING_REQUIRED = "missing_required"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SectionAvailability:
    state: SectionAvailabilityState
    reason_code: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class PluginErrorSummary:
    code: str
    message: str
    stage: str
    details: Mapping[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))


@dataclass(frozen=True)
class PluginOverview:
    plugin_id: str
    name: str
    plugin_type: str
    source: str
    description: str | None
    installed_version: str | None
    active_version: str | None
    status: str
    active_config_state: ConfigState
    blocked_reason: str | None = None
    last_error_summary: PluginErrorSummary | None = None


@dataclass(frozen=True)
class PluginConfigSchemaInfo:
    title: str | None
    schema_version: str | None
    schema_ref: str | None


@dataclass(frozen=True)
class PluginConfigEntry:
    key: str
    display_mode: ConfigDisplayMode
    display_value: str | None
    is_sensitive: bool
    is_required: bool
    is_overridden: bool


@dataclass(frozen=True)
class PluginConfigSummary:
    availability: SectionAvailability
    schema_version: str | None
    config_state: ConfigState
    missing_required_count: int
    masked_sensitive_count: int
    last_validated_at: str | None
    last_updated_at: str | None
    reload_required: bool


@dataclass(frozen=True)
class PluginConfigView:
    availability: SectionAvailability
    schema: PluginConfigSchemaInfo | None
    config_state: ConfigState
    entries: tuple[PluginConfigEntry, ...]
    last_validated_at: str | None
    last_updated_at: str | None
    reload_required: bool


@dataclass(frozen=True)
class PluginDependencyRecord:
    name: str
    kind: DependencyKind
    required: bool
    resolved_state: DependencyResolvedState
    blocked_reason: str | None = None
    version_range: str | None = None


@dataclass(frozen=True)
class PluginDependencySummary:
    availability: SectionAvailability
    required_count: int
    optional_count: int
    missing_count: int
    blocked_reason_summary: str | None
    reverse_dependency_count: int


@dataclass(frozen=True)
class PluginDependenciesView:
    availability: SectionAvailability
    plugin_dependencies: tuple[PluginDependencyRecord, ...]
    python_dependencies: tuple[PluginDependencyRecord, ...]
    system_dependencies: tuple[PluginDependencyRecord, ...]
    reverse_dependencies: tuple[PluginDependencyRecord, ...]


@dataclass(frozen=True)
class PluginCapabilityRecord:
    name: str
    kind: str
    risk_level: CapabilityRiskLevel
    requires_policy_gate: bool
    requires_approval: bool
    availability_state: SectionAvailabilityState


@dataclass(frozen=True)
class PluginCapabilitiesView:
    availability: SectionAvailability
    declared_capabilities: tuple[PluginCapabilityRecord, ...]
    risk_level_summary: CapabilityRiskLevel
    requires_policy_gate: bool
    requires_approval: bool
    provided_objects_summary: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provided_objects_summary", MappingProxyType(dict(self.provided_objects_summary)))


@dataclass(frozen=True)
class PluginHealthSummary:
    availability: SectionAvailability
    status: HealthStatus
    last_check_at: str | None
    degraded_reason: str | None
    last_error_summary: PluginErrorSummary | None
    latest_runtime_failure_ref: str | None
    recent_runtime_error_count: int
    last_used_at: str | None


@dataclass(frozen=True)
class PluginHealthView:
    availability: SectionAvailability
    status: HealthStatus
    last_check_at: str | None
    degraded_reason: str | None
    last_error_summary: PluginErrorSummary | None
    latest_runtime_failure_ref: str | None
    recent_runtime_error_count: int
    last_used_at: str | None
    runtime_error_refs: tuple[str, ...]
    recent_usage_summary: Mapping[str, Any] = field(default_factory=dict)
    health_checks: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_error_refs", tuple(self.runtime_error_refs))
        object.__setattr__(self, "recent_usage_summary", MappingProxyType(dict(self.recent_usage_summary)))
        object.__setattr__(
            self,
            "health_checks",
            tuple(MappingProxyType(dict(item)) for item in self.health_checks),
        )


@dataclass(frozen=True)
class PluginAuditSummary:
    availability: SectionAvailability
    last_changed_at: str | None
    last_actor: str | None
    recent_action_types: tuple[str, ...]
    latest_audit_ref: str | None


@dataclass(frozen=True)
class PluginAuditEntry:
    audit_id: str
    action: str
    actor: str
    result: str
    occurred_at: str
    safe_details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "safe_details", MappingProxyType(dict(self.safe_details)))


@dataclass(frozen=True)
class PluginAuditView:
    availability: SectionAvailability
    entries: tuple[PluginAuditEntry, ...]


@dataclass(frozen=True)
class PluginOpsSummary:
    availability: SectionAvailability
    operable_state: str
    action_blockers: tuple[str, ...]
    requires_confirmation: bool
    high_risk_actions: tuple[str, ...]


@dataclass(frozen=True)
class PluginDetailSnapshot:
    overview: PluginOverview
    config_summary: PluginConfigSummary
    config_view: PluginConfigView
    dependency_summary: PluginDependencySummary
    dependencies_view: PluginDependenciesView
    capabilities_view: PluginCapabilitiesView
    health_summary: PluginHealthSummary
    health_view: PluginHealthView
    audit_summary: PluginAuditSummary
    audit_view: PluginAuditView
    ops_summary: PluginOpsSummary
