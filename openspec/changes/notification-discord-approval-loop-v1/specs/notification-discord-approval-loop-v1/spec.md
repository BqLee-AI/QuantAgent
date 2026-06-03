## ADDED Requirements

### Requirement: 平台 SHALL 调度审批通知到 notification 插件

系统 SHALL 在收到 `notification.requested` 后，通过平台 dispatcher 选择已配置的 notification 插件并调用 `notification.send`。

#### Scenario: notification.requested 调用 Discord send
- **WHEN** approval 编排发布包含 `approval_id` 的 `notification.requested`
- **AND** notification dispatcher 已启用并配置 `quantagent.official.notification.discord`
- **THEN** dispatcher 构造 `NotificationSendInput`
- **AND** 通过 Registry record 与 Runtime invoke 调用 `notification.send`
- **AND** 不直接 import Discord 插件实现

#### Scenario: dispatcher 不把 requested 当作已送达
- **WHEN** 系统发布 `notification.requested`
- **THEN** 该事件仍只表示发送请求
- **AND** 只有 dispatcher 完成插件调用后才可以发布 `notification.completed`
- **AND** `notification.completed` 不表示用户已审批、不表示 broker 已执行

#### Scenario: dispatcher 缺配置时安全降级
- **WHEN** dispatcher 未启用、目标插件不存在、插件状态非法或缺少 `notification.send`
- **THEN** 系统不调用插件
- **AND** 事件处理路径发布 failed `notification.completed`
- **AND** 同步 service 路径返回 failed `NotificationDispatchResult`
- **AND** 错误不暴露本地路径、webhook URL、secret、token 或 traceback

### Requirement: Discord 审批通知消息 SHALL 脱敏并携带可回流 approval_id

系统 SHALL 将审批通知转换为适合 Discord 文本发送的脱敏消息，并包含可由回流 adapter 解析的审批 ID。

#### Scenario: 消息包含最小审批上下文
- **WHEN** dispatcher 构造 Discord 审批通知文本
- **THEN** 文本包含 `approval_id: <id>`
- **AND** 文本包含动作摘要、风险方向、确认等级和可选过期时间
- **AND** 文本说明用户可以回复 approve、reject 或 reanalysis

#### Scenario: 消息不泄露敏感信息
- **WHEN** `notification.requested` 来源 action 包含 prompt、secret、token、cookie、私有策略或 broker credential
- **THEN** Discord 文本不包含这些原文
- **AND** `NotificationSendInput.metadata` 也不包含这些原文

#### Scenario: 文本消息不是放行凭证
- **WHEN** 用户收到 Discord 审批通知
- **THEN** 该消息本身不表示 action approved
- **AND** 该消息本身不表示 dry-run、broker 或 live trading 已执行成功

### Requirement: 平台 SHALL 发布发送完成摘要

系统 SHALL 在 notification 插件调用完成后生成发送完成摘要，用于区分发送请求、插件调用结果和审批结果。

#### Scenario: 成功发送生成 completed 摘要
- **WHEN** Discord 插件返回 `NotificationSendResult(accepted=true)`
- **THEN** dispatcher 发布 `notification.completed`
- **AND** payload 至少包含 notification request id、plugin id、accepted、retryable、code、message、approval id 和 action request id

#### Scenario: 发送失败保留 retryable 语义
- **WHEN** Discord 插件返回网络超时、网络错误或上游拒绝
- **THEN** dispatcher 在结果中保留 `retryable`
- **AND** 第一刀不要求生产级重试队列或 DLQ

#### Scenario: completed payload 不表达审批或执行结果
- **WHEN** 系统发布 `notification.completed`
- **THEN** payload 不包含 `approval.completed` 的 decision status
- **AND** payload 不表达用户 approve/reject
- **AND** payload 不表达真实 broker 成交或执行成功

### Requirement: 真实 notification ingress SHALL 注入 approval handoff

系统 SHALL 为真实 API notification ingress 提供 approval handoff adapter 注入 seam，使成功 receive item 在配置了 approval runtime 时可以进入 approval input。

