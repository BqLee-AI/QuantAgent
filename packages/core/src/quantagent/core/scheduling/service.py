from __future__ import annotations

import asyncio
import logging
import math
import re
from collections.abc import Mapping
from dataclasses import replace
from typing import Any
from uuid import uuid4

from quantagent.core.events.ports import EventBusPublisher
from quantagent.core.events.service import SourceEventPublisher
from quantagent.core.registry.models import PluginError, PluginRecord, PluginStatus
from quantagent.core.registry.service import PluginRegistry
from quantagent.core.runtime import PluginRuntimeInvocation, PluginRuntimeService
from quantagent.core.scheduling.clock import SchedulingClock, SystemSchedulingClock
from quantagent.core.scheduling.models import PluginRunRecord, PluginRunStatus, PluginTriggerRequest
from quantagent.core.scheduling.repository import PluginRunRepository
from quantagent.plugin_sdk import PluginRuntimeError, SourceFetchResult, freeze_json_mapping
from quantagent.plugin_sdk.io import JsonObject, JsonValue

logger = logging.getLogger(__name__)


class PluginSchedulingService:
    def __init__(
        self,
        *,
        registry: PluginRegistry,
        runtime: PluginRuntimeService,
        repository: PluginRunRepository,
        clock: SchedulingClock | None = None,
        publisher: EventBusPublisher | None = None,
    ) -> None:
        self._registry = registry
        self._runtime = runtime
        self._repository = repository
        self._clock = clock or SystemSchedulingClock()
        self._publisher = publisher

    async def trigger(self, request: PluginTriggerRequest) -> PluginRunRecord:
        run: PluginRunRecord | None = None
        started_monotonic = self._clock.monotonic()

        try:
            # Revalidate before creating a normal run so tampered DTOs still become audited failures.
            validated_request = _revalidate_request(request)
            plugin_record = self._registry.get_plugin(validated_request.plugin_id)
            run, started_monotonic = self._start_run(validated_request, plugin_record)
            precheck_error = _precheck_plugin(plugin_record, capability=validated_request.capability)
            if precheck_error is not None:
                return self._finish_run(run, status=PluginRunStatus.FAILED, error_summary=_error_to_summary(precheck_error), started_monotonic=started_monotonic)

            invocation = await self._invoke_runtime(plugin_record, validated_request)
            runtime_error = _primary_runtime_error(invocation)
            if runtime_error is not None:
                cleanup_error = invocation.cleanup_error if invocation.error is not None else None
                return self._finish_run(
                    run,
                    status=PluginRunStatus.FAILED,
                    error_summary=_error_to_summary(runtime_error, cleanup_error=cleanup_error),
                    started_monotonic=started_monotonic,
                )

            output_summary = _summarize_mapping(invocation.result.output if invocation.result is not None else {})
            finished_run = self._finish_run(
                run,
                status=PluginRunStatus.SUCCEEDED,
                output_summary=output_summary,
                started_monotonic=started_monotonic,
            )
            await self._maybe_publish_source_event(invocation, finished_run, validated_request)
            return finished_run
        except asyncio.TimeoutError:
            return self._finish_run(
                _ensure_run(run),
                status=PluginRunStatus.TIMEOUT,
                error_summary=_error_to_summary(
                    PluginError(
                        code="PLUGIN_INVOKE_TIMEOUT",
                        message="Plugin invoke exceeded the configured timeout.",
                        stage="invoke",
                        details={"plugin_id": request.plugin_id, "timeout_ms": request.timeout_ms},
                    )
                ),
                started_monotonic=started_monotonic,
            )
        except PluginRuntimeError as exc:
            if run is None:
                run, started_monotonic = self._start_failed_precheck_run(request)
            return self._finish_run(
                run,
                status=PluginRunStatus.FAILED,
                error_summary=_error_to_summary(exc),
                started_monotonic=started_monotonic,
            )
        except Exception as exc:
            if run is None:
                run, started_monotonic = self._start_failed_precheck_run(request)
            return self._finish_run(
                run,
                status=PluginRunStatus.FAILED,
                error_summary=_error_to_summary(
                    PluginError(
                        code="PLUGIN_SCHEDULING_FAILED",
                        message="Scheduling failed before runtime invoke completed.",
                        stage="schedule_precheck",
                        details={"error_type": exc.__class__.__name__, "plugin_id": request.plugin_id},
                    )
                ),
                started_monotonic=started_monotonic,
            )

    def _start_run(
        self,
        request: PluginTriggerRequest,
        plugin_record: PluginRecord | None,
    ) -> tuple[PluginRunRecord, float]:
        run = self._repository.create(
            PluginRunRecord(
                run_id=f"run_{uuid4().hex}",
                plugin_id=request.plugin_id,
                plugin_version=_plugin_version(plugin_record),
                capability=request.capability,
                request_id=request.request_id,
                trigger_type=request.trigger_type,
                status=PluginRunStatus.QUEUED,
                timeout_ms=request.timeout_ms,
                metadata=request.metadata,
            )
        )

        started_monotonic = self._clock.monotonic()
        return (
            self._repository.update(
                replace(
                    run,
                    status=PluginRunStatus.RUNNING,
                    started_at=self._clock.now(),
                )
            ),
            started_monotonic,
        )

    def _start_failed_precheck_run(self, request: PluginTriggerRequest) -> tuple[PluginRunRecord, float]:
        run = PluginRunRecord(
            run_id=f"run_{uuid4().hex}",
            plugin_id=_safe_identifier(request.plugin_id, fallback="invalid-plugin-id"),
            plugin_version=None,
            capability=_safe_identifier(request.capability, fallback="invalid-capability"),
            request_id=_safe_identifier(request.request_id, fallback="invalid-request-id"),
            trigger_type=request.trigger_type,
            status=PluginRunStatus.RUNNING,
            started_at=self._clock.now(),
            timeout_ms=request.timeout_ms,
        )
        self._repository.create(replace(run, status=PluginRunStatus.QUEUED, started_at=None))
        started_monotonic = self._clock.monotonic()
        return self._repository.update(run), started_monotonic

    async def _invoke_runtime(self, record: PluginRecord, request: PluginTriggerRequest) -> PluginRuntimeInvocation:
        invoke_coro = self._runtime.invoke(
            record,
            capability=request.capability,
            request_id=request.request_id,
            config=request.effective_config,
            input=request.input,
            metadata=request.metadata,
        )
        if request.timeout_ms is None:
            return await invoke_coro
        return await asyncio.wait_for(invoke_coro, timeout=request.timeout_ms / 1000)

    async def _maybe_publish_source_event(
        self,
        invocation: PluginRuntimeInvocation,
        run: PluginRunRecord,
        request: PluginTriggerRequest,
    ) -> None:
        if self._publisher is None:
            return
        if request.capability != "source.fetch":
            return
        if invocation.result is None or not invocation.result.output:
            return
        try:
            source_result = SourceFetchResult.from_mapping(invocation.result.output, stage="publish")
            await SourceEventPublisher(self._publisher).publish_source_fetch_result(
                source_result,
                producer="plugin-scheduling",
                request_id=request.request_id,
                plugin_id=request.plugin_id,
                causation_id=run.run_id,
            )
        except Exception as exc:
            logger.warning(
                "Event publish failed after successful scheduling.",
                extra={"plugin_id": run.plugin_id, "run_id": run.run_id, "error_type": type(exc).__name__},
            )

    def _finish_run(
        self,
        run: PluginRunRecord,
        *,
        status: PluginRunStatus,
        started_monotonic: float,
        output_summary: Mapping[str, JsonValue] | None = None,
        error_summary: Mapping[str, JsonValue] | None = None,
    ) -> PluginRunRecord:
        finished_record = replace(
            run,
            status=status,
            finished_at=self._clock.now(),
            duration_ms=max(0, int((self._clock.monotonic() - started_monotonic) * 1000)),
            output_summary=output_summary or {},
            error_summary=error_summary,
        )
        return self._repository.update(finished_record)


