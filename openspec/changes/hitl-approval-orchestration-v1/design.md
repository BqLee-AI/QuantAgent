## Context

HITL 授权不是单个 Web approve / reject 按钮，而是高风险动作进入人类确认、策略评估、Policy Gate 和受控执行前的安全链路。当前真源分工如下：

- `docs/design/08-api-and-websocket-design.md` 定义 `ActionRequest -> ApprovalPolicyResolver -> ApprovalRequest -> ApprovalInput -> ApprovalEvaluation -> ApprovalDecision -> Policy Gate -> Broker / Notification / Reanalysis`。
- `openspec/specs/kafka-event-bus-v1/spec.md` 定义 Event Bus V1 envelope、topic policy、memory / Kafka backend、plugin isolation、非持久化真源和敏感信息保护。
- `openspec/changes/notification-receive-handoff-v1/` 与 `packages/core/src/quantagent/core/notifications/` 已经定义并实现 `NotificationReceiveFact`、`NotificationIngressAuditEntry` 和 `NotificationApprovalHandoffPort`；notification ingress 只做 receive fact / audit / handoff，不直接发布 approval topic 或实现审批状态机。
- `packages/core/AGENTS.md` 约束 core 不依赖 app、FastAPI、React、具体插件，关键状态变化和 Approval / Audit 需要按可回放、append-only 思路设计。
- `.agents/skills/references/core-and-plugin-architecture-gate.md` 约束 core/package 依赖方向、事件 payload 版本化、插件隔离和人工确认必须可审计。

本 change 只把编排能力固定到 OpenSpec；实现 PR 需要在 OpenSpec-only PR 获认可后再开始。

## Goals / Non-Goals

**Goals:**

- 固定 `action.requested` 和 `approval.input_received` 作为 HITL 编排入口 topic。
- 固定 core-only approval package 的职责、文件规划、模型和端口。
- 固定 `InMemoryEventBus` harness 能验证 AI 请求、通知消息、人工输入、审批完成和 Policy Gate 阻断。
- 复用已打通的 notification ingress handoff seam，让外部通知回流先成为 `NotificationReceiveFact` 和 append-only ingress audit，再进入 approval evaluation。
- 覆盖所有授权模式、超时动作、manual-only、模糊文本、敏感信息脱敏和 dry-run/mock 边界。
- 保留后续数据库持久化、audit、API、Web、真实 notification 和真实 broker 的扩展点。

**Non-Goals:**

- 不做 API / Web / DB / contracts / generated client。
- 不接真实 notification provider 或真实 broker。
- 不实现完整风控策略引擎，只定义 `PolicyGate` port 和 test fake。
- 不把 Event Bus 当成业务状态真源。
- 不让插件直接发布审批事件或标记审批完成。

## Decisions

### 1. 新增两个 topic，而不是只走 service-first

本轮新增：

```text
action.requested
approval.input_received
```

`action.requested` 表达 Agent、Decision 或工具发出的动作请求，交由 approval action handler 消费。`approval.input_received` 表达人工输入从 Web、一次性链接、IM、邮件或 CLI 等通道回流，交由 approval input handler 消费。

选择新增 topic 的原因：

- issue 目标是验证“AI 发请求 -> handler 消费 -> 发通知 -> 人工输入回流”的消息队列闭环。
- 只走 service-first 不能证明 Event Bus topic policy、handler contract 和 human input 回流语义。
- 新 topic 会扩大契约面，所以必须同步修改 `kafka-event-bus-v1` spec delta、后续 topic allowlist、README 和 contract tests。

### 2. Approval 编排放在 `packages/core`

后续实现新增目录：

```text
packages/core/src/quantagent/core/approval/
  __init__.py
  README.md
  models.py
  policies.py
  evaluator.py
  repository.py
  ports.py
  publishers.py
  notification_handoff.py
  service.py
  handlers.py
  harness.py
```

职责划分：

