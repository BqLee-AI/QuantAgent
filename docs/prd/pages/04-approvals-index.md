# 04. 审批工作台

## 页面定位

审批工作台是处理 ApprovalRequest 的队列页。它不是任务中心，也不是执行控制台，而是高风险建议进入 Policy Gate 之前的人类确认入口。

## 用户任务

- 查看待处理、即将过期、已处理和已过期的审批请求。
- 按推荐度、到期时间、风险方向和确认等级排序。
- 对请求执行 approve、reject、request_reanalysis 或 amend。
- 在必要时进入审批详情或事件详情复核证据。

## 主对象和真源

主对象是 ApprovalRequest。

| 信息 | 真源 |
| --- | --- |
| 审批队列 | `/approvals` 类 REST 资源 |
| 审批动作 | `/approvals/{approval_id}/actions/*` |
| 到期策略 | ApprovalPolicyResolver 输出 |
| 关联事件 | Event 摘要 |
| 建议和风险 | ActionRequest / DecisionResult 摘要 |
| 审计 | audit logs |

## 页面结构

```text
页面头
  -> 队列概览
  -> 筛选与排序
  -> 审批列表
  -> 受限批量操作区
```

## 关键模块

### 队列概览

必须展示：

- 待处理数量。
- 即将过期数量。
- 高风险 increase_risk 数量。
- 需要 strong_confirm / link_confirm / manual_only 的数量。

### 筛选与排序

筛选：

- 状态：pending / approved / rejected / expired。
- 风险方向：increase_risk / reduce_risk / neutral。
- 风险等级。
- 确认等级。
- 关联行业或来源。

排序：

- 即将过期优先。
- 建议推荐度优先。
- 风险最高优先。
- 最新创建优先。

### 审批列表

每条审批必须展示：

- 关联事件标题和来源。
- 建议动作。
- 建议推荐度。
- 事件可信度摘要。
- 分析置信度摘要。
- 风险方向和风险等级。
- `expires_at` 倒计时。
- `expiration_action`。
- required_confirmation_level。
- 触发信息摘要。
- 查看详情和查看事件入口。

### 审批动作

支持：

- approve。
- reject。
- request_reanalysis。
- amend。

交互要求：

- increase_risk 默认二次确认。
- strong_confirm / link_confirm / manual_only 不能被弱确认入口处理。
- request_reanalysis 建议要求填写原因。
- amend 必须展示修改前后摘要，并写审计。
- 操作失败要展示 request_id / trace_id。

### 批量处理

首版只允许受限批量操作：

- 同一状态。
- 同一风险方向。
- 同一 confirmation level。
- 不包含 manual_only。
- 不包含已过期或即将进入自动过期处理的请求。

批量 approve 默认不建议作为 P0 必做；如果实现，必须有二次确认并明确“批准只代表人工确认，不代表真实执行完成”。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| 无待处理审批 | 展示空态和返回事件中心入口 |
| 即将过期 | 倒计时高亮 |
| 已过期 | 禁用动作，展示 expiration_action 结果或等待同步 |
| 部分动作失败 | 行内错误，不阻断其他行 |
| 权限不足 | 禁用动作，展示能力缺失和 request_id |
| 实时断连 | 允许 REST 刷新，提示状态可能延迟 |

## 风控边界

- approve 不等于真实执行完成。
- 前端不直接决定 executor。
- 用户拒绝后，同一建议不得继续自动执行。
- 批量处理必须比逐条处理更保守。
- manual_only 只允许强确认入口，不允许通过一次性链接或文本确认绕过。

## 验收口径

必须成立：

- 用户能在列表层理解审批来源、风险、到期策略和建议内容。
- 用户能处理 approve / reject / request_reanalysis / amend。
- 高风险和即将过期请求有明确视觉层级。
- 批量处理边界清晰，不误导为真实执行。

失败信号：

- 审批项只有标题和按钮，缺少风险方向、确认等级和到期策略。
- 批量批准不区分风险和确认等级。
- UI 文案暗示批准即下单或真实执行完成。

## 非目标

- 不做真实执行结果页。
- 不做复杂多人会签流。
- 不做通用任务中心。
- 不绕过 Policy Gate。
