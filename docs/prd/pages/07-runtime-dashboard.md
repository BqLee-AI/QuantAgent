# 07. 运行看板

## 页面定位

运行看板用于查看系统当前运行健康度、Agent 运行、工具调用、调度状态和关键错误。它是解释系统是否正常工作的后台页，而不是操盘者的第一入口。

页面主对象是**运行态**。

## 页面目标

- 给出系统整体健康感知。
- 告诉用户哪些事件分析卡住了、哪些工具失败了。
- 为事件详情页中的“我想看系统过程”需求提供承接。
- 帮助用户判断当前建议是否可能受到运行异常影响。

## 入口与出口

### 入口

- Dashboard 的系统健康提醒区
- 事件详情页中的运行摘要
- 顶部导航“运行态”

### 出口

- Agent Run 详情
- Tool Invocation 详情
- 返回事件详情或 Dashboard

## 页面布局

建议采用上下分区布局：

```text
页面头
  -> 运行概览条
  -> 中部双栏：Agent 运行 / 工具调用
  -> 下方双栏：调度任务 / 错误告警
```

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 说明本页定位 | `features/runtime/components/RuntimePageHeader` |
| 运行概览条 | 展示整体状态 | `features/runtime/components/RuntimeSummaryBar` |
| Agent 运行列表 | 展示最近运行 | `features/runtime/components/AgentRunList` |
| 工具调用列表 | 展示最近调用 | `features/runtime/components/ToolInvocationList` |
| 调度任务区 | 展示 scheduler 状态 | `features/runtime/components/SchedulerPanel` |
| 错误告警区 | 展示 runtime failed 等关键错误 | `features/runtime/components/RuntimeAlertsPanel` |

## 模块详细要求

### 1. 页面头

展示：

- 标题：`运行看板`
- 副标题：解释它是系统解释与排障页，不是操盘首页

### 2. 运行概览条

建议展示：

| 指标 | 说明 |
| --- | --- |
| 运行中 Agent 数 | 当前活跃分析任务 |
| 最近失败数 | 最近失败运行规模 |
| 工具错误数 | 最近工具失败规模 |
| 调度延迟 | 当前 scheduler 是否积压 |

### 3. Agent 运行列表

每条必须展示：

- eventId
- runId
- 状态
- 耗时
- 最近更新时间
- 进入详情按钮

### 4. 工具调用列表

每条必须展示：

- 工具名
- invocationId
- 状态
- 耗时
- 错误摘要

### 5. 调度任务区

展示：

- 排队任务数
- 失败任务数
- 最近一次调度时间

### 6. 错误告警区

高亮：

- runtime.failed
- 关键来源故障
- 工具重试异常
- WebSocket / realtime 退化状态

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| 正常 | 展示完整概览 |
| 无运行数据 | 展示空态 |
| 局部失败 | 对应模块展示错误提示，不阻断整页 |
| 严重异常 | 错误告警区置顶高亮 |

## 示例

```text
运行看板
运行中 Agent：4
最近失败：2
工具错误：5
调度延迟：12s

最近 Agent Run
- run_1023 事件 evt_77 analyzing 12s
- run_1024 事件 evt_78 failed 4s

错误告警
- NewsVerificationTool 近 10 分钟失败 3 次
- Realtime 已降级为 polling
```

## 推荐前端模块拆分

- `RuntimePageHeader`
- `RuntimeSummaryBar`
- `AgentRunList`
- `AgentRunRow`
- `ToolInvocationList`
- `ToolInvocationRow`
- `SchedulerPanel`
- `RuntimeAlertsPanel`

## 对应数据建议

```ts
type RuntimeSummary = {
  activeAgentRuns: number
  recentFailures: number
  toolErrors: number
  schedulerLagSeconds: number
}
```

## 非目标

- 不做深度 APM 工具替代品
- 不做完整日志平台
- 不做实时终端监控墙
