## 1. OpenSpec artifacts

- [x] 1.1 创建 `notification-discord-approval-loop-v1` proposal，明确 why now、范围、非目标和风险边界。
- [x] 1.2 创建 design，明确发送 dispatcher、API handoff 注入、消息格式、事件语义和验证入口。
- [x] 1.3 创建 spec，覆盖 Discord 审批通知发送、completed 摘要、真实 ingress handoff、approval 安全评估和插件边界。
- [x] 1.4 运行 `openspec validate notification-discord-approval-loop-v1 --type change --strict --json`；当前已用系统 `openspec` 可执行文件校验通过。

## 2. Core notification dispatcher

- [x] 2.1 在 `packages/core/src/quantagent/core/notifications/models.py` 增补发送侧模型：`NotificationDispatchRequest`、`NotificationDispatchResult`、`NotificationDeliverySummary`。
- [x] 2.2 新增 `packages/core/src/quantagent/core/notifications/message.py`，实现脱敏审批通知文本 builder，确保输出包含 `approval_id: <id>`。
- [x] 2.3 新增 `packages/core/src/quantagent/core/notifications/sender.py`，实现 `NotificationDispatchService`，通过 Registry + Runtime 调用 `notification.send`。
- [x] 2.4 新增 `packages/core/src/quantagent/core/notifications/publishers.py`，封装 `notification.completed` envelope 映射。
- [x] 2.5 新增 `packages/core/src/quantagent/core/notifications/handlers.py`，实现 `NotificationRequestedHandler` 消费 `notification.requested`。
- [x] 2.6 更新 `packages/core/src/quantagent/core/notifications/README.md`，说明 sender / ingress / handoff 的职责边界和非目标。

## 3. Event and contract boundaries

- [x] 3.1 检查 `packages/core/src/quantagent/core/events/topics.py` 和 events README，确认 `notification.completed` topic 已被允许并有发送完成语义说明。
- [x] 3.2 当前 topic policy 已允许 `notification.completed`；实现时需补充 README 或 stable spec，明确其 payload 只表示发送尝试结果。
- [x] 3.3 确保 `notification.completed` payload 不包含审批 decision、broker 执行结果、secret、token、完整 prompt 或私有策略。

## 4. API ingress approval handoff wiring

- [x] 4.1 更新 `apps/api/src/quantagent/api/services/notification_ingress.py`，允许注入已组装的 `NotificationIngressService` 或 handoff adapter，避免 host 只能创建 no-op service。
- [x] 4.2 在 API app state composition 中接入 `ApprovalNotificationHandoffAdapter`；当前代码尚无生产级 approval app state 时，先提供可测试注入 seam，可选择 service 直调或 publisher 发布 `approval.input_received`，但不得在 API host 中判定 approve/reject。
- [x] 4.3 保留无 approval runtime 时的 no-op 降级，并在结果、日志或 README 中明确不代表真实审批回流已完成。
- [x] 4.4 更新 `apps/api/README.md`，说明 Discord approval loop 的 ingress 配置、send dispatcher 配置和真实 smoke 边界。

## 5. Discord plugin boundary check

- [x] 5.1 确认 `plugins/notifications/discord/src/discord_plugin.py` 不 import core approval、Event Bus、API 或具体 app。
- [x] 5.2 如需要调整 README 或 config schema，仅补充发送/接收配置说明，不把审批状态机写进插件。
- [x] 5.3 确认插件 tests 仍只验证 `notification.send` / `notification.receive` 协议适配，不断言平台审批完成。

## 6. Tests

- [x] 6.1 新增 `packages/core/tests/test_notification_dispatch.py`，覆盖 dispatcher 成功调用、缺配置、插件缺 capability、runtime failure、非法 result 和 retryable 保留。
- [x] 6.2 新增消息 builder 测试，断言 Discord 文本包含 `approval_id` 且不泄露 prompt、secret、token、cookie、私有策略或 broker credential。
- [x] 6.3 新增 `packages/core/tests/test_notification_approval_loop.py`，用 `InMemoryEventBus` / fake runtime 跑通 `notification.requested -> notification.send -> notification.completed`。
- [x] 6.4 扩展 `packages/core/tests/test_notification_ingress.py` 或新增 API 测试，覆盖真实 ingress 使用 approval handoff adapter。
- [x] 6.5 扩展 `apps/api/src/tests/test_app.py`，覆盖 no-op 降级、注入 handoff、错误不泄密和 OpenAPI/route 注册不回退到 Discord 专属 host。
- [x] 6.6 保留 Discord 插件默认测试使用 mock transport / signing fixture，不依赖真实网络。

## 7. Validation

- [x] 7.1 运行 `uv run python -m unittest packages/core/tests/test_notification_dispatch.py`。
- [x] 7.2 运行 `uv run python -m unittest packages/core/tests/test_notification_approval_loop.py`。
- [x] 7.3 运行 `uv run python -m unittest packages/core/tests/test_notification_ingress.py`。
- [x] 7.4 运行 `cd apps/api && uv run python -m unittest discover -s src`。
- [x] 7.5 运行 `uv run python -m unittest discover -s plugins/notifications/discord/tests -p 'test_*.py'`。
- [x] 7.6 如本地具备真实 Discord 测试环境，可手动运行 `smoke_send.py` / `smoke_receive.py`，并在 PR 中标记为补充验证而非默认验收。本轮已完成真实 Discord smoke：webhook 发送 `SENT`，同伴 App `/notify` 回流到 `approval-fullflow` 并生成 `escalated` decision；另用结构化强确认验证 fake executor `dry_run_requested`。

## 8. Review gates

- [x] 8.1 OpenSpec-only PR 只包含本 change artifacts，不混入实现代码。
- [x] 8.2 实现 PR 说明链接本 change，并写清 `notification.requested`、`notification.completed`、`approval.completed` 三者语义差异。
- [x] 8.3 Review 时确认 `packages/core` 没有依赖 FastAPI、apps 或具体 Discord 插件实现。
- [x] 8.4 Review 时确认 Discord 插件没有承担审批状态、Policy Gate、executor 或 Event Bus 发布职责。

## 9. Local smoke replay

- [x] 9.1 固化本地 fullflow smoke 入口，提供明确命令创建 `ActionRequest`、发送 Discord 通知、等待 `/notify` 回流，并只在该命令运行时暴露 debug 状态接口。
- [x] 9.2 补充 `docs/demo/` 操作指南，说明 env、localtunnel、Discord App endpoint、`/notify` 文本和预期结果；不得记录真实 secret。
