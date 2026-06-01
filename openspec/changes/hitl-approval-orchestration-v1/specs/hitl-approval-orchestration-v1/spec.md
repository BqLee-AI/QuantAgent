## ADDED Requirements

### Requirement: HITL 编排接收行为请求事件

系统 SHALL 在 core 层通过 `action.requested` 事件接收 Agent、Decision 或工具发出的行为请求，并将其转换为审批编排输入。

#### Scenario: action.requested 进入审批编排
- **WHEN** fake AI 或 Decision producer 发布 `action.requested`
- **THEN** `ActionRequestedHandler` 通过 Event Bus handler contract 消费该 envelope
- **AND** handler 将 JSON-safe payload 映射为 `ActionRequest`
- **AND** handler 调用 `ApprovalOrchestrationService.submit_action()`
- **AND** handler 不直接创建 approved 状态、不调用 broker、不绕过 Policy Gate

#### Scenario: 非法行为请求被结构化拒绝
- **WHEN** `action.requested` payload 缺少必要字段、包含不可 JSON 序列化对象或包含禁止对象
- **THEN** 编排入口拒绝该请求
- **AND** 错误摘要不暴露 secret、token、cookie、完整 prompt、私有策略或交易密钥
- **AND** executor 不被调用

### Requirement: HITL 编排解析审批策略

系统 SHALL 根据 `ActionRequest` 解析 `ResolvedApprovalPolicy`，并覆盖通知、等待审批、限时审批、强人工确认和阻断等模式。

#### Scenario: 所有授权模式都有确定行为
- **WHEN** `ApprovalPolicyResolver` 处理行为请求
- **THEN** 它支持 `no_approval_notify_only`
- **AND** 支持 `execute_then_notify`
- **AND** 支持 `approval_required`
- **AND** 支持 `approval_with_timeout`
- **AND** 支持 `manual_only`
- **AND** 支持 `blocked`
- **AND** 每个结果包含确认等级、允许通道、过期动作和安全理由摘要

#### Scenario: AI hint 不能绕过系统底线
- **WHEN** `ActionRequest.ai_policy_hint` 建议更宽松的授权模式
- **THEN** 系统底线规则、用户策略和策略约束仍优先
- **AND** AI hint 不得直接生成 approved decision
- **AND** 增加风险动作默认需要更强确认

### Requirement: HITL 编排创建审批请求并发布通知

系统 SHALL 在需要人工介入时创建 `ApprovalRequest`，保存关联关系，并发布 `approval.requested` 与 `notification.requested`。

#### Scenario: approval_required 进入 pending approval
- **WHEN** policy mode 为 `approval_required`
- **THEN** 编排服务创建 `ApprovalRequest(status=pending)`
- **AND** repository 能通过 `approval_id` 和 `action_request_id` 找回原始 action 与审批请求
- **AND** 系统发布 `approval.requested`
- **AND** 系统发布 `notification.requested`

#### Scenario: notify-only 不创建执行请求
- **WHEN** policy mode 为 `no_approval_notify_only`
- **THEN** 系统发布 `notification.requested`
- **AND** 系统发布 `approval.completed` 表达不需要审批或仅通知完成
- **AND** Policy Gate 不被调用
- **AND** executor 不被调用

#### Scenario: execute_then_notify 先过 Policy Gate 再执行
- **WHEN** policy mode 为 `execute_then_notify`
- **THEN** 系统不等待人工输入
- **AND** 系统必须先调用 Policy Gate
- **AND** 只有 Policy Gate 允许后才调用 fake executor
- **AND** 系统发布 `notification.requested`
- **AND** 系统发布 `approval.completed`
- **AND** completed payload 只表达 mock / dry-run 请求摘要，不表达真实 broker 成功

#### Scenario: blocked 直接完成为阻断
- **WHEN** policy mode 为 `blocked`
- **THEN** 系统发布 `approval.completed` 表达 blocked
- **AND** 不发布可确认的 approval link
- **AND** Policy Gate 不被调用
- **AND** executor 不被调用

### Requirement: 通知消息必须脱敏并保留授权上下文

