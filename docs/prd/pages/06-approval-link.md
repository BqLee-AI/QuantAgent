# 06. 一次性授权页

## 页面定位

一次性授权页用于通过短期授权链接处理特定审批请求。它服务于不进入完整后台也需要快速确认的场景，例如移动端临时打开链接、外部提醒中的快速确认或临时审批。

页面主对象是**审批请求**，但它工作在受限上下文中。

## 页面目标

- 在受限上下文中安全展示审批必要信息。
- 避免依赖完整主导航和后台布局。
- 让用户在短时间窗口完成批准或拒绝。
- 清楚告诉用户当前链接是否有效、是否已过期、是否已被使用。

## 入口与出口

### 入口

- 从一次性审批链接直接进入
- 从外部通知渠道跳转进入

### 出口

- 审批成功后显示结果页
- 审批失败后引导回完整后台审批页
- token 无效时提供返回登录页或后台的入口

## 页面布局

建议采用单列聚焦布局：

```text
授权状态头
  -> 审批摘要卡
  -> 快速决策区
  -> 结果反馈区
```

不应出现完整后台导航和复杂多列布局。

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 授权状态头 | 展示 token 是否有效 | `features/approvals/components/ApprovalLinkStatusHeader` |
| 审批摘要卡 | 展示事件、建议、风险、时效 | `features/approvals/components/ApprovalLinkSummaryCard` |
| 快速决策区 | 批准 / 拒绝 | `features/approvals/components/ApprovalLinkDecisionPanel` |
| 结果反馈区 | 展示成功或失败 | `features/approvals/components/ApprovalLinkResultPanel` |

## 模块详细要求

### 1. 授权状态头

状态包括：

- token 有效
- token 已过期
- token 已使用
- token 无效

示例：

```text
一次性授权
状态：有效
剩余可用时间：09:12
```

### 2. 审批摘要卡

必须展示：

- 关联事件标题
- 建议摘要
- 风险等级
- 建议推荐度摘要
- 到期时间

可选展示：

- 触发信息摘要
- 分析置信度摘要

### 3. 快速决策区

按钮：

- `批准`
- `拒绝`

交互要求：

- 点击后要二次确认
- 确认文案需强调该动作会记录审计
- 若 token 即将过期，要在按钮附近高亮剩余时间

### 4. 结果反馈区

展示：

- 已批准
- 已拒绝
- 操作失败
- 已失效

并提供：

- 返回后台审批页
- 返回登录页

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| token 有效 | 展示摘要和按钮 |
| token 即将过期 | 高亮剩余时间 |
| token 已过期 | 禁用操作，仅展示说明 |
| token 已使用 | 展示已处理结果 |
| token 无效 | 展示错误态和返回入口 |

## 示例

```text
一次性授权
关联事件：路透：美国考虑收紧对伊朗石油出口限制
建议：观察性做多近月原油
风险：中
建议推荐度：78 / 100
剩余时间：09:12
[批准] [拒绝]
```

## 推荐前端模块拆分

- `ApprovalLinkStatusHeader`
- `ApprovalLinkSummaryCard`
- `ApprovalLinkDecisionPanel`
- `ApprovalLinkResultPanel`

## 对应数据建议

```ts
type ApprovalLinkContext = {
  tokenStatus: 'valid' | 'expired' | 'used' | 'invalid'
  expiresAt?: string
  eventTitle?: string
  actionTitle?: string
  riskLevel?: 'low' | 'medium' | 'high'
  recommendationScore?: number
}
```

## 非目标

- 不做完整后台代替页
- 不做批量审批
- 不做复杂证据面板
