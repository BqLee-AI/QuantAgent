## Why

`apps/scheduler` 当前只创建 `EventBusRuntime` 就退出，没有组装 `PluginSchedulingService`，也没有真正触发任何插件。Issue #204 已完成桥接代码（`PluginSchedulingService` 接受可选 `EventBusPublisher`，`trigger()` 成功后发布 `source.event.captured` 事件），但 scheduler app 仍是一个空壳。这是整条 **插件调度 → 事件总线 → 消费** 链路跑通的最后一个组装缺口。

## What Changes

- `create_scheduler_runtime()` 从只返回 `EventBusRuntime` 升级为返回完整的 `SchedulerRuntime`（封装 EventBusRuntime + PluginSchedulingService + PluginRegistry）
- `run()` 启动后触发一次 `source.fetch`（通过环境变量 `SCHEDULE_PLUGIN_ID` 指定插件，默认 `quantagent.official.source.placeholder`），将结果通过事件总线发布，然后优雅退出
- 新增 `SchedulerRuntime` dataclass 作为 scheduler app 的 composition root 返回类型
- 事件总线后端默认为 Kafka（生产环境）；`EVENT_BUS_BACKEND=memory` 仅用于单元测试
- `run()` 输出结构化 JSON 日志（run_id、status、duration_ms 等），方便 worker 端对齐排查

## Capabilities

### New Capabilities

- `scheduler-single-trigger`: scheduler app 组装完整调度链路并执行单次插件触发，结果发到事件总线后优雅退出

### Modified Capabilities

<!-- 无现有 spec 需要修改 -->

## Impact

- **代码**: `apps/scheduler/src/quantagent/scheduler/main.py`（主改动）、`apps/scheduler/src/tests/test_scheduler_main.py`（更新测试）
- **依赖**: `packages/core` 中已有的 `PluginSchedulingService`、`PluginRegistry`、`PluginRuntimeService`、`InMemoryPluginRunRepository`、`EventBusRuntime`；无新依赖引入
- **配置**: 新增环境变量 `SCHEDULE_PLUGIN_ID`（默认 `quantagent.official.source.placeholder`）
- **运行时**: scheduler app 从空壳变为真正可调度的入口；Docker Compose 中 `scheduler` 服务可端到端验证
- **无破坏性变更**: 现有 API、core、plugin-sdk 不受影响