- `models.py`：定义 JSON-safe domain models，不使用 ORM、API DTO、Plugin DTO 或不可序列化对象。
- `policies.py`：实现保守 `ApprovalPolicyResolver`，解析授权模式、确认等级、过期动作和理由摘要。
- `evaluator.py`：实现 rule evaluator，将 `ApprovalInput` 转成 approve / reject / request_reanalysis / unclear / escalate 等结构化判断。
- `repository.py`：提供 `ApprovalRepository` Protocol 和 `InMemoryApprovalRepository`，保存 action、request、input、evaluation、decision 的关联记录。
- `ports.py`：定义 `PolicyGate`、`ActionExecutor`、`NotificationMessageSink` 等端口，不依赖具体 app、插件或 broker。
- `publishers.py`：封装 `approval.requested`、`notification.requested`、`approval.completed` 的 envelope 映射。
- `notification_handoff.py`：实现 approval 域的 `NotificationApprovalHandoffPort` adapter，把 `NotificationApprovalHandoffRequest` 映射为 `ApprovalInput`，并选择直接调用 `submit_input()` 或发布 `approval.input_received`。
- `service.py`：实现 `ApprovalOrchestrationService.submit_action()`、`submit_input()`、`expire_approval()`。
- `handlers.py`：实现 `ActionRequestedHandler` 和 `ApprovalInputReceivedHandler`，只做 envelope 适配并调用 service。
- `harness.py`：提供测试专用 fake AI producer、notification handoff producer / adapter、human authorization message builder、fake human input producer 和 fake executor。fake notification consumer 只用于验证 `notification.requested` 消息形状，不替代已存在的 notification ingress handoff seam。

不把 API route、数据库持久化、Web 展示、真实通知或 broker 逻辑放入该目录。

### 3. Core models 使用领域对象，不复用 EventEnvelope payload dict

核心模型字段草案：

```text
ActionRequest
  id
  action_type
  action_side
  target_type
  target_id
  instrument
  market
  amount
  leverage
  confidence_score
  risk_flags
  urgency
  proposed_payload
  strategy_policy
  user_policy
  ai_policy_hint
  correlation_id

ResolvedApprovalPolicy
  mode
  required_confirmation_level
  expires_at
  expiration_action
  allowed_channels
  reason_summary

ApprovalRequest
  id
  action_request_id
  target_type
  target_id
  action_type
  action_side
  risk_level
  urgency
  summary
  proposed_payload
  required_confirmation_level
  expires_at
  expiration_action
  policy_source
  status

ApprovalInput
  id
  approval_id
  channel
  actor_ref
  raw_text
  structured_payload
  received_at

ApprovalEvaluation
  approval_id
  input_id
  evaluator_type
  interpreted_intent
  confidence
  extracted_changes
  requires_stronger_confirmation
  reason_summary

ApprovalDecision
  approval_id
  action_request_id
  status
  intent
  policy_gate_status
  execution_status
  reason_summary
```

所有模型需要提供可测试的 JSON-safe 映射，事件 payload 不得包含 ORM model、DB session、插件实例、完整 prompt、secret、token、cookie、私有策略或不可序列化对象。

最小枚举约束：

- `ApprovalRequest.status` 至少包含 `pending`、`completed`、`expired`、`escalated`、`blocked`。
- `ApprovalEvaluation.interpreted_intent` 至少包含 `approve`、`reject`、`request_reanalysis`、`unclear`、`escalate`。
- `ApprovalDecision.status` 至少包含 `not_required`、`pending`、`approved`、`rejected`、`reanalysis_requested`、`expired`、`escalated`、`blocked`、`policy_blocked`、`policy_gate_failed`、`execution_requested`、`execution_failed`。
- `ApprovalDecision.policy_gate_status` 只能表达 `not_required`、`allowed`、`denied`、`unavailable`、`failed` 这类 gate 结果，不能表达 broker 执行成功。
- `ApprovalDecision.execution_status` 只能表达 `not_requested`、`mock_requested`、`dry_run_requested`、`request_failed` 这类请求摘要，不能表达 live trading、真实成交或真实 broker 成功。

