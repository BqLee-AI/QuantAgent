from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from quantagent.core.config import settings
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.db.session import create_session_factory
from quantagent.core.events import (
    EventBusRuntime,
    EventBusSettings,
    SourceEventPublisher,
    build_event_bus_runtime,
)
from quantagent.core.registry import PluginRegistry, RegistryScanner
from quantagent.core.runtime import PluginRuntimeService
from quantagent.core.scheduling import SourceBindingService
from quantagent.core.worker_routing import (
    IndustryAnalysisRequestedPublisher,
    SourceBindingOwnerResolver,
    TopicPublishingIndustryGateway,
    WorkerArticleEnrichmentService,
    WorkerCapturedEventRoutingService,
)
from quantagent.worker.consumer import CapturedSourceEventHandler, InMemoryWorkerRouteAuditSink


def create_worker_runtime() -> EventBusRuntime:
    """组装 worker 的 event bus runtime，不在入口定义协议细节。"""
    return build_event_bus_runtime(EventBusSettings.from_settings(settings))


@dataclass(frozen=True)
class WorkerApp:
    runtime: EventBusRuntime
    handler: CapturedSourceEventHandler
    session: object

    async def consume_once(self) -> None:
        await self.runtime.consumer.subscribe(
            topics=("source.event.captured",),
            group_id=settings.EVENT_BUS_KAFKA_DEFAULT_GROUP_ID,
            handler=self.handler,
        )

    async def close(self) -> None:
        close = getattr(self.session, "close", None)
        if callable(close):
            close()
        await self.runtime.close()


def create_worker_app() -> WorkerApp:
    runtime = create_worker_runtime()
    session = create_session_factory()()
    registry = PluginRegistry(
        RegistryScanner(
            official_root=_repo_root() / "plugins",
            runtime_root=_repo_root() / "runtime" / "plugins",
        )
    )
    plugin_runtime = PluginRuntimeService()
    binding_service = SourceBindingService(SourceBindingRepository(session))
    handler = CapturedSourceEventHandler(
        routing_service=WorkerCapturedEventRoutingService(
            binding_service=binding_service,
            owner_resolver=SourceBindingOwnerResolver(),
            industry_gateway=TopicPublishingIndustryGateway(
                publisher=IndustryAnalysisRequestedPublisher(runtime.publisher)
            ),
            enrichment_service=WorkerArticleEnrichmentService(
                registry=registry,
                runtime=plugin_runtime,
            ),
        ),
        audit_sink=InMemoryWorkerRouteAuditSink(),
    )
    return WorkerApp(runtime=runtime, handler=handler, session=session)


async def run_once() -> None:
    app = create_worker_app()
    try:
        await app.consume_once()
    finally:
        await app.close()


def run() -> None:
    # V1 CLI 执行一次订阅/消费主流程；长期 loop 后续只扩展生命周期，不把业务塞回入口。
    asyncio.run(run_once())


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]
