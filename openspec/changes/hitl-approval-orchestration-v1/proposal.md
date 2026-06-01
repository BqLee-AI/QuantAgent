## Why

当前 Event Bus V1 已经落地 `EventEnvelope`、固定 topic policy、memory backend、Kafka adapter、publisher / consumer ports，以及 `SourceEventPublisher` 示例链路。`docs/design/08-api-and-websocket-design.md` 已经定义 HITL 授权主链路：

```text
ActionRequest
  -> ApprovalPolicyResolver
  -> ApprovalRequest
  -> ApprovalInput
  -> ApprovalEvaluation
  -> ApprovalDecision
  -> Policy Gate
  -> Broker / Notification / Reanalysis
```

缺口在于：core 还没有把“行为请求进入审批处理链路”收成可测试、可复用、可审计的编排边界。若继续让 Decision、Approval、Notification、dry-run 各自拼 payload 或绕过统一服务，后续会出现 topic 语义、审批策略、通知消息、人工输入和 Policy Gate 放行条件各自漂移的问题。

同时，`notification-receive-handoff-v1` 已经把 `notification.receive` 收口为 `NotificationReceiveFact`、append-only ingress audit 和 `NotificationApprovalHandoffPort`。因此本 change 不再把外部通知回流当成尚未存在的 fake seam，而是在 approval 域消费这条 handoff：外部渠道输入先由 notification ingress 记录为平台事实，再由 approval handoff adapter 转成 `ApprovalInput` 或发布 `approval.input_received`。

本 change 先用 OpenSpec 固定 `action.requested -> approval.requested / notification.requested -> notification.receive handoff -> approval.input_received -> approval.completed` 的 core-only 消息闭环，让后续实现 PR 有同一条证据链。

## What Changes

- 新增 `hitl-approval-orchestration-v1` capability，定义 HITL 行为请求审批编排的 core 边界、模型、事件流、失败路径和验证口径。
- 修改 `kafka-event-bus-v1` topic policy，新增 `action.requested` 和 `approval.input_received` 两个稳定 topic。
- 固定后续实现落点：`packages/core/src/quantagent/core/approval/` 承载 domain models、policy resolver、rule evaluator、in-memory repository、ports、publisher helper、orchestration service 和 event handlers。
- 固定第一刀范围：使用 `InMemoryEventBus`、`NotificationApprovalHandoffPort` 测试实现与 fake producer / executor / PolicyGate 跑通审批消息闭环，不接 API、数据库、Web、真实 broker。
- 固定安全边界：用户输入、一次性链接、IM 文本和 AI hint 都不能直接放行执行；approve 后仍必须经过 Policy Gate。
- 固定 dry-run 边界：第一刀不发布 `broker.dry_run_requested`，只通过 fake `ActionExecutor` 和 `approval.completed` 的执行摘要表达 mock / dry-run 请求结果。

## Out Of Scope

- 不实现 Approval REST API、FastAPI router、OpenAPI、`packages/contracts` 或前端真实数据接入。
- 不新增数据库表、Alembic migration、持久化 repository、outbox、replay、DLQ 或 audit log 表。
- 不接真实 Discord、Telegram、Email、WebSocket notification consumer。
- 不接真实 broker、真实券商、真实密钥、生产账户或 live trading。
- 不把 dry-run、通知或用户 approve 表达成真实执行完成。
- 不允许插件直接创建 approved 状态、直接发布 Event Bus 消息或绕过 core Approval / Policy Gate。
- 不在 `packages/core` 中引入 FastAPI、React、具体 app 入口或具体插件实现依赖。

## Capabilities

### New Capabilities

- `hitl-approval-orchestration-v1`：定义 HITL 行为请求审批的 core 编排链路、授权模式、人工输入评估、通知消息生成、Policy Gate 调用点、完成事件和测试 harness。

### Modified Capabilities

- `kafka-event-bus-v1`：扩展默认 topic policy，允许 `action.requested` 和 `approval.input_received`。
- `notification-receive-handoff-v1`：复用 `NotificationApprovalHandoffPort` 作为外部通知输入进入 approval 域的移交 seam，不让 notification ingress 直接实现审批状态机。

## Impact

- OpenSpec：新增 `openspec/changes/hitl-approval-orchestration-v1/`，包含 proposal、design、tasks 和两个 spec delta。
- 后续 core 实现：主要影响 `packages/core/src/quantagent/core/approval/`、`packages/core/src/quantagent/core/events/topics.py`、`packages/core/src/quantagent/core/events/README.md` 与 core tests。
- 后续测试：新增 approval policy、orchestration、event handlers、topic contract 和 harness tests。
- Review 流程：本 change 属于 OpenSpec-only PR 输入；维护者明确评论“没问题”或批准前，不进入实现代码 PR。
