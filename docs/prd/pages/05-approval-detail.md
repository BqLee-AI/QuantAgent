# 05. 审批详情页

## 页面定位

审批详情页用于处理单条 ApprovalRequest 的完整确认。相比审批工作台列表，它提供更完整的事件上下文、证据、风险、确认等级、到期策略和历史记录。

## 用户任务

- 在批准、拒绝、重分析或修改前复核完整上下文。
- 理解 ActionRequest 为什么产生，以及 Policy Gate 要求怎样的人类确认。
- 查看支持证据、反方观点、风险方向和到期策略。
- 完成强确认或进入事件详情、审计时间线继续复核。

## 主对象和真源

主对象是 ApprovalRequest。

| 信息 | 真源 |
| --- | --- |
| 审批核心信息 | ApprovalRequest |
| 动作内容 | ActionRequest 摘要 |
| 策略解释 | ResolvedApprovalPolicy / ApprovalEvaluation |
| 事件上下文 | Event / ScoredAnalysis 摘要 |
| 处理历史 | ApprovalInput / ApprovalDecision / audit logs |
| 运行追踪 | trace_id / request_id |

## 页面结构

```text
页面头
  -> 审批概览
  -> 左栏：事件上下文 + 证据 + 反方观点
  -> 右栏：动作详情 + 策略解释 + 操作区
  -> 底部：处理历史 + 关联入口
```

## 关键模块

### 审批概览

必须展示：

- Approval ID。
- 状态。
- risk_level。
- risk_direction。
- recommendation_score。
- analysis_confidence。
- required_confirmation_level。
- `expires_at`。
- `expiration_action`。
- policy_source。

### 事件上下文

必须展示：

- 事件摘要。
- 来源权威度。
- 事件可信度。
- 影响行业和标的。
- 触发信息。
- 事件详情入口。

### 证据和风险

必须展示：

- 支持证据摘要。
- 反方观点摘要。
- 不确定性和数据缺口。
- 多信源验证状态。
- 关键工具失败对本审批的影响，如果存在。

### 动作详情

必须展示：

- action_type。
- action_side。
- target_type / target_id。
- instrument / market，如果适用。
- proposed_payload 的脱敏摘要。
- blocked_brokers / allowed_brokers 摘要，如果有。

不得展示完整私有策略、secret、账户密钥或敏感参数。

### 操作区

支持：

- approve。
- reject。
- request_reanalysis。
- amend。

交互要求：

- strong_confirm 需要明确结构化确认。
- link_confirm 应提示也可通过一次性链接确认，但当前后台仍可处理。
- manual_only 只保留强确认入口。
- amend 必须展示修改前后摘要。
- 操作后展示结果，并刷新审计历史。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| pending | 操作区可用 |
| approved / rejected | 操作区只读，展示处理结果 |
| expired | 禁用动作，展示 expiration_action |
| blocked | 展示阻断原因和策略来源 |
| 权限不足 | 操作禁用，展示 capability 缺失 |
| 操作失败 | 保留当前上下文，展示 request_id / trace_id |

## 风控边界

- 批准只表示人类确认，后续仍由 Policy Gate 和 broker mode 决定。
- 不允许前端根据分数绕过 required_confirmation_level。
- 不允许在详情页展示完整模型推理链。
- 不允许明文展示 secret、token、交易账户敏感信息或完整私有策略。

## 验收口径

必须成立：

- 用户能解释为什么这条审批需要人工确认。
- 用户能看到风险方向、确认等级和到期策略。
- 用户能看到支持和反方观点，而不是只看到建议动作。
- 所有动作结果都能回写审计历史。

失败信号：

- 页面只展示“批准 / 拒绝”按钮和一段建议。
- 缺少 expiration_action 或 confirmation level。
- 高风险动作可以通过弱确认入口处理。

## 非目标

- 不做多人审批流编排。
- 不做真实执行结果页。
- 不做策略规则编辑器。
- 不做完整 payload diff 工具。
