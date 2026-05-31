from __future__ import annotations

from quantagent.core.config import settings
from quantagent.core.events import EventBusRuntime, EventBusSettings, build_event_bus_runtime


def create_worker_runtime() -> EventBusRuntime:
    """组装 worker 的 event bus runtime，不在入口定义协议细节。"""
    return build_event_bus_runtime(EventBusSettings.from_settings(settings))


def run() -> None:
    # 当前 worker 只固定 composition root；真实消费 loop 由后续 issue 驱动。
    create_worker_runtime()
