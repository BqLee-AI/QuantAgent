from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from quantagent.api.http.errors import BadRequestError, NotFoundError, ServiceUnavailableError
from quantagent.api.schemas.runtime_inspect import (
    AgentRunDetail,
    AgentRunSummary,
    RuntimeBackendStatusSummary,
    RuntimeErrorDetail,
    RuntimeErrorSummary,
    RuntimeErrorSummaryPayload,
    RuntimeHealthSeveritySummary,
    RuntimeHealthSummary,
    RuntimeInspectPageInfo,
    RuntimeInspectUnavailable,
    RuntimeListMeta,
    RuntimeListResponse,
    RuntimePartialStatus,
    RuntimeRef,
    SchedulerRunDetail,
    SchedulerRunSummary,
    ToolInvocationDetail,
    ToolInvocationSummary,
)
from quantagent.core.db.repositories import SchedulerRunRepository

_KEY_VALUE_SECRET_PATTERN = re.compile(r"(token|secret|password|cookie)=([^\s]+)", re.IGNORECASE)
_CONNECTION_SECRET_PATTERN = re.compile(r"postgresql\+\w+://[^\s]+", re.IGNORECASE)
_PATH_PATTERN = re.compile(r"(/[^/\s]+)+")
_SUPPORTED_RUNTIME_STATUSES = frozenset({"queued", "running", "succeeded", "failed", "timeout", "cancelled"})
_SUPPORTED_TRIGGER_TYPES = frozenset({"manual", "interval"})


@dataclass(frozen=True)
class RuntimeInspectListFilters:
    page: int = 1
    page_size: int = 20
    event_id: str | None = None
    trace_id: str | None = None
    plugin_id: str | None = None
    status: str | None = None
    time_from: datetime | None = None
    time_to: datetime | None = None


