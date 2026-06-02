## Context

当前已有三段能力：

- `ApprovalOrchestrationService` 会在需要通知人类时发布 `notification.requested`，payload 是脱敏的审批摘要。
- 官方 `Discord Notification` 插件声明 `notification.send` / `notification.receive`，能发送最小文本到 Discord webhook，也能接收 Discord interaction webhook 并输出标准化 item。
- `NotificationIngressService` 成功收到 `notification.receive` item 后，可以记录 `NotificationReceiveFact`、append-only ingress audit，并调用 `NotificationApprovalHandoffPort`。

缺口在两端接线：

- 发送侧缺 `notification.requested -> notification.send` dispatcher。
- 接收侧 API host 默认创建的 ingress service 使用 no-op handoff，没有把真实 receive item 交给 approval adapter。

## Goals

- 让审批通知发送请求通过 Registry + Runtime 调用官方 Discord notification 插件的 `notification.send` capability；默认测试仍可使用 fake runtime 或 mock transport。
- 让真实 Discord interaction 回流进入 approval input，而不是停在 HTTP response 或 no-op handoff。
- 保持 API host 通用、Discord 协议在插件层、审批判断在 approval 域。
- 为发送结果提供最小完成语义，避免把 `notification.requested` 误读成已送达。
- 保持所有消息、日志、审计和测试 fixture 不暴露 secret、完整 prompt、私有策略或交易密钥。

## Non-Goals

- 不新增生产数据库持久化、outbox、DLQ 或投递历史查询 API。
- 不做 Discord button/modal/followup/deferred response。
- 不支持多个 notification provider 的动态选择策略；第一刀只支持通过配置绑定一个 notification 插件。
- 不把 notification dispatcher 做成插件生命周期管理器。
- 不让 Discord 文本 approve 直接满足 strong / manual-only 确认。

## File Plan

### Core notification sender

- `packages/core/src/quantagent/core/notifications/sender.py`
  - 新增 `NotificationDispatchService`
  - 校验目标插件记录、`notification.send` capability 和插件类型
  - 构造 `NotificationSendInput`
  - 调用 `PluginRuntimeService.invoke(...)`
  - 校验 `NotificationSendResult`
  - 返回 `NotificationDispatchResult`

- `packages/core/src/quantagent/core/notifications/message.py`
  - 新增审批通知文本 builder
  - 输入 JSON-safe 的 `notification.requested` payload
  - 可以复用 `HumanAuthorizationMessage` 的字段语义，但不得依赖 approval harness 的测试类型
  - 输出脱敏 Discord 文本，必须包含 `approval_id: <id>`
  - 不依赖 Discord 插件实现，不 import `plugins/**`

- `packages/core/src/quantagent/core/notifications/models.py`
  - 增补发送侧领域模型：
    - `NotificationDispatchRequest`
    - `NotificationDispatchResult`
    - `NotificationDeliverySummary`
  - 字段保持 JSON-safe，不包含 HTTP status code 常量或 API envelope

- `packages/core/src/quantagent/core/notifications/handlers.py`
  - 新增 `NotificationRequestedHandler`
  - 消费 `EventEnvelope(topic="notification.requested")`
  - 调用 `NotificationDispatchService`
  - 通过 `NotificationEventPublisher` 发布 `notification.completed`

- `packages/core/src/quantagent/core/notifications/publishers.py`
  - 新增 `NotificationEventPublisher`
  - 发布 `notification.completed`
  - payload 只表达发送尝试结果，不表达用户审批或 broker 执行结果

- `packages/core/src/quantagent/core/notifications/README.md`
  - 更新发送侧职责、接收侧 handoff 和非目标

- `packages/core/tests/test_notification_dispatch.py`
  - 覆盖 dispatcher、消息脱敏、plugin invoke、失败路径、completed payload

- `packages/core/tests/test_notification_approval_loop.py`
  - 覆盖从 `notification.requested` 到 dispatcher，再到 notification receive handoff 的内存闭环

### API ingress wiring

- `apps/api/src/quantagent/api/services/notification_ingress.py`
  - 允许注入已配置的 `NotificationIngressService` 或 handoff port，避免 host 内部只能创建 no-op service
  - 当前代码尚无 API 生产级 approval service app state；本 change 只要求提供组合 seam，测试可注入 approval service 或 event bus publisher
  - 不在 API service 中解析 Discord payload、不判定 approve/reject、不调用 Policy Gate

