# 09. Tool Invocation 详情

## 页面定位

Tool Invocation 详情页用于查看单次工具调用的输入摘要、状态变化、耗时、重试和错误，帮助定位分析失败或工具效果不稳定的问题。

页面主对象是**Tool Invocation**。

## 页面目标

- 解释工具调用发生了什么。
- 提供定位失败和重试的上下文。
- 帮助用户判断这次工具失败是否影响最终建议质量。

## 入口与出口

### 入口

- 从运行看板工具列表进入
- 从 Agent Run 详情中的工具调用摘要进入

### 出口

- 返回 Agent Run 详情
- 返回运行看板
- 去关联事件详情

## 页面布局

建议采用：

```text
页面头
  -> 调用概览卡
  -> 输入摘要卡
  -> 状态时间线
  -> 错误与重试区
  -> 关联入口区
```

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 标识工具调用对象 | `features/runtime/components/ToolInvocationHeader` |
| 调用概览卡 | 展示状态与耗时 | `features/runtime/components/ToolInvocationOverviewCard` |
| 输入摘要卡 | 展示脱敏输入摘要 | `features/runtime/components/ToolInvocationInputCard` |
| 状态时间线 | 展示状态变化 | `features/runtime/components/ToolInvocationTimeline` |
| 错误与重试区 | 展示异常与重试 | `features/runtime/components/ToolInvocationErrorPanel` |
| 关联入口区 | 跳往 Run / Event | `features/runtime/components/ToolInvocationLinks` |

## 功能明细

### 调用概览卡

展示：

- invocationId
- toolName
- 状态
- 开始时间
- 结束时间
- 总耗时

### 输入摘要卡

要求：

- 只展示脱敏后的关键输入摘要
- 不展示 secrets、token、完整私有策略

### 状态时间线

节点建议：

- queued
- started
- retrying
- completed / failed

### 错误与重试区

展示：

- 错误类型
- 错误摘要
- retryable
- 重试次数

### 关联入口区

提供：

- 查看 Agent Run
- 查看事件详情

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| completed | 展示成功摘要 |
| failed | 高亮错误区 |
| retrying | 展示重试中 |
| 无数据 | 展示不可见或不存在 |

## 示例

```text
Tool Invocation
工具：NewsVerificationTool
状态：failed
重试次数：1
错误：上游来源超时
retryable：true
```

## 推荐前端模块拆分

- `ToolInvocationHeader`
- `ToolInvocationOverviewCard`
- `ToolInvocationInputCard`
- `ToolInvocationTimeline`
- `ToolInvocationErrorPanel`
- `ToolInvocationLinks`

## 非目标

- 不展示原始 secrets
- 不做工具开发控制台