class RuntimeInspectService:
    def __init__(self, *, session: Session | None, request: Request) -> None:
        self._session = session
        self._request = request

    def get_runtime_health(self) -> RuntimeHealthSummary:
        unavailable_resources = [
            _unavailable_resource("agent_runs", "agent_runs_read_model_missing", "AgentRun read model is not implemented in V1."),
            _unavailable_resource(
                "tool_invocations",
                "tool_invocations_read_model_missing",
                "ToolInvocation read model is not implemented in V1.",
            ),
            _unavailable_resource(
                "runtime_errors",
                "runtime_errors_read_model_missing",
                "RuntimeError read model is not implemented in V1.",
            ),
        ]
        scheduler_status = "healthy" if self._session is not None else "unavailable"
        worker_status = "not_configured"
        partial_status: RuntimePartialStatus = "degraded" if unavailable_resources else "ready"
        return RuntimeHealthSummary(
            active_agent_run_count=0,
            recent_failed_agent_run_count=0,
            recent_failed_tool_invocation_count=0,
            runtime_error_severity_summary=RuntimeHealthSeveritySummary(critical=0, warning=0, info=0),
            backend_status=RuntimeBackendStatusSummary(
                api="healthy",
                scheduler=scheduler_status,
                worker=worker_status,
            ),
            websocket_status_hint="unknown",
            partial_status=partial_status,
            unavailable_resources=unavailable_resources,
            generated_at=datetime.now(UTC),
        )

    def list_agent_runs(self, *, filters: RuntimeInspectListFilters) -> RuntimeListResponse[AgentRunSummary]:
        self._reject_unsupported_shared_filters(filters=filters, resource_name="agent runs")
        return self._unavailable_list(
            filters=filters,
            reason="agent_runs_read_model_missing",
            message="AgentRun read model is not implemented in V1.",
        )

    def get_agent_run(self, run_id: str) -> AgentRunDetail:
        raise NotFoundError(
            "AgentRun not available",
            details={
                "resource": "agent_run",
                "run_id": run_id,
                "reason": "agent_runs_read_model_missing",
            },
        )

    def list_tool_invocations(self, *, filters: RuntimeInspectListFilters) -> RuntimeListResponse[ToolInvocationSummary]:
        self._reject_unsupported_shared_filters(filters=filters, resource_name="tool invocations")
        return self._unavailable_list(
            filters=filters,
            reason="tool_invocations_read_model_missing",
            message="ToolInvocation read model is not implemented in V1.",
        )

    def get_tool_invocation(self, invocation_id: str) -> ToolInvocationDetail:
        raise NotFoundError(
            "ToolInvocation not available",
            details={
                "resource": "tool_invocation",
                "invocation_id": invocation_id,
                "reason": "tool_invocations_read_model_missing",
            },
        )

    def list_runtime_errors(self, *, filters: RuntimeInspectListFilters, severity: str | None = None, component: str | None = None) -> RuntimeListResponse[RuntimeErrorSummary]:
        self._reject_unsupported_shared_filters(filters=filters, resource_name="runtime errors")
        if severity is not None and not severity.strip():
            raise BadRequestError("severity must not be empty")
        if component is not None and not component.strip():
            raise BadRequestError("component must not be empty")
        return self._unavailable_list(
            filters=filters,
            reason="runtime_errors_read_model_missing",
            message="RuntimeError read model is not implemented in V1.",
        )

    def get_runtime_error(self, error_id: str) -> RuntimeErrorDetail:
        raise NotFoundError(
            "RuntimeError not available",
            details={
                "resource": "runtime_error",
                "error_id": error_id,
                "reason": "runtime_errors_read_model_missing",
            },
        )

    def list_scheduler_runs(
        self,
        *,
        filters: RuntimeInspectListFilters,
        trigger_type: str | None = None,
    ) -> RuntimeListResponse[SchedulerRunSummary]:
        repository = self._require_scheduler_run_repository()
        status = _normalize_optional_str(filters.status)
        plugin_id = _normalize_optional_str(filters.plugin_id)
        if filters.trace_id is not None:
            raise BadRequestError(
                "SchedulerRun inspect does not support trace_id filter in V1",
                details={"resource": "scheduler_runs", "filter": "trace_id"},
            )
        if status is not None and status not in _SUPPORTED_RUNTIME_STATUSES:
            raise BadRequestError("Unsupported scheduler run status", details={"status": status})
        normalized_trigger_type = _normalize_optional_str(trigger_type)
        if normalized_trigger_type is not None and normalized_trigger_type not in _SUPPORTED_TRIGGER_TYPES:
            raise BadRequestError("Unsupported scheduler trigger type", details={"trigger_type": normalized_trigger_type})
        if filters.event_id is not None:
            raise BadRequestError(
                "SchedulerRun inspect does not support event_id filter in V1",
                details={"resource": "scheduler_runs", "filter": "event_id"},
            )

        records = repository.list_runs(
            status=status,
            source_plugin_id=plugin_id,
            request_id=None,
            trigger_mode=normalized_trigger_type,
            started_from=filters.time_from,
            started_to=filters.time_to,
            limit=filters.page_size,
            offset=(filters.page - 1) * filters.page_size,
        )
        items = []
        for record in records:
            items.append(_scheduler_run_summary(record))
        return RuntimeListResponse(
            items=items,
            meta=RuntimeListMeta(
                state="empty" if not items else "ready",
                page=RuntimeInspectPageInfo(page=filters.page, page_size=filters.page_size, returned=len(items)),
                unavailable=None,
            ),
        )

    def get_scheduler_run(self, run_id: str) -> SchedulerRunDetail:
        repository = self._require_scheduler_run_repository()
        record = repository.get(run_id)
        if record is None:
            raise NotFoundError("SchedulerRun not found", details={"run_id": run_id})
        return _scheduler_run_detail(record)

    def _require_scheduler_run_repository(self) -> SchedulerRunRepository:
        if self._session is None:
            raise ServiceUnavailableError(
                "SchedulerRun inspect is temporarily unavailable",
                details={"resource": "scheduler_runs", "reason": "database_not_configured"},
            )
        return SchedulerRunRepository(self._session)

    def _reject_unsupported_shared_filters(self, *, filters: RuntimeInspectListFilters, resource_name: str) -> None:
        unsupported_filters = []
        if filters.event_id is not None:
            unsupported_filters.append("event_id")
        if filters.trace_id is not None:
            unsupported_filters.append("trace_id")
        if filters.plugin_id is not None:
            unsupported_filters.append("plugin_id")
        if filters.status is not None:
            unsupported_filters.append("status")
        if filters.time_from is not None:
            unsupported_filters.append("time_from")
        if filters.time_to is not None:
            unsupported_filters.append("time_to")
        if unsupported_filters:
            raise BadRequestError(
                f"{resource_name.title()} filters are not implemented in V1",
                details={"unsupported_filters": unsupported_filters},
            )

    def _unavailable_list(
        self,
        *,
        filters: RuntimeInspectListFilters,
        reason: str,
        message: str,
    ) -> RuntimeListResponse[Any]:
        return RuntimeListResponse(
            items=[],
            meta=RuntimeListMeta(
                state="unavailable",
                page=RuntimeInspectPageInfo(page=filters.page, page_size=filters.page_size, returned=0),
                unavailable=_unavailable_resource("runtime_inspect", reason, message),
            ),
        )


def _scheduler_run_summary(record: Any) -> SchedulerRunSummary:
    return SchedulerRunSummary(
        run_id=record.run_id,
        binding_id=record.binding_id,
        plugin_id=record.source_plugin_id,
        request_id=record.request_id,
        trigger_type=record.trigger_mode,
        status=record.status,
        started_at=record.started_at,
        ended_at=record.finished_at,
        duration_ms=record.duration_ms,
        error_summary=_build_scheduler_error_summary(record),
    )


def _scheduler_run_detail(record: Any) -> SchedulerRunDetail:
    summary = _scheduler_run_summary(record)
    return SchedulerRunDetail(
        **summary.model_dump(),
        event_ref=None,
        captured_count_summary={"captured_count": int(record.captured_count or 0)},
    )


def _build_scheduler_error_summary(record: Any) -> RuntimeErrorSummaryPayload | None:
    if record.failure_code is None and record.failure_message is None:
        return None
    return RuntimeErrorSummaryPayload(
        error_code=record.failure_code or "SCHEDULER_RUN_FAILED",
        error_message_summary=_sanitize_text(record.failure_message or "Scheduler run failed."),
        failure_stage=record.failure_stage,
        retryable=record.retryable,
    )


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _sanitize_text(value: str) -> str:
    sanitized = _KEY_VALUE_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[masked]", value)
    sanitized = _CONNECTION_SECRET_PATTERN.sub("[masked-connection]", sanitized)
    sanitized = _PATH_PATTERN.sub("[path]", sanitized)
    return sanitized


def _unavailable_resource(resource: str, reason: str, message: str) -> RuntimeInspectUnavailable:
    return RuntimeInspectUnavailable(status="unavailable", reason=f"{resource}:{reason}", message=message)
