## Why

当前仓库已经具备 `source.fetch -> source.event.captured` 的发布桥接、`SourceBinding` / `SchedulerRun` 持久化真源，以及 `SourceBinding` / `SchedulerRun` 的只读与动作契约，但 worker 侧仍停留在 composition root 占位，缺少“收到 captured 事件后如何按 binding/owner 路由到行业处理入口”的稳定边界。若继续直接实现，最容易退化成按 `plugin_id` 粗分发、在 worker 里硬编码行业分支，或在 #217 / #221 各自发明另一套归属规则。

## What Changes

- 定义 worker 在消费 `source.event.captured` 后的 V1 路由职责：解码事件、解析 `binding_id`、加载 `SourceBinding` 归属、解析行业入口、调用受控行业处理入口。
- 固定 V1 事件契约要求：供 worker 路由使用的 captured 事件必须携带稳定 `binding_id`，且不得退化为按 `plugin_id` 路由。
- 固定 V1 owner 范围：本轮只要求 `owner_type == "industry"` 的成功路径，其余 owner 类型返回受控失败或忽略结果，不扩展到完整 runtime/private owner 分支。
- 固定失败路径：覆盖 binding 缺失、binding 非 active、owner 不支持、重复消息、下游行业入口失败五类情形，并明确 worker 的审计 / 重试 / ack 语义边界。
- 固定 worker / core 分层：worker app 只负责消费编排与生命周期，路由、归属解析、入口解析和调用契约落在 `packages/core` seam，不把行业业务塞进 worker 入口。

## Capabilities

### New Capabilities
- `worker-captured-source-routing`: 定义 worker 消费 `source.event.captured` 后按 `SourceBinding` / owner 路由到行业处理入口的事件契约、service 分层和失败语义。

### Modified Capabilities
- `scheduling-event-bus-bridge-v1`: `source.event.captured` 的平台发布契约需要新增稳定 `binding_id` 归属位点，供 worker 路由复用。

## Impact

- 受影响真源：issue #224、#217、#221、#226，`docs/design/02-core-architecture-and-runtime.md`、`docs/design/06-source-plugin-design.md`、`docs/design/07-industry-package-design.md`。
- 预期实现边界：`apps/worker/src/quantagent/worker/**`、`packages/core/src/quantagent/core/events/**`、`packages/core/src/quantagent/core/scheduling/**`，以及对应测试与 README。
- 本 PR 仅新增 `openspec/changes/worker-route-captured-source-event-by-binding-owner-v1/**`，不混入 worker/core 实现代码、依赖升级或无关格式化。
