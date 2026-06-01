from __future__ import annotations

import os
from dataclasses import dataclass

from quantagent.core.events import (
    EventBusRuntime,
    EventBusSettings,
    build_event_bus_runtime,
)
from quantagent.core.registry.service import PluginRegistry, build_plugin_registry
from quantagent.core.runtime import PluginRuntimeService
from quantagent.core.scheduling import (
    InMemoryPluginRunRepository,
    PluginSchedulingService,
)


# composition root：封装 scheduler app 的完整运行时依赖
@dataclass
class SchedulerRuntime:
    event_bus: EventBusRuntime
    scheduling: PluginSchedulingService
    registry: PluginRegistry

    async def close(self) -> None:
        await self.event_bus.close()


def create_scheduler_runtime() -> SchedulerRuntime:
    """组装 scheduler 的完整运行时：EventBusRuntime + PluginRegistry + PluginSchedulingService。

    EVENT_BUS_BACKEND 默认为 kafka（scheduler 级覆盖，不改 Settings 全局默认）。
    memory 后端仅用于单元测试。
    """
    # scheduler 级覆盖：默认 kafka，不改 Settings 全局默认（Settings 保持 memory）
    backend = os.environ.get("EVENT_BUS_BACKEND", "kafka")
    bootstrap_servers = os.environ.get("EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS", "")

    event_bus_settings = EventBusSettings(
        backend=backend,
        kafka_bootstrap_servers=bootstrap_servers or None,
        kafka_client_id=os.environ.get("EVENT_BUS_KAFKA_CLIENT_ID", "quantagent-scheduler"),
        kafka_default_group_id=os.environ.get("EVENT_BUS_KAFKA_DEFAULT_GROUP_ID", "quantagent-scheduler"),
        topic_prefix=os.environ.get("EVENT_BUS_TOPIC_PREFIX", ""),
    )
    # 显式校验：直接构造 EventBusSettings 时不走 from_settings()，需要手动调 validate
    event_bus_settings.validate()
    event_bus = build_event_bus_runtime(event_bus_settings)

    # 默认路径 plugins/ + runtime/plugins/，依赖 Dockerfile COPY plugins ./plugins
    # 和 docker-compose.yml 的 runtime volume 挂载
    registry = build_plugin_registry()
    runtime_service = PluginRuntimeService()
    repository = InMemoryPluginRunRepository()

    scheduling = PluginSchedulingService(
        registry=registry,
        runtime=runtime_service,
        repository=repository,
        publisher=event_bus.publisher,
    )

    return SchedulerRuntime(
        event_bus=event_bus,
        scheduling=scheduling,
        registry=registry,
    )
