## Context

当前 `NotificationIngressService` 已经能：

- 校验 plugin record 与 capability
- 调用 `notification.receive`
- 校验 `NotificationReceiveResult`
- 把协议响应交回 API host

但它还没做平台侧后续处理。成功 `item` 只在返回值里存在，既不是平台事实，也没有审计，也没有向 approval 主链显式移交。

这次设计要解决的问题很具体：

- 给 `notification.receive` 成功后的平台侧真源一个最小落点
- 保持 append-only 审计
- 为后续 `#241` 提供可替换的 approval handoff seam
- 不在 core 里提前实现 approval 编排

## Goals

- 保持 `NotificationIngressService` 仍是 notification ingress 唯一平台编排入口
- 成功 `item` 进入统一的 `NotificationReceiveFact`
- 每次 fact 创建与 handoff 都生成 append-only 审计记录
- 默认 handoff 行为可安全 no-op，保证当前实现不会误导为“已经完成审批”

## Non-Goals

- 不实现 approval 领域对象
- 不引入 Event Bus topic
- 不把 notification ingress service 变成 approval service
- 不引入数据库依赖

## File Plan

新增或修改以下文件：

- `packages/core/src/quantagent/core/notifications/models.py`
  - 定义 receive fact / audit / handoff 模型
- `packages/core/src/quantagent/core/notifications/repository.py`
  - 定义 `NotificationReceiveFactRepository`
  - 提供 `InMemoryNotificationReceiveFactRepository`
- `packages/core/src/quantagent/core/notifications/audit.py`
  - 定义 `NotificationIngressAuditSink`
  - 提供 `InMemoryNotificationIngressAuditSink`
- `packages/core/src/quantagent/core/notifications/handoff.py`
  - 定义 `NotificationApprovalHandoffPort`
  - 提供 `NoopNotificationApprovalHandoff`
  - 提供 `InMemoryNotificationApprovalHandoff`
- `packages/core/src/quantagent/core/notifications/ingress.py`
  - 串接上述 seam
- `packages/core/src/quantagent/core/notifications/README.md`
  - 记录职责边界
- `packages/core/tests/test_notification_ingress.py`
  - 补充 fact / audit / handoff 验证

## Layering

调用链保持：

```text
apps/api host
  -> NotificationIngressService
  -> runtime invoke(notification.receive)
  -> NotificationReceiveResult
  -> NotificationReceiveFactRepository
  -> NotificationIngressAuditSink
  -> NotificationApprovalHandoffPort
```

职责约束：

- API host 仍然只做 transport host
- 插件继续只做协议适配
- `NotificationIngressService` 只做 notification ingress 平台编排
- approval handoff port 只表达“把事实移交给后续审批入口”，不在本 change 内实现审批业务

## Models

### `NotificationReceiveFact`

字段：

- `fact_id`
- `plugin_id`
- `transport`
- `request_id`
- `correlation_id`
- `interaction_id`
- `source_id`
- `text`
- `payload_summary`
- `metadata`
- `received_at`
- `guild_id`
- `channel_id`
- `author_id`

说明：

- 这是平台侧事实，不是 plugin DTO
- `metadata` 只保存 JSON-safe 摘要，不回填原始 body 或敏感 secret

### `NotificationIngressAuditEntry`

字段：

- `audit_id`
- `event_type`
- `plugin_id`
- `request_id`
- `correlation_id`
- `recorded_at`
- `details`

说明：

- 审计采用 append-only 语义
- 当前至少覆盖：
  - `notification.receive.recorded`
  - `notification.receive.approval_handoff`

### `NotificationApprovalHandoffRequest`

字段：

- `handoff_id`
- `fact_id`
- `plugin_id`
- `transport`
- `request_id`
- `correlation_id`
- `interaction_id`
- `source_id`
- `text`
- `payload_summary`
- `metadata`
- `received_at`
- `guild_id`
- `channel_id`
- `author_id`

说明：

- 它是 approval 域的前置移交 DTO，不是 approval 域本体
- 它只描述“平台已经收到并标准化了一条 notification receive 输入”

## Repository / Sink / Port

### `NotificationReceiveFactRepository`

当前提供：

- `create(fact)`
- `get(fact_id)`
- `list(plugin_id=None)`

第一版只给内存实现，用于验证平台事实边界。后续数据库化时可替换实现，不改 ingress service。

### `NotificationIngressAuditSink`

当前提供：

- `append(entry)`
- `list()`

同样只提供内存实现，但语义固定为 append-only。

### `NotificationApprovalHandoffPort`

当前提供：

- `async handoff(request) -> NotificationApprovalHandoffResult`

默认实现：

- `NoopNotificationApprovalHandoff`
  - 返回 `ignored`
  - 明确表示“事实已记录，但还没有接入 approval workflow”
- `InMemoryNotificationApprovalHandoff`
  - 记录请求并返回预设结果，供测试使用

## Ingress Behavior

`NotificationIngressService.receive()` 新行为：

1. 校验 plugin record、capability 和 `NotificationReceiveResult`
2. 若 `accepted=false` 或 `item is None`
   - 直接返回
   - 不生成 fact
   - 不触发 handoff
3. 若 `accepted=true` 且存在 `item`
   - 生成 `NotificationReceiveFact`
   - 保存到 repository
   - 追加 `notification.receive.recorded` 审计
   - 构造 `NotificationApprovalHandoffRequest`
   - 调用 handoff port
   - 成功时追加 `notification.receive.approval_handoff` 审计
   - 失败时保留 fact，并追加 `notification.receive.approval_handoff_failed` 审计
   - 把 fact 与 handoff result 附加到返回值

## Correlation / Request Rules

- `request_id` 沿用 ingress host 传入值
- `correlation_id` 优先取 `receive_input.request_metadata.correlation_id`
- 若未提供，则回退为由 `interaction_id` + `request_id` 派生的稳定值

这样后续 `#241` 可以直接复用 correlation 链，而不需要重新猜 notification ingress 这层的关联关系。

## Security / Audit Notes

- 不保存原始 HTTP body
- 不保存 signature header、public key、secret ref 明文
- `metadata` 只保存 request metadata、item metadata 和 plugin metadata 的 JSON-safe 摘要
- 中文注释与 README 明确写出：approval handoff seam 不是审批完成

## Why This Does Not Conflict With #241

`#241` 负责 approval 领域编排，本 change 只负责前置 notification ingress 平台落点。

具体区分：

- 本 change 创建的是 `NotificationReceiveFact`
- `#241` 将来创建的是 approval 领域对象
- 本 change 只调用 `NotificationApprovalHandoffPort`
- `#241` 将来实现这个 port 背后的审批服务、topic、状态机和策略

因此依赖方向会是：

```text
notification ingress -> approval handoff port -> future approval orchestration
```

而不是：

```text
notification ingress 直接实现 approval orchestration
```

## Validation

最小验证：

- `packages/core/tests/test_notification_ingress.py`
  - response-only 成功路径不生成 fact
  - 有 `item` 的成功路径生成 fact
  - 有 `item` 的成功路径追加两条审计
  - handoff 异常时保留 fact，并生成 failed audit
  - handoff port 被调用并接收到 fact 对应的字段
  - `accepted=false` 路径不触发 fact / handoff
- `openspec validate notification-receive-handoff-v1 --type change --strict`
