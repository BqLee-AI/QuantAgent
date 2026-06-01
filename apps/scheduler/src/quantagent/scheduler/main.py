from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from quantagent.core.config import settings
from quantagent.core.events import EventBusRuntime, EventBusSettings, build_event_bus_runtime
from quantagent.core.events.service import SourceEventPublisher
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.db.session import create_session_factory
from quantagent.core.registry import PluginRegistry, RegistryScanner
from quantagent.core.runtime import PluginRuntimeService
from quantagent.core.scheduling import (
    SchedulerLoopTickResult,
    SchedulerRunService,
    SourceBindingSchedulerLoopService,
    SourceBindingService,
)

logger = logging.getLogger(__name__)


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
        commit=session.commit,
        rollback=session.rollback,
        publisher=SourceEventPublisher(runtime.publisher),
        default_timeout_ms=settings.SCHEDULER_RUN_TIMEOUT_MS,
    )
    return SchedulerApp(loop_service=loop_service, runtime=runtime, session=session)


async def run_once() -> SchedulerLoopTickResult:
    app = create_scheduler_app()
    try:
        result = await app.run_once()
        _log_tick_result(result)
        return result
    finally:
        await app.close()


def run() -> None:
    asyncio.run(_run_forever())


async def _run_forever() -> None:
    app = create_scheduler_app()
    try:
        await app.run_forever()
    finally:
        await app.close()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _log_tick_result(result: SchedulerLoopTickResult) -> None:
    logger.info(
        "Scheduler tick completed.",
        extra={
            "due_bindings": result.due_bindings,
            "processed_bindings": result.processed_bindings,
            "succeeded_runs": result.succeeded_runs,
            "failed_runs": result.failed_runs,
            "persistence_failures": result.persistence_failures,
            "emitted_events": result.emitted_events,
            "duration_ms": result.duration_ms,
        },
    )
