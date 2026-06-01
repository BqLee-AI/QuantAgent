from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from quantagent.core.events.service import SourceEventPublisher
from quantagent.core.registry.models import PluginError
from quantagent.core.registry.service import PluginRegistry
from quantagent.core.runtime import PluginRuntimeInvocation, PluginRuntimeService
from quantagent.core.scheduling.binding_models import SourceBindingRecord
from quantagent.core.scheduling.binding_service import SourceBindingService
from quantagent.core.scheduling.clock import SchedulingClock, SystemSchedulingClock
from quantagent.core.scheduling.models import (
    IntervalSchedulePolicy,
    PluginRunStatus,
    PluginTriggerType,
)
from quantagent.core.scheduling.run_service import SchedulerRunService
from quantagent.core.scheduling.service import (
    _build_plugin_runtime_config,
    _error_to_summary,
    _precheck_plugin,
    _primary_runtime_error,
)
from quantagent.core.source_binding.policy_models import SchedulePolicyHint
from quantagent.plugin_sdk import PluginRuntimeError, SourceFetchResult, dto_validation_error, freeze_json_mapping
from quantagent.plugin_sdk.io import JsonObject

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceBindingLoopRunResult:
    binding_id: str
    run_id: str | None
    status: PluginRunStatus | None
    request_id: str | None
    next_run_at: datetime | None
    captured_count: int
    event_published: bool
    persistence_failed: bool = False
    skipped: bool = False
    error_code: str | None = None


@dataclass(frozen=True)
class SchedulerLoopTickResult:
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    due_bindings: int
    processed_bindings: int
    succeeded_runs: int
    failed_runs: int
    skipped_bindings: int
    persistence_failures: int
    emitted_events: int
    heartbeat_at: datetime
    binding_results: tuple[SourceBindingLoopRunResult, ...]