`approval.completed` payload 的最小字段来自 `ApprovalDecision` 与关联 `ApprovalRequest` / `ActionRequest` 的安全上下文。`ApprovalDecision` 必须直接携带 `approval_id`、`action_request_id`、`status`、`intent`、`policy_gate_status`、`execution_status` 和 `reason_summary`；`correlation_id` / `causation_id` 这类追踪字段可以由关联请求或 envelope 上下文补齐。它是完成事件摘要，不是持久化审批详情、审计记录或 broker 执行回执。

### 4. PolicyGate 是执行前 port，不实现完整策略引擎

`PolicyGate` 作为端口固定在 executor 前：

```text
ApprovalDecision(approved)
  -> PolicyGate.evaluate(...)
  -> ActionExecutor.execute(...)
  -> approval.completed
```

后续实现只需要 conservative default / test fake，覆盖 allow、deny、error 三类路径。完整风控策略引擎依赖账户、权限、风险规则、钱包事实和持久化，不进入本 issue。

保守默认：任何可能调用 executor 的路径都必须显式注入 `PolicyGate`。如果未注入或 gate 不可用，编排服务必须生成 `policy_gate_status=unavailable` 或 `policy_gate_failed` 的完成结果，并且不得调用 executor。

规则：

- 用户 approve 后仍必须经过 Policy Gate。
- `execute_then_notify` 也必须先经过 Policy Gate；它只是跳过人工等待，不跳过执行前 gate。
- Policy Gate 拒绝或异常时不得调用 executor。
- `blocked`、`manual_only` 弱确认、`unclear`、`request_reanalysis`、`reject` 路径不得调用 executor。
- `approval.completed` 中只能表达 executor 被请求、被阻断或未执行，不能表达真实 broker 成功。

### 5. 第一刀不发布 `broker.dry_run_requested`

本轮 dry-run/mock 行为通过 fake `ActionExecutor` 记录调用，并在 `approval.completed` payload 中表达执行摘要，例如 `execution_status=requested`、`mock_requested` 或同等安全语义。

不发布 `broker.dry_run_requested` 的原因：

- 当前还没有 broker dry-run consumer、executor plugin 接线、wallet facts 风控消费和审计持久化。
- 提前发布 broker topic 容易让下游误以为 broker dry-run 链路已完成。
- 后续可以单独 issue 接 `broker.dry_run_requested` / `broker.dry_run_completed`。

### 6. 通知链路复用 notification handoff，并保留脱敏消息 builder

发送方向仍由 approval 编排发布 `notification.requested`，payload 只携带人工判断所需的脱敏摘要。测试可以用 `HumanAuthorizationMessageBuilder` 消费这个事件并生成授权消息：

```text
HumanAuthorizationMessage
  approval_id
  action_request_id
  summary
  risk_direction
  required_confirmation_level
  expires_at
  expiration_action
  allowed_channels
  safe_context
```

消息必须包含人类做决定所需的摘要、风险方向、确认等级和过期策略，但不得包含 secret、token、完整 prompt、私有策略、交易密钥或未经允许的敏感交易细节。

回流方向不再由 fake notification consumer 直接伪造业务入口，而是复用 `notification-receive-handoff-v1`：

```text
notification.receive
  -> NotificationReceiveFact
  -> NotificationIngressAuditEntry(notification.receive.recorded)
  -> NotificationApprovalHandoffPort
  -> ApprovalInput / approval.input_received
```

approval 域需要提供 `NotificationApprovalHandoffPort` 的实现或 adapter。该 adapter 只把 `NotificationApprovalHandoffRequest` 标准化为 `ApprovalInput`，不得在 notification ingress 层判定 approve / reject，不得调用 Policy Gate 或 executor。

真实 Discord / Telegram / Email / WebSocket provider、发送调度器和投递状态不进入本轮；但外部通知输入进入 approval 的 seam 已经存在，后续实现应接入该 seam，而不是另造并行 fake 回流路径。

### 6.1 通知测试按链路层次收口

当前通知能力需要按三层分别验证，避免把“已有插件能力”误写成“平台发送闭环已完成”：

