from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from quantagent.core.config import settings
from quantagent.core.events import EventBusRuntime, EventBusSettings, build_event_bus_runtime
from quantagent.core.events.service import SourceEventPublisher
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.raw_event_capture_repository import RawEventCaptureRepository
from quantagent.core.db.repositories.raw_event_repository import RawEventRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.db.session import create_session_factory
from quantagent.core.registry import PluginRegistry, RegistryScanner
from quantagent.core.raw_events import RawEventService
from quantagent.core.runtime import PluginRuntimeService
from quantagent.core.scheduling import (
    SchedulerLoopTickResult,
    SchedulerRunService,
    SourceBindingSchedulerLoopService,
    SourceBindingService,
)

logger = logging.getLogger(__name__)
_last_idle_log_at: datetime | None = None
_last_idle_signature: tuple[object, ...] | None = None


@dataclass(frozen=True)
class SchedulerApp:
    loop_service: SourceBindingSchedulerLoopService
    runtime: EventBusRuntime
    session: Session

    async def run_once(self, *, due_limit: int | None = None) -> SchedulerLoopTickResult:
        return await self.loop_service.run_once(
            due_limit=due_limit or settings.SCHEDULER_DUE_LIMIT,
        )

    async def run_forever(self) -> None:
        await self.loop_service.run_forever(
            poll_interval_seconds=settings.SCHEDULER_POLL_INTERVAL_SECONDS,
            due_limit=settings.SCHEDULER_DUE_LIMIT,
            on_tick=_log_tick_result,
        )

    async def close(self) -> None:
        self.session.close()
        await self.runtime.close()


def create_scheduler_runtime() -> EventBusRuntime:
    """组装 scheduler 的 event bus runtime，不在入口写死 event 协议。"""
    return build_event_bus_runtime(EventBusSettings.from_settings(settings))


def create_scheduler_app() -> SchedulerApp:
    runtime = create_scheduler_runtime()
    session = create_session_factory()()
    registry = PluginRegistry(
        RegistryScanner(
            official_root=_repo_root() / "plugins",
            runtime_root=_repo_root() / "runtime" / "plugins",
        )
    )
    loop_service = SourceBindingSchedulerLoopService(
        registry=registry,
        runtime=PluginRuntimeService(),
        binding_service=SourceBindingService(SourceBindingRepository(session)),
        run_service=SchedulerRunService(SchedulerRunRepository(session)),
        raw_event_service=RawEventService(
            raw_event_repository=RawEventRepository(session),
            raw_event_capture_repository=RawEventCaptureRepository(session),
            source_binding_repository=SourceBindingRepository(session),
            scheduler_run_repository=SchedulerRunRepository(session),
        ),
        commit=session.commit,
        rollback=session.rollback,
        publisher=SourceEventPublisher(runtime.publisher),
        default_timeout_ms=settings.SCHEDULER_RUN_TIMEOUT_MS,
    )
    return SchedulerApp(loop_service=loop_service, runtime=runtime, session=session)


async def run_once() -> SchedulerLoopTickResult:
    _configure_logging()
    app = create_scheduler_app()
    try:
        logger.info(
            "Scheduler run_once started: backend=%s due_limit=%s",
            app.runtime.backend,
            settings.SCHEDULER_DUE_LIMIT,
        )
        result = await app.run_once()
        _log_tick_result(result)
        return result
    finally:
        await app.close()


def run() -> None:
    _configure_logging()
    asyncio.run(_run_forever())


async def _run_forever() -> None:
    app = create_scheduler_app()
    try:
        logger.info(
            "Scheduler service started: backend=%s poll_interval_seconds=%s due_limit=%s",
            app.runtime.backend,
            settings.SCHEDULER_POLL_INTERVAL_SECONDS,
            settings.SCHEDULER_DUE_LIMIT,
        )
        await app.run_forever()
    finally:
        await app.close()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _log_tick_result(result: SchedulerLoopTickResult) -> None:
    if result.due_bindings == 0 and result.failed_runs == 0 and result.persistence_failures == 0:
        _log_idle_tick_result(result)
        return
    logger.info(
        (
            "Scheduler tick completed: due_bindings=%s processed_bindings=%s "
            "succeeded_runs=%s failed_runs=%s emitted_events=%s duration_ms=%s next_due=%s"
        ),
        result.due_bindings,
        result.processed_bindings,
        result.succeeded_runs,
        result.failed_runs,
        result.emitted_events,
        result.duration_ms,
        _format_next_due(result),
        extra={
            "due_bindings": result.due_bindings,
            "processed_bindings": result.processed_bindings,
            "succeeded_runs": result.succeeded_runs,
            "failed_runs": result.failed_runs,
            "persistence_failures": result.persistence_failures,
            "emitted_events": result.emitted_events,
            "duration_ms": result.duration_ms,
            "next_due": _next_due_for_extra(result),
        },
    )


def _log_idle_tick_result(result: SchedulerLoopTickResult) -> None:
    global _last_idle_log_at, _last_idle_signature

    summary = result.schedule_summary
    signature: tuple[object, ...] = (
        summary.active_bindings,
        summary.active_scheduled_bindings,
        summary.cooling_down_bindings,
        summary.unscheduled_active_bindings,
        tuple((item.binding_id, item.next_run_at.isoformat()) for item in summary.next_due_bindings),
    )
    should_log = _last_idle_log_at is None or _last_idle_signature != signature
    if not should_log:
        idle_for_seconds = (result.finished_at - _last_idle_log_at).total_seconds()
        should_log = idle_for_seconds >= settings.SCHEDULER_IDLE_LOG_INTERVAL_SECONDS
    if not should_log:
        return

    _last_idle_log_at = result.finished_at
    _last_idle_signature = signature
    logger.info(
        (
            "Scheduler idle: active_bindings=%s cooling_down_bindings=%s "
            "unscheduled_active_bindings=%s next_due=%s"
        ),
        summary.active_bindings,
        summary.cooling_down_bindings,
        summary.unscheduled_active_bindings,
        _format_next_due(result),
        extra={
            "active_bindings": summary.active_bindings,
            "active_scheduled_bindings": summary.active_scheduled_bindings,
            "cooling_down_bindings": summary.cooling_down_bindings,
            "unscheduled_active_bindings": summary.unscheduled_active_bindings,
            "next_due": _next_due_for_extra(result),
        },
    )


def _format_next_due(result: SchedulerLoopTickResult) -> str:
    previews = result.schedule_summary.next_due_bindings
    if not previews:
        return "none"
    return "; ".join(
        (
            f"{item.binding_id} plugin={item.source_plugin_id} owner={item.owner_type}:{item.owner_id} "
            f"in={item.seconds_until_due}s at={item.next_run_at.isoformat()}"
        )
        for item in previews
    )


def _next_due_for_extra(result: SchedulerLoopTickResult) -> list[dict[str, object]]:
    return [
        {
            "binding_id": item.binding_id,
            "source_plugin_id": item.source_plugin_id,
            "owner_type": item.owner_type,
            "owner_id": item.owner_id,
            "next_run_at": item.next_run_at.isoformat(),
            "seconds_until_due": item.seconds_until_due,
        }
        for item in result.schedule_summary.next_due_bindings
    ]


def _configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
