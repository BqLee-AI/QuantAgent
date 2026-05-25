## 背景

QuantAgent 的插件系统不是单纯的“把 Python 文件放进目录”。它需要让第三方或官方插件作者只关心插件能力，同时让核心系统统一治理配置、生命周期、调度、调用、审计和高风险动作。

Registry V1 解决了“发现和展示插件”的第一步；本 change 解决“第一批官方插件该如何围绕主链路分工”的问题。

## 目标与非目标

**目标：**

- 定义第一版官方插件主链路和每个节点的职责。
- 明确哪些是插件包能力，哪些必须留在核心底座。
- 定义每个插件节点的输入输出 DTO 方向，后续由 #142 或相关 change 细化。
- 为 RSS、Tavily、Analysis、Strategy Draft、Discord、Approval、Binance Dry-run 的后续 issue 提供边界。
- 明确 OpenSpec-first 推进：先评审设计/契约，再开实现 PR。

**非目标：**

- 不实现插件代码。
- 不改 API、Web、core runtime 或数据库。
- 不定义完整 ToolRegistry、Scheduler、AgentRuntime、Policy Gate 实现。
- 不支持 Binance live trading。
- 不接入真实 secrets、broker key 或生产交易账户。
- 不实现插件市场、安装、依赖自动安装或插件自定义前端。

## 主链路

```text
RSS Source Plugin
  -> SourceItem / RawEventCandidate DTO
  -> Evidence tools: Readability / Tavily
  -> Evidence DTO
  -> Analysis Plugin
  -> AnalysisResult DTO
  -> Strategy Draft Plugin
  -> StrategyDraft DTO
  -> Discord Notification Plugin
  -> Approval Core + Approval Page
  -> Binance Dry-run Executor Plugin
  -> ExecutorDryRunResult DTO
```

这条链路分两类职责：

```text
插件包负责：
  - manifest
  - config.schema.json
  - input/output schema
  - 插件能力实现
  - 插件级测试和 README

核心底座负责：
  - 插件发现与 Registry
  - 配置保存和 secret 注入
  - 生命周期管理
  - Scheduler
  - Plugin Runtime / ToolRegistry 调用
  - Event Bus / Persistence / Audit
  - Approval / Decision / Policy Gate
```

## 决策

### 1. RSS 重新按插件包边界推进

RSS 插件 V1 SHOULD 只负责读取 RSS/Atom feed、解析条目并输出结构化 DTO。它不负责 RawEvent repository、SourceBinding、Scheduler、Event Bus 或数据库。

旧的 “RSS pull source 到 RawEvent 入库” 范围容易把插件作者带入核心持久化和调度实现，因此后续应新开 RSS 插件包 issue，并把旧方向作为关闭或重整对象。

### 2. Tavily 是 evidence source/data tool，不是编排器

Tavily 插件 V1 SHOULD 暴露 `search` 和 `extract` 两类工具能力，输出 evidence/search/extract DTO。其他插件或 Agent 后续只能通过 Plugin Runtime / ToolRegistry 调用这些工具。

Tavily 插件 SHALL NOT 直接调用 RSS、Readability、Discord、Binance 或其他插件。插件互调和工具编排属于核心 runtime / ToolRegistry / AgentRuntime 的职责。

### 3. Analysis 与 Strategy Draft 必须分层

Analysis Plugin SHOULD 把 event 和 evidence 转成结构化分析结果，例如 summary、key facts、market impact、confidence、uncertainty 和 evidence refs。

Strategy Draft Plugin SHOULD 消费 AnalysisResult，输出可审批的策略草案，例如 action proposal、symbol、direction、time horizon、rationale、risk notes 和 requires approval。

Analysis 不输出可执行订单；Strategy Draft 不调用 executor。

### 4. Discord 是 notification plugin，不是策略或审批核心

Discord 插件 SHOULD 只负责发送通知或接收必要的低风险消息输入。它可以消费 StrategyDraft、Approval link 或 Analysis 摘要，但不能生成策略、创建审批状态、执行交易或绕过核心审计。

### 5. Approval 是核心高风险闸门，不是普通插件

审批页面和 Approval Request/Decision 属于核心 Decision / Policy Gate / Web 工作台边界。插件可以请求创建审批，但不能自己成为审批真源，也不能绕过审批触发 executor。

### 6. Binance 第一版只做 dry-run executor

Binance Executor Plugin V1 SHALL 只做 dry-run/mock。它接受已审批或测试态执行请求，校验 Binance 形状的字段，返回 ExecutorDryRunResult。它不得保存真实密钥、不得调用真实下单接口、不得提供 live trading 开关。

真实执行需要在 Approval、Policy Gate、Audit、Wallet facts、Secrets 和风险约束稳定之后另开 change。

### 7. OpenSpec issue 和 PR 先行

本阶段 SHOULD 先开 OpenSpec-only issue 和 OpenSpec-only PR。实现 issue 可以在 OpenSpec 被认可后逐步拆分；如果提前创建，也应标记 `status:needs-review` 或 `status:blocked`，并写明 blocked by `official-plugin-v1-main-chain`。

## 数据交接草图

```text
SourceItem
  id?
  source_plugin_id
  title
  url
  summary
  published_at
  author
  external_id
  raw_payload

Evidence
  source_tool_id
  url?
  query?
  title
  content
  snippet
  score?
  retrieved_at

AnalysisResult
  summary
  key_facts[]
  market_impact
  direction
  confidence
  uncertainty
  evidence_refs[]

StrategyDraft
  action
  symbol?
  direction?
  time_horizon
  rationale
  risk_notes[]
  confidence
  requires_approval

ExecutorDryRunResult
  status
  estimated_order
  validation_errors[]
  audit_hints
```

这些字段是设计方向，不在本 change 中替代 #142 的最终 DTO 细化。

## 风险与取舍

- [风险] 先做 OpenSpec 会让实现速度看起来变慢。
  -> 缓解：当前最大风险不是写不出插件，而是职责边界漂移；先收契约可以减少后续返工。

- [风险] 官方插件 issue 太多，统筹困难。
  -> 缓解：保留一个 OpenSpec-only 跟进 issue，只跟踪主链路和依赖，不承载实现细节。

- [风险] Tavily 被误解成“插件调用其他插件”的入口。
  -> 缓解：spec 明确 Tavily 只是 evidence tool provider，插件互调属于 runtime / ToolRegistry。

- [风险] Binance dry-run 后续被偷扩成 live trading。
  -> 缓解：spec 明确第一版禁止真实下单、真实密钥和 live trading 开关。