#### Scenario: Discord interaction 回流进入 approval input
- **WHEN** Discord interaction webhook 通过签名校验并被插件解析为 `NotificationReceiveItem`
- **AND** item 文本包含可解析的 `approval_id`
- **THEN** notification ingress 记录 `NotificationReceiveFact`
- **AND** 追加 `notification.receive.recorded` 审计
- **AND** 调用 `ApprovalNotificationHandoffAdapter`
- **AND** adapter 将输入映射为 `ApprovalInput` 或发布 `approval.input_received`

#### Scenario: API host 不理解 Discord 业务语义
- **WHEN** API host 处理 `/api/v1/integrations/notifications/ingress`
- **THEN** API host 只读取 headers、body、query、path 和 request id
- **AND** 不解析 Discord slash command 字段
- **AND** 不判定 approve/reject/reanalysis
- **AND** 不调用 Policy Gate 或 executor

#### Scenario: 无 approval runtime 时不误报闭环完成
- **WHEN** API 运行环境没有配置 approval service 或 approval input publisher
- **THEN** notification ingress 可以保留 no-op handoff
- **AND** 系统必须明确返回或记录 handoff ignored
- **AND** 不得声称真实审批 input 已进入 approval 编排

### Requirement: Discord 回流输入 SHALL 复用 approval 安全评估

系统 SHALL 将 Discord 回流视为 approval input，由 approval evaluator 和 Policy Gate 决定后续状态。

#### Scenario: Discord approve 仍需 evaluation 和 Policy Gate
- **WHEN** Discord 回流文本表达 approve
- **THEN** handoff adapter 只生成 `ApprovalInput`
- **AND** approval evaluator 解释 intent
- **AND** 只有满足确认等级且 Policy Gate 允许后才可以调用 executor

#### Scenario: manual-only 或强确认不被文本满足
- **WHEN** 审批要求 manual-only、strong confirm 或 link confirm
- **AND** Discord 文本回复 approve
- **THEN** approval evaluator 生成 escalated 或等价安全结果
- **AND** executor 不被调用

#### Scenario: 未知审批 ID 安全失败
- **WHEN** Discord 回流文本缺少 approval id 或引用不存在的 approval id
- **THEN** notification fact 可以保留
- **AND** handoff 返回 failed 或 ignored
- **AND** Policy Gate 不被调用
- **AND** executor 不被调用

#### Scenario: 终态审批不被 Discord 输入改写
- **WHEN** Discord 回流引用已 completed、expired、rejected、blocked 或 escalated 的审批
- **THEN** 系统返回 ignored / already completed 摘要或结构化失败
- **AND** 不改变最终 decision
- **AND** executor 不被调用

### Requirement: 插件边界 SHALL 保持协议适配职责

系统 SHALL 保持 Discord 插件只负责 Discord 协议适配，不承担平台审批业务。

#### Scenario: Discord 插件不依赖 approval 域
- **WHEN** 实现官方 Discord notification 插件
- **THEN** 插件不得 import `quantagent.core.approval`
- **AND** 插件不得直接发布 Event Bus topic
- **AND** 插件不得写 approval request、approval input、decision 或 audit record

#### Scenario: Core 不依赖具体 Discord 插件
- **WHEN** 实现 notification dispatcher 或 ingress handoff
- **THEN** `packages/core` 不得 import `plugins.notifications.discord`
- **AND** 只能通过 Registry、Runtime 和 plugin-sdk DTO 调用插件

### Requirement: 默认验证 SHALL 不依赖真实 Discord 网络

系统 SHALL 用单元测试覆盖平台闭环，并将真实 Discord smoke 保持为显式补充验证。

#### Scenario: 单元测试使用 fake runtime 或 mock transport
- **WHEN** 运行默认 core / API 单元测试
- **THEN** 测试不需要真实 Discord webhook URL
- **AND** 不需要真实 Discord public/private key
- **AND** 不需要外部网络

#### Scenario: 真实 Discord smoke 是 env-gated
- **WHEN** 开发者提供真实 Discord 环境变量并手动运行 smoke
- **THEN** 可以验证真实 webhook send 或 interaction receive
- **AND** smoke 通过不表示生产级重试、投递持久化、审批执行或 broker 执行已完成
