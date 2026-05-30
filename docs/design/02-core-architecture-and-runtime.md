# 02. 核心架构与运行时设计

## 文档状态

**状态**：草案 v0.1  
**范围**：核心运行时主流程、事件模型、插件协作、行业包输出、决策边界、持久化边界  
**不包含**：具体行业包实现、详细数据库表结构、真实交易执行细节、前端页面设计

## 文档使用约定

本文档用于定义初始工程方向和模块边界，不要求实际开发严格逐字照做。开发过程中如果发现实现成本、框架限制、性能问题或业务边界变化，应以实际验证结果为准，并回写设计文档。

## 设计结论

- `Event` 是系统核心抽象。
- 所有数据源插件、行业包插件、Agent workflow、前端状态和审计记录都围绕事件流转。
- 核心运行时采用事件驱动管线。
- 行业包必须输出统一结构，不能各自返回任意格式。
- Decision 独立成模块，行业包可以提出分析、建议和执行请求，但不能绕过 Decision / Policy Gate。
- 初版优先实现 notification + human approval；broker 插件接口保留真实执行边界，但初版只做虚盘，不操作实盘。
- broker 插件初版至少支持 disabled / 虚盘 / mock，未来真实执行作为受控能力逐步接入。
- 持久化是核心运行时的一部分，负责事件状态、插件状态、配置、审计和用户操作记录。

## 核心运行时流程

```text
Source Plugin
  -> Event Bus
  -> Router Agent
  -> Industry Plugin
  -> Scoring / Debate
  -> Decision
  -> Notification / Human Approval / Broker
  -> Persistence / Audit
```

## 阶段职责

| 阶段 | 职责 | 产物 |
| --- | --- | --- |
| Source Plugin | 抓取或接收外部信息 | Raw event |
| Event Bus | 分发事件、解耦模块 | Event envelope |
| Router Agent | 识别实体、行业和候选插件 | Routing decision |
| Industry Plugin | 执行行业分析和市场映射 | Industry analysis |
| Scoring / Debate | 聚合支持和反对观点，计算置信度 | Scored analysis |
| Decision | 决定通知、人工确认、虚盘或拒绝 | Decision result |
| Notification | 推送或展示建议 | Notification record |
| Human Approval | 用户确认、拒绝或要求重分析 | Approval record |
| Broker | 交易通道，预留真实执行能力 | 初版 disabled / 虚盘 |
| Persistence / Audit | 保存事件、状态、配置、审计记录 | Database records |

## Event 核心模型

事件是系统最重要的领域对象。它不是简单日志，而是贯穿整个运行时的状态载体。

### Event 最小字段

```text
Event
  id
  source
  source_type
  title
  content
  url
  published_at
  captured_at
  language
  entities
  tags
  status
  trace_id
  metadata
```

### Event 状态

```text
captured
  -> routed
  -> analyzing
  -> scored
  -> decision_ready
  -> pending_approval
  -> approved
  -> rejected
  -> notified
  -> dry_run_executed
  -> failed
```

状态约束：

- 状态流转必须可审计。
- 每次状态变化都需要记录时间、操作者或模块、原因。
- 插件不能随意跳过 Decision 阶段。
- 真实交易执行状态暂不进入初版主路径。

## 持久化边界

事件状态、插件状态、用户确认、通知记录和审计记录都需要持久化，否则系统无法回放、排查和评估。数据库、ORM 和迁移工具选型见 [01. 技术栈与项目结构设计](01-tech-stack-and-project-structure.md)。

### 初版持久化对象

初版优先持久化：

- Event。
- Event state transition。
- Plugin registry record。
- Plugin config。
- Routing decision。
- Industry analysis summary。
- Scored analysis summary。
- Decision result。
- Notification record。
- Human approval record。
- Runtime error。

暂缓持久化：

- 完整模型原始推理链。
- 真实交易订单。
- 复杂回测结果。
- 大规模原始网页快照。

## Event Envelope

Event Bus 传递的不是裸 Event，而是 Event Envelope。

```text
EventEnvelope
  id
  topic
  payload
  producer
  created_at
  correlation_id
  causation_id
  headers
  retry_count
  schema_version
```

原因：

- 支持追踪事件因果关系。
- 支持失败重试。
- 支持默认内存 fake 与 Kafka 可选运行时共用同一 wire contract。
- 支持多个插件订阅同一个事件。
- `payload` 允许承载 source captured、routing、decision 和 runtime failure 等不同阶段消息，而不强行把裸 `Event` 作为唯一根对象。

当前运行约定：

- 普通本地开发和单元测试默认使用内存 fake，不依赖 Kafka broker。
- 真实 Kafka 通过显式配置启用，作为 worker / scheduler / future runtime 的跨进程分发 backend。
- Event Bus 不替代数据库与审计真源；RawEvent / Event 持久化、outbox、replay 和 DLQ 另行演进。

## Topic 设计

初版建议使用稳定 topic 命名：

```text
source.event.captured
event.routed
industry.analysis.requested
industry.analysis.completed
analysis.scored
decision.created
approval.requested
approval.completed
notification.requested
notification.completed
broker.dry_run_requested
broker.dry_run_completed
runtime.failed
```

## Router Agent

Router Agent 负责把事件路由到一个或多个行业包。

### 输入

- Event。
- 已注册行业插件列表。
- 行业插件 manifest。
- 行业关键词、实体规则和能力描述。

### 输出

