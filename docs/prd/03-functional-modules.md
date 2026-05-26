# 03. 功能模块

## 模块总览

系统功能分为五层：事件接入、路由、行业分析、决策审批、运行时治理。事件从 Source Plugin 进入 Event Bus 后，由 Router Agent 选择行业包，再由 AgentRuntime、Scoring / Debate 和 Decision / Policy Gate 输出通知、审批、dry-run 或受控执行结果。

```text
Source Plugin
  -> Event Bus
  -> Router Agent
  -> Industry Plugin / AgentRuntime
  -> Scoring / Debate
  -> Decision / Policy Gate
  -> Notification / Human Approval / Broker
  -> Persistence / Audit / WebSocket
```

## 3.1 事件接入与路由

### Source Plugin

Source Plugin 负责采集、接收和标准化外部信息，不直接做行业判断。Pull 类数据源由统一 Scheduler 调度，链接正文读取优先通过 Readability 和 Jina 类插件/工具完成。

### Router Agent

Router Agent 负责从事件中提取实体、行业和候选标的，并把事件路由到一个或多个行业包。

要求：

- 支持多行业并行路由。
- 支持输出路由理由和置信度。
- 支持低置信度回退到仅通知或人工标注。
- 不直接给出最终执行结论。

## 3.2 行业包与 AgentRuntime

### Industry Plugin

行业包是插件，必须通过 `plugin.yaml` 注册。行业包可以包含 SourceBinding、AgentDefinition、Skill、Tool、market mapping 和评分提示，但不能绕过 Registry、ToolRegistry、Skill Registry 或 Decision。

### AgentRuntime

AgentRuntime 是统一的 Agent 运行入口，负责加载 AgentDefinition、授权工具、注入上下文并调用 DeepAgents 运行时。

要求：

- 输入和输出必须结构化。
- 行业包不能自己绕过核心直接创建 Agent。
- 外部行动必须通过 tool invocation 完成。

### ToolRegistry 与 Skill Registry

- ToolRegistry 统一治理工具来源、参数 schema、权限和审计。
- Skill Registry 统一治理标准 Skill 包、版本、来源和授权。
- 行业包自定义工具和 Skill 不能直接裸露给 Agent，必须先注册和授权。

## 3.3 Scoring / Decision / Approval

### Scoring / Debate

Scoring / Debate 负责聚合多个行业包输出，形成支持观点、反方观点、风险提示和标准置信度。

### Decision / Policy Gate

Decision / Policy Gate 根据置信度、风险、权限和用户策略决定进入哪种结果：

- 仅通知。
- 人工确认。
- 限时确认。
- dry-run。
- 阻断。
- 受控执行。

### HITL

HITL 以审批工作台、一次性授权页和限时确认构成。用户必须能看到建议动作、关键证据、风险和审计记录入口，并可确认、拒绝或要求重新分析。

## 3.4 Registry、状态与审计

### Registry

Registry 负责插件发现、manifest 校验、依赖解析、生命周期管理和运行时状态查询。

### Persistence / Audit

系统需要记录事件状态、插件状态、审批结果、通知结果、错误和审计信息，确保后续能够回放和排查。

### 状态流

建议状态如下：

```text
captured -> routed -> analyzing -> scored -> decision_ready -> pending_approval -> approved/rejected
-> notified / dry_run_executed / executed -> failed
```
