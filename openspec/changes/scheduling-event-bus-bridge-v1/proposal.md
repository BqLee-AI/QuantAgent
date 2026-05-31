## Why

QuantAgent 的插件调度和事件总线已经各自实现（PR #196 Kafka Event Bus V1），但彼此是孤岛：`PluginSchedulingService.trigger()` 完成插件执行后只写审计记录，从不通知事件总线。这导致整条主链路——插件调度→执行→事件发布→下游消费——从未被端到端跑通过。

Issue #204 提出需要让调度服务在插件成功执行后，将结果发布到事件总线。本 change 先用 OpenSpec 固定桥接的架构边界、接口契约和验收口径，避免后续实现 PR 在调度服务和事件总线之间引入不当耦合。

## What Changes

- 定义 `PluginSchedulingService` 接受可选 `EventBusPublisher` 的注入契约。
- 固定桥接语义：仅当 `trigger()` 返回 `SUCCEEDED` 且 `capability == "source.fetch"` 时，通过已有的 `SourceEventPublisher` 发布 `source.event.captured` 事件。
- 固定失败隔离：事件发布失败不改变 `PluginRunRecord` 状态，调度层和发布层保持关注点分离。
- 固定零回归保证：`publisher=None` 时行为与现有完全一致。
- 为后续 CLI demo、scheduler app、worker app 的端到端跑通奠定基础。

## Capabilities

### New Capabilities

- `scheduling-event-bus-bridge-v1`: 定义 PluginSchedulingService 与 EventBusPublisher 之间的桥接契约，覆盖成功路径发布、失败隔离、capability 过滤和零回归保证。

### Modified Capabilities

- 无。本 change 只新增桥接能力，不修改 `EventBusPublisher`、`SourceEventPublisher`、`EventEnvelope` 等已有契约。

## Impact

- 后续实现主要影响 `packages/core/src/quantagent/core/scheduling/service.py`（新增可选 publisher 参数和发布逻辑）和 `packages/core/tests/test_scheduling.py`（新增单元测试）。
- 不影响 `packages/core/events/` 下的任何已有模块。
- 不影响 `packages/plugin-sdk/` 下的任何已有模块。
- 不引入新的外部依赖。
- 后续依赖本 change 的 PR：CLI demo 命令、scheduler app 调度触发、worker app 消息消费。