- `apps/api/src/quantagent/api/main.py` 或现有 app state composition 文件
  - 若运行入口已经有 approval service / event bus app state，则在 app 创建时组装 `ApprovalNotificationHandoffAdapter`
  - 若没有生产级 approval service，则保留 no-op，并在 README/测试中说明“ingress 可用”不等于“审批回流已接入”

- `apps/api/src/tests/test_app.py`
  - 覆盖 notification ingress 启用时可使用注入 handoff
  - 覆盖缺少 approval runtime 时不误报已完成审批
  - 覆盖错误响应不泄露 Discord webhook URL、公钥或 secret

- `apps/api/README.md`
  - 更新 Discord approval loop 配置说明
  - 明确 `NOTIFICATION_INGRESS_PLUGIN_CONFIG` 只放插件配置
  - 明确真实 Discord smoke 是 env-gated 补充验证

### Discord plugin

第一刀不要求修改 `plugins/notifications/discord/src/discord_plugin.py`。如果实现发现需要最小兼容，只允许改插件 README/tests 或增强 config schema 文档，不让插件理解 approval service、Event Bus 或 Policy Gate。

## Layering

发送链路：

```text
ApprovalOrchestrationService
  -> EventEnvelope(topic=notification.requested)
  -> NotificationRequestedHandler
  -> NotificationDispatchService
  -> PluginRegistry.get_plugin(configured_plugin_id)
  -> PluginRuntimeService.invoke(capability=notification.send)
  -> NotificationSendResult
  -> NotificationEventPublisher.publish_notification_completed()
```

接收链路：

```text
POST /api/v1/integrations/notifications/ingress
  -> NotificationIngressHostService
  -> NotificationIngressService
  -> PluginRuntimeService.invoke(capability=notification.receive)
  -> NotificationReceiveFact + NotificationIngressAuditEntry
  -> ApprovalNotificationHandoffAdapter
  -> ApprovalInput or EventEnvelope(topic=approval.input_received)
  -> ApprovalOrchestrationService.submit_input()
```

依赖方向：

```text
apps/api -> packages/core -> packages/plugin-sdk <- plugins/notifications/discord
```

禁止方向：

- `packages/core` 不 import `apps/api`、FastAPI、Starlette 或 `plugins/**`
- Discord 插件不 import `quantagent.core.approval`
- API host 不 import Discord plugin implementation

## Models / Event Drafts

### `NotificationDispatchRequest`

字段草案：

- `request_id`
- `plugin_id`
- `correlation_id`
- `causation_id`
- `approval_id`
- `action_request_id`
- `channel`
- `text`
- `metadata`

说明：

- `text` 是发送给 notification 插件的脱敏文本。
- `metadata` 可包含 `approval_id`、`action_request_id`、`source_topic`，不得包含完整 prompt、secret、token、cookie、私有策略或 broker credential。

### `NotificationDispatchResult`

字段草案：

- `request_id`
- `plugin_id`
- `accepted`
- `retryable`
- `code`
- `message`
- `correlation_id`
- `causation_id`
- `approval_id`
- `action_request_id`
- `metadata`

说明：

- `accepted=true` 只表示插件接受或 provider 请求成功，不表示用户已看见、不表示审批完成。
- `retryable=true` 表示平台可重试，但第一刀不实现持久化重试队列。
- 该模型是同步 service 返回值和测试断言对象，不替代 `notification.completed` 事件契约。

### `notification.completed` payload

最小字段：

- `notification_request_id`
- `plugin_id`
- `accepted`
- `retryable`
- `code`
- `message`
- `approval_id`
- `action_request_id`
- `channel`

禁止字段：

- Discord webhook URL
- public/private key
- signature header
- 完整 prompt
- secret、token、cookie
- 私有策略和 broker credential
- live trading / broker success 语义

## Message Format

第一刀使用纯文本消息，不引入 Discord component：

```text
QuantAgent approval requested
approval_id: <approval-id>
summary: <sanitized summary>
risk: <risk_direction>
confirmation: <required_confirmation_level>
expires_at: <optional expires_at>

Reply with:
approval_id: <approval-id> approve
approval_id: <approval-id> reject
approval_id: <approval-id> reanalysis
```

规则：

- 必须包含 `approval_id: <id>`，保证回流 adapter 能解析。
- 允许包含 `action_request_id`，但不得包含 `proposed_payload` 原文。
- 文本 approve 进入 approval evaluator 后仍按弱确认处理；manual-only / strong confirm 可能 escalated。

