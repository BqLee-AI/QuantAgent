# 07. Runtime

## 页面定位

Runtime 是解释和排障页，用于查看 AgentRun、ToolInvocation、scheduler run 和 runtime error。它服务于“系统为什么这样判断”和“当前系统是否影响判断质量”，不是操盘者第一入口。

## 用户任务

- 看到当前运行健康摘要。
- 从事件详情回溯某次分析过程。
- 查看失败 AgentRun、ToolInvocation 和 RuntimeError。
- 按 event_id、trace_id、status、plugin_id 排查。

## 主对象和真源

| 信息 | 真源 |
| --- | --- |
| Agent run | `/agents/runs` 类资源 |
| Tool invocation | `/tools/invocations` 类资源 |
| Runtime error | `/runtime/errors` |
| 健康摘要 | `/runtime/health` |
| 实时变化 | WebSocket topic 触发刷新 |

## 页面结构

```text
页面头
  -> 运行健康摘要
  -> 筛选与追踪输入
  -> AgentRun 列表
  -> ToolInvocation 列表
  -> RuntimeError 列表
```

## 关键模块

### 运行健康摘要

展示：

- 当前运行中 AgentRun 数。
- 最近失败数。
- 工具错误数。
- runtime error 严重级别摘要。
- 实时连接状态。

### 筛选与追踪

支持：

- event_id。
- trace_id。
- plugin_id。
- status。
- 时间范围。

### AgentRun 列表

展示：

- run_id。
- event_id。
- run_type。
- status。
- provider_policy。
- model_used。
- token_usage / cost_estimate 摘要。
- started_at / ended_at。
- duration。
- error summary。
- 详情入口。

### ToolInvocation 列表

展示：

- invocation_id。
- tool_id。
- 来源插件。
- risk_level。
- status。
- duration。
- retry_count。
- error summary。
- 详情入口。

### RuntimeError 列表

展示：

- component。
- severity。
- status。
- error_code。
- error_message 摘要。
- provider / provider_policy，如果错误来自模型供应商。
- trace_id。
- 关联事件或插件。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| 无运行数据 | 展示空态 |
| 局部资源失败 | 对应模块错误，不阻断整页 |
| 严重错误 | RuntimeError 列表置顶 |
| 实时断连 | 展示连接降级状态并允许手动刷新 |

## 安全边界

- 不展示完整模型推理链。
- 不展示完整 prompt。
- 模型、token 和成本只展示结构化摘要。
- Tool 输入输出默认展示脱敏摘要。
- 展开更详细参数需要 capability，后端仍必须校验。

## 验收口径

必须成立：

- 用户能从事件详情定位到相关运行过程。
- 用户能用 trace_id 或 event_id 排查。
- 工具失败和 Agent 失败不会被隐藏。
- 页面不替代日志平台，也不展示敏感原始载荷。

## 非目标

- 不做完整 APM。
- 不做日志搜索平台。
- 不做实时监控墙。
- 不做模型调试器。
