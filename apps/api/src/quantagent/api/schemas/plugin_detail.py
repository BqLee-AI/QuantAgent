from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AvailabilityStateValue = Literal[
    "ready",
    "not_configured",
    "not_collected",
    "forbidden",
    "unavailable",
    "degraded",
]
ConfigStateValue = Literal["valid", "invalid", "missing_required", "not_configured", "unavailable"]
ConfigDisplayModeValue = Literal["plain", "masked", "reference", "unset"]
DependencyKindValue = Literal["plugin", "python", "system", "reverse_plugin"]
DependencyResolvedStateValue = Literal["resolved", "missing", "blocked", "not_collected"]
CapabilityRiskLevelValue = Literal["low", "medium", "high"]
HealthStatusValue = Literal["healthy", "degraded", "failed", "not_collected", "unavailable"]
PluginActionValue = Literal["enable", "disable", "reload", "rescan", "uninstall"]


class SectionAvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: AvailabilityStateValue
    reason_code: str | None = None
    message: str | None = None


class PluginErrorSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class PluginOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    description: str | None = None
    installed_version: str | None = None
    active_version: str | None = None
    status: str = Field(min_length=1)
    active_config_state: ConfigStateValue
    blocked_reason: str | None = None
    last_error_summary: PluginErrorSummaryResponse | None = None


class PluginConfigSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    schema_version: str | None = None
    config_state: ConfigStateValue
    missing_required_count: int = Field(ge=0)
    masked_sensitive_count: int = Field(ge=0)
    last_validated_at: str | None = None
    last_updated_at: str | None = None
    reload_required: bool


class PluginConfigSchemaInfoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    schema_version: str | None = None
    schema_ref: str | None = None


class PluginConfigEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    display_mode: ConfigDisplayModeValue
    display_value: str | None = None
    is_sensitive: bool
    is_required: bool
    is_overridden: bool


class PluginConfigViewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    schema_: PluginConfigSchemaInfoResponse | None = Field(default=None, alias="schema")
    config_state: ConfigStateValue
    entries: list[PluginConfigEntryResponse] = Field(default_factory=list)
    last_validated_at: str | None = None
    last_updated_at: str | None = None
    reload_required: bool


class PluginDependencySummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    required_count: int = Field(ge=0)
    optional_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    blocked_reason_summary: str | None = None
    reverse_dependency_count: int = Field(ge=0)


class PluginDependencyRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    kind: DependencyKindValue
    required: bool
    resolved_state: DependencyResolvedStateValue
    blocked_reason: str | None = None
    version_range: str | None = None


class PluginDependenciesViewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    plugin_dependencies: list[PluginDependencyRecordResponse] = Field(default_factory=list)
    python_dependencies: list[PluginDependencyRecordResponse] = Field(default_factory=list)
    system_dependencies: list[PluginDependencyRecordResponse] = Field(default_factory=list)
    reverse_dependencies: list[PluginDependencyRecordResponse] = Field(default_factory=list)


class PluginCapabilityRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    risk_level: CapabilityRiskLevelValue
    requires_policy_gate: bool
    requires_approval: bool
    availability_state: AvailabilityStateValue


class PluginCapabilitiesViewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    declared_capabilities: list[PluginCapabilityRecordResponse] = Field(default_factory=list)
    risk_level_summary: CapabilityRiskLevelValue
    requires_policy_gate: bool
    requires_approval: bool
    provided_objects_summary: dict[str, Any] = Field(default_factory=dict)


class PluginHealthSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    status: HealthStatusValue
    last_check_at: str | None = None
    degraded_reason: str | None = None
    last_error_summary: PluginErrorSummaryResponse | None = None
    latest_runtime_failure_ref: str | None = None
    recent_runtime_error_count: int = Field(ge=0)
    last_used_at: str | None = None


class PluginHealthViewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    status: HealthStatusValue
    last_check_at: str | None = None
    degraded_reason: str | None = None
    last_error_summary: PluginErrorSummaryResponse | None = None
    latest_runtime_failure_ref: str | None = None
    recent_runtime_error_count: int = Field(ge=0)
    last_used_at: str | None = None
    runtime_error_refs: list[str] = Field(default_factory=list)
    recent_usage_summary: dict[str, Any] = Field(default_factory=dict)
    health_checks: list[dict[str, Any]] = Field(default_factory=list)


class PluginAuditSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    last_changed_at: str | None = None
    last_actor: str | None = None
    recent_action_types: list[str] = Field(default_factory=list)
    latest_audit_ref: str | None = None


class PluginAuditEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    result: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)
    safe_details: dict[str, Any] = Field(default_factory=dict)


class PluginAuditViewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    entries: list[PluginAuditEntryResponse] = Field(default_factory=list)


class PluginOpsSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: SectionAvailabilityResponse
    operable_state: str = Field(min_length=1)
    action_blockers: list[str] = Field(default_factory=list)
    requires_confirmation: bool
    high_risk_actions: list[str] = Field(default_factory=list)


class PluginActionHintResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: PluginActionValue
    allowed: bool
    disabled_reason: str | None = None
    requires_confirmation: bool


class PluginActionStateHintResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: PluginActionValue
    state: AvailabilityStateValue
    reason_code: str | None = None
    message: str | None = None


class PluginRelatedResourcesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: str = Field(min_length=1)
    config_schema: str = Field(min_length=1)
    dependencies: str = Field(min_length=1)
    health: str = Field(min_length=1)
    audit: str = Field(min_length=1)


class PluginDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: PluginOverviewResponse
    config_summary: PluginConfigSummaryResponse
    dependency_summary: PluginDependencySummaryResponse
    capabilities: PluginCapabilitiesViewResponse
    health_summary: PluginHealthSummaryResponse
    audit_summary: PluginAuditSummaryResponse
    ops_summary: PluginOpsSummaryResponse
    allowed_actions: list[PluginActionHintResponse] = Field(default_factory=list)
    action_state_hints: list[PluginActionStateHintResponse] = Field(default_factory=list)
    related_resources: PluginRelatedResourcesResponse
