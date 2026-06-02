## 1. OpenSpec 审核门禁

- [x] 1.1 创建 `hitl-approval-orchestration-v1` change，范围限定为 OpenSpec 文档。
- [x] 1.2 完成 `proposal.md`，说明 why now、当前缺口、目标、非目标、影响面和审核门槛。
- [x] 1.3 完成 `design.md`，固定 core-only approval 编排、topic 决策、模型字段草案、文件职责、数据流、失败路径和验证策略。
- [x] 1.4 完成 `specs/hitl-approval-orchestration-v1/spec.md`，覆盖行为请求入口、审批请求、人工输入、evaluation、Policy Gate、完成事件、脱敏和 harness。
- [x] 1.5 完成 `specs/kafka-event-bus-v1/spec.md`，新增 `action.requested` 和 `approval.input_received` topic policy 要求。
- [x] 1.6 运行 `openspec validate hitl-approval-orchestration-v1 --type change --strict --json`。
- [x] 1.7 提交 OpenSpec-only PR，维护者明确评论“没问题”或批准后再进入实现代码 PR。

## 2. 实现：契约与事件 Gate

- [x] 2.1 同步 `DEFAULT_EVENT_TOPICS`，加入 `action.requested` 和 `approval.input_received`。
- [x] 2.2 更新 `packages/core/src/quantagent/core/events/README.md` 的默认 topic 和新增 topic 说明。
- [x] 2.3 补充 Event Bus contract tests，验证新增 topic 被接受、未知 topic 仍被拒绝。
- [x] 2.4 核对 envelope payload 只包含 JSON-safe 数据，不包含 ORM、DB session、API envelope、插件实例或不可序列化对象。

## 3. 实现：Core Approval 模型与策略

- [x] 3.1 在 `packages/core/src/quantagent/core/approval/models.py` 定义 `ActionRequest`、`ResolvedApprovalPolicy`、`ApprovalRequest`、`ApprovalInput`、`ApprovalEvaluation`、`ApprovalDecision` 和 `HumanAuthorizationMessage`。
- [x] 3.2 在 `models.py` 中固定最小枚举边界：request status、evaluation intent、decision status、policy gate status 和 execution status。
- [x] 3.3 在 `policies.py` 实现保守 `ApprovalPolicyResolver`，覆盖 `no_approval_notify_only`、`execute_then_notify`、`approval_required`、`approval_with_timeout`、`manual_only`、`blocked`。
- [x] 3.4 在 `evaluator.py` 实现 rule evaluator，覆盖 approve、reject、request_reanalysis、unclear、requires_stronger_confirmation。
- [x] 3.5 为安全边界、状态机、脱敏、Policy Gate 调用点补必要中文注释。

## 4. 实现：Repository、Ports 与 Publishers

- [x] 4.1 在 `repository.py` 定义 `ApprovalRepository` Protocol 和 `InMemoryApprovalRepository`，支持按 `approval_id` / `action_request_id` 查找关联记录。
- [x] 4.2 在 `ports.py` 定义 `PolicyGate`、`ActionExecutor` 和通知消息相关端口，不依赖 app、具体插件或真实 broker。
- [x] 4.3 明确未注入 `PolicyGate` 时默认阻断所有可能调用 executor 的路径。
- [x] 4.4 在 `publishers.py` 封装 `approval.requested`、`notification.requested` 和 `approval.completed` envelope 映射。
- [x] 4.5 明确第一刀不发布 `broker.dry_run_requested`，只记录 fake executor 请求和安全执行摘要。
- [x] 4.6 实现 approval 域的 `NotificationApprovalHandoffPort` adapter，消费 `NotificationApprovalHandoffRequest` 并映射为 `ApprovalInput` 或 `approval.input_received`。
- [x] 4.7 adapter 必须复用 notification ingress 已记录的 `NotificationReceiveFact` / handoff 事实，不在 notification ingress 层判定 approve / reject、调用 Policy Gate 或 executor。

## 5. 实现：Orchestration 与 Event Handlers

- [x] 5.1 在 `service.py` 实现 `ApprovalOrchestrationService.submit_action()`，处理 action requested、policy resolve、approval request 创建、通知发布和 notify-only / blocked / execute-then-notify 分支。
- [x] 5.2 在 `service.py` 实现 `submit_input()`，处理人工输入、evaluation、Policy Gate、executor 调用和 completed 事件。
- [x] 5.3 在 `service.py` 实现 `expire_approval()`，覆盖 `expire_reject`、`expire_approve`、`expire_notify_only`、`expire_reanalysis`、`escalate`。
- [x] 5.4 在 `handlers.py` 实现 `ActionRequestedHandler` 和 `ApprovalInputReceivedHandler`，handler 只做 envelope 适配和 service 调用。
- [x] 5.5 处理 `execute_then_notify`：跳过人工等待，但仍先经过 Policy Gate，允许后才调用 fake executor。
- [x] 5.6 处理找不到 ID、重复输入、终态后输入、模糊文本、manual-only 弱确认、Policy Gate 拒绝、executor 失败和敏感信息脱敏。

## 6. 实现：Harness、README 与测试

- [x] 6.1 在 `harness.py` 提供 fake AI / Decision producer、fake notification consumer、human authorization message builder、fake human input producer、fake executor、fake PolicyGate。
- [x] 6.1a 增补 notification receive handoff fake / adapter harness，让测试从 `NotificationApprovalHandoffRequest` 进入 `ApprovalInput` evaluation。
- [x] 6.2 为 `quantagent.core.approval` 补 `README.md`，说明职责、边界、入口、不要放 API / ORM / Web / 真实 broker / 具体插件。
- [x] 6.3 新增 `test_approval_policy.py`，覆盖授权模式和过期动作解析。
- [x] 6.4 新增 `test_approval_orchestration.py`，覆盖 approve、reject、request_reanalysis、unclear、manual_only、blocked、timeout、execute_then_notify、Policy Gate 拒绝、缺少 Policy Gate、重复 input 和终态后 input。
- [x] 6.5 新增 `test_approval_event_bus_topics.py`，覆盖新增 topic 和 handler envelope 适配。
- [x] 6.6 新增 `test_approval_harness.py`，覆盖完整 fake 消息闭环和脱敏消息生成。
- [x] 6.7 扩展 harness / tests，覆盖 `NotificationApprovalHandoffPort` adapter 从 notification receive handoff 到 `ApprovalInput` evaluation 的链路。
- [x] 6.8 增补 `notification.requested` payload 测试，断言它只表示发送请求事件，不表示 dispatcher 已调用插件、provider 已送达或 `notification.completed` 已发布。
- [x] 6.9 增补 handoff adapter 失败路径测试：无法解析 approval id、审批不存在、终态后输入、重复 input、模糊文本和 manual-only 弱确认都不得触发 executor。
- [x] 6.10 明确 Discord webhook smoke 只作为手动或 env-gated 补充验证，不进入默认 HITL / core approval 单测。
- [x] 6.11 运行 core event bus、notification ingress 与 approval 相关 unittest，验证无真实 Kafka、数据库、notification provider、broker 或外部网络依赖。
