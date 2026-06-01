from __future__ import annotations

import asyncio
import logging
import os
import sys
from uuid import uuid4

from quantagent.core.scheduling import PluginTriggerRequest, PluginTriggerType
from quantagent.scheduler.runtime import SchedulerRuntime, create_scheduler_runtime

logger = logging.getLogger(__name__)

# 默认插件 ID，可通过 SCHEDULE_PLUGIN_ID 环境变量覆盖
_DEFAULT_PLUGIN_ID = "quantagent.official.source.placeholder"


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
