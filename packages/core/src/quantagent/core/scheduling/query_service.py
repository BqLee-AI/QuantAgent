from __future__ import annotations

import binascii
import base64
import json
from datetime import UTC, datetime

from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.scheduling.api_models import (
    CursorPage,
    EffectiveConfigSummary,
    SchedulerRunDetailView,
    SchedulerRunQuery,
    SchedulerRunSummaryView,
    SourceBindingDetailView,
    SourceBindingQuery,
    SourceBindingRunRef,
    SourceBindingSummaryView,
    build_recent_run_refs,
)
from quantagent.core.scheduling.binding_models import SourceBindingRecord, SourceBindingStatus
from quantagent.core.scheduling.models import PluginRunStatus, PluginTriggerType
from quantagent.core.scheduling.run_models import SchedulerRunRecord
from quantagent.plugin_sdk.io import JsonObject, freeze_json_mapping


class SchedulingQueryNotFoundError(ValueError):
    def __init__(self, *, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} not found: {resource_id}")
        self.resource = resource
        self.resource_id = resource_id


class SchedulingQueryService:
    def __init__(
        self,
        *,
        binding_repository: SourceBindingRepository,
        run_repository: SchedulerRunRepository,
    ) -> None:
        self._binding_repository = binding_repository
        self._run_repository = run_repository

    def list_bindings(self, query: SourceBindingQuery) -> CursorPage:
        items, next_cursor = self._binding_repository.list_for_api(
            owner_type=query.owner_type,
            owner_id=query.owner_id,
            source_plugin_id=query.source_plugin_id,
            status=query.status.value if query.status is not None else None,
            cursor=_decode_cursor(query.cursor),
            limit=query.limit,
        )
        return CursorPage(
            items=tuple(self._binding_summary_from_record(_binding_to_record(item)) for item in items),
            next_cursor=_encode_cursor(next_cursor),
        )

    def get_binding_detail(self, binding_id: str) -> SourceBindingDetailView:
        binding = self._binding_repository.get(binding_id)
        if binding is None:
            raise SchedulingQueryNotFoundError(resource="source_binding", resource_id=binding_id)
        record = _binding_to_record(binding)
        recent_run_records = self._run_repository.list_by_binding(binding_id=binding_id, limit=5)
        recent_runs = tuple(self._run_summary_from_record(_run_to_record(item)) for item in recent_run_records)
        last_error = self._build_last_error_summary(recent_runs[0] if recent_runs else None)
        return SourceBindingDetailView(
            summary=self._binding_summary_from_record(record),
            effective_config_summary=_summarize_effective_config(record.effective_config_snapshot),
            config_version=record.updated_at.astimezone(UTC).isoformat(),
            config_validation_status=_config_validation_status(record),
            rate_limit_policy_summary=record.rate_limit_policy,
            retry_policy_summary=record.retry_policy,
            last_error_summary=last_error,
            audit_refs=(_binding_audit_ref(record.binding_id, record.updated_at),),
            recent_run_refs=build_recent_run_refs(recent_runs),
        )

    def list_binding_runs(self, binding_id: str, query: SchedulerRunQuery) -> CursorPage:
        if self._binding_repository.get(binding_id) is None:
            raise SchedulingQueryNotFoundError(resource="source_binding", resource_id=binding_id)
        items, next_cursor = self._run_repository.list_for_api(
            binding_id=binding_id,
            status=query.status.value if query.status is not None else None,
            trigger_mode=query.trigger_mode.value if query.trigger_mode is not None else None,
            started_after=query.started_after,
            started_before=query.started_before,
            cursor=_decode_cursor(query.cursor),
            limit=query.limit,
        )
        return CursorPage(
            items=tuple(self._run_summary_from_record(_run_to_record(item)) for item in items),
            next_cursor=_encode_cursor(next_cursor),
        )

    def list_runs(self, query: SchedulerRunQuery) -> CursorPage:
        items, next_cursor = self._run_repository.list_for_api(
            binding_id=query.binding_id,
            status=query.status.value if query.status is not None else None,
            trigger_mode=query.trigger_mode.value if query.trigger_mode is not None else None,
            started_after=query.started_after,
            started_before=query.started_before,
            cursor=_decode_cursor(query.cursor),
            limit=query.limit,
        )
        return CursorPage(
            items=tuple(self._run_summary_from_record(_run_to_record(item)) for item in items),
            next_cursor=_encode_cursor(next_cursor),
        )

    def get_run_detail(self, run_id: str) -> SchedulerRunDetailView:
        run = self._run_repository.get(run_id)
        if run is None:
            raise SchedulingQueryNotFoundError(resource="scheduler_run", resource_id=run_id)
        record = _run_to_record(run)
        actor = _build_actor_summary(record.metadata)
        return SchedulerRunDetailView(
            summary=self._run_summary_from_record(record),
            request_id=record.request_id,
            actor=actor,
            correlation_id=_optional_str(record.metadata.get("correlation_id")) or record.request_id,
            binding_snapshot_ref=f"binding:{record.binding_id}@{(record.created_at or datetime.now(UTC)).astimezone(UTC).isoformat()}",
            output_summary=record.output_summary,
            error_code=record.failure_code,
            error_stage=record.failure_stage,
            error_retryable=record.retryable,
            audit_ref=_run_audit_ref(record.run_id, record.request_id),
        )

    def _binding_summary_from_record(self, record: SourceBindingRecord) -> SourceBindingSummaryView:
        return SourceBindingSummaryView(
            id=record.binding_id,
            source_plugin_id=record.source_plugin_id,
            owner_type=record.owner_type,
            owner_id=record.owner_id,
            status=record.status,
            blocked_reason=record.disabled_reason,
            schedule_summary=_schedule_summary(record),
            last_run_ref=(
                SourceBindingRunRef(
                    run_id=record.last_run_id,
                    status=record.last_run_status,
                    started_at=record.last_run_at,
                    finished_at=record.last_run_at,
                )
                if record.last_run_id is not None and record.last_run_status is not None
                else None
            ),
            next_run_at=record.next_run_at,
            health_summary=_health_summary(record),
            allowed_actions=_allowed_actions(record.status),
        )

    def _run_summary_from_record(self, record: SchedulerRunRecord) -> SchedulerRunSummaryView:
        return SchedulerRunSummaryView(
            id=record.run_id,
            binding_id=record.binding_id,
            source_plugin_id=record.source_plugin_id,
            trigger_mode=record.trigger_mode,
            status=record.status,
            started_at=record.started_at,
            finished_at=record.finished_at,
            duration_ms=record.duration_ms,
            attempt_index=record.attempt_index,
            captured_count=record.captured_count,
            failure_summary=_failure_summary(record),
        )

    def _build_last_error_summary(self, run: SchedulerRunSummaryView | None) -> JsonObject:
        if run is None or run.status not in {PluginRunStatus.FAILED, PluginRunStatus.TIMEOUT, PluginRunStatus.CANCELLED}:
            return freeze_json_mapping({}, stage="invoke")
        return freeze_json_mapping(
            {
                "status": run.status.value,
                "run_id": run.id,
                "finished_at": run.finished_at.astimezone(UTC).isoformat() if run.finished_at is not None else None,
                "failure": run.failure_summary,
            },
            stage="invoke",
        )