def _plugin_version(record: PluginRecord | None) -> str | None:
    if record is None or record.manifest is None:
        return None
    return record.manifest.version


def _ensure_run(run: PluginRunRecord | None) -> PluginRunRecord:
    if run is None:
        raise RuntimeError("Scheduling run must exist before timeout handling.")
    return run


def _safe_identifier(value: Any, *, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return fallback


def _revalidate_request(request: PluginTriggerRequest) -> PluginTriggerRequest:
    return replace(
        request,
        input=freeze_json_mapping(request.input, stage="invoke"),
        effective_config=freeze_json_mapping(request.effective_config, stage="config"),
        metadata=freeze_json_mapping(request.metadata, stage="schedule_precheck"),
    )


def _precheck_plugin(record: PluginRecord | None, *, capability: str) -> PluginError | None:
    if record is None:
        return PluginError(
            code="PLUGIN_NOT_FOUND",
            message="Plugin record was not found in registry.",
            stage="schedule_precheck",
            details={"capability": capability},
        )
    if record.status != PluginStatus.VALID:
        return PluginError(
            code="PLUGIN_RECORD_NOT_LOADABLE",
            message="Plugin record is not valid for runtime loading.",
            stage="load",
            details={"plugin_id": record.id, "status": record.status.value},
        )
    if record.manifest is None:
        return PluginError(
            code="PLUGIN_MANIFEST_MISSING",
            message="Plugin record does not include a manifest.",
            stage="load",
            details={"plugin_id": record.id},
        )
    if capability not in record.manifest.capabilities:
        return PluginError(
            code="PLUGIN_CAPABILITY_UNAVAILABLE",
            message="Plugin capability is not declared by manifest.",
            stage="invoke",
            details={"plugin_id": record.id, "capability": capability},
        )
    return None


def _primary_runtime_error(invocation: PluginRuntimeInvocation) -> PluginError | None:
    if invocation.error is not None:
        return invocation.error
    return invocation.cleanup_error


SENSITIVE_KEYWORDS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "password",
        "secret",
        "session",
        "token",
    }
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)(token|secret|password|cookie|authorization|api[_-]?key)\s*[:=]\s*[^,\s]+"
)
LOCAL_PATH_PATTERN = re.compile(r"(/(?:home|tmp|var|Users)/[^\s,;]+|[A-Za-z]:\\[^\s,;]+)")
REDACTED = "[REDACTED]"