1. `notification.requested` 发送请求事件：HITL 只验证 approval 编排会发布脱敏、可被人工理解的发送请求事件。测试应断言 payload 包含 `approval_id`、`action_request_id`、summary、确认等级、过期策略和允许通道，并且不包含完整 prompt、secret、token、cookie、私有策略或 broker credential。
2. `notification.receive -> NotificationReceiveFact -> NotificationApprovalHandoffPort` 回流 seam：这是当前已打通且和 HITL 直接相关的通知链路。HITL 后续实现必须深化测试，覆盖 handoff request 映射为 `ApprovalInput`、找不到审批 ID、终态后输入、重复输入、模糊文本和 manual-only 弱确认等路径。
3. `notification.send` 插件能力：Discord 插件已有发送 DTO 和 webhook 发送能力，但平台 dispatcher 尚未实现。HITL change 不把真实 provider 发送、dispatcher 选插件、调用 `notification.send` 或发布 `notification.completed` 作为本轮验收；这些应由后续 notification dispatcher / sender change 承接。

真实 Discord webhook smoke 只能作为手动或 env-gated 补充验证，不进入默认 core approval 单测，也不能作为 HITL 编排已具备生产通知发送闭环的证据。

### 7. In-memory repository 只验证状态机和关联查找

第一刀使用 `InMemoryApprovalRepository` 保存：

- `action_request_id -> ActionRequest`
- `approval_id -> ApprovalRequest`
- `approval_id -> ApprovalInput[]`
- `approval_id -> ApprovalEvaluation[]`
- `approval_id -> ApprovalDecision[]`

它用于证明“根据 ID 找回原请求”的语义，不作为 API / Web 数据真源。数据库持久化、事务、并发、audit 落库和恢复能力需要后续 issue。

最小幂等规则：

- 相同 `ApprovalInput.id` 重复提交时，不得重复生成 executor 调用；实现可以返回已记录的 evaluation / decision。
- `ApprovalRequest` 已进入终态后，后续输入不得改变最终 decision，只能生成安全的 ignored / already_completed 摘要或结构化错误。
- 同一 `approval_id` 的并发保护不在本轮实现生产级锁；in-memory harness 至少要用测试证明重复输入不会产生重复执行副作用。

### 8. 状态真源与审计边界保持清晰

Event Bus 只表达状态变化和异步分发：

- 发布 `approval.requested` 不代表 Approval 已持久化到数据库。
- 发布 `approval.completed` 不代表 audit record 已落库。
- Memory harness 的 repository 只服务测试，不提供生产恢复保证。

后续实现需要在 README 和注释中说明这些边界，避免把 Event Bus 当成持久化或审计真源。

## Data Flow Blueprint

核心消息链路：

```text
fake AI / Decision producer
  -> EventEnvelope(topic=action.requested)
  -> ActionRequestedHandler
  -> ApprovalOrchestrationService.submit_action()
  -> ApprovalPolicyResolver
  -> InMemoryApprovalRepository
  -> approval.requested / notification.requested / approval.completed
  -> notification sender / fake message builder
  -> HumanAuthorizationMessage
  -> external notification receive / fake notification handoff
  -> NotificationReceiveFact + NotificationIngressAuditEntry
  -> NotificationApprovalHandoffPort adapter
  -> ApprovalInput or EventEnvelope(topic=approval.input_received)
  -> ApprovalInputReceivedHandler
  -> ApprovalOrchestrationService.submit_input()
  -> ApprovalRuleEvaluator
  -> PolicyGate
  -> fake ActionExecutor
  -> approval.completed
```

分支说明：

- `approval_required` 和 `approval_with_timeout` 会进入 `approval.requested` / `notification.requested` / 等待输入或超时。
- `no_approval_notify_only` 只发布通知和完成摘要，不等待 `approval.input_received`。
- `execute_then_notify` 先经过 Policy Gate，允许后调用 fake executor，再发布通知和完成摘要。
- `blocked` 直接完成为阻断，不发布可确认的 approval link，不调用 Policy Gate 或 executor。

超时链路：