def _binding_to_record(binding) -> SourceBindingRecord:
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


def _run_to_record(run) -> SchedulerRunRecord:
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


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _allowed_actions(status: SourceBindingStatus) -> tuple[str, ...]:
    if status == SourceBindingStatus.ACTIVE:
        return ("pause", "run-now")
    if status == SourceBindingStatus.PAUSED:
        return ("resume", "run-now")
    return ()


def _schedule_summary(record: SourceBindingRecord) -> JsonObject:
    summary: dict[str, object] = {}
    for key in ("interval_seconds", "cron", "timezone", "mode"):
        if key in record.schedule_policy:
            summary[key] = record.schedule_policy[key]
    if record.next_run_at is not None:
        summary["next_run_at"] = record.next_run_at.astimezone(UTC).isoformat()
    return freeze_json_mapping(summary, stage="schedule_precheck")


def _health_summary(record: SourceBindingRecord) -> JsonObject:
    return freeze_json_mapping(
        {
            "consecutive_failure_count": record.consecutive_failure_count,
            "last_success_at": record.last_success_at.astimezone(UTC).isoformat() if record.last_success_at is not None else None,
            "last_heartbeat_at": record.last_heartbeat_at.astimezone(UTC).isoformat() if record.last_heartbeat_at is not None else None,
            "last_run_status": record.last_run_status.value if record.last_run_status is not None else None,
        },
        stage="schedule_precheck",
    )