def _error_to_summary(
    error: PluginError | PluginRuntimeError,
    *,
    cleanup_error: PluginError | None = None,
) -> JsonObject:
    details = dict(_sanitize_mapping(error.details))
    if cleanup_error is not None:
        details["cleanup_error"] = _error_to_summary(cleanup_error)
    # Preserve the source stage so DTO validation failures stay attributable to the failing boundary.
    return freeze_json_mapping(
        {
            "code": error.code,
            "message": _sanitize_string(error.message),
            "stage": error.stage,
            "retryable": error.retryable,
            "details": details,
        },
        stage=error.stage,
    )


def _summarize_mapping(value: Mapping[str, Any]) -> JsonObject:
    return freeze_json_mapping(
        {str(key): _sanitize_json_value(item, key=str(key)) for key, item in value.items()},
        stage="invoke",
    )


def _sanitize_mapping(value: Mapping[str, Any]) -> Mapping[str, JsonValue]:
    return {str(key): _sanitize_json_value(item, key=str(key)) for key, item in value.items()}


def _sanitize_json_value(value: Any, *, key: str | None = None) -> JsonValue:
    if key is not None and _is_sensitive_key(key):
        return REDACTED
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return f"[NON_FINITE_FLOAT:{value!r}]"
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, Mapping):
        return {str(child_key): _sanitize_json_value(child_value, key=str(child_key)) for child_key, child_value in value.items()}
    if isinstance(value, list | tuple):
        return tuple(_sanitize_json_value(item, key=key) for item in value)
    return f"[UNSERIALIZABLE:{value.__class__.__name__}]"


def _sanitize_string(value: str) -> str:
    return LOCAL_PATH_PATTERN.sub(REDACTED, SENSITIVE_VALUE_PATTERN.sub(REDACTED, value))


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(keyword in normalized for keyword in SENSITIVE_KEYWORDS)
