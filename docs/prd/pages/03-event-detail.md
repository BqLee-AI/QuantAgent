# 03. 事件详情 / 决策页

## 页面定位

事件详情 / 决策页是操盘者围绕单条事件做深入判断的核心页面。这个页面不是普通资讯详情页，而是一个把**事件事实、行业影响分析和最佳动作建议**串起来的决策页面。

页面主对象是**事件**。

## 页面目标

- 回答用户最关心的问题：`这影响什么行业/标的？`
- 让用户先看到行业影响分析，再看到最佳动作建议。
- 让用户知道这个建议是由哪条信息触发的。
- 让用户在不直接执行的前提下进入审批工作台。

## 入口与出口

### 入口

- 从首页重点事件区点击进入
- 从首页事件列表点击进入
- 从审批页点击关联事件进入
- 从审计页或运行页回跳进入

### 出口

- 去审批工作台
- 去运行详情
- 去相关插件/行业包页
- 返回事件首页

## 页面布局

采用明确的左右分栏：

```text
页面头
左栏：事件事实
右栏：行业影响分析 + 最佳动作
下方：分析补充 / 运行摘要 / 审计入口
```

推荐比例：

- 左栏 40%
- 右栏 60%

右侧必须是视觉主导区。

## 页面模块

| 模块 | 作用 | 是否 P0 必须 | 推荐前端模块 |
| --- | --- | --- | --- |
| 页面头 | 标识事件和整体状态 | 是 | `features/events/components/EventDetailHeader` |
| 事件事实卡组 | 让用户快速复盘原始信息 | 是 | `features/events/components/EventFactsPanel` |
| 行业影响分析区 | 首屏重点 | 是 | `features/events/components/IndustryImpactPanel` |
| 最佳动作卡 | 告诉用户当前最优建议 | 是 | `features/events/components/BestActionCard` |
| 分析支撑区 | 展示支持/反方观点和风险补充 | 建议 | `features/events/components/AnalysisSupportPanel` |
| 审批入口区 | 进入审批链路 | 是 | `features/events/components/ApprovalEntryCard` |
| 运行摘要区 | 看分析过程摘要 | 否 | `features/events/components/EventRunSummary` |

## 模块详细要求

### 1. 页面头

展示：

- 页面标题：事件摘要标题
- 事件状态：captured / analyzing / decision_ready / pending_approval 等
- 来源与发布时间
- 返回事件首页入口

示例：

```text
美国考虑收紧对伊朗石油出口限制
状态：decision_ready
来源：Reuters
发布时间：2026-05-24 09:14 CST
```

### 2. 事件事实卡组

左侧主要解决“发生了什么”。

建议拆成 3 张卡：

#### 2.1 事件摘要卡

- 标题
- 一段摘要
- 关键词

#### 2.2 来源卡

- 来源名称
- 来源类型：媒体 / 官方公告 / 社交账号 / 论文
- 来源可信度摘要

#### 2.3 时间卡

- 发布时间
- 采集时间
- 当前距发布时间多久

### 3. 行业影响分析区

这是全页最核心的区域。

#### 必须展示字段

| 字段 | 说明 |
| --- | --- |
| 影响行业 | 这条事件波及哪些行业 |
| 影响标的 | 这条事件波及哪些候选标的 |
| 影响方向 | 利多 / 利空 / 中性 / 不确定 |
| 影响持续时间 | 短期 / 中期 / 长期 |
| 风险点 | 为什么不能盲信 |

#### 推荐视觉

建议做成“分析卡 + 结构化网格”的形式：

```text
行业影响分析
  行业：原油 / 航运 / 油服
  标的：Brent front-month / XLE
  方向：利多原油，利空高依赖进口炼化
  持续时间：短中期
  风险点：尚缺官方二次确认
```

### 4. 最佳动作卡

首版只展示 1 个最佳动作。

#### 必须展示字段

| 字段 | 说明 |
| --- | --- |
| 动作标题 | 一句话建议 |
| 标的 | 对应资产或交易对象 |
| 逻辑理由 | 为什么建议这个动作 |
| 建议推荐度 | 当前建议值得审批的程度 |
| 分析置信度 | 当前分析结论稳定度 |
| 风险等级 | 低 / 中 / 高 |
| 推荐原因 | 为什么它优于其他候选动作 |
| 触发信息说明 | 明确由哪条事件信息触发 |

#### 交互

- 不在本卡直接放批准按钮
- 只展示 `进入审批`
- 可展示 `请求重分析`

#### 示例

```text
最佳动作
建议：观察性做多近月原油
标的：Brent Front-Month
逻辑理由：供应受限预期会先作用于近月价格
建议推荐度：78 / 100
分析置信度：74 / 100
风险等级：中
推荐原因：相对能源股，近月原油对供应冲击反应更直接
触发信息：Reuters 关于制裁收紧的首发报道
```

### 5. 分析支撑区

这个模块回答“为什么不是拍脑袋结论”。

建议包含：

- 支持观点摘要
- 反方观点摘要
- 不确定性说明

如果信息密度太高，可默认折叠，但不能完全消失。

### 6. 审批入口区

这里是详情页到审批页的桥。

建议显示：

- 当前建议是否已创建审批
- 审批状态
- 进入审批页按钮

示例：

```text
当前建议需人工确认
状态：待审批
[进入审批工作台]
```

### 7. 运行摘要区

用于承接“我想知道系统怎么得出这个建议”的需求，但不打断主决策流程。

可展示：

- 关联 Agent Run 数
- 最近一次分析时间
- 是否有工具调用失败
- 进入运行详情入口

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| 分析中 | 右侧显示“分析生成中”，左侧事实先可见 |
| 已完成 | 左右区完整可见 |
| 无最佳动作 | 展示“当前无建议动作，仅保留分析结论” |
| 分析失败 | 右侧显示失败摘要和重试建议 |
| 待审批 | 入口区高亮 |

## 示例

### 示例：原油事件详情

左侧：

```text
事件摘要
美国考虑收紧对伊朗石油出口限制，市场预期全球原油供应边际收缩。

来源
Reuters
类型：主流媒体
可信度：高

时间
发布时间：09:14
采集时间：09:15
```

右侧：

```text
行业影响分析
行业：原油、航运、油服
标的：Brent front-month、XLE
方向：利多原油
持续时间：短中期
风险点：缺少官方二次确认

最佳动作
观察性做多近月原油
建议推荐度：78/100
分析置信度：74/100
风险等级：中
[进入审批]
```

## 推荐前端模块拆分

- `EventDetailHeader`
- `EventFactsPanel`
- `EventSummaryCard`
- `EventSourceCard`
- `EventTimingCard`
- `IndustryImpactPanel`
- `BestActionCard`
- `AnalysisSupportPanel`
- `ApprovalEntryCard`
- `EventRunSummary`

## 对应数据建议

```ts
type EventDetail = {
  id: string
  title: string
  summary: string
  status: string
  sourceName: string
  sourceType: 'media' | 'official' | 'social' | 'paper'
  sourceReliabilityLevel: 'high' | 'medium' | 'low'
  publishedAt: string
  capturedAt: string
  impact: {
    industries: string[]
    assets: string[]
    direction: string
    duration: string
    risks: string[]
  }
  bestAction?: {
    title: string
    symbol: string
    rationale: string
    reliabilityScore: number
    riskLevel: 'low' | 'medium' | 'high'
    recommendedBecause: string
    triggerSummary: string
  }
}
```

## 非目标

- 不做多动作对比工作台
- 不做图表交易终端
- 不做本页直接批准执行
- 不展示完整 chain-of-thought
