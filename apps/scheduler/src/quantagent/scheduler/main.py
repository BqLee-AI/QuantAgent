from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from uuid import uuid4

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
    PluginTriggerRequest,
    PluginTriggerType,
)

logger = logging.getLogger(__name__)


# composition root：封装 scheduler app 的完整运行时依赖
@dataclass
class SchedulerRuntime:
    event_bus: EventBusRuntime
    scheduling: PluginSchedulingService
    registry: PluginRegistry

    async def close(self) -> None:
        await self.event_bus.close()


# 默认插件 ID，可通过 SCHEDULE_PLUGIN_ID 环境变量覆盖
_DEFAULT_PLUGIN_ID = "quantagent.official.source.placeholder"


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


def run() -> None:
    """CLI 入口：触发一次 source.fetch，发布事件后优雅退出。"""
    asyncio.run(_run())


async def _run() -> None:
    runtime: SchedulerRuntime | None = None
    try:
        runtime = create_scheduler_runtime()

        plugin_id = os.environ.get("SCHEDULE_PLUGIN_ID", _DEFAULT_PLUGIN_ID)
        request_id = f"req_{uuid4().hex}"

        request = PluginTriggerRequest(
            plugin_id=plugin_id,
            capability="source.fetch",
            request_id=request_id,
            trigger_type=PluginTriggerType.MANUAL,
        )

        record = await runtime.scheduling.trigger(request)

        # 结构化日志：方便 worker 端用 run_id 对齐排查
        log_method = logger.warning if record.status.value == "failed" else logger.info
        log_method(
            "scheduler trigger completed",
            extra={
                "run_id": record.run_id,
                "status": record.status.value,
                "duration_ms": record.duration_ms,
                "plugin_id": record.plugin_id,
                "capability": record.capability,
                "error_summary": record.error_summary,
            },
        )

        sys.exit(0 if record.status.value != "failed" else 1)
    except Exception:
        logger.exception("scheduler run failed")
        sys.exit(1)
    finally:
        if runtime is not None:
            await runtime.close()
