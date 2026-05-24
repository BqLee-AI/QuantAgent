# 05. 审批详情页

## 页面定位

审批详情页用于承接单条审批请求的完整查看与处理。相比审批工作台列表，它提供更充分的证据、分析上下文、审批历史和操作确认，适用于用户在列表层面无法直接拍板、需要更强上下文支持的场景。

页面主对象是**审批请求**。

## 页面目标

- 让用户在单条审批上下文内做更稳妥判断。
- 展示建议动作、关键证据、风险方向、变更记录和审批结果。
- 为高风险审批提供更清晰的二次确认空间。
- 让用户从审批详情稳定回跳到事件详情和审计时间线。

## 入口与出口

### 入口

- 从审批工作台点击“查看详情”进入
- 从事件详情中的审批入口进入
- 从一次性授权页校验失败后转回完整后台审批页

### 出口

- 返回审批工作台
- 进入关联事件详情
- 进入事件级审计时间线
- 执行审批动作后停留本页或返回列表

## 页面布局

建议采用上下双层结构：

```text
页面头
  -> 审批概览卡
  -> 左右双栏
     左：证据摘要 + 事件上下文
     右：建议详情 + 审批操作
  -> 底部：审批历史 / 关联入口
```

这样做的原因：

- 左侧更适合承载“为什么建议成立”
- 右侧更适合承载“你现在要不要批准”
- 审批历史放底部，避免抢首屏判断注意力

## 页面模块

| 模块 | 作用 | 是否 P1 必须 | 推荐前端模块 |
| --- | --- | --- | --- |
| 页面头 | 标识审批对象、状态和来源 | 是 | `features/approvals/components/ApprovalDetailHeader` |
| 审批概览卡 | 展示审批核心元信息 | 是 | `features/approvals/components/ApprovalOverviewCard` |
| 事件上下文卡 | 补充审批对应的事件摘要 | 是 | `features/approvals/components/ApprovalEventContextCard` |
| 证据摘要区 | 展示支持证据、反方观点、风险 | 是 | `features/approvals/components/ApprovalEvidencePanel` |
| 建议详情区 | 展示建议动作完整说明 | 是 | `features/approvals/components/ApprovalActionDetail` |
| 审批操作区 | 承载 approve / reject / reanalysis / amend | 是 | `features/approvals/components/ApprovalDecisionPanel` |
| 审批历史区 | 展示已发生处理记录 | 是 | `features/approvals/components/ApprovalHistoryPanel` |
| 关联入口区 | 跳往事件详情、审计时间线 | 建议 | `features/approvals/components/ApprovalRelatedLinks` |

## 模块详细要求

### 1. 页面头

展示：

- 标题：`审批详情`
- 审批状态：pending / approved / rejected / expired
- 关联事件标题
- 返回审批工作台入口

示例：

```text
审批详情
状态：pending
关联事件：路透：美国考虑收紧对伊朗石油出口限制
```

### 2. 审批概览卡

至少展示：

| 字段 | 说明 |
| --- | --- |
| 审批 ID | 唯一标识 |
| recommendation score | 当前建议推荐度 |
| 分析置信度 | 当前分析结论稳定度 |
| 风险等级 | 低 / 中 / 高 |
| 创建时间 | 审批产生时间 |
| expires_at | 过期时间 |
| expiration_action | 过期后默认行为 |

### 3. 事件上下文卡

这个模块用于让审批页不脱离事件语境。

建议展示：

- 事件摘要
- 来源名称
- 来源权威度
- 事件可信度
- 影响行业

用户应能在这里快速回忆“我为什么会收到这条审批”。

### 4. 证据摘要区

首版建议展示：

- 支持证据 2 到 4 条
- 反方观点 1 到 2 条
- 风险摘要 1 到 3 条
- 关键触发信息 1 条

建议拆成：

#### 4.1 支持证据卡

- Reuters 首发报道
- 行业分析认为供给预期将收缩

#### 4.2 反方观点卡

- 尚无官方二次确认
- 市场可能已有部分预期

#### 4.3 风险卡

- 建议不适合误解为自动放行
- 若消息被澄清，价格可能快速回吐

### 5. 建议详情区

建议展示：

| 字段 | 说明 |
| --- | --- |
| 建议标题 | 一句话建议 |
| 标的 | 建议指向对象 |
| 逻辑理由 | 为什么建议这个动作 |
| 建议推荐度 | 是否值得优先审批 |
| 分析置信度 | 分析结论稳定程度 |
| 风险等级 | 当前建议风险级别 |
| 触发信息 | 明确由哪条信息触发 |
| 推荐原因 | 为什么选这个动作而不是其他动作 |

### 6. 审批操作区

按钮：

- `批准`
- `拒绝`
- `请求重分析`
- `修改后提交`

交互要求：

- 高风险动作前需二次确认
- `请求重分析` 可选填原因
- `修改后提交` 首版可以作为占位动作，不要求完整实现复杂编辑器

### 7. 审批历史区

展示节点：

- 创建审批
- 已查看
- 已批准 / 已拒绝
- 请求重分析
- 审批被更新

### 8. 关联入口区

必须允许用户：

- 查看原事件详情
- 查看事件级审计时间线

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| 待处理 | 审批操作区可用 |
| 已批准 | 操作区只读，展示结果 |
| 已拒绝 | 操作区只读，展示拒绝原因 |
| 已过期 | 显示过期说明和 expiration_action |
| 加载失败 | 保留页头和重试入口 |

## 示例

```text
审批详情
状态：pending
事件：路透：美国考虑收紧对伊朗石油出口限制
建议：观察性做多近月原油
建议推荐度：78/100
分析置信度：74/100
到期时间：14:30

支持证据
- Reuters 首发报道
- 原油行业包已完成一级影响分析

反方观点
- 尚无官方二次确认

风险
- 市场可能先反应后回吐
- 不应将批准误解为真实执行已完成
```

## 推荐前端模块拆分

- `ApprovalDetailHeader`
- `ApprovalOverviewCard`
- `ApprovalEventContextCard`
- `ApprovalEvidencePanel`
- `ApprovalActionDetail`
- `ApprovalDecisionPanel`
- `ApprovalHistoryPanel`
- `ApprovalRelatedLinks`

## 对应数据建议

```ts
type ApprovalDetail = {
  id: string
  eventId: string
  eventTitle: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  recommendationScore: number
  analysisConfidenceScore: number
  riskLevel: 'low' | 'medium' | 'high'
  createdAt: string
  expiresAt?: string
  expirationAction?: string
  eventContext: {
    summary: string
    sourceName: string
    sourceAuthorityLevel: 'A' | 'B' | 'C' | 'D'
    eventReliabilityScore: number
    industries: string[]
  }
  action: {
    title: string
    symbol: string
    rationale: string
    triggerSummary: string
    recommendedBecause: string
  }
  evidence: {
    supportPoints: string[]
    counterPoints: string[]
    risks: string[]
  }
}
```

## 非目标

- 不做复杂审批流编排器
- 不做全文 diff 审核器
- 不做真实执行结果页
