from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from quantagent.core.registry import PluginRegistry, PluginStatus, PluginType
from quantagent.core.registry.scanner import RegistryScanner
from quantagent.core.runtime import PluginRuntimeService
from quantagent.core.scheduling import (
    FrozenSchedulingClock,
    InMemoryPluginRunRepository,
    PluginRunStatus,
    PluginSchedulingService,
    PluginTriggerRequest,
    PluginTriggerType,
)


PLACEHOLDER_PLUGIN_ID = "quantagent.official.source.placeholder"


class PluginFoundationDemoStagesTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.clock = FrozenSchedulingClock(datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc))
        self.repository = InMemoryPluginRunRepository()

    def test_stage_1_registry_discovers_placeholder_manifest(self) -> None:
        registry = self._registry()

        record = registry.get_plugin(PLACEHOLDER_PLUGIN_ID)

        self.assertIsNotNone(record)
        self.assertEqual(record.status, PluginStatus.VALID)
        self.assertEqual(record.path, Path("plugins/sources/placeholder-source").resolve())
        self.assertIsNotNone(record.manifest)
        self.assertEqual(record.manifest.type, PluginType.SOURCE)
        self.assertEqual(record.manifest.entrypoint, "placeholder_source:plugin")
        self.assertEqual(record.manifest.capabilities, ("source.fetch",))
        self._print_stage(
            "阶段 1 / Registry",
            implemented=True,
            how="RegistryScanner 扫描真实 plugins/ 目录，读取 plugin.yaml，校验 manifest/config schema 后生成 PluginRecord。",
            evidence=(
                f"插件 {record.id} 已发现，状态={record.status.value}，类型={record.manifest.type.value}，"
                f"入口={record.manifest.entrypoint}，能力={', '.join(record.manifest.capabilities)}。"
            ),
        )

    async def test_stage_2_runtime_loads_entrypoint_and_returns_source_output(self) -> None:
        record = self._placeholder_record()

        invocation = await PluginRuntimeService().invoke(
            record,
            capability="source.fetch",
            request_id="req-demo-runtime",
            config={"query": "config-default"},
            input={},
            metadata={"origin": "demo-stage-runtime"},
        )

        self.assertTrue(invocation.ok)
        self.assertIsNotNone(invocation.result)
        self.assertEqual(invocation.result.output["items"][0]["external_id"], "placeholder:config-default")
        self.assertEqual(invocation.result.output["items"][0]["metadata"]["plugin_id"], PLACEHOLDER_PLUGIN_ID)
        self.assertEqual(invocation.result.output["items"][0]["metadata"]["request_id"], "req-demo-runtime")
        self.assertEqual(invocation.result.output["metadata"]["source"], "placeholder")
        self._print_stage(
            "阶段 2 / Runtime",
            implemented=True,
            how=(
                "PluginRuntimeService 使用 PluginRecord.path 定位插件目录里的 entrypoint 文件，"
                "用隔离模块名加载 placeholder_source:plugin，注入 RuntimeContext 后调用 source.fetch。"
            ),
            evidence=(
                "插件返回 SourceFetchResult DTO，external_id="
                f"{invocation.result.output['items'][0]['external_id']}，"
                f"request_id={invocation.result.output['items'][0]['metadata']['request_id']}。"
            ),
        )

    async def test_stage_3_scheduling_records_lifecycle_and_audit_summary(self) -> None:
        service = PluginSchedulingService(
            registry=self._registry(),
            runtime=PluginRuntimeService(),
            repository=self.repository,
            clock=self.clock,
        )

        run = await service.trigger(
            PluginTriggerRequest(
                plugin_id=PLACEHOLDER_PLUGIN_ID,
                capability="source.fetch",
                request_id="req-demo-scheduling",
                trigger_type=PluginTriggerType.MANUAL,
                input={"query": "rss"},
                effective_config={},
                metadata={"origin": "demo-stage-scheduling"},
            )
        )

        self.assertEqual(run.status, PluginRunStatus.SUCCEEDED)
        self.assertEqual(run.plugin_id, PLACEHOLDER_PLUGIN_ID)
        self.assertEqual(run.metadata["origin"], "demo-stage-scheduling")
        self.assertEqual(run.output_summary["items"][0]["external_id"], "placeholder:rss")
        self.assertEqual(run.output_summary["items"][0]["metadata"]["request_id"], "req-demo-scheduling")
        self.assertEqual(run.output_summary["metadata"]["source"], "placeholder")
        self.assertEqual(
            [item.status for item in self.repository.get_history(run.run_id)],
            [PluginRunStatus.QUEUED, PluginRunStatus.RUNNING, PluginRunStatus.SUCCEEDED],
        )
        self._print_stage(
            "阶段 3 / Scheduling",
            implemented=True,
            how=(
                "PluginSchedulingService 接收 PluginTriggerRequest，查询 Registry，调用 Runtime，"
                "并把 queued/running/succeeded 生命周期写入 PluginRunRecord 审计记录。"
            ),
            evidence=(
                f"run_id={run.run_id}，状态={run.status.value}，"
                f"history={[item.status.value for item in self.repository.get_history(run.run_id)]}，"
                f"output_summary.items[0].external_id={run.output_summary['items'][0]['external_id']}。"
            ),
            note="这一步只证明调度和审计已跑通；RawEvent 入库、去重、Event Bus、真实 RSS 抓取仍是后续后端能力。",
        )

    def _registry(self) -> PluginRegistry:
        return PluginRegistry(
            RegistryScanner(
                official_root=Path("plugins"),
                runtime_root=Path("runtime/plugin-foundation-demo-missing"),
            )
        )

    def _placeholder_record(self):
        record = self._registry().get_plugin(PLACEHOLDER_PLUGIN_ID)
        assert record is not None
        return record

    def _print_stage(
        self,
        stage: str,
        *,
        implemented: bool,
        how: str,
        evidence: str,
        note: str | None = None,
    ) -> None:
        lines = [
            "",
            f"[插件底座 Demo] {stage}",
            f"- 是否实现：{'是' if implemented else '否'}",
            f"- 怎么实现：{how}",
            f"- 验证结果：{evidence}",
        ]
        if note is not None:
            lines.append(f"- 边界说明：{note}")
        print("\n".join(lines))


if __name__ == "__main__":
    unittest.main()