```text
RoutingDecision
  event_id
  selected_industries
  rejected_industries
  entities
  reasoning_summary
  confidence
  requires_human_review
```

约束：

- 路由结果必须包含原因摘要。
- 一个事件可以路由到多个行业包。
- 低置信度路由可以进入人工确认或仅通知。
- Router Agent 不直接给交易建议。

## Industry Plugin

行业包是插件。它可以依赖数据源插件、Agent、评分规则、市场映射和候选 broker。

### 输入

- Event。
- RoutingDecision。
- 行业包配置。
- 可用数据源和市场数据 adapter。

### 输出

所有行业包必须输出统一结构。

```text
IndustryAnalysis
  event_id
  industry_plugin_id
  industry_plugin_version
  impact_summary
  first_order_impacts
  second_order_impacts
  affected_markets
  affected_instruments
  evidence
  counter_arguments
  confidence_score
  recommended_actions
  risk_flags
  requires_verification
  metadata
```

### 统一结构原因

- Decision 模块不能理解每个行业包的私有格式。
- 前端需要统一展示分析结果。
- 后续回测、审计和评估需要稳定数据结构。
- 第三方行业包必须能被系统治理。

## Scoring / Debate

Scoring 和 Debate 负责把行业包分析转成更稳定的决策输入。

### 职责

- 聚合多个行业包输出。
- 生成支持观点和反方观点。
- 标记不确定性。
- 校验证据数量和质量。
- 输出标准置信度。

### 输出

```text
ScoredAnalysis
  event_id
  analyses
  support_arguments
  counter_arguments
  evidence_quality
  confidence_score
  risk_flags
  recommended_actions
  decision_hints
```

## Decision 模块

Decision 必须独立，不允许行业包直接决定是否执行。

### 职责

- 根据置信度、风险、权限、市场、用户设置决定下一步动作。
- 将行业建议转换为系统动作。
- 阻止高风险插件绕过人工确认。
- 为未来真实交易执行预留风控入口。

### Decision 输出

```text
DecisionResult
  event_id
  action
  reason
  confidence_score
  required_approval
  allowed_brokers
  blocked_brokers
  risk_flags
  audit_summary
```

### Action 枚举

```text
notify_only
request_human_approval
dry_run_broker
reject
```

初版不支持 `execute_trade`。

## Notification 与 Human Approval

初版优先实现通知和人工确认。

### Notification

通知模块负责把决策结果推送到 UI 或外部渠道。

初版建议：

- UI 内通知为必需。
- Discord / Telegram 可作为插件预留。
- 外部通知失败不应影响事件审计记录。

### Human Approval

人工确认负责接收用户决策。

用户操作：

- approve。
- reject。
- request_reanalysis。

约束：

- 用户拒绝后，不允许同一决策继续进入 broker。
- 用户确认记录必须可审计。
- 人工确认不能绕过系统级风险限制。

## Broker 初版边界

broker 插件结构保留。初版只做虚盘，不操作实盘；未来真实下单必须通过明确配置和风控策略放行。
虚盘对应现有协议字段和事件命名中的 `dry_run`，接口、枚举和 topic 名称不随中文术语改名。

初版 broker 支持：

- disabled。
- 虚盘，不操作实盘。
- mock execution record。

默认不支持：

- 自动仓位管理。
- 自动止损止盈。

原因：

- 自动交易涉及资金、权限、合规、风控和审计，不能默认开放。
- 行业包和 Agent 可以通过 broker tool 请求执行。
- broker tool 必须检查用户配置、市场权限、confidence score、risk flags、仓位限制和是否需要 human approval。
- 先打通事件、分析、决策、通知、人工确认和虚盘；实盘执行后续再按行业包和 broker 配置逐步打开。

## 插件生命周期

插件运行时生命周期：

```text
discovered
  -> validated
  -> registered
  -> configured
  -> loaded
  -> started
  -> stopped
  -> reloaded
  -> uninstalled
```

要求：

- 每个生命周期动作必须记录日志。
- 热重载需要先 stop，再 reload，再 start。
- 热重载失败时应回退到旧版本或保持插件 stopped。
- 插件卸载不得删除历史审计数据。

## 错误处理

错误需要结构化，不允许只返回自然语言。

```text
RuntimeError
  code
  message
  stage
  event_id
  plugin_id
  retryable
  details
```

错误策略：

- Source 插件失败：记录失败并按配置重试。
- Router 失败：进入 failed 或人工处理。
- Industry Plugin 失败：不影响其他行业包继续分析。
- Scoring 失败：降级为人工确认或通知。
- Decision 失败：禁止 broker。
- Notification 失败：记录失败，不删除决策结果。

## 初版实现范围

必须实现：

- Event 模型。
- Event Envelope。
- 默认内存 fake Event Bus。
- Kafka 可选运行时适配。
- PostgreSQL 连接与 SQLAlchemy ORM 基础结构。
- Alembic 迁移基础结构。
- Router Agent 输出结构。
- IndustryAnalysis 统一结构。
- ScoredAnalysis 统一结构。
- Decision 独立模块。
- Notification 基础能力。
- Human Approval 基础状态。
- Broker 虚盘接口，不操作实盘。

暂缓实现：

- 真实交易执行。
- RawEvent / Event 持久化、outbox、replay、DLQ 数据库记录。
- 多服务之间的分布式事务。
- 复杂插件依赖解析。
- 插件签名校验。

## 待确认问题

暂无。后续进入具体数据库模型设计时再拆分讨论。
