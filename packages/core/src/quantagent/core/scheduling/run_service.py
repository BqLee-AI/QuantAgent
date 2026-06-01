from __future__ import annotations

from datetime import datetime

from quantagent.core.db.models.scheduler_run import SchedulerRunORM
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.events.codec import sanitize_string
from quantagent.core.scheduling.clock import SchedulingClock, SystemSchedulingClock
from quantagent.core.scheduling.models import PluginRunStatus, PluginTriggerType
from quantagent.core.scheduling.run_models import SchedulerRunRecord
from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping, to_json_value

TERMINAL_RUN_STATUSES = frozenset(
    {
        PluginRunStatus.SUCCEEDED,
        PluginRunStatus.FAILED,
        PluginRunStatus.TIMEOUT,
        PluginRunStatus.CANCELLED,
    }
)


class SchedulerRunService:
    def __init__(
        self,
        repository: SchedulerRunRepository,
        *,
        clock: SchedulingClock | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or SystemSchedulingClock()

    def create_run(
        self,
        *,
        run_id: str,
        binding_id: str,
        source_plugin_id: str,
        source_plugin_version: str | None,
        trigger_mode: PluginTriggerType,
        request_id: str,
        status: PluginRunStatus,
        attempt_index: int | None = None,
        timeout_ms: int | None = None,
        metadata: JsonObject | None = None,
        started_at: datetime | None = None,
    ) -> SchedulerRunRecord:
        run = self._repository.create(
            SchedulerRunORM(
                run_id=run_id,
                binding_id=binding_id,
                source_plugin_id=source_plugin_id,
                source_plugin_version=source_plugin_version,
                trigger_mode=trigger_mode.value,
                request_id=request_id,
                status=status.value,
                attempt_index=attempt_index,
                timeout_ms=timeout_ms,
                metadata_json=dict(to_json_value(freeze_json_mapping(metadata or {}, stage="schedule_precheck"))),
                started_at=started_at,
            )
        )
        return _to_record(run)

    def finish_run(
        self,
        *,
        run_id: str,
        status: PluginRunStatus,
        finished_at: datetime | None = None,
        duration_ms: int | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        failure_stage: str | None = None,
        retryable: bool | None = None,
        output_summary: JsonObject | None = None,
        captured_count: int | None = None,
    ) -> SchedulerRunRecord:
        current = self._require_run(run_id)
        if current.finished_at is not None:
            raise ValueError("finished scheduler run cannot be overwritten.")
        if status not in TERMINAL_RUN_STATUSES:
            raise ValueError("finish_run only accepts terminal scheduler run statuses.")
        # append-only 的含义是每个 run_id 只允许从进行中推进到终态，禁止事后覆盖终态历史。
        current.status = status.value
        current.finished_at = finished_at or self._clock.now()
        current.duration_ms = duration_ms
        current.failure_code = failure_code
        # 失败摘要只保留脱敏后的可审计信息，避免把 token、cookie 或本地路径原样入库。
        current.failure_message = _sanitize_failure_message(failure_message)
        current.failure_stage = failure_stage
        current.retryable = retryable
        current.output_summary = dict(to_json_value(freeze_json_mapping(output_summary or {}, stage="invoke")))
        current.captured_count = captured_count
        return _to_record(self._repository.save(current))

    def list_binding_runs(self, *, binding_id: str, limit: int = 50) -> list[SchedulerRunRecord]:
        return [_to_record(item) for item in self._repository.list_by_binding(binding_id=binding_id, limit=limit)]

    def _require_run(self, run_id: str) -> SchedulerRunORM:
        run = self._repository.get(run_id)
        if run is None:
            raise ValueError(f"Unknown scheduler run: {run_id}")
        return run


def _to_record(run: SchedulerRunORM) -> SchedulerRunRecord:
    return SchedulerRunRecord(
        run_id=run.run_id,
        binding_id=run.binding_id,
        source_plugin_id=run.source_plugin_id,
        source_plugin_version=run.source_plugin_version,
        trigger_mode=PluginTriggerType(run.trigger_mode),
        request_id=run.request_id,
        status=PluginRunStatus(run.status),
        attempt_index=run.attempt_index,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=run.duration_ms,
        timeout_ms=run.timeout_ms,
        failure_code=run.failure_code,
        failure_message=run.failure_message,
        failure_stage=run.failure_stage,
        retryable=run.retryable,
        output_summary=freeze_json_mapping(run.output_summary or {}, stage="invoke"),
        captured_count=run.captured_count,
        metadata=freeze_json_mapping(run.metadata_json or {}, stage="schedule_precheck"),
        created_at=run.created_at,
    )


def _sanitize_failure_message(value: str | None) -> str | None:
    if value is None:
        return None
    sanitized = sanitize_string(value).strip()
    return sanitized or None
