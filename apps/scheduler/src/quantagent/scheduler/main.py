from __future__ import annotations

from quantagent.core.config import settings
from quantagent.core.events import EventBusRuntime, EventBusSettings, build_event_bus_runtime


def create_scheduler_runtime() -> EventBusRuntime:
    """组装 scheduler 的 event bus runtime，不在入口写死 event 协议。"""
    return build_event_bus_runtime(EventBusSettings.from_settings(settings))


def run() -> None:
    # 当前 scheduler 只固定 composition root；真实调度 loop 由后续 issue 驱动。
    create_scheduler_runtime()