class SourceBindingSchedulerLoopService:
    def __init__(
        self,
        *,
        registry: PluginRegistry,
        runtime: PluginRuntimeService,
        binding_service: SourceBindingService,
        run_service: SchedulerRunService,
        clock: SchedulingClock | None = None,
        commit: Callable[[], None] | None = None,
        rollback: Callable[[], None] | None = None,
        publisher: SourceEventPublisher | None = None,
        capability: str = "source.fetch",
        default_timeout_ms: int | None = None,
        actor: str = "scheduler-loop",
    ) -> None:
        self._registry = registry
        self._runtime = runtime
        self._binding_service = binding_service
        self._run_service = run_service
        self._clock = clock or SystemSchedulingClock()
        self._commit = commit or (lambda: None)
        self._rollback = rollback or (lambda: None)
        self._publisher = publisher
        self._capability = capability
        self._default_timeout_ms = default_timeout_ms
        self._actor = actor

    async def run_once(self, *, due_limit: int = 100) -> SchedulerLoopTickResult:
        started_at = self._clock.now()
        started_monotonic = self._clock.monotonic()
        due_bindings = self._binding_service.list_due_bindings(now=started_at, limit=due_limit)
        binding_results: list[SourceBindingLoopRunResult] = []

        for binding in due_bindings:
            binding_results.append(await self._run_binding(binding))

        finished_at = self._clock.now()
        duration_ms = max(0, int((self._clock.monotonic() - started_monotonic) * 1000))
        succeeded_runs = sum(1 for item in binding_results if item.status == PluginRunStatus.SUCCEEDED)
        failed_runs = sum(
            1
            for item in binding_results
            if item.status in {PluginRunStatus.FAILED, PluginRunStatus.TIMEOUT, PluginRunStatus.CANCELLED}
        )
        skipped_bindings = sum(1 for item in binding_results if item.skipped)
        persistence_failures = sum(1 for item in binding_results if item.persistence_failed)
        emitted_events = sum(1 for item in binding_results if item.event_published)

        return SchedulerLoopTickResult(
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            due_bindings=len(due_bindings),
            processed_bindings=len(binding_results),
            succeeded_runs=succeeded_runs,
            failed_runs=failed_runs,
            skipped_bindings=skipped_bindings,
            persistence_failures=persistence_failures,
            emitted_events=emitted_events,
            heartbeat_at=finished_at,
            binding_results=tuple(binding_results),
        )

    async def run_forever(
        self,
        *,
        poll_interval_seconds: float,
        due_limit: int = 100,
        stop_event: asyncio.Event | None = None,
        on_tick: Callable[[SchedulerLoopTickResult], None] | None = None,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than zero.")

        while True:
            tick = await self.run_once(due_limit=due_limit)
            if on_tick is not None:
                on_tick(tick)
            if stop_event is not None and stop_event.is_set():
                return
            try:
                if stop_event is None:
                    await asyncio.sleep(poll_interval_seconds)
                else:
                    await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
                    return
            except TimeoutError:
                continue

    async def _run_binding(self, binding: SourceBindingRecord) -> SourceBindingLoopRunResult:
        started_at = self._clock.now()
        started_monotonic = self._clock.monotonic()
        request_id = f"scheduler-{uuid4().hex}"
        metadata = freeze_json_mapping(
            {
                "binding": {
                    "binding_id": binding.binding_id,
                    "owner_type": binding.owner_type,
                    "owner_id": binding.owner_id,
                },
                "entrypoint": "scheduler.interval-loop",
            },
            stage="schedule_precheck",
        )
        run = None
        source_result = None
        run_status: PluginRunStatus | None = None
        error_summary: JsonObject | None = None
        output_summary: JsonObject = {}
        captured_count = 0
        next_run_at = None

        try:
            # 先原子 claim 再 invoke，避免两个 scheduler 基于同一个 due snapshot 重复执行同一 binding。
            claimed_binding = self._binding_service.claim_due_binding(
                binding.binding_id,
                expected_next_run_at=binding.next_run_at,
                claimed_at=started_at,
                actor=self._actor,
            )
            if claimed_binding is None:
                return SourceBindingLoopRunResult(
                    binding_id=binding.binding_id,
                    run_id=None,
                    status=None,
                    request_id=request_id,
                    next_run_at=None,
                    captured_count=0,
                    event_published=False,
                    skipped=True,
                )
            run = self._run_service.create_run(
                run_id=f"run_{uuid4().hex}",
                binding_id=binding.binding_id,
                source_plugin_id=binding.source_plugin_id,
                source_plugin_version=binding.source_plugin_version,
                trigger_mode=PluginTriggerType.INTERVAL,
                request_id=request_id,
                status=PluginRunStatus.RUNNING,
                timeout_ms=self._default_timeout_ms,
                metadata=metadata,
                started_at=started_at,
            )
            if not self._commit_initial_state(binding_id=binding.binding_id, run_id=run.run_id):
                return SourceBindingLoopRunResult(
                    binding_id=binding.binding_id,
                    run_id=run.run_id,
                    status=None,
                    request_id=request_id,
                    next_run_at=None,
                    captured_count=0,
                    event_published=False,
                    persistence_failed=True,
                    error_code="SCHEDULER_PERSISTENCE_FAILED",
                )

            try:
                policy = _load_interval_policy(binding)
            except PluginRuntimeError as exc:
                run_status = PluginRunStatus.FAILED
                error_summary = _error_to_summary(exc)
                policy = None

            precheck_error = _precheck_plugin(
                self._registry.get_plugin(binding.source_plugin_id),
                capability=self._capability,
            )
            if run_status is not None:
                pass
            elif precheck_error is not None:
                run_status = PluginRunStatus.FAILED
                error_summary = _error_to_summary(precheck_error)
            else:
                try:
                    source_result = await self._invoke_source_plugin(
                        binding=claimed_binding,
                        request_id=request_id,
                        metadata=metadata,
                    )
                    run_status = PluginRunStatus.SUCCEEDED
                    captured_count = len(source_result.items)
                    output_summary = _summarize_source_fetch_result(source_result)
                except asyncio.TimeoutError:
                    run_status = PluginRunStatus.TIMEOUT
                    error_summary = _error_to_summary(
                        PluginError(
                            code="PLUGIN_INVOKE_TIMEOUT",
                            message="Plugin invoke exceeded the configured timeout.",
                            stage="invoke",
                            details={"binding_id": binding.binding_id, "timeout_ms": self._default_timeout_ms},
                        )
                    )
                except PluginRuntimeError as exc:
                    run_status = PluginRunStatus.FAILED
                    error_summary = _error_to_summary(exc)

            finished_at = self._clock.now()
            # schedule_policy 非法时清空 next_run_at，避免 active binding 因坏配置在每个 tick 被重复扫到。
            next_run_at = policy.next_run_at(finished_at, applied_jitter_seconds=0) if policy is not None else None
            duration_ms = max(0, int((self._clock.monotonic() - started_monotonic) * 1000))
            finished = self._run_service.finish_run(
                run_id=run.run_id,
                status=run_status,
                finished_at=finished_at,
                duration_ms=duration_ms,
                failure_code=error_summary["code"] if error_summary is not None else None,
                failure_message=error_summary["message"] if error_summary is not None else None,
                failure_stage=error_summary["stage"] if error_summary is not None else None,
                retryable=error_summary["retryable"] if error_summary is not None else None,
                output_summary=output_summary,
                captured_count=captured_count,
            )
            binding_updated = self._binding_service.apply_run_result_if_active(
                binding_id=binding.binding_id,
                run_id=finished.run_id,
                status=finished.status,
                finished_at=finished.finished_at or finished_at,
                next_run_at=next_run_at,
                actor=self._actor,
            )
            if not self._commit_terminal_state(binding_id=binding.binding_id, run_id=finished.run_id):
                return SourceBindingLoopRunResult(
                    binding_id=binding.binding_id,
                    run_id=finished.run_id,
                    status=run_status,
                    request_id=request_id,
                    next_run_at=next_run_at if binding_updated is not None else None,
                    captured_count=captured_count,
                    event_published=False,
                    persistence_failed=True,
                    error_code="SCHEDULER_PERSISTENCE_FAILED",
                )

            event_published = False
            # terminal run 要落库，但只有 binding 仍 active 才允许回写下一次调度并向下游发成功事件。
            if binding_updated is not None:
                event_published = await self._publish_source_event(
                    binding=claimed_binding,
                    source_result=source_result,
                    request_id=request_id,
                    run_id=finished.run_id,
                )
            return SourceBindingLoopRunResult(
                binding_id=binding.binding_id,
                run_id=finished.run_id,
                status=run_status,
                request_id=request_id,
                next_run_at=next_run_at if binding_updated is not None else None,
                captured_count=captured_count,
                event_published=event_published,
                error_code=error_summary["code"] if error_summary is not None else None,
            )
        except Exception as exc:
            self._rollback_safely(binding_id=binding.binding_id)
            logger.exception(
                "Scheduler failed to process due binding.",
                extra={"binding_id": binding.binding_id, "error_type": exc.__class__.__name__},
            )
            return SourceBindingLoopRunResult(
                binding_id=binding.binding_id,
                run_id=run.run_id if run is not None else None,
                status=PluginRunStatus.FAILED,
                request_id=request_id,
                next_run_at=next_run_at,
                captured_count=captured_count,
                event_published=False,
                persistence_failed=True,
                error_code="SCHEDULER_LOOP_UNHANDLED_ERROR",
            )

    async def _invoke_source_plugin(
        self,
        *,
        binding: SourceBindingRecord,
        request_id: str,
        metadata: JsonObject,
    ) -> SourceFetchResult:
        record = self._registry.get_plugin(binding.source_plugin_id)
        if record is None:
            raise PluginRuntimeError(
                code="PLUGIN_NOT_FOUND",
                message="Plugin record was not found in registry.",
                stage="schedule_precheck",
            )
        runtime_config = _build_plugin_runtime_config(
            record,
            _BindingTriggerRequest(
                plugin_id=binding.source_plugin_id,
                effective_config=binding.effective_config_snapshot,
            ),
        )
        invocation = await self._invoke_runtime(
            record=record,
            request_id=request_id,
            runtime_config=runtime_config,
            metadata=metadata,
        )
        runtime_error = _primary_runtime_error(invocation)
        if runtime_error is not None:
            raise PluginRuntimeError(
                code=runtime_error.code,
                message=runtime_error.message,
                stage=runtime_error.stage,
                retryable=runtime_error.retryable,
                details=runtime_error.details,
            )
        if invocation.result is None:
            raise PluginRuntimeError(
                code="PLUGIN_INVOKE_RESULT_MISSING",
                message="Plugin invoke completed without a result payload.",
                stage="invoke",
            )
        return SourceFetchResult.from_mapping(invocation.result.output, stage="invoke")

    async def _invoke_runtime(
        self,
        *,
        record,
        request_id: str,
        runtime_config: JsonObject,
        metadata: JsonObject,
    ) -> PluginRuntimeInvocation:
        invoke_coro = self._runtime.invoke(
            record,
            capability=self._capability,
            request_id=request_id,
            config=runtime_config,
            input={},
            metadata=metadata,
        )
        if self._default_timeout_ms is None:
            return await invoke_coro
        return await asyncio.wait_for(invoke_coro, timeout=self._default_timeout_ms / 1000)

    def _commit_initial_state(self, *, binding_id: str, run_id: str) -> bool:
        try:
            # 先提交 started/heartbeat，再调用插件，避免长耗时 invoke 完全没有可审计起点。
            self._commit()
            return True
        except Exception:
            self._rollback_safely(binding_id=binding_id)
            logger.exception(
                "Scheduler failed to persist initial run state.",
                extra={"binding_id": binding_id, "run_id": run_id},
            )
            return False

    def _commit_terminal_state(self, *, binding_id: str, run_id: str) -> bool:
        try:
            # 先提交 run/history，再发布事件，避免下游看到成功事件但数据库里仍没有终态记录。
            self._commit()
            return True
        except Exception:
            self._rollback_safely(binding_id=binding_id)
            logger.exception(
                "Scheduler failed to persist terminal run state.",
                extra={"binding_id": binding_id, "run_id": run_id},
            )
            return False

    async def _publish_source_event(
        self,
        *,
        binding: SourceBindingRecord,
        source_result: SourceFetchResult | None,
        request_id: str,
        run_id: str,
    ) -> bool:
        if self._publisher is None or source_result is None or not source_result.items:
            return False
        try:
            await self._publisher.publish_source_fetch_result(
                source_result,
                producer="scheduler-loop",
                request_id=request_id,
                plugin_id=binding.source_plugin_id,
                causation_id=run_id,
                correlation_id=request_id,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Scheduler published a successful run but failed to emit source.event.captured.",
                extra={
                    "binding_id": binding.binding_id,
                    "run_id": run_id,
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            return False

    def _rollback_safely(self, *, binding_id: str) -> None:
        try:
            self._rollback()
        except Exception:
            logger.exception(
                "Scheduler rollback failed after binding processing error.",
                extra={"binding_id": binding_id},
            )


@dataclass(frozen=True)
class _BindingTriggerRequest:
    plugin_id: str
    effective_config: JsonObject


def _load_interval_policy(binding: SourceBindingRecord) -> IntervalSchedulePolicy | None:
    if not binding.schedule_policy:
        raise PluginRuntimeError(
            code="SCHEDULER_INTERVAL_POLICY_MISSING",
            message="Source binding is missing schedule_policy for interval scheduling.",
            stage="schedule_precheck",
            details={"binding_id": binding.binding_id},
        )
    try:
        hint = SchedulePolicyHint.from_mapping(binding.schedule_policy)
    except ValueError as exc:
        raise dto_validation_error(
            str(exc),
            field_name="schedule_policy",
            stage="schedule_precheck",
            details={"binding_id": binding.binding_id},
        ) from exc
    if not hint.enabled:
        raise PluginRuntimeError(
            code="SCHEDULER_INTERVAL_POLICY_DISABLED",
            message="Source binding schedule_policy is disabled while binding status is still active.",
            stage="schedule_precheck",
            details={"binding_id": binding.binding_id},
        )
    return IntervalSchedulePolicy(
        interval_seconds=hint.interval_seconds,
        jitter_seconds=hint.jitter_seconds,
        enabled=hint.enabled,
        metadata=hint.metadata,
    )


def _summarize_source_fetch_result(result: SourceFetchResult) -> JsonObject:
    return freeze_json_mapping(
        {
            "item_count": len(result.items),
            "next_cursor": result.next_cursor,
            "metadata": result.metadata,
        },
        stage="invoke",
    )
