from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from quantagent.core.registry.detail_models import (
    CapabilityRiskLevel,
    ConfigDisplayMode,
    ConfigState,
    DependencyKind,
    DependencyResolvedState,
    HealthStatus,
    PluginAuditSummary,
    PluginAuditView,
    PluginCapabilitiesView,
    PluginCapabilityRecord,
    PluginConfigEntry,
    PluginConfigSchemaInfo,
    PluginConfigSummary,
    PluginConfigView,
    PluginDependenciesView,
    PluginDependencyRecord,
    PluginDependencySummary,
    PluginDetailSnapshot,
    PluginErrorSummary,
    PluginHealthSummary,
    PluginHealthView,
    PluginOpsSummary,
    PluginOverview,
    SectionAvailability,
    SectionAvailabilityState,
)
from quantagent.core.registry.models import PluginError, PluginManifest, PluginRecord, PluginSource, PluginStatus, PluginType
from quantagent.core.registry.service import PluginRegistry


class PluginDetailReadService:
    """组装 Plugin Detail 只读快照，不引入 HTTP、鉴权或前端展示语义。"""

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def get_plugin_detail(self, plugin_id: str) -> PluginDetailSnapshot | None:
        record = self._registry.get_plugin(plugin_id)
        if record is None:
            return None
        all_records = self._registry.list_plugins()
        config_view = self._build_config_view(record)
        dependencies_view = self._build_dependencies_view(record, all_records)
        capabilities_view = self._build_capabilities_view(record)
        health_view = self._build_health_view(record)
        audit_view = self._build_audit_view(record)
        ops_summary = self._build_ops_summary(record)
        return PluginDetailSnapshot(
            overview=self._build_overview(record, config_view.config_state),
            config_summary=self._build_config_summary(config_view),
            config_view=config_view,
            dependency_summary=self._build_dependency_summary(dependencies_view),
            dependencies_view=dependencies_view,
            capabilities_view=capabilities_view,
            health_summary=self._build_health_summary(health_view),
            health_view=health_view,
            audit_summary=self._build_audit_summary(audit_view),
            audit_view=audit_view,
            ops_summary=ops_summary,
        )

    def _build_overview(self, record: PluginRecord, config_state: ConfigState) -> PluginOverview:
        manifest = record.manifest
        return PluginOverview(
            plugin_id=record.id,
            name=manifest.name if manifest is not None else record.id,
            plugin_type=manifest.type.value if manifest is not None else "unknown",
            source=record.source.value,
            description=manifest.description if manifest is not None else None,
            installed_version=manifest.version if manifest is not None else None,
            active_version=manifest.version if manifest is not None and record.status == PluginStatus.VALID else None,
            status=record.status.value,
            active_config_state=config_state,
            blocked_reason=_blocked_reason(record),
            last_error_summary=_error_summary(record.last_error),
        )

    def _build_config_view(self, record: PluginRecord) -> PluginConfigView:
        if record.manifest is None or record.config_schema_path is None:
            return PluginConfigView(
                availability=SectionAvailability(
                    state=SectionAvailabilityState.UNAVAILABLE,
                    reason_code="config_schema_unavailable",
                    message="plugin manifest or config schema is unavailable",
                ),
                schema=None,
                config_state=ConfigState.UNAVAILABLE,
                entries=(),
                last_validated_at=None,
                last_updated_at=None,
                reload_required=False,
            )

        schema = self._registry.read_config_schema(record.id)
        if schema is None:
            return PluginConfigView(
                availability=SectionAvailability(
                    state=SectionAvailabilityState.UNAVAILABLE,
                    reason_code="config_schema_unreadable",
                    message="plugin config schema could not be read safely",
                ),
                schema=PluginConfigSchemaInfo(
                    title=None,
                    schema_version=None,
                    schema_ref=None,
                ),
                config_state=ConfigState.UNAVAILABLE,
                entries=(),
                last_validated_at=None,
                last_updated_at=None,
                reload_required=False,
            )

        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required_fields = {
            item
            for item in schema.get("required", [])
            if isinstance(item, str) and item.strip()
        }
        entries = tuple(
            PluginConfigEntry(
                key=key,
                display_mode=ConfigDisplayMode.UNSET,
                display_value=None,
                is_sensitive=_is_sensitive_field(key, value),
                is_required=key in required_fields,
                is_overridden=False,
            )
            for key, value in sorted(properties.items())
            if isinstance(key, str) and isinstance(value, Mapping)
        )
        return PluginConfigView(
            availability=SectionAvailability(
                state=SectionAvailabilityState.NOT_CONFIGURED,
                reason_code="config_snapshot_not_collected",
                message="current plugin config snapshot is not available yet",
            ),
            schema=PluginConfigSchemaInfo(
                title=_optional_string(schema.get("title")),
                schema_version=_optional_string(schema.get("$schema")),
                schema_ref=None,
            ),
            config_state=ConfigState.NOT_CONFIGURED,
            entries=entries,
            last_validated_at=None,
            last_updated_at=None,
            reload_required=False,
        )

    def _build_config_summary(self, view: PluginConfigView) -> PluginConfigSummary:
        return PluginConfigSummary(
            availability=view.availability,
            schema_version=view.schema.schema_version if view.schema is not None else None,
            config_state=view.config_state,
            missing_required_count=sum(1 for entry in view.entries if entry.is_required and entry.display_mode == ConfigDisplayMode.UNSET),
            masked_sensitive_count=sum(
                1 for entry in view.entries if entry.is_sensitive and entry.display_mode in {ConfigDisplayMode.MASKED, ConfigDisplayMode.REFERENCE}
            ),
            last_validated_at=view.last_validated_at,
            last_updated_at=view.last_updated_at,
            reload_required=view.reload_required,
        )

    def _build_dependencies_view(
        self,
        record: PluginRecord,
        all_records: Iterable[PluginRecord],
    ) -> PluginDependenciesView:
        if record.manifest is None:
            return PluginDependenciesView(
                availability=SectionAvailability(
                    state=SectionAvailabilityState.UNAVAILABLE,
                    reason_code="manifest_unavailable",
                    message="plugin manifest is unavailable",
                ),
                plugin_dependencies=(),
                python_dependencies=(),
                system_dependencies=(),
                reverse_dependencies=(),
            )

        dependencies = record.manifest.dependencies
        plugin_dependencies = tuple(
            self._build_plugin_dependency(item, all_records)
            for item in _normalize_plugin_dependency_declarations(dependencies.get("plugins"))
        )
        python_dependencies = tuple(
            PluginDependencyRecord(
                name=item["name"],
                kind=DependencyKind.PYTHON,
                required=item["required"],
                resolved_state=DependencyResolvedState.NOT_COLLECTED,
                blocked_reason="python_dependency_not_collected",
                version_range=item["version_range"],
            )
            for item in _normalize_string_dependencies(dependencies.get("python"))
        )
        system_dependencies = tuple(
            PluginDependencyRecord(
                name=item["name"],
                kind=DependencyKind.SYSTEM,
                required=item["required"],
                resolved_state=DependencyResolvedState.NOT_COLLECTED,
                blocked_reason="system_dependency_not_collected",
                version_range=item["version_range"],
            )
            for item in _normalize_string_dependencies(dependencies.get("system"))
        )
        reverse_dependencies = tuple(
            PluginDependencyRecord(
                name=other.id,
                kind=DependencyKind.REVERSE_PLUGIN,
                required=item["required"],
                resolved_state=DependencyResolvedState.RESOLVED,
                blocked_reason=None,
                version_range=item["version_range"],
            )
            for other in all_records
            if other.manifest is not None and other.id != record.id
            for item in _normalize_plugin_dependency_declarations(other.manifest.dependencies.get("plugins"))
            if item["name"] == record.id
        )
        return PluginDependenciesView(
            availability=SectionAvailability(state=SectionAvailabilityState.READY),
            plugin_dependencies=plugin_dependencies,
            python_dependencies=python_dependencies,
            system_dependencies=system_dependencies,
            reverse_dependencies=reverse_dependencies,
        )

    def _build_plugin_dependency(
        self,
        declaration: Mapping[str, Any],
        all_records: Iterable[PluginRecord],
    ) -> PluginDependencyRecord:
        dependency_id = declaration["name"]
        matching = next((record for record in all_records if record.id == dependency_id), None)
        if matching is None:
            return PluginDependencyRecord(
                name=dependency_id,
                kind=DependencyKind.PLUGIN,
                required=declaration["required"],
                resolved_state=DependencyResolvedState.MISSING,
                blocked_reason="plugin_dependency_missing",
                version_range=declaration["version_range"],
            )
        if matching.status != PluginStatus.VALID:
            return PluginDependencyRecord(
                name=dependency_id,
                kind=DependencyKind.PLUGIN,
                required=declaration["required"],
                resolved_state=DependencyResolvedState.BLOCKED,
                blocked_reason="plugin_dependency_blocked",
                version_range=declaration["version_range"],
            )
        return PluginDependencyRecord(
            name=dependency_id,
            kind=DependencyKind.PLUGIN,
            required=declaration["required"],
            resolved_state=DependencyResolvedState.RESOLVED,
            blocked_reason=None,
            version_range=declaration["version_range"],
        )

    def _build_dependency_summary(self, view: PluginDependenciesView) -> PluginDependencySummary:
        all_dependencies = (
            *view.plugin_dependencies,
            *view.python_dependencies,
            *view.system_dependencies,
        )
        required_count = sum(1 for item in all_dependencies if item.required)
        optional_count = sum(1 for item in all_dependencies if not item.required)
        missing_count = sum(1 for item in all_dependencies if item.resolved_state == DependencyResolvedState.MISSING)
        blocked_reason_summary = next(
            (item.blocked_reason for item in all_dependencies if item.blocked_reason),
            None,
        )
        return PluginDependencySummary(
            availability=view.availability,
            required_count=required_count,
            optional_count=optional_count,
            missing_count=missing_count,
            blocked_reason_summary=blocked_reason_summary,
            reverse_dependency_count=len(view.reverse_dependencies),
        )

    def _build_capabilities_view(self, record: PluginRecord) -> PluginCapabilitiesView:
        manifest = record.manifest
        if manifest is None:
            return PluginCapabilitiesView(
                availability=SectionAvailability(
                    state=SectionAvailabilityState.UNAVAILABLE,
                    reason_code="manifest_unavailable",
                    message="plugin manifest is unavailable",
                ),
                declared_capabilities=(),
                risk_level_summary=CapabilityRiskLevel.LOW,
                requires_policy_gate=False,
                requires_approval=False,
                provided_objects_summary={},
            )
        capabilities = tuple(
            PluginCapabilityRecord(
                name=capability,
                kind=capability.split(".", 1)[0],
                risk_level=_capability_risk_level(manifest.type, capability),
                requires_policy_gate=_requires_policy_gate(manifest.type, capability),
                requires_approval=_requires_approval(manifest.type, capability),
                availability_state=SectionAvailabilityState.READY,
            )
            for capability in manifest.capabilities
        )
        provided_objects_summary: dict[str, Any] = {}
        if manifest.type == PluginType.INDUSTRY:
            provided_objects_summary["source_binding_templates_count"] = len(manifest.source_bindings)
        if manifest.type == PluginType.BROKER:
            provided_objects_summary["supported_runtime_modes"] = ["disabled", "dry_run", "mock"]
        return PluginCapabilitiesView(
            availability=SectionAvailability(state=SectionAvailabilityState.READY),
            declared_capabilities=capabilities,
            risk_level_summary=max(
                (item.risk_level for item in capabilities),
                default=CapabilityRiskLevel.LOW,
                key=_risk_weight,
            ),
            requires_policy_gate=any(item.requires_policy_gate for item in capabilities),
            requires_approval=any(item.requires_approval for item in capabilities),
            provided_objects_summary=provided_objects_summary,
        )

    def _build_health_view(self, record: PluginRecord) -> PluginHealthView:
        error_summary = _error_summary(record.last_error)
        if record.status in {PluginStatus.INVALID, PluginStatus.FAILED}:
            return PluginHealthView(
                availability=SectionAvailability(
                    state=SectionAvailabilityState.DEGRADED,
                    reason_code="registry_validation_failed",
                    message="registry record indicates a failed or invalid plugin state",
                ),
                status=HealthStatus.FAILED,
                last_check_at=None,
                degraded_reason=_blocked_reason(record),
                last_error_summary=error_summary,
                latest_runtime_failure_ref=None,
                recent_runtime_error_count=1 if error_summary is not None else 0,
                last_used_at=None,
                runtime_error_refs=(),
                recent_usage_summary={},
                health_checks=(),
            )
        if record.status == PluginStatus.DISABLED:
            return PluginHealthView(
                availability=SectionAvailability(state=SectionAvailabilityState.READY),
                status=HealthStatus.UNAVAILABLE,
                last_check_at=None,
                degraded_reason="plugin_disabled",
                last_error_summary=error_summary,
                latest_runtime_failure_ref=None,
                recent_runtime_error_count=0,
                last_used_at=None,
                runtime_error_refs=(),
                recent_usage_summary={},
                health_checks=(),
            )
        return PluginHealthView(
            availability=SectionAvailability(
                state=SectionAvailabilityState.NOT_COLLECTED,
                reason_code="plugin_health_not_collected",
                message="plugin health provider has not collected data yet",
            ),
            status=HealthStatus.NOT_COLLECTED,
            last_check_at=None,
            degraded_reason=None,
            last_error_summary=error_summary,
            latest_runtime_failure_ref=None,
            recent_runtime_error_count=0,
            last_used_at=None,
            runtime_error_refs=(),
            recent_usage_summary={},
            health_checks=(),
        )

    def _build_health_summary(self, view: PluginHealthView) -> PluginHealthSummary:
        return PluginHealthSummary(
            availability=view.availability,
            status=view.status,
            last_check_at=view.last_check_at,
            degraded_reason=view.degraded_reason,
            last_error_summary=view.last_error_summary,
            latest_runtime_failure_ref=view.latest_runtime_failure_ref,
            recent_runtime_error_count=view.recent_runtime_error_count,
            last_used_at=view.last_used_at,
        )

    def _build_audit_view(self, _record: PluginRecord) -> PluginAuditView:
        return PluginAuditView(
            availability=SectionAvailability(
                state=SectionAvailabilityState.NOT_COLLECTED,
                reason_code="plugin_audit_not_collected",
                message="plugin audit provider has not collected data yet",
            ),
            entries=(),
        )

    def _build_audit_summary(self, view: PluginAuditView) -> PluginAuditSummary:
        recent_actions = tuple(entry.action for entry in view.entries[:3])
        latest_entry = view.entries[0] if view.entries else None
        return PluginAuditSummary(
            availability=view.availability,
            last_changed_at=latest_entry.occurred_at if latest_entry is not None else None,
            last_actor=latest_entry.actor if latest_entry is not None else None,
            recent_action_types=recent_actions,
            latest_audit_ref=latest_entry.audit_id if latest_entry is not None else None,
        )

    def _build_ops_summary(self, record: PluginRecord) -> PluginOpsSummary:
        blockers: list[str] = []
        if record.status in {PluginStatus.INVALID, PluginStatus.FAILED}:
            blockers.append("plugin_invalid")
        if record.source == PluginSource.OFFICIAL:
            blockers.append("official_plugin_protected")
        return PluginOpsSummary(
            availability=SectionAvailability(state=SectionAvailabilityState.READY),
            operable_state="planned_only",
            action_blockers=tuple(blockers),
            requires_confirmation=True,
            high_risk_actions=("uninstall",),
        )


