# 08. 操盘者工作台 V1 页面与治理信息架构

## 文档状态

**版本**：v1.1
**状态**：PRD 收口稿
**关联 issue**：#127、#129、#130、#131、#132
**适用范围**：V1 Web 工作台的信息架构、页面优先级、主链路、治理对象层级和后续页面 PRD 的阅读入口
**依据**：`docs/prd/01-07`、`docs/design/02-core-architecture-and-runtime.md`、`docs/design/03-plugin-system-and-registry.md`、`docs/design/05-agent-workflow-design.md`、`docs/design/07-industry-package-design.md`、`docs/design/08-api-and-websocket-design.md`、`docs/design/09-frontend-architecture-design.md`

## 顶层结论

V1 Web 工作台的第一目标是帮助操盘者从事件流中发现高价值事件，理解行业影响，处理需要人工确认的建议，并能回放建议变化过程。

因此页面信息架构必须按运行链路和治理对象分层，而不是把所有 Registry 资源都铺成同级导航。

## V1 主链路

```text
Dashboard
  -> Events
  -> Event Detail / Decision
  -> Approval Inbox / Approval Detail / Approval Link
  -> Event Audit Timeline
```

这条链路必须优先回答：

- 今天最值得看的事件是什么。
- 这条事件影响哪些行业、标的和风险方向。
- 系统给出的最佳动作是什么，依据和反方观点是什么。
- 这条建议是否需要人工确认，确认后进入什么受控链路。
- 建议如何生成、如何变更、谁在什么时候做了什么动作。

## 页面优先级

| 优先级 | 页面 | 路由 | 主对象 | 说明 |
| --- | --- | --- | --- | --- |
| P0 | 登录页 | `/login` | Session | 建立会话后进入 Dashboard |
| P0 | Dashboard | `/` | 高价值事件 / 待审批 / 关键健康提醒 | 登录后的操盘总控页 |
| P0 | 高价值事件中心 | `/events` | Event | 承接事件浏览、筛选和重点事件扩展 |
| P0 | 事件详情 / 决策页 | `/events/:eventId` | Event | 结构化展示事实、分析和最佳动作 |
| P0 | 审批工作台 | `/approvals` | ApprovalRequest | 集中处理待确认建议 |
| P0 | 审批详情页 | `/approvals/:approvalId` | ApprovalRequest | 高风险或不确定审批的完整上下文 |
| P0 | 一次性授权页 | `/approval-link/:token` | ApprovalRequest | link_confirm 的受限确认入口 |
| P0 | 事件级审计时间线 | `/events/:eventId/audit` | Event / AuditLog | 按事件回放建议、重分析和人工动作 |
| P1 | Runtime | `/runtime` | AgentRun / ToolInvocation / RuntimeError | 解释系统过程和关键失败 |
| P1 | Agent Run 详情 | `/runtime/agents/:runId` | AgentRun | 展示结构化运行过程，不展示完整推理链 |
| P1 | Tool Invocation 详情 | `/runtime/tools/:invocationId` | ToolInvocation | 展示工具调用摘要、权限、错误和 trace |
| P2 | Registry / Plugins | `/plugins` | PluginRecord | 插件治理统一入口，按类型分视图 |
| P2 | Plugin Detail | `/plugins/:pluginId` | PluginRecord | 配置、依赖、能力、健康、审计 |
| P2 | Model Providers / LLM Policies | `/models` | ProviderManager / ProviderPolicy | 管理模型供应商、策略、fallback、预算和用量 |
| P2 | Settings | `/settings` | UserPreference / Session | 只承接会话和个人偏好，不承接核心风控规则 |

## 不作为顶层页面的对象

| 对象 | V1 展示位置 | 不作为顶层页面的原因 |
| --- | --- | --- |
| Skill | Agent Run、Plugin Detail、Industry 插件能力 tab | Skill 是 Registry 子资源，来源可能是官方、行业包内置或 runtime/private，不是操盘主任务 |
| Tool | Tool Invocation、Agent Run、Plugin Detail | Tool 是受控外部能力，治理重点是调用记录、权限、来源插件和 schema |
| Industry Package | Plugins 的 `industry` 类型视图、Plugin Detail | 行业包本质是 `industry` 类型插件，不能和 Plugin 平铺成两个并列主对象 |
| Source Binding | Industry 插件详情和事件路由解释 | Source Binding 是行业包与 source 插件之间的连接关系 |
| Broker | Plugins 的 `broker` 类型视图、Approval / Policy 说明 | Broker 是高风险交易通道插件类型，初版只能 disabled / dry_run / mock |

技术上可以保留 `/skills`、`/tools`、`/industries` 等资源路由或后续 deep link，但 V1 产品导航不应把它们抬成与事件、审批、运行态同级的入口。

## 治理对象层级

```text
Registry / Plugins
  -> Plugin type
      -> source
      -> industry
          -> SourceBinding
          -> AgentDefinition
          -> Skill
          -> Tool
          -> MarketMapping
      -> strategy
      -> notification
      -> broker
  -> Plugin Detail
      -> Overview
      -> Config
      -> Dependencies
      -> Provided Capabilities
      -> Health
      -> Audit

Runtime
  -> AgentRun
      -> used Skills
      -> ToolInvocations
      -> provider_policy / model_used
  -> ToolInvocation
  -> RuntimeError

Model Providers / LLM Policies
  -> Providers
  -> Policies
      -> fast
      -> balanced
      -> reasoning
      -> local
  -> Usage & Cost
  -> Failures
```

