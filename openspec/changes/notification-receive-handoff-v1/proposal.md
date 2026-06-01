## Why

`notification-plugin-ingress-v1` 已经收住了 transport host、runtime invoke 和插件协议适配边界，但成功的 `notification.receive` 结果仍然停留在“HTTP 请求生命周期里的插件返回值”。

这会留下三个实际缺口：

1. 平台没有统一的 `receive fact`。
   收到 Discord 或未来其他平台的交互后，如果没有先落成平台事实，后续审批、重分析或人工回溯都没有统一真源。

2. 没有 append-only 审计。
   通知入口天然会承载人工授权、命令输入或高风险确认。若没有审计链，后面无法解释“系统什么时候收到了什么输入，并交给了谁处理”。

3. 还没有和 approval 主链的安全衔接 seam。
   这次不能直接实现 `#241` 的 HITL 审批编排，也不能提前发明新的 approval topic；但也不能继续让 `NotificationReceiveResult.item` 卡在 notification ingress 层不往上交。

因此本 change 只收一个更小的边界：在不实现完整 approval orchestration 的前提下，把成功的 `notification.receive` 输入收成平台 `receive fact`，追加 append-only audit，并通过一个显式的 `approval handoff` port 移交给后续上层能力。

## What Changes

- 在 `packages/core/src/quantagent/core/notifications/` 新增平台侧模型：
  - `NotificationReceiveFact`
  - `NotificationIngressAuditEntry`
  - `NotificationApprovalHandoffRequest`
  - `NotificationApprovalHandoffResult`
- 为 notification ingress 编排补三类 seam：
  - receive fact repository
  - append-only audit sink
  - approval handoff port
- 更新 `NotificationIngressService`：
  - 只有在 `accepted=true` 且存在 `item` 时才生成平台事实
  - 生成 fact 后立即追加审计
  - 调用 `approval handoff` port，但默认只提供 no-op / in-memory 行为
- 明确与 `#241` 的边界：
  - 本 change 不实现 `ApprovalRequest`、`ApprovalInput`、`ApprovalEvaluation`、`ApprovalDecision`
  - 不新增 `approval.*` topic
  - 不实现 Policy Gate、executor 或 approval state machine

## Non-Goals

- 不做完整 HITL 审批编排；该职责留给 `#241`
- 不新增 `notification.received` stable topic
- 不落数据库表、Alembic migration、outbox 或 replay
- 不让 notification 插件自己 publish topic、写 approval record 或推进业务状态
- 不在 API 层加入任何新的平台特化逻辑

## Impact

- `packages/core/src/quantagent/core/notifications/**`
- `packages/core/tests/test_notification_ingress.py`
- `docs/references/plugins/notification.md`
- `openspec/changes/notification-receive-handoff-v1/**`

## Conflict Boundary With #241

`#241` 的目标是完整 HITL approval orchestration，涉及：

- `action.requested`
- `approval.requested`
- `approval.input_received`
- `approval.completed`
- Policy Gate / executor / timeout / evaluation

本 change 只做 notification ingress 的平台事实、审计和 handoff seam，不消费也不发布这些 topic，不引入 approval 领域状态机。这样可以保证：

- `notification.receive` 不再是悬空的插件返回值
- 同时又不会与 `#241` 的 approval 领域建模和 topic 设计发生职责冲突
