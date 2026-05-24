# 06. 一次性授权页

## 页面定位

一次性授权页服务于 `link_confirm` 场景，用短期 token 展示某个 ApprovalRequest 的最小必要上下文，并允许用户在受限环境中完成批准或拒绝。

它不是完整后台的替代页，也不能处理 manual_only 审批。

## 用户任务

- 打开外部通知中的一次性链接。
- 确认链接是否有效、是否过期、是否已使用。
- 查看最小必要事件、建议和风险摘要。
- 完成 approve 或 reject。
- 失败时进入登录或完整后台审批详情。

## 主对象和真源

主对象是 ApprovalRequest 的 link context。

| 信息 | 真源 |
| --- | --- |
| token 状态 | Approval link 校验接口 |
| 审批摘要 | 受限 ApprovalRequest context |
| 动作结果 | ApprovalInput / ApprovalDecision |
| 审计 | audit logs |

## 页面结构

```text
授权状态
  -> 审批摘要
  -> 风险和到期提示
  -> 快速决策
  -> 结果反馈
```

不展示完整主导航。

## 必须展示的信息

- token 状态：valid / expired / used / invalid。
- 剩余可用时间。
- 关联事件标题。
- 建议动作摘要。
- 风险方向和风险等级。
- required_confirmation_level。
- expiration_action。
- 触发信息摘要。
- 审计提示。

## 操作规则

允许：

- approve。
- reject。

不允许：

- amend。
- 批量审批。
- manual_only 审批。
- 查看完整敏感配置或完整策略。

交互要求：

- approve / reject 前必须二次确认。
- 即将过期时高亮倒计时。
- 操作成功后禁用按钮，并展示结果。
- 操作失败时显示可追踪错误摘要，不泄露 token 原文。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| valid | 展示摘要和操作按钮 |
| near_expiry | 高亮剩余时间 |
| expired | 禁用操作，展示 expiration_action |
| used | 展示已处理结果 |
| invalid | 展示错误和返回登录入口 |
| permission_mismatch | 展示受限错误，引导进入后台 |
| operation_failed | 展示错误摘要和 request_id |

## 安全边界

- token 不长期保存在前端状态中。
- 页面只展示该 token 允许访问的最小字段。
- 不展示 secret、完整策略、完整 prompt、敏感账户信息。
- link_confirm 不能替代 manual_only。
- 所有操作写审计。

## 验收口径

必须成立：

- 用户能知道链接是否还能用。
- 用户能在最小上下文中理解建议、风险和到期后果。
- 操作后结果明确，不允许重复提交。
- 过期、已使用、无效 token 都有清晰退路。

失败信号：

- 一次性页展示完整后台数据。
- token 无效时仍保留操作按钮。
- manual_only 被一次性链接处理。

## 非目标

- 不做完整审批详情页。
- 不做批量审批。
- 不做策略或 payload 编辑。
- 不替代 Web 后台强确认入口。
