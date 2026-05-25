## ADDED Requirements

### Requirement: 官方插件 V1 主链路必须显式分层

QuantAgent SHALL define the official plugin V1 main chain as a staged flow from source discovery to dry-run execution, with plugin package responsibilities separated from core platform responsibilities.

#### Scenario: 主链路节点被明确
- **WHEN** official plugin V1 work is planned
- **THEN** the planned chain includes RSS source discovery, evidence tools, analysis, strategy draft, Discord notification, core approval, and Binance dry-run execution
- **AND** each node has a separate responsibility and acceptance boundary

#### Scenario: 插件包不承担核心底座职责
- **WHEN** a plugin package is implemented
- **THEN** the package owns its manifest, config schema, input/output schema, capability implementation, README, and plugin-level tests
- **AND** the package does not own core persistence, Event Bus, Scheduler, ToolRegistry, Approval, Policy Gate, audit, or secret storage

### Requirement: RSS Source Plugin V1 只负责订阅源条目输出

RSS Source Plugin V1 SHALL read RSS/Atom feeds and produce structured source item output without implementing core source runtime infrastructure.

#### Scenario: RSS 插件输出结构化条目
- **WHEN** RSS Source Plugin V1 reads a feed
- **THEN** it returns structured items containing fields such as title, url, summary, published_at, author, external_id, and raw payload
- **AND** the output can be validated as JSON DTO

#### Scenario: RSS 插件不写核心入库链路
- **WHEN** RSS Source Plugin V1 is implemented
- **THEN** it does not implement RawEvent repository, SourceBinding, Scheduler loop, Event Bus publishing, or database migrations
- **AND** those responsibilities remain in core runtime changes

### Requirement: Evidence tools 通过受控工具边界暴露

Evidence source/data tool plugins SHALL expose search or read capabilities as tools that are later invoked through Plugin Runtime or ToolRegistry, not by direct plugin-to-plugin imports.

#### Scenario: Readability 作为链接正文读取工具
- **WHEN** a URL needs article text extraction
- **THEN** Readability Link Reader can expose a read_url style capability
- **AND** the capability returns structured evidence content rather than arbitrary natural language only

#### Scenario: Tavily 第一版只做 search 和 extract
- **WHEN** Tavily Source/Data Tool Plugin V1 is planned
- **THEN** its first version exposes search and extract capabilities
- **AND** crawl, map, research, or plugin orchestration capabilities are deferred unless a later OpenSpec change approves them

#### Scenario: Tavily 不直接编排其他插件
- **WHEN** another plugin or Agent needs Tavily results
- **THEN** the call goes through Plugin Runtime or ToolRegistry using a tool id and schema-validated input
- **AND** Tavily does not directly import or call RSS, Readability, Discord, Binance, or other plugin implementations

### Requirement: Analysis Plugin V1 输出结构化分析

Analysis Plugin V1 SHALL transform event and evidence inputs into a structured analysis result, without producing executable trading actions.

#### Scenario: Analysis 输出可消费 DTO
- **WHEN** Analysis Plugin V1 receives source items and evidence
- **THEN** it returns an AnalysisResult containing summary, key facts, market impact, direction or sentiment, confidence, uncertainty, and evidence references
- **AND** the result can be validated as JSON DTO

#### Scenario: Analysis 不生成订单
- **WHEN** Analysis Plugin V1 returns a result
- **THEN** the result does not contain approved order requests, exchange execution parameters, or executor status
- **AND** trading action proposal is left to Strategy Draft Plugin

### Requirement: Strategy Draft Plugin V1 输出可审批策略草案

Strategy Draft Plugin V1 SHALL transform structured analysis into a strategy draft that can be reviewed and approved, without executing trades.

#### Scenario: StrategyDraft 可被通知和审批消费
- **WHEN** Strategy Draft Plugin V1 receives an AnalysisResult
- **THEN** it returns a StrategyDraft containing action proposal, symbol when applicable, direction, time horizon, rationale, risk notes, confidence, and requires_approval
- **AND** the draft is suitable for Discord notification and Approval UI display

#### Scenario: StrategyDraft 不是执行请求
- **WHEN** Strategy Draft Plugin V1 returns a draft
- **THEN** the draft is not treated as an approved executor request
- **AND** executor invocation still requires Approval and Decision / Policy Gate boundaries

### Requirement: Discord 插件只承担通知职责

Discord Notification Plugin SHALL send or receive low-risk notification messages without owning strategy generation, approval state, or execution.

#### Scenario: Discord 推送审批上下文
- **WHEN** a strategy draft needs user attention
- **THEN** Discord Notification Plugin may send analysis summary, strategy draft summary, severity, and approval link
- **AND** it returns structured delivery status such as message id, status, and error

#### Scenario: Discord 不绕过审批
- **WHEN** Discord Notification Plugin handles a notification
- **THEN** it does not approve, reject, amend, or execute the strategy
- **AND** approval decisions remain in core Approval / Decision boundaries

### Requirement: Approval 是核心高风险闸门

Approval for strategy drafts and executor requests SHALL be owned by core Approval / Decision / Policy Gate boundaries rather than by ordinary plugins.

#### Scenario: 插件只能请求审批
- **WHEN** a plugin produces a strategy draft or execution candidate
- **THEN** core creates or manages the ApprovalRequest and ApprovalDecision
- **AND** the plugin cannot mark its own request as approved

#### Scenario: 审批页面消费 DTO
- **WHEN** Approval UI displays a request
- **THEN** it consumes core API DTOs for strategy, evidence, risk, and execution preview
- **AND** it does not load plugin-defined custom frontend components

### Requirement: Binance Executor V1 只能 dry-run

Binance Executor Plugin V1 SHALL provide dry-run or mock execution only and SHALL NOT perform live trading.

#### Scenario: Dry-run 校验交易形状
- **WHEN** Binance Dry-run Executor receives an approved or test-mode execution request
- **THEN** it validates fields such as symbol, side, order type, quantity or notional, and time in force
- **AND** it returns an ExecutorDryRunResult with estimated order, validation errors, status, and audit hints

#### Scenario: 禁止真实交易路径
- **WHEN** Binance Executor V1 is implemented
- **THEN** it does not store real exchange secrets, call live order placement APIs, or expose a live trading switch
- **AND** real execution requires a later OpenSpec change covering Policy Gate, audit, secrets, wallet facts, and risk controls

### Requirement: 官方插件 V1 必须 OpenSpec-first 推进

Official plugin V1 work SHALL be coordinated through OpenSpec artifacts before implementation PRs change runtime behavior or plugin package code.

#### Scenario: OpenSpec-only PR 先行
- **WHEN** official plugin V1 main chain is proposed
- **THEN** an OpenSpec-only PR is created with proposal, design, tasks, specs, and metadata
- **AND** the PR does not include implementation code, runtime changes, API changes, Web changes, secrets, or real trading integration

#### Scenario: 实现 issue 依赖 OpenSpec
- **WHEN** concrete plugin implementation issues are created before the OpenSpec is approved
- **THEN** they are marked as needs-review or blocked
- **AND** they reference the official plugin V1 main chain OpenSpec as their design dependency
