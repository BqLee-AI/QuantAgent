from __future__ import annotations

from datetime import datetime

from quantagent.core.db.models.source_binding import SourceBindingORM
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.scheduling.binding_models import CreateSourceBindingInput, SourceBindingRecord, SourceBindingStatus
from quantagent.core.scheduling.clock import SchedulingClock, SystemSchedulingClock
from quantagent.core.scheduling.models import PluginRunStatus
from quantagent.plugin_sdk.io import freeze_json_mapping, to_json_value


class SourceBindingService:
    def __init__(
        self,
        repository: SourceBindingRepository,
        *,
        clock: SchedulingClock | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or SystemSchedulingClock()

    def create_binding(self, data: CreateSourceBindingInput) -> SourceBindingRecord:
        if data.status == SourceBindingStatus.DISABLED and data.next_run_at is not None:
            raise ValueError("disabled bindings must not have next_run_at.")
        binding = self._repository.create(
            SourceBindingORM(
                binding_id=data.binding_id,
                owner_type=data.owner_type,
                owner_id=data.owner_id,
                source_plugin_id=data.source_plugin_id,
                source_plugin_version=data.source_plugin_version,
                effective_config_snapshot=dict(to_json_value(data.effective_config_snapshot)),
                schedule_policy=dict(to_json_value(data.schedule_policy)),
                retry_policy=dict(to_json_value(data.retry_policy)),
                rate_limit_policy=dict(to_json_value(data.rate_limit_policy)),
                status=data.status.value,
                next_run_at=data.next_run_at,
                created_by=data.created_by,
                updated_by=data.created_by,
            )
        )
        return _to_record(binding)

    def list_due_bindings(self, *, now: datetime | None = None, limit: int = 100) -> list[SourceBindingRecord]:
        due_at = now or self._clock.now()
        return [_to_record(item) for item in self._repository.list_due_bindings(now=due_at, limit=limit)]

    def claim_due_binding(
        self,
        binding_id: str,
        *,
        expected_next_run_at: datetime,
        claimed_at: datetime | None = None,
        actor: str | None = None,
    ) -> SourceBindingRecord | None:
        actual_claimed_at = claimed_at or self._clock.now()
        claimed = self._repository.claim_due_binding(
            binding_id=binding_id,
            expected_next_run_at=expected_next_run_at,
            claimed_at=actual_claimed_at,
            actor=actor,
        )
        if not claimed:
            return None
        binding = self._require_binding(binding_id)
        return _to_record(binding)

    def mark_heartbeat(self, binding_id: str, *, heartbeat_at: datetime | None = None, actor: str | None = None) -> SourceBindingRecord:
        binding = self._require_binding(binding_id)
        binding.last_heartbeat_at = heartbeat_at or self._clock.now()
        binding.updated_by = actor
        return _to_record(self._repository.save(binding))

    def apply_run_result(
        self,
        *,
        binding_id: str,
        run_id: str,
        status: PluginRunStatus,
        finished_at: datetime,
        next_run_at: datetime | None,
        actor: str | None = None,
    ) -> SourceBindingRecord:
        binding = self._require_binding(binding_id)
        binding.last_run_id = run_id
        binding.last_run_status = status.value
        binding.last_run_at = finished_at
        binding.next_run_at = next_run_at
        binding.updated_by = actor
        # 这里用摘要字段承接热路径查询，历史真源仍然保留在 SchedulerRun。
        if status == PluginRunStatus.SUCCEEDED:
            binding.last_success_at = finished_at
            binding.consecutive_failure_count = 0
        elif status in {PluginRunStatus.FAILED, PluginRunStatus.TIMEOUT, PluginRunStatus.CANCELLED}:
            binding.consecutive_failure_count += 1
        return _to_record(self._repository.save(binding))

    def apply_run_result_if_active(
        self,
        *,
        binding_id: str,
        run_id: str,
        status: PluginRunStatus,
        finished_at: datetime,
        next_run_at: datetime | None,
        actor: str | None = None,
    ) -> SourceBindingRecord | None:
        values: dict[str, object] = {
            "last_run_id": run_id,
            "last_run_status": status.value,
            "last_run_at": finished_at,
            "next_run_at": next_run_at,
            "updated_by": actor,
        }
        # 非显然约束：只有 binding 仍是 active 才允许回写下一次调度与热路径摘要，避免 pause/disable during invoke 被旧结果覆盖。
        if status == PluginRunStatus.SUCCEEDED:
            values["last_success_at"] = finished_at
            values["consecutive_failure_count"] = 0
        elif status in {PluginRunStatus.FAILED, PluginRunStatus.TIMEOUT, PluginRunStatus.CANCELLED}:
            binding = self._require_binding(binding_id)
            values["consecutive_failure_count"] = binding.consecutive_failure_count + 1
        updated = self._repository.update_if_status(
            binding_id=binding_id,
            expected_status=SourceBindingStatus.ACTIVE.value,
            values=values,
        )
        if not updated:
            return None
        return _to_record(self._require_binding(binding_id))

    def disable_binding(self, binding_id: str, *, reason: str, actor: str | None = None) -> SourceBindingRecord:
        binding = self._require_binding(binding_id)
        binding.status = SourceBindingStatus.DISABLED.value
        binding.next_run_at = None
        binding.disabled_reason = reason
        binding.updated_by = actor
        return _to_record(self._repository.save(binding))

    def pause_binding(self, binding_id: str, *, actor: str | None = None) -> SourceBindingRecord:
        binding = self._require_binding(binding_id)
        if binding.status == SourceBindingStatus.DISABLED.value:
            raise ValueError("disabled binding cannot be paused.")
        binding.status = SourceBindingStatus.PAUSED.value
        binding.updated_by = actor
        return _to_record(self._repository.save(binding))

    def resume_binding(self, binding_id: str, *, next_run_at: datetime, actor: str | None = None) -> SourceBindingRecord:
        binding = self._require_binding(binding_id)
        if binding.status == SourceBindingStatus.DISABLED.value:
            raise ValueError("disabled binding cannot be resumed.")
        binding.status = SourceBindingStatus.ACTIVE.value
        binding.next_run_at = next_run_at
        binding.updated_by = actor
        return _to_record(self._repository.save(binding))

    def _require_binding(self, binding_id: str) -> SourceBindingORM:
        binding = self._repository.get(binding_id)
        if binding is None:
            raise ValueError(f"Unknown source binding: {binding_id}")
        return binding


def _to_record(binding: SourceBindingORM) -> SourceBindingRecord:
    return SourceBindingRecord(
        binding_id=binding.binding_id,
        owner_type=binding.owner_type,
        owner_id=binding.owner_id,
        source_plugin_id=binding.source_plugin_id,
        source_plugin_version=binding.source_plugin_version,
        effective_config_snapshot=freeze_json_mapping(binding.effective_config_snapshot or {}, stage="config"),
        schedule_policy=freeze_json_mapping(binding.schedule_policy or {}, stage="schedule_precheck"),
        retry_policy=freeze_json_mapping(binding.retry_policy or {}, stage="schedule_precheck"),
        rate_limit_policy=freeze_json_mapping(binding.rate_limit_policy or {}, stage="schedule_precheck"),
        status=SourceBindingStatus(binding.status),
        last_run_id=binding.last_run_id,
        last_run_status=PluginRunStatus(binding.last_run_status) if binding.last_run_status is not None else None,
        last_run_at=binding.last_run_at,
        last_success_at=binding.last_success_at,
        next_run_at=binding.next_run_at,
        last_heartbeat_at=binding.last_heartbeat_at,
        consecutive_failure_count=binding.consecutive_failure_count,
        disabled_reason=binding.disabled_reason,
        created_at=binding.created_at,
        updated_at=binding.updated_at,
        created_by=binding.created_by,
        updated_by=binding.updated_by,
    )
