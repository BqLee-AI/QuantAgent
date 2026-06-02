## Why

`hitl-approval-orchestration-v1` 已经把审批主链路收成 core-only harness：`action.requested -> approval.requested / notification.requested -> approval.input_received -> approval.completed`。它同时明确 `notification.requested` 只表示“平台请求发送通知”，不表示 notification dispatcher 已选择插件、`notification.send` 已调用、外部 provider 已送达或 `notification.completed` 已发布。

`add-discord-experimental-plugins` 已经落地官方 `Discord Notification` 插件，支持 `notification.send` 和 `notification.receive`。`notification-receive-handoff-v1` 已经让成功的 `notification.receive` item 进入 `NotificationReceiveFact`、append-only ingress audit 和 `NotificationApprovalHandoffPort`。当前缺口不是插件能力本身，而是平台还没有把 HITL 审批通知的发送请求调度到 Discord 插件，也没有在 API 真实 ingress 中把 approval handoff adapter 注入进去。

如果不单独收口这条真实接线，后续实现容易出现两个问题：

- 把 `notification.requested` 误当成真实发送完成，跳过 dispatcher / send result / completed 语义。
- 在 API 或 Discord 插件里直接拼审批状态，绕过 `NotificationReceiveFact`、approval handoff adapter、`ApprovalOrchestrationService` 和 Policy Gate。

本 change 只收“Discord 审批通知闭环”这一刀：把审批产生的脱敏 `notification.requested` 发送到官方 Discord notification 插件，并让真实 Discord interaction 回流通过通用 notification ingress 进入 approval input。

## What Changes

- 新增 `notification-discord-approval-loop-v1` capability，定义审批通知从 `notification.requested` 到 Discord `notification.send`，再从 Discord `notification.receive` 回流到 approval input 的平台闭环。
- 在 core 层规划 notification dispatcher / sender service：消费 `notification.requested`，构造 `NotificationSendInput`，通过 Registry + Runtime 调用目标 notification 插件；事件处理路径必须发布 `notification.completed`，同步 service 调用路径只能返回 `NotificationDispatchResult`，不能用私有摘要替代 topic 契约。
- 在 API 层规划真实 ingress 接线：`NotificationIngressHostService` 仍是通用 HTTP host，但需要能注入带 `ApprovalNotificationHandoffAdapter` 的 `NotificationIngressService`，让成功 receive item 进入 approval 域。
- 固定 Discord 审批消息的最小文本协议：发送内容必须带可回流的 `approval_id`，但不得包含 secret、完整 prompt、私有策略、交易密钥或真实 broker credential。
- 固定安全边界：Discord 文本 approve 仍属于弱确认；是否 approve、reject、escalate、execute 由 approval evaluator、Policy Gate 和 executor port 决定，Discord 插件不做业务判断。

## Out Of Scope

- 不实现多 provider dispatcher 策略、插件市场配置 UI、多租户 routing、多 endpoint binding 或插件配置持久化。
- 不支持 Discord message component、button、modal、autocomplete、followup message、deferred response、gateway 或 polling。
- 不新增数据库表、Alembic migration、生产级 outbox、DLQ、持久化 notification delivery record 或审计表。
- 不接真实 broker、真实下单、live trading、生产账户或 broker credential。
- 不让 Discord 插件、API host 或 dispatcher 直接创建 approved 状态、发布 `approval.completed`、调用 Policy Gate 或调用 executor。
- 不把 `notification.completed` 表达成用户已审批、动作已执行或 broker 已完成。

## Capabilities

### New Capabilities

- `notification-discord-approval-loop-v1`：定义 HITL 审批通知的 Discord 发送 dispatcher、发送完成语义、真实 ingress approval handoff 注入、消息脱敏和回流验证。

### Modified Capabilities

- `hitl-approval-orchestration-v1`：实现其后续 notification dispatcher / sender change 的承接范围，不改变 HITL core approval 的安全语义。
- `notification-receive-handoff-v1`：复用已落地的 `NotificationApprovalHandoffPort`，在 API 真实 ingress 中接入 approval adapter。
- `discord-experimental-plugins`：复用官方 Discord notification 插件的 `notification.send` / `notification.receive` capability，不把插件升级成审批服务。
- `kafka-event-bus-v1`：复用当前 topic policy 中已允许的 `notification.requested` / `notification.completed`；本 change 补充 `notification.completed` payload 语义，不新增 topic。

## Impact

- OpenSpec：新增 `openspec/changes/notification-discord-approval-loop-v1/`。
- 后续 core 实现：主要影响 `packages/core/src/quantagent/core/notifications/`、`packages/core/src/quantagent/core/approval/` 的集成 seam、`packages/core/src/quantagent/core/events/` topic 文档与 tests。
- 后续 API 实现：主要影响 `apps/api/src/quantagent/api/services/notification_ingress.py`、API app state / dependency composition、`apps/api/README.md` 和 API tests。
- 后续插件实现：原则上不需要改 Discord 插件协议；如需消息格式 helper，应保留在平台 sender，不让插件理解审批状态。
- Review 流程：本 change 属于 OpenSpec-only PR 输入；维护者明确评论“没问题”或批准前，不进入实现代码 PR。
