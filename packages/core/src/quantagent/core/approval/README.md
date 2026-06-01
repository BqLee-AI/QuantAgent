# core approval

`quantagent.core.approval` 承载 HITL 行为请求审批编排的 core-only 边界。它把 `action.requested`、审批策略解析、人工输入评估、Policy Gate 调用点、fake executor 摘要和 `approval.completed` 收到一条可测试链路里。

## 职责

这个目录负责：

- 定义 JSON-safe approval domain models。
- 解析保守审批策略，覆盖 notify-only、execute-then-notify、approval-required、timeout、manual-only 和 blocked。
- 保存 in-memory action / approval / input / evaluation / decision 关联记录，用于测试编排和 ID 查找语义。
- 定义 `PolicyGate` 与 `ActionExecutor` port。
- 发布 `approval.requested`、`notification.requested` 和 `approval.completed`。
- 通过 `notification_handoff.py` 消费 notification ingress 已记录的 handoff fact，并转成 `ApprovalInput` 或 `approval.input_received`。
- 提供 Event Bus handler 和本地 fake harness。

这个目录不负责：

- FastAPI route、HTTP 状态码、API envelope 或 OpenAPI。
- ORM model、Alembic migration、数据库事务、outbox、replay 或 audit 表。
- Web 页面、React 状态、前端 DTO 或 generated client。
- 真实 notification provider、真实 broker、真实密钥、生产账户或 live trading。
- 具体插件实现或插件间 import。

## 入口

- `ApprovalOrchestrationService.submit_action()`：处理 `ActionRequest`。
- `ApprovalOrchestrationService.submit_input()`：处理 `ApprovalInput`。
- `ApprovalOrchestrationService.expire_approval()`：处理 timeout 收敛。
- `ActionRequestedHandler` / `ApprovalInputReceivedHandler`：只做 EventEnvelope 到 service 的适配。
- `ApprovalNotificationHandoffAdapter`：只做 notification handoff request 到 approval input 的适配。
- `harness.py`：测试专用 fake producer、fake notification consumer、fake human input producer、fake PolicyGate 和 fake executor。

## 状态边界

Event Bus 只表达状态变化，不是审批、审计或 broker 执行真源。`InMemoryApprovalRepository` 只用于第一刀 harness 和单元测试，不能作为 API / Web 数据真源。后续生产持久化、append-only audit、outbox、DLQ 和 replay 需要单独 issue / OpenSpec。

## 安全边界

用户 approve 后仍必须经过 `PolicyGate`。未注入 `PolicyGate` 时，任何可能调用 executor 的路径默认阻断。自然语言文本、IM 回复、一次性链接消息和 AI policy hint 都不能直接绕过 evaluation 和 Policy Gate。

`approval.completed` 只表达安全完成摘要和 fake executor 请求状态，不表达真实 broker 成功、live trading、真实成交或真实账户状态。