```text
ApprovalOrchestrationService.expire_approval(approval_id)
  -> expiration_action
  -> reject / approve through PolicyGate / notify-only / reanalysis / escalate
  -> approval.completed and optional notification.requested
```

## Failure Paths

- 未知 topic：由 Event Bus topic policy 拒绝。
- 非 JSON-safe payload：由 EventEnvelope / codec contract 拒绝。
- 找不到 `approval_id` 或 `action_request_id`：input handler 返回结构化失败，不调用 executor。
- `NotificationApprovalHandoffRequest` 找不到审批关联、缺少可解析 approval id 或引用已终态审批：adapter 返回安全失败 / ignored 结果，不调用 executor。
- 文本输入模糊或置信度不足：evaluation 进入 `unclear` 或 `escalated`，不自动 approve。
- `manual_only` 遇到 approval link、IM 文本或弱确认：进入 escalated，不调用 executor。
- `blocked` policy：发布 completed blocked，不调用 PolicyGate 或 executor。
- PolicyGate 拒绝或异常：发布 completed blocked / gate_failed，不调用 executor。
- Notification message builder 遇到敏感字段：输出脱敏摘要，不泄露原文。
- Executor 失败：发布 completed execution_failed / requested_failed 摘要，不表达真实 broker 成功。

## Validation Strategy

OpenSpec-only PR 最小验证：

```bash
openspec validate hitl-approval-orchestration-v1 --type change --strict --json
```

后续实现 PR 的最小验证：

```bash
uv run python -m unittest packages/core/tests/test_event_bus_contract.py packages/core/tests/test_event_bus_memory.py
uv run python -m unittest packages/core/tests/test_approval_policy.py
uv run python -m unittest packages/core/tests/test_approval_orchestration.py
uv run python -m unittest packages/core/tests/test_approval_event_bus_topics.py
uv run python -m unittest packages/core/tests/test_approval_harness.py
uv run python -m unittest packages/core/tests/test_notification_ingress.py
```

通知相关验证分层：

- `test_approval_orchestration.py` / `test_approval_harness.py`：验证 `notification.requested` payload 形状、脱敏边界，以及 handoff adapter 进入 `ApprovalInput` evaluation 后不绕过 Policy Gate。
- `test_notification_ingress.py`：验证 receive fact、append-only ingress audit、handoff 成功 / 失败和 correlation 规则。
- Discord plugin tests / smoke：只验证插件自身 `notification.send` 能力；真实 webhook smoke 需要显式环境变量和人工触发，不作为默认 CI gate。

人工 review 需要核对：

- `packages/core` 没有依赖 FastAPI、React、apps、具体插件或真实 broker。
- 新增 topic 同步到 Event Bus stable spec、README 和 contract tests。
- Event payload 不包含 ORM、API envelope、Plugin DTO、DB session 或不可 JSON 序列化对象。
- approval handoff adapter 只消费 notification ingress 的 `NotificationApprovalHandoffRequest`，不把 notification ingress 变成 approval service。
- 测试说明没有把 `notification.requested` 或 Discord 插件 smoke 误称为平台真实发送闭环。
- approve、dry-run 和 completed 文义没有被写成 live trading 或真实执行成功。

## Risks / Trade-offs

- [Risk] 新增 topic 扩大 Event Bus 契约面。
  Mitigation：通过 `kafka-event-bus-v1` spec delta、topic contract tests 和 README 同步收口。

- [Risk] in-memory repository 容易被误解成生产状态真源。
  Mitigation：design、README 和 tests 明确它只服务编排验证，生产持久化另开 issue。

- [Risk] 本轮只接 notification receive handoff seam，不能证明真实发送调度器或真实外部 provider 投递正确。
  Mitigation：发送方向只验证 `notification.requested` 消息形状和脱敏边界；接收方向复用已落地的 `NotificationReceiveFact` / audit / handoff seam，真实 provider 投递由后续 notification issue 承接。

- [Risk] 不发布 `broker.dry_run_requested` 会少一段异步 broker 验证。
  Mitigation：本轮聚焦 Approval 编排，broker dry-run topic 接线单独处理，避免过早表达执行已完成。