系统 SHALL 将 `notification.requested` 转换为脱敏的 `HumanAuthorizationMessage`，用于测试人工授权消息生成边界，并 SHALL 通过 notification ingress handoff seam 接收外部通知回流。

#### Scenario: fake notification consumer 生成安全授权消息
- **WHEN** fake notification consumer 消费 `notification.requested`
- **THEN** 它生成 `HumanAuthorizationMessage`
- **AND** 消息包含审批 ID、动作摘要、风险方向、确认等级、过期动作、允许通道和安全上下文
- **AND** 消息不包含 secret、token、cookie、完整 prompt、私有策略、交易密钥或未经允许的敏感交易细节

#### Scenario: notification.requested 不是真实发送完成
- **WHEN** approval 编排发布 `notification.requested`
- **THEN** 该事件只表示平台请求发送一条通知
- **AND** 它不表示 notification dispatcher 已选择插件
- **AND** 它不表示 `notification.send` 已被调用
- **AND** 它不表示外部 provider 已送达
- **AND** 它不表示 `notification.completed` 已发布

#### Scenario: 消息不能充当直接放行凭证
- **WHEN** 用户看到 `HumanAuthorizationMessage`
- **THEN** 该消息只能用于生成人工输入或引导确认
- **AND** 消息本身不表示动作已经 approved
- **AND** 消息本身不表示 broker 或 dry-run 已执行成功

#### Scenario: notification receive handoff 进入 approval 域
- **WHEN** notification ingress 已经把外部用户回复记录为 `NotificationReceiveFact`
- **AND** notification ingress 调用 `NotificationApprovalHandoffPort`
- **THEN** approval 域的 handoff adapter 接收 `NotificationApprovalHandoffRequest`
- **AND** adapter 将其映射为 `ApprovalInput` 或发布 `approval.input_received`
- **AND** notification ingress 不直接发布 `approval.completed`
- **AND** notification ingress 不调用 Policy Gate 或 executor

### Requirement: HITL 编排接收人工输入事件

系统 SHALL 通过 `approval.input_received` 或 notification approval handoff adapter 接收人工输入，并将输入保存、评估和转换为审批决策。

#### Scenario: approval.input_received 进入 evaluation
- **WHEN** fake human input producer 发布 `approval.input_received`
- **THEN** `ApprovalInputReceivedHandler` 消费该 envelope
- **AND** handler 将 payload 映射为 `ApprovalInput`
- **AND** 编排服务保存原始输入
- **AND** 编排服务生成 `ApprovalEvaluation`
- **AND** 文本输入不得直接等价于批准

#### Scenario: handoff adapter 复用同一 evaluation 入口
- **WHEN** `NotificationApprovalHandoffPort` adapter 接收到 `NotificationApprovalHandoffRequest`
- **THEN** adapter 复用 `ApprovalOrchestrationService.submit_input()` 或发布 `approval.input_received`
- **AND** 编排服务保存由 handoff 转换出的 `ApprovalInput`
- **AND** 编排服务生成 `ApprovalEvaluation`
- **AND** handoff adapter 不自行判定 approve / reject / request_reanalysis

#### Scenario: handoff adapter 找不到审批时安全失败
- **WHEN** `NotificationApprovalHandoffRequest` 无法解析出有效 `approval_id`
- **OR** 解析出的 `approval_id` 不存在
- **THEN** adapter 返回安全失败或 ignored 结果
- **AND** Policy Gate 不被调用
- **AND** executor 不被调用

#### Scenario: handoff adapter 不改写终态审批
- **WHEN** `NotificationApprovalHandoffRequest` 引用已经 completed、expired、rejected、blocked 或 escalated 的审批
- **THEN** adapter 返回 ignored / already_completed 摘要或结构化错误
- **AND** 编排服务不得改变最终 decision
- **AND** executor 不被调用

#### Scenario: 找不到审批请求不会执行动作
- **WHEN** `approval.input_received` 引用不存在的 `approval_id`
- **THEN** 系统返回结构化失败或发布安全失败摘要
- **AND** Policy Gate 不被调用
- **AND** executor 不被调用

### Requirement: Evaluation 处理批准、拒绝、重分析和模糊输入