## Configuration

第一刀配置保持保守：

- API ingress 继续使用：
  - `NOTIFICATION_INGRESS_ENABLED`
  - `NOTIFICATION_INGRESS_PLUGIN_ID`
  - `NOTIFICATION_INGRESS_PLUGIN_CONFIG`
- 发送 dispatcher 可新增 API/worker 运行时配置：
  - `NOTIFICATION_DISPATCH_ENABLED`
  - `NOTIFICATION_DISPATCH_PLUGIN_ID`
  - `NOTIFICATION_DISPATCH_PLUGIN_CONFIG`
  - `NOTIFICATION_DISPATCH_CHANNEL=discord`

配置约束：

- dispatcher 是 core 能力，运行入口可以是 API 测试 harness、worker 或后续专用 consumer；本 change 不把长期归属固定到 API。
- 插件 secret 继续通过 `webhook_secret_ref` 和 `__secrets__` 或后续 secret resolver 传递，不在 OpenSpec、README 示例或测试 fixture 中写真实 URL。
- 如果实现阶段无法提供安全 secret resolver，则 dispatcher tests 使用 fake runtime / mock plugin，不要求真实 Discord webhook。

## Failure Paths

- `notification.requested` payload 非 mapping 或缺少 `approval_id`：dispatcher 拒绝，发布 failed `notification.completed` 或返回结构化失败，不调用插件。
- 配置未启用 dispatcher：handler 忽略或返回 disabled 摘要，不调用插件，不影响 approval pending 状态。
- 插件不存在、状态非法或缺少 `notification.send`：发送失败，结果不泄露本地路径或 secret。
- Runtime invoke 失败或插件返回非法 DTO：发送失败，`retryable` 根据错误类型保守设置。
- Discord webhook 网络超时：插件返回 retryable，dispatcher 不重复执行无限重试。
- Discord interaction 签名非法：由插件返回 401 响应，不生成 fact，不进入 approval。
- Discord interaction accepted 但缺少可解析 approval id：notification fact 保留，handoff adapter 返回 failed，不调用 Policy Gate 或 executor。
- 引用未知或终态 approval：handoff adapter 返回安全失败 / ignored，不改变最终 decision。
- 文本 approve 对 manual-only / strong confirm 不足：approval evaluator escalated，不调用 executor。

## Validation Strategy

OpenSpec-only PR 最小验证：

```bash
openspec validate notification-discord-approval-loop-v1 --type change --strict --json
```

如果 `uvx openspec` 不可用，可以使用仓库环境中的 `openspec` 可执行文件；若两者都不可用，应在最终说明中记录未验证原因，并至少检查 artifacts 路径和内容。

后续实现 PR 最小验证：

```bash
uv run python -m unittest packages/core/tests/test_notification_dispatch.py
uv run python -m unittest packages/core/tests/test_notification_approval_loop.py
uv run python -m unittest packages/core/tests/test_notification_ingress.py
cd apps/api && uv run python -m unittest discover -s src
uv run python -m unittest discover -s plugins/notifications/discord/tests -p 'test_*.py'
```

可选真实 smoke：

```bash
uv run python plugins/notifications/discord/smoke_send.py
NOTIFICATION_INGRESS_TEST_PRIVATE_KEY=<hex-private-key> uv run python plugins/notifications/discord/smoke_receive.py
```

真实 smoke 只作为 env-gated 补充验证，不作为默认验收项，不表示 broker 或审批执行完成。

## Risks / Trade-offs

- [Risk] 第一刀没有持久化 delivery record，进程重启会丢失发送历史。
  Mitigation：本 change 只验证平台通过 Runtime 发起 `notification.send` 调用和事件语义；持久化 delivery / outbox / retry queue 后续单独设计。

- [Risk] 纯文本 `approval_id` 协议可用但体验弱。
  Mitigation：先跑通安全闭环；Discord component / modal 后续独立 change。

- [Risk] API app state 可能尚未有生产级 approval service。
  Mitigation：设计允许注入 service 或 publisher；缺失时保持 no-op 并明确不能声称真实审批回流已完成。

- [Risk] `notification.completed` 容易被误读成用户已确认。
  Mitigation：spec 和 README 明确它只表达发送尝试结果，审批结论仍只看 `approval.completed`。
