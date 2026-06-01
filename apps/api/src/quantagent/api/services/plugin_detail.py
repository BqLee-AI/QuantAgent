from __future__ import annotations

from quantagent.api.auth import (
    PLUGIN_CONFIGURE_CAPABILITY,
    PLUGIN_INSTALL_CAPABILITY,
    RUNTIME_INSPECT_CAPABILITY,
    CurrentActor,
)
from quantagent.api.schemas.plugin_detail import (
    PluginActionHintResponse,
    PluginActionStateHintResponse,
    PluginAuditEntryResponse,
    PluginAuditSummaryResponse,
    PluginAuditViewResponse,
    PluginCapabilitiesViewResponse,
    PluginCapabilityRecordResponse,
    PluginConfigEntryResponse,
    PluginConfigSchemaInfoResponse,
    PluginConfigSummaryResponse,
    PluginConfigViewResponse,
    PluginDependenciesViewResponse,
    PluginDependencyRecordResponse,
    PluginDependencySummaryResponse,
    PluginDetailResponse,
    PluginErrorSummaryResponse,
    PluginHealthSummaryResponse,
    PluginHealthViewResponse,
    PluginOpsSummaryResponse,
    PluginOverviewResponse,
    PluginRelatedResourcesResponse,
    SectionAvailabilityResponse,
)
from quantagent.core.registry import (
    PluginDependenciesView,
    PluginDetailReadService,
    PluginRegistry,
    SectionAvailability,
    SectionAvailabilityState,
)