系统 SHALL 将人工输入转换为结构化 intent，并对模糊、低置信和弱确认路径升级或阻断。

#### Scenario: 结构化 approve 仍需 Policy Gate
- **WHEN** 用户通过允许通道提交结构化 approve
- **THEN** evaluation 生成 approve intent
- **AND** 编排服务调用 Policy Gate
- **AND** 只有 Policy Gate 通过后才允许调用 executor

#### Scenario: reject 不调用 executor
- **WHEN** 用户提交 reject
- **THEN** 系统发布 `approval.completed(status=rejected)` 或等价安全语义
- **AND** Policy Gate 不被调用
- **AND** executor 不被调用

#### Scenario: request_reanalysis 不调用 executor
- **WHEN** 用户要求重新分析
- **THEN** 系统发布 `approval.completed(status=reanalysis_requested)` 或等价安全语义
- **AND** executor 不被调用
- **AND** 后续重分析链路可由单独 change 承接

#### Scenario: 模糊文本升级而非自动批准
- **WHEN** 用户通过文本通道提交模糊同意、低置信表达或无法解析输入
- **THEN** evaluation 生成 `unclear` 或 `escalated`
- **AND** 系统不得自动 approve
- **AND** executor 不被调用

#### Scenario: manual_only 不能被弱确认满足
- **WHEN** 审批要求 `manual_only`
- **AND** 输入来自 approval link、IM 文本、邮件文本或其他弱确认通道
- **THEN** 系统生成 escalated decision
- **AND** executor 不被调用

### Requirement: Policy Gate 是执行前强制边界

系统 SHALL 在任何执行请求前调用 `PolicyGate`，并在 gate 拒绝或失败时阻断 executor。

#### Scenario: Policy Gate 允许后才调用 executor
- **WHEN** evaluation 得到 approve
- **AND** Policy Gate 返回 allow
- **THEN** 系统可以调用 fake `ActionExecutor`
- **AND** 系统发布 `approval.completed`
- **AND** completed payload 只表达执行请求状态或 mock / dry-run 摘要，不表达真实 broker 成功

#### Scenario: 缺少 Policy Gate 时默认阻断
- **WHEN** 编排路径可能调用 executor
- **AND** `PolicyGate` 未注入或不可用
- **THEN** 系统发布 `approval.completed(status=policy_gate_failed)` 或等价安全语义
- **AND** executor 不被调用

#### Scenario: Policy Gate 拒绝时不调用 executor
- **WHEN** evaluation 得到 approve
- **AND** Policy Gate 返回 deny
- **THEN** 系统发布 `approval.completed(status=policy_blocked)` 或等价安全语义
- **AND** executor 不被调用
- **AND** completed payload 包含脱敏阻断摘要

#### Scenario: Policy Gate 失败时不调用 executor
- **WHEN** Policy Gate 抛出异常或返回不可用
- **THEN** 系统发布安全失败结果
- **AND** executor 不被调用
- **AND** 错误摘要不暴露内部路径、完整栈、secret 或私有策略

### Requirement: 限时审批按过期动作收敛

系统 SHALL 支持 `approval_with_timeout` 的过期动作，并在超时后生成确定结果。

#### Scenario: expire_reject 超时拒绝
- **WHEN** 审批超时且 `expiration_action=expire_reject`
- **THEN** 系统发布 rejected / expired 完成结果
- **AND** executor 不被调用

#### Scenario: expire_approve 仍需 Policy Gate
- **WHEN** 审批超时且 `expiration_action=expire_approve`
- **THEN** 系统调用 Policy Gate
- **AND** 只有 Policy Gate 允许后才调用 executor

#### Scenario: expire_notify_only 只通知
- **WHEN** 审批超时且 `expiration_action=expire_notify_only`
- **THEN** 系统发布 completed expired / notify-only 结果
- **AND** 系统可以发布 `notification.requested`
- **AND** executor 不被调用

#### Scenario: expire_reanalysis 请求重分析
- **WHEN** 审批超时且 `expiration_action=expire_reanalysis`
- **THEN** 系统发布 reanalysis_requested 完成结果
- **AND** executor 不被调用

