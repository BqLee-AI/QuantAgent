from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quantagent.core.events import EventBusHandler, EventBusSettings, build_event_bus_runtime
from quantagent.core.registry import PluginRegistry, RegistryScanner
from quantagent.core.runtime import PluginRuntimeService
from quantagent.core.scheduling import InMemoryPluginRunRepository, PluginSchedulingService, PluginTriggerRequest, PluginTriggerType


PLACEHOLDER_PLUGIN_ID = "quantagent.official.source.placeholder"


@dataclass
class DemoResult:
    exit_code: int
    output: str


class _RecordingConsumer(EventBusHandler):
    def __init__(self) -> None:
        self.last_envelope: Any | None = None

    async def handle(self, envelope) -> None:
        self.last_envelope = envelope


async def run_demo() -> DemoResult:
    lines: list[str] = []

    repo_root = Path(__file__).resolve().parents[5]
    registry = PluginRegistry(
        RegistryScanner(
            official_root=repo_root / "plugins",
            runtime_root=repo_root / "runtime" / "plugins",
        )
    )
    records = registry.list_plugins()
    lines.append(f"🔍 Scanning plugins... found {len(records)} plugin(s)")
    for record in records:
        if record.manifest is not None:
            marker = "✅" if record.status.value == "valid" else "⚠️"
            lines.append(f"   {marker} {record.id} v{record.manifest.version}")

    record = registry.get_plugin(PLACEHOLDER_PLUGIN_ID)
    if record is None or record.manifest is None:
        lines.append(f"❌ Required demo plugin missing: {PLACEHOLDER_PLUGIN_ID}")
        return DemoResult(exit_code=1, output="\n".join(lines))

    # Demo 固定使用 memory backend，避免宿主环境把最小闭环演示拉到 Kafka/外部依赖上。
    event_runtime = build_event_bus_runtime(
        EventBusSettings(
            backend="memory",
            kafka_bootstrap_servers=None,
            kafka_client_id="quantagent-demo",
            kafka_default_group_id="quantagent-demo",
            topic_prefix=None,
        )
    )
    consumer = _RecordingConsumer()
    await event_runtime.consumer.subscribe(
        topics=("source.event.captured",),
        group_id="quantagent-demo",
        handler=consumer,
    )

    scheduling = PluginSchedulingService(
        registry=registry,
        runtime=PluginRuntimeService(),
        repository=InMemoryPluginRunRepository(),
        publisher=event_runtime.publisher,
    )
    request = PluginTriggerRequest(
        plugin_id=PLACEHOLDER_PLUGIN_ID,
        capability="source.fetch",
        request_id="demo-source-fetch",
        trigger_type=PluginTriggerType.MANUAL,
        input={"query": "demo"},
        effective_config={},
        metadata={"origin": "quantagent-demo"},
    )

    lines.append("")
    lines.append("🚀 Triggering plugin: source.fetch")
    lines.append(f"   Plugin: {PLACEHOLDER_PLUGIN_ID}")

    try:
        run = await scheduling.trigger(request)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        lines.append(f"❌ Demo failed before scheduling completed: {exc.__class__.__name__}")
        await event_runtime.close()
        return DemoResult(exit_code=1, output="\n".join(lines))

    lines.append(f"   Status: {run.status.value.upper()} {'✓' if run.status.value == 'succeeded' else '✗'}")
    lines.append(f"   Duration: {run.duration_ms or 0}ms")

    if consumer.last_envelope is None:
        lines.append("")
        lines.append("❌ Consumer did not receive source.event.captured")
        await event_runtime.close()
        return DemoResult(exit_code=1, output="\n".join(lines))

    envelope = consumer.last_envelope
    lines.append("")
    lines.append(f"📤 Event published to: {envelope.topic}")
    lines.append(f"   Event ID: {envelope.id}")
    lines.append(f"   Items: {len(envelope.payload.get('items', []))} source item(s)")
    lines.append("")
    lines.append("📩 Consumer received event!")
    lines.append(f"   Topic: {envelope.topic}")
    lines.append(f"   Payload: {{ plugin_id: \"{envelope.payload.get('plugin_id')}\", items: {len(envelope.payload.get('items', []))} }}")
    lines.append("")
    lines.append("✨ Demo complete! The full pipeline works.")

    await event_runtime.close()
    return DemoResult(exit_code=0, output="\n".join(lines))


def main() -> int:
    result = asyncio.run(run_demo())
    print(result.output)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