def _failure_summary(record: SchedulerRunRecord) -> JsonObject:
    return freeze_json_mapping(
        {
            "code": record.failure_code,
            "message": record.failure_message,
            "stage": record.failure_stage,
            "retryable": record.retryable,
        },
        stage="invoke",
    )


def _config_validation_status(record: SourceBindingRecord) -> str:
    if record.disabled_reason and "config" in record.disabled_reason.lower():
        return "invalid"
    return "valid"


def _summarize_effective_config(snapshot: JsonObject) -> EffectiveConfigSummary:
    masked: list[str] = []
    values = _sanitize_config_mapping(snapshot, prefix="", masked=masked)
    raw_refs = snapshot.get("config_source_refs")
    refs = tuple(item for item in raw_refs if isinstance(item, str)) if isinstance(raw_refs, list) else ()
    last_validated_at = _optional_str(snapshot.get("last_validated_at"))
    return EffectiveConfigSummary(
        values=values,
        secret_fields_masked=tuple(masked),
        last_validated_at=last_validated_at,
        config_source_refs=refs,
    )


def _sanitize_config_mapping(snapshot: JsonObject, *, prefix: str, masked: list[str]) -> JsonObject:
    sanitized: dict[str, object] = {}
    for key, value in snapshot.items():
        path = f"{prefix}.{key}" if prefix else key
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "api_key", "apikey", "auth", "header")):
            masked.append(path)
            continue
        if isinstance(value, dict):
            nested = _sanitize_config_mapping(freeze_json_mapping(value, stage="config"), prefix=path, masked=masked)
            if nested:
                sanitized[key] = dict(nested)
            continue
        if isinstance(value, list):
            # 中文注释：列表只保留标量，避免把复杂插件私有结构直接透出给 API。
            sanitized[key] = [item for item in value if isinstance(item, (str, int, float, bool))][:10]
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
    return freeze_json_mapping(sanitized, stage="config")


def _build_actor_summary(metadata: JsonObject) -> JsonObject:
    actor = metadata.get("actor")
    if isinstance(actor, dict):
        return freeze_json_mapping(actor, stage="schedule_precheck")
    return freeze_json_mapping({}, stage="schedule_precheck")


def _binding_audit_ref(binding_id: str, updated_at: datetime) -> str:
    return f"audit:source-binding:{binding_id}:{updated_at.astimezone(UTC).isoformat()}"


def _run_audit_ref(run_id: str, request_id: str) -> str:
    return f"audit:scheduler-run:{run_id}:{request_id}"


def _encode_cursor(payload: dict[str, str] | None) -> str | None:
    if payload is None:
        return None
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str | None) -> dict[str, str] | None:
    if cursor is None:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeEncodeError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("invalid cursor") from exc
    if not isinstance(payload, dict):
        raise ValueError("cursor must decode to an object")
    return {str(key): str(value) for key, value in payload.items()}