class PluginDetailApiService:
    """API 私有映射层，负责 section 级裁剪与 DTO 适配。"""

    def __init__(self, registry: PluginRegistry) -> None:
        self._detail_service = PluginDetailReadService(registry)

    def get_plugin_detail(self, plugin_id: str, actor: CurrentActor) -> PluginDetailResponse | None:
        snapshot = self._detail_service.get_plugin_detail(plugin_id)
        if snapshot is None:
            return None
        return PluginDetailResponse(
            overview=PluginOverviewResponse(
                plugin_id=snapshot.overview.plugin_id,
                name=snapshot.overview.name,
                type=snapshot.overview.plugin_type,
                source=snapshot.overview.source,
                description=snapshot.overview.description,
                installed_version=snapshot.overview.installed_version,
                active_version=snapshot.overview.active_version,
                status=snapshot.overview.status,
                active_config_state=snapshot.overview.active_config_state.value,
                blocked_reason=snapshot.overview.blocked_reason,
                last_error_summary=_error_summary(snapshot.overview.last_error_summary),
            ),
            config_summary=self._config_summary(snapshot, actor),
            dependency_summary=PluginDependencySummaryResponse(
                availability=_availability(snapshot.dependency_summary.availability),
                required_count=snapshot.dependency_summary.required_count,
                optional_count=snapshot.dependency_summary.optional_count,
                missing_count=snapshot.dependency_summary.missing_count,
                blocked_reason_summary=snapshot.dependency_summary.blocked_reason_summary,
                reverse_dependency_count=snapshot.dependency_summary.reverse_dependency_count,
            ),
            capabilities=PluginCapabilitiesViewResponse(
                availability=_availability(snapshot.capabilities_view.availability),
                declared_capabilities=[
                    PluginCapabilityRecordResponse(
                        name=item.name,
                        kind=item.kind,
                        risk_level=item.risk_level.value,
                        requires_policy_gate=item.requires_policy_gate,
                        requires_approval=item.requires_approval,
                        availability_state=item.availability_state.value,
                    )
                    for item in snapshot.capabilities_view.declared_capabilities
                ],
                risk_level_summary=snapshot.capabilities_view.risk_level_summary.value,
                requires_policy_gate=snapshot.capabilities_view.requires_policy_gate,
                requires_approval=snapshot.capabilities_view.requires_approval,
                provided_objects_summary=dict(snapshot.capabilities_view.provided_objects_summary),
            ),
            health_summary=self._health_summary(snapshot, actor),
            audit_summary=self._audit_summary(snapshot, actor),
            ops_summary=self._ops_summary(snapshot, actor),
            allowed_actions=self._allowed_actions(snapshot, actor),
            action_state_hints=self._action_state_hints(snapshot, actor),
            related_resources=PluginRelatedResourcesResponse(
                config=f"/api/v1/plugins/{plugin_id}/config",
                config_schema=f"/api/v1/plugins/{plugin_id}/config-schema",
                dependencies=f"/api/v1/plugins/{plugin_id}/dependencies",
                health=f"/api/v1/plugins/{plugin_id}/health",
                audit=f"/api/v1/plugins/{plugin_id}/audit",
            ),
        )

    def get_plugin_config(self, plugin_id: str, actor: CurrentActor) -> PluginConfigViewResponse | None:
        snapshot = self._detail_service.get_plugin_detail(plugin_id)
        if snapshot is None:
            return None
        if PLUGIN_CONFIGURE_CAPABILITY not in actor.capabilities:
            return PluginConfigViewResponse(
                availability=_availability(_forbidden("config visibility requires plugin.configure")),
                schema=self._config_schema(snapshot),
                config_state=snapshot.config_view.config_state.value,
                entries=[],
                last_validated_at=snapshot.config_view.last_validated_at,
                last_updated_at=snapshot.config_view.last_updated_at,
                reload_required=snapshot.config_view.reload_required,
            )
        return PluginConfigViewResponse(
            availability=_availability(snapshot.config_view.availability),
            schema=self._config_schema(snapshot),
            config_state=snapshot.config_view.config_state.value,
            entries=[
                PluginConfigEntryResponse(
                    key=entry.key,
                    display_mode=entry.display_mode.value,
                    display_value=entry.display_value,
                    is_sensitive=entry.is_sensitive,
                    is_required=entry.is_required,
                    is_overridden=entry.is_overridden,
                )
                for entry in snapshot.config_view.entries
            ],
            last_validated_at=snapshot.config_view.last_validated_at,
            last_updated_at=snapshot.config_view.last_updated_at,
            reload_required=snapshot.config_view.reload_required,
        )

    def get_plugin_dependencies(self, plugin_id: str, actor: CurrentActor) -> PluginDependenciesViewResponse | None:
        snapshot = self._detail_service.get_plugin_detail(plugin_id)
        if snapshot is None:
            return None
        view = snapshot.dependencies_view
        if PLUGIN_CONFIGURE_CAPABILITY not in actor.capabilities:
            # 中文注释：低权限调用方不返回反向依赖，避免把 owner/binding 关系提前泄露到 #220/#226。
            view = PluginDependenciesView(
                availability=view.availability,
                plugin_dependencies=view.plugin_dependencies,
                python_dependencies=view.python_dependencies,
                system_dependencies=view.system_dependencies,
                reverse_dependencies=(),
            )
        return PluginDependenciesViewResponse(
            availability=_availability(view.availability),
            plugin_dependencies=[_dependency_record(item) for item in view.plugin_dependencies],
            python_dependencies=[_dependency_record(item) for item in view.python_dependencies],
            system_dependencies=[_dependency_record(item) for item in view.system_dependencies],
            reverse_dependencies=[_dependency_record(item) for item in view.reverse_dependencies],
        )

    def get_plugin_health(self, plugin_id: str, actor: CurrentActor) -> PluginHealthViewResponse | None:
        snapshot = self._detail_service.get_plugin_detail(plugin_id)
        if snapshot is None:
            return None
        if RUNTIME_INSPECT_CAPABILITY not in actor.capabilities:
            return PluginHealthViewResponse(
                availability=_availability(_forbidden("health visibility requires runtime.inspect")),
                status=snapshot.health_view.status.value,
                last_check_at=snapshot.health_view.last_check_at,
                degraded_reason=snapshot.health_view.degraded_reason,
                last_error_summary=_error_summary(snapshot.health_view.last_error_summary),
                latest_runtime_failure_ref=None,
                recent_runtime_error_count=0,
                last_used_at=None,
                runtime_error_refs=[],
                recent_usage_summary={},
                health_checks=[],
            )
        return PluginHealthViewResponse(
            availability=_availability(snapshot.health_view.availability),
            status=snapshot.health_view.status.value,
            last_check_at=snapshot.health_view.last_check_at,
            degraded_reason=snapshot.health_view.degraded_reason,
            last_error_summary=_error_summary(snapshot.health_view.last_error_summary),
            latest_runtime_failure_ref=snapshot.health_view.latest_runtime_failure_ref,
            recent_runtime_error_count=snapshot.health_view.recent_runtime_error_count,
            last_used_at=snapshot.health_view.last_used_at,
            runtime_error_refs=list(snapshot.health_view.runtime_error_refs),
            recent_usage_summary=dict(snapshot.health_view.recent_usage_summary),
            health_checks=[dict(item) for item in snapshot.health_view.health_checks],
        )

    def get_plugin_audit(self, plugin_id: str, actor: CurrentActor) -> PluginAuditViewResponse | None:
        snapshot = self._detail_service.get_plugin_detail(plugin_id)
        if snapshot is None:
            return None
        if PLUGIN_INSTALL_CAPABILITY not in actor.capabilities:
            return PluginAuditViewResponse(
                availability=_availability(_forbidden("audit visibility requires plugin.install")),
                entries=[],
            )
        return PluginAuditViewResponse(
            availability=_availability(snapshot.audit_view.availability),
            entries=[
                PluginAuditEntryResponse(
                    audit_id=entry.audit_id,
                    action=entry.action,
                    actor=entry.actor,
                    result=entry.result,
                    occurred_at=entry.occurred_at,
                    safe_details=dict(entry.safe_details),
                )
                for entry in snapshot.audit_view.entries
            ],
        )

    def _config_summary(self, snapshot, actor: CurrentActor) -> PluginConfigSummaryResponse:
        availability = snapshot.config_summary.availability
        if PLUGIN_CONFIGURE_CAPABILITY not in actor.capabilities:
            availability = _forbidden("config visibility requires plugin.configure")
        return PluginConfigSummaryResponse(
            availability=_availability(availability),
            schema_version=snapshot.config_summary.schema_version,
            config_state=snapshot.config_summary.config_state.value,
            missing_required_count=snapshot.config_summary.missing_required_count,
            masked_sensitive_count=snapshot.config_summary.masked_sensitive_count,
            last_validated_at=snapshot.config_summary.last_validated_at,
            last_updated_at=snapshot.config_summary.last_updated_at,
            reload_required=snapshot.config_summary.reload_required,
        )

    def _health_summary(self, snapshot, actor: CurrentActor) -> PluginHealthSummaryResponse:
        availability = snapshot.health_summary.availability
        if RUNTIME_INSPECT_CAPABILITY not in actor.capabilities:
            availability = _forbidden("health visibility requires runtime.inspect")
        return PluginHealthSummaryResponse(
            availability=_availability(availability),
            status=snapshot.health_summary.status.value,
            last_check_at=snapshot.health_summary.last_check_at,
            degraded_reason=snapshot.health_summary.degraded_reason,
            last_error_summary=_error_summary(snapshot.health_summary.last_error_summary),
            latest_runtime_failure_ref=snapshot.health_summary.latest_runtime_failure_ref if RUNTIME_INSPECT_CAPABILITY in actor.capabilities else None,
            recent_runtime_error_count=snapshot.health_summary.recent_runtime_error_count if RUNTIME_INSPECT_CAPABILITY in actor.capabilities else 0,
            last_used_at=snapshot.health_summary.last_used_at if RUNTIME_INSPECT_CAPABILITY in actor.capabilities else None,
        )

    def _audit_summary(self, snapshot, actor: CurrentActor) -> PluginAuditSummaryResponse:
        availability = snapshot.audit_summary.availability
        if PLUGIN_INSTALL_CAPABILITY not in actor.capabilities:
            availability = _forbidden("audit visibility requires plugin.install")
        return PluginAuditSummaryResponse(
            availability=_availability(availability),
            last_changed_at=snapshot.audit_summary.last_changed_at if PLUGIN_INSTALL_CAPABILITY in actor.capabilities else None,
            last_actor=snapshot.audit_summary.last_actor if PLUGIN_INSTALL_CAPABILITY in actor.capabilities else None,
            recent_action_types=list(snapshot.audit_summary.recent_action_types) if PLUGIN_INSTALL_CAPABILITY in actor.capabilities else [],
            latest_audit_ref=snapshot.audit_summary.latest_audit_ref if PLUGIN_INSTALL_CAPABILITY in actor.capabilities else None,
        )

    def _ops_summary(self, snapshot, actor: CurrentActor) -> PluginOpsSummaryResponse:
        availability = snapshot.ops_summary.availability
        if PLUGIN_INSTALL_CAPABILITY not in actor.capabilities:
            availability = _forbidden("ops visibility requires plugin.install")
        return PluginOpsSummaryResponse(
            availability=_availability(availability),
            operable_state=snapshot.ops_summary.operable_state,
            action_blockers=list(snapshot.ops_summary.action_blockers),
            requires_confirmation=snapshot.ops_summary.requires_confirmation,
            high_risk_actions=list(snapshot.ops_summary.high_risk_actions),
        )

    def _allowed_actions(self, snapshot, actor: CurrentActor) -> list[PluginActionHintResponse]:
        blockers = list(snapshot.ops_summary.action_blockers)
        has_capability = PLUGIN_INSTALL_CAPABILITY in actor.capabilities
        actions = ("enable", "disable", "reload", "rescan", "uninstall")
        results: list[PluginActionHintResponse] = []
        for action in actions:
            if not has_capability:
                results.append(
                    PluginActionHintResponse(
                        action=action,
                        allowed=False,
                        disabled_reason="permission_denied",
                        requires_confirmation=snapshot.ops_summary.requires_confirmation,
                    )
                )
                continue
            if action == "uninstall":
                results.append(
                    PluginActionHintResponse(
                        action=action,
                        allowed=False,
                        disabled_reason="action_not_implemented",
                        requires_confirmation=snapshot.ops_summary.requires_confirmation,
                    )
                )
                continue
            results.append(
                PluginActionHintResponse(
                    action=action,
                    allowed=not blockers,
                    disabled_reason=blockers[0] if blockers else None,
                    requires_confirmation=snapshot.ops_summary.requires_confirmation,
                )
            )
        return results

    def _action_state_hints(self, snapshot, actor: CurrentActor) -> list[PluginActionStateHintResponse]:
        actions = ("enable", "disable", "reload", "rescan", "uninstall")
        if PLUGIN_INSTALL_CAPABILITY not in actor.capabilities:
            return [
                PluginActionStateHintResponse(
                    action=action,
                    state="forbidden",
                    reason_code="permission_denied",
                    message="plugin operation visibility requires plugin.install",
                )
                for action in actions
            ]
        if snapshot.ops_summary.action_blockers:
            return [
                PluginActionStateHintResponse(
                    action=action,
                    state="degraded",
                    reason_code=snapshot.ops_summary.action_blockers[0],
                    message=", ".join(snapshot.ops_summary.action_blockers),
                )
                for action in actions
            ]
        return [
            PluginActionStateHintResponse(
                action=action,
                state="ready" if action != "uninstall" else "unavailable",
                reason_code=None if action != "uninstall" else "action_not_implemented",
                message=None if action != "uninstall" else "future mutation endpoint not implemented",
            )
            for action in actions
        ]

    def _config_schema(self, snapshot) -> PluginConfigSchemaInfoResponse | None:
        schema = snapshot.config_view.schema
        if schema is None:
            return None
        return PluginConfigSchemaInfoResponse(
            title=schema.title,
            schema_version=schema.schema_version,
            schema_ref=schema.schema_ref,
        )


def _availability(value: SectionAvailability) -> SectionAvailabilityResponse:
    return SectionAvailabilityResponse(
        state=value.state.value,
        reason_code=value.reason_code,
        message=value.message,
    )


def _error_summary(value) -> PluginErrorSummaryResponse | None:
    if value is None:
        return None
    return PluginErrorSummaryResponse(
        code=value.code,
        message=value.message,
        stage=value.stage,
        details=dict(value.details),
        retryable=value.retryable,
    )


def _dependency_record(value) -> PluginDependencyRecordResponse:
    return PluginDependencyRecordResponse(
        name=value.name,
        kind=value.kind.value,
        required=value.required,
        resolved_state=value.resolved_state.value,
        blocked_reason=value.blocked_reason,
        version_range=value.version_range,
    )


def _forbidden(message: str) -> SectionAvailability:
    return SectionAvailability(
        state=SectionAvailabilityState.FORBIDDEN,
        reason_code="permission_denied",
        message=message,
    )