这个层级的目的：

- 避免把插件包和插件暴露出的子资源混为同级页面。
- 避免用户在第一阶段被 Skill、Tool、Industry 等技术对象打散注意力。
- 保留系统可观测能力，让技术用户仍可从运行过程和插件详情进入子资源。

## 页面职责边界

### Dashboard

必须做：

- 展示今日重点事件。
- 展示待处理审批摘要。
- 展示影响决策质量的关键健康提醒。
- 引导进入事件、审批和运行态。

不做：

- 不替代完整事件列表。
- 不做插件治理首页。
- 不提供内联审批或执行动作。

### Events

必须做：

- 展示重点事件区和完整事件列表。
- 支持时间、行业、可信度、分析状态等筛选。
- 支持最新和高价值混合排序。
- 点击进入事件详情。

不做：

- 不做新闻全文阅读器。
- 不做审批操作。
- 不做运行态调试面板。

### Event Detail / Decision

必须做：

- 区分事件事实、行业影响分析、最佳动作建议。
- 展示支持观点、反方观点、风险和触发信息。
- 明确建议是否已生成 ApprovalRequest。
- 提供进入审批、运行摘要和审计时间线的入口。

不做：

- 不展示完整 chain-of-thought。
- 不直接批准或执行。
- 不做多候选动作比较工作台。

### Approvals

必须做：

- 展示 ApprovalRequest 队列。
- 展示 `expires_at`、`expiration_action`、风险方向和确认等级。
- 支持 approve、reject、request_reanalysis、amend。
- 支持逐条处理；批量处理需要受更强限制。

不做：

- 不做真实执行结果页。
- 不绕过 Policy Gate。
- 不把批准文案写成“已下单”或“已执行”。

### Runtime

必须做：

- 展示 AgentRun、ToolInvocation、RuntimeError 的摘要。
- 能按 event_id、trace_id、status、plugin_id 排查。
- 从事件详情回溯系统如何得到结构化输出。

不做：

- 不替代 APM 或日志平台。
- 不展示完整模型推理链。

### Registry / Plugins

必须做：

- 统一展示插件记录，并按 source / industry / strategy / notification / broker 类型分视图。
- 进入插件详情查看配置、依赖、能力、健康和审计。
- 对 broker 类型明确展示 disabled / dry_run / mock，初版不支持实盘执行。

不做：

- 不把 Skill、Tool、Industry 分别做成顶层导航。
- 不做插件市场。
- 不允许插件注入自定义前端组件。

### Model Providers / LLM Policies

必须做：

- 展示模型供应商状态、secret reference、限流和最近失败。
- 管理 `fast`、`balanced`、`reasoning`、`local` 等 ProviderPolicy。
- 展示默认模型、fallback 模型、超时、token、temperature、预算和允许供应商。
- 从 AgentRun 回溯 `provider_policy`、`model_used`、token usage 和 cost estimate。

不做：

- 不承接 prompt 编辑。
- 不做生产级模型评估平台。
- 不展示 API key 原文。
- 不让 AgentDefinition 直接绑定具体 secret 或绕过 provider policy。

### Settings

必须做：

- 展示当前会话、actor、环境和退出登录。
- 管理个人展示偏好、通知提醒偏好和实时刷新偏好。

不做：

- 不承接插件配置、secret 管理、LLM provider key、模型策略、broker 权限和生产风控规则。
- 不把高风险系统开关做成普通偏好项。

## 必须对齐的系统约束

- REST 是业务状态真源，WebSocket 只做状态提醒和 query invalidation。
- 前端通过 generated client、types 和 Zod schema 消费 API，不在 PRD 中发明最终 contract。
- 高风险动作必须经过 Decision / Policy Gate。
- 初版 broker 只允许 disabled / dry_run / mock。
- 插件配置采用 schema-driven form，敏感字段只展示 masked value 或 secret reference。
- 模型供应商配置通过 ProviderManager / ProviderPolicy 治理，AgentDefinition 只引用 provider policy，不直接绑定 API key。
- Agent run 和 tool invocation 只展示结构化摘要，不展示完整模型推理链。
- 审批、插件生命周期、配置变更、高风险工具调用和运行时错误都必须可审计。

## 文档拆分策略

`pages/` 下文档只作为页面附录，不作为独立架构真源。页面附录应服务于以下问题：

- 页面要解决哪个用户任务。
- 依赖哪个主对象和状态。
- 入口、出口和不可做事项是什么。
- 空态、失败、权限不足、实时断连如何处理。
- 验收标准是什么。

组件名、字段草案和原型只能作为参考，不应替代 `packages/contracts`、OpenAPI、JSON Schema 或 OpenSpec。

## 后续 OpenSpec 建议

若本 PRD 评审通过，应创建统一 change：

```text
web-trader-workbench-v1
```

建议包含：

- Dashboard / Events / Event Detail 行为 spec。
- ApprovalRequest / ApprovalDecision / ApprovalLink 行为 spec。
- EventAuditTimeline 节点和 diff 摘要 spec。
- Scoring 展示语义 spec。
- Registry / Plugin 治理入口的非顶层 Skill / Tool / Industry 约束。
- Model Providers / LLM Policies 治理入口、ProviderPolicy 字段和敏感信息边界。
