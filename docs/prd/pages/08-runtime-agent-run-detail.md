# 08. Agent Run 详情

## 页面定位

Agent Run 详情页用于查看单次分析运行的结构化过程摘要，帮助用户理解某条事件是如何被分析的。它解释的是运行过程，而不是展示完整模型内部推理。

页面主对象是**Agent Run**。

## 页面目标

- 展示结构化时间线，而不是完整推理链。
- 让用户知道使用了哪些 Skill、哪些工具、哪里出错了。
- 让用户从系统过程回到事件和建议上下文。

## 入口与出口

### 入口

- 从运行看板 Agent 列表进入
- 从事件详情运行摘要进入

### 出口

- Tool Invocation 详情
- 关联事件详情
- 返回运行看板

## 页面布局

建议采用：

```text
页面头
  -> Run 概览卡
  -> 步骤时间线
  -> 下方双栏：Skill 使用摘要 / 工具调用摘要
  -> 底部：输出摘要与错误摘要
```

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 标识 run 与关联事件 | `features/runtime/components/AgentRunDetailHeader` |
| Run 概览卡 | 展示 run 基本信息 | `features/runtime/components/AgentRunOverviewCard` |
| 步骤时间线 | 展示结构化步骤 | `features/runtime/components/AgentRunTimeline` |
| Skill 使用摘要 | 展示调用的 Skill | `features/runtime/components/RunSkillPanel` |
| 工具调用摘要 | 展示相关工具调用 | `features/runtime/components/RunToolsPanel` |
| 输出摘要与错误摘要 | 展示产出与失败说明 | `features/runtime/components/RunOutputPanel` |

## 功能明细

### Run 概览卡

展示：

- runId
- eventId
- AgentDefinition
- 状态
- 总耗时
- startedAt / endedAt

### 步骤时间线

至少支持展示：

- started
- step_added
- tool_called
- output_generated
- completed / failed

### Skill 使用摘要

展示：

- Skill 名称
- 来源
- 版本
- 是否成功参与本次分析

### 工具调用摘要

展示：

- 工具名称
- 调用状态
- 耗时
- 详情入口

### 输出摘要与错误摘要

展示：

- 结构化输出摘要
- 错误摘要
- 如果失败，明确失败阶段

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| completed | 展示完整时间线与输出摘要 |
| failed | 高亮失败节点和错误摘要 |
| running | 时间线持续增长 |
| 无数据 | 展示 run 不存在或不可见错误态 |

## 示例

```text
Run run_1023
关联事件：evt_77
Agent：OilIndustryAgent
状态：completed
耗时：12.4s

时间线
- 09:15 Router 完成
- 09:15 Oil Industry Agent 启动
- 09:16 调用 NewsVerificationTool
- 09:16 输出结构化分析
```

## 推荐前端模块拆分

- `AgentRunDetailHeader`
- `AgentRunOverviewCard`
- `AgentRunTimeline`
- `RunSkillPanel`
- `RunToolsPanel`
- `RunOutputPanel`

## 非目标

- 不展示完整 chain-of-thought
- 不做低层 token trace 诊断页