#### Scenario: escalate 升级确认
- **WHEN** 审批超时且 `expiration_action=escalate`
- **THEN** 系统发布 escalated 完成结果
- **AND** executor 不被调用

### Requirement: HITL harness 覆盖完整消息闭环

系统 SHALL 提供测试专用 harness，使用 InMemoryEventBus 与 notification approval handoff seam 覆盖从行为请求到审批完成的核心链路。

#### Scenario: fake 链路完成审批闭环
- **WHEN** test harness 发布 `action.requested`
- **THEN** action handler 创建审批请求并发布 `approval.requested` 与 `notification.requested`
- **AND** fake notification consumer 生成脱敏 `HumanAuthorizationMessage`
- **AND** fake notification receive handoff 生成 `NotificationApprovalHandoffRequest`
- **AND** approval handoff adapter 复用 `ApprovalInputReceivedHandler` 或 `ApprovalOrchestrationService.submit_input()`
- **AND** input handler 生成 evaluation 和 decision
- **AND** 系统最终发布 `approval.completed`

#### Scenario: harness 不依赖外部基础设施
- **WHEN** 运行 approval harness tests
- **THEN** 测试不需要真实 Kafka
- **AND** 不需要真实数据库
- **AND** 不需要真实 notification provider
- **AND** 不需要真实 broker、真实密钥、生产账户或外部网络

#### Scenario: 真实 Discord smoke 不属于默认 HITL 验收
- **WHEN** 开发者运行 HITL approval 默认单元测试
- **THEN** 测试不要求真实 Discord webhook
- **AND** 测试不要求真实 notification provider token 或 secret
- **AND** Discord webhook smoke 只能作为手动或 env-gated 补充验证
- **AND** smoke 通过不表示平台 notification dispatcher 已实现

### Requirement: HITL 编排保持最小幂等边界

系统 SHALL 防止重复人工输入或终态后输入造成重复执行副作用。

#### Scenario: 相同 input id 不重复执行
- **WHEN** 同一个 `ApprovalInput.id` 被重复提交
- **THEN** repository 返回既有 input / evaluation / decision 或生成安全重复摘要
- **AND** Policy Gate 不被重复调用
- **AND** executor 不被重复调用

#### Scenario: 终态审批不被后续输入改写
- **WHEN** `ApprovalRequest` 已经 completed、expired、rejected、blocked、escalated 或进入其他终态
- **AND** 后续又收到 `approval.input_received`
- **THEN** 系统不得改变最终 decision
- **AND** executor 不被调用
- **AND** 系统返回 ignored / already_completed 摘要或结构化错误

### Requirement: approval.completed 使用安全完成摘要

系统 SHALL 将 `approval.completed` 作为审批完成摘要事件，而不是持久化详情、审计记录或 broker 回执。

#### Scenario: completed payload 字段最小且脱敏
- **WHEN** 系统发布 `approval.completed`
- **THEN** payload 至少包含 `approval_id`、`action_request_id`、`status`、`intent`、`policy_gate_status`、`execution_status` 和 `reason_summary`
- **AND** payload 不包含 ORM model、API envelope、DB session、完整 prompt、secret、token、cookie、私有策略或交易密钥
- **AND** payload 不表达 live trading、真实成交或真实 broker 成功

### Requirement: Core approval package 保持依赖边界

系统 SHALL 将 HITL 编排实现保持在 core package 边界内，并禁止依赖 app、Web、具体插件或真实 broker。

#### Scenario: core approval 不依赖 app 或具体插件
- **WHEN** 后续实现 `quantagent.core.approval`
- **THEN** 它不得 import `fastapi`
- **AND** 不得 import `starlette`
- **AND** 不得 import `apps.api`
- **AND** 不得 import `apps.web`
- **AND** 不得 import `plugins.*`
- **AND** 不得返回 API envelope、HTTP status code、React 类型或 ORM model

#### Scenario: README 固定职责边界
- **WHEN** 后续实现新增 `quantagent.core.approval`
- **THEN** 该目录提供 README 或最小 usage note
- **AND** README 说明职责、入口、状态真源边界和禁止放入的 API / ORM / Web / broker / plugin 逻辑
