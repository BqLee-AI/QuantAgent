## 1. OpenSpec

- [x] 1.1 为 `notification-receive-handoff-v1` 写 proposal，明确为什么需要 receive fact / audit / approval handoff
- [x] 1.2 为 `notification-receive-handoff-v1` 写 design，明确文件职责、数据流和与 `#241` 的边界
- [x] 1.3 为 `notification-receive-handoff-v1` 写可验证 spec

## 2. Core Notification Models

- [x] 2.1 新增 `NotificationReceiveFact`
- [x] 2.2 新增 `NotificationIngressAuditEntry`
- [x] 2.3 新增 `NotificationApprovalHandoffRequest/Result`
- [x] 2.4 保持全部模型 JSON-safe，且不暴露 FastAPI / DB / plugin 实现对象

## 3. Repository / Sink / Port

- [x] 3.1 新增 `NotificationReceiveFactRepository` 与内存实现
- [x] 3.2 新增 `NotificationIngressAuditSink` 与内存实现
- [x] 3.3 新增 `NotificationApprovalHandoffPort`
- [x] 3.4 提供默认 `NoopNotificationApprovalHandoff`，保证当前主线不误导为“审批已完成”

## 4. Ingress Orchestration

- [x] 4.1 更新 `NotificationIngressService`，让成功 `item` 进入 receive fact
- [x] 4.2 在 fact 创建后追加 append-only 审计
- [x] 4.3 在 fact 创建后调用 approval handoff port
- [x] 4.4 返回值中暴露 fact / handoff result，便于 API 或后续服务观测

## 5. Docs

- [x] 5.1 为 `packages/core/src/quantagent/core/notifications/` 补 README
- [x] 5.2 更新 `docs/references/plugins/notification.md`，说明 receive fact / audit / handoff 的平台职责

## 6. Validation

- [x] 6.1 补 `packages/core/tests/test_notification_ingress.py`
- [x] 6.2 跑最小单测
- [x] 6.3 运行 `openspec validate notification-receive-handoff-v1 --type change --strict`