def _error_summary(error: PluginError | None) -> PluginErrorSummary | None:
    if error is None:
        return None
    return PluginErrorSummary(
        code=error.code,
        message=error.message,
        stage=error.stage,
        details=error.details,
        retryable=error.retryable,
    )


def _blocked_reason(record: PluginRecord) -> str | None:
    if record.status == PluginStatus.DISABLED:
        return "plugin is disabled"
    if record.status in {PluginStatus.INVALID, PluginStatus.FAILED} and record.last_error is not None:
        return record.last_error.message
    return None


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_plugin_dependency_declarations(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    items: list[dict[str, Any]] = []
    for raw in value:
        if isinstance(raw, str) and raw.strip():
            items.append({"name": raw.strip(), "required": True, "version_range": None})
            continue
        if not isinstance(raw, Mapping):
            continue
        name = _optional_string(raw.get("id")) or _optional_string(raw.get("name"))
        if name is None:
            continue
        version_range = _optional_string(raw.get("version")) or _optional_string(raw.get("version_range"))
        items.append(
            {
                "name": name,
                "required": bool(raw.get("required", True)),
                "version_range": version_range,
            }
        )
    return tuple(items)


def _normalize_string_dependencies(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    items: list[dict[str, Any]] = []
    for raw in value:
        if isinstance(raw, str) and raw.strip():
            items.append({"name": raw.strip(), "required": True, "version_range": raw.strip()})
            continue
        if not isinstance(raw, Mapping):
            continue
        name = _optional_string(raw.get("name")) or _optional_string(raw.get("id"))
        if name is None:
            continue
        items.append(
            {
                "name": name,
                "required": bool(raw.get("required", True)),
                "version_range": _optional_string(raw.get("version")) or _optional_string(raw.get("version_range")),
            }
        )
    return tuple(items)


def _is_sensitive_field(field_name: str, schema: Mapping[str, Any]) -> bool:
    lower_name = field_name.lower()
    description = str(schema.get("description", "")).lower()
    if lower_name.endswith("_ref"):
        return True
    if lower_name.endswith("_key") or lower_name == "public_key":
        return True
    sensitive_tokens = ("secret", "token", "password", "webhook", "api_key", "apikey", "private_key")
    if any(token in lower_name for token in sensitive_tokens):
        return True
    if "secret reference" in description or "secret" in description:
        return True
    return False


def _capability_risk_level(plugin_type: PluginType, capability: str) -> CapabilityRiskLevel:
    if plugin_type == PluginType.BROKER or capability.startswith("broker."):
        return CapabilityRiskLevel.HIGH
    if plugin_type in {PluginType.STRATEGY, PluginType.NOTIFICATION} or capability.endswith(".send"):
        return CapabilityRiskLevel.MEDIUM
    return CapabilityRiskLevel.LOW


def _requires_policy_gate(plugin_type: PluginType, capability: str) -> bool:
    return plugin_type in {PluginType.BROKER, PluginType.STRATEGY} or capability.startswith("broker.")


def _requires_approval(plugin_type: PluginType, capability: str) -> bool:
    return plugin_type == PluginType.BROKER or capability.startswith("broker.")


def _risk_weight(level: CapabilityRiskLevel) -> int:
    if level == CapabilityRiskLevel.HIGH:
        return 3
    if level == CapabilityRiskLevel.MEDIUM:
        return 2
    return 1
