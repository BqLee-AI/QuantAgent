## ADDED Requirements

### Requirement: Router Agent output MUST evolve to `event_intake_decision.v2` with v1 compatibility

系统 SHALL 支持 `event_intake_decision.v2` 作为 Router Agent 新输出契约，同时 MUST 能兼容读取历史 `event_intake_decision.v1` routed records。

#### Scenario: v2 output is validated before publish
- **WHEN** Router Agent single-call intake 产出模型结果
- **THEN** 系统 MUST 将结果校验为 `event_intake_decision.v2` 或显式兼容的历史 v1 结构
- **AND** 校验成功后才能发布 `event.routed` 并持久化 routed read model
- **AND** schema validation failure MUST 形成结构化 failure/review/discard outcome，不得静默 route 到后续行业分析

#### Scenario: v1 records remain readable
- **WHEN** `/events` 或 `/runtime` 读取历史 `event_intake_decision.v1` routed record
- **THEN** read model mapper MUST 尽可能映射出 decision、summary、quality、relevance、routing、trace 和 key fields
- **AND** v1 缺失的 v2 字段 MUST 标记为 `not_provided`、`unavailable` 或等价安全缺省
- **AND** 系统 MUST NOT 要求重跑历史 v1 事件才能打开事件详情

### Requirement: Router Agent semantic text fields MUST default to Chinese

系统 SHALL 通过 prompt、schema 说明和测试约束 Router Agent 的用户可读语义文本默认使用中文输出。

#### Scenario: User-readable semantic fields are Chinese
- **WHEN** Router Agent 产出 `event_intake_decision.v2`
- **THEN** 用户可读的 `structured_news.canonical_title`、`structured_news.short_summary`、`structured_news.bullet_summary`、tag label、event type label、quality reason、relevance reason、routing reason、next step hint、audit reason、review reason 和 discard reason 描述 MUST 默认使用中文
- **AND** 这些中文文本 MUST 位于对应语义字段中
- **AND** 系统 MUST NOT 通过单独的 `display` 文本对象来承载中文内容真源

#### Scenario: Machine fields remain stable codes
- **WHEN** Router Agent 产出 decision、discard_reason、relationship、schema_version、industry_id、priority、ticker、URL、numeric metrics 或 source refs
- **THEN** 这些机器稳定字段 MUST 保持约定的英文 enum、code 或原始事实标识
- **AND** 它们 MUST 可用于筛选、回测、聚合和下游分析
- **AND** 中文 label 或 reason MUST NOT 替代机器 code

### Requirement: Router Agent output MUST use semantic blocks instead of a display text layer

系统 SHALL 将 Router Agent 输出按 `quality`、`relevance`、`structured_news`、`routing` 和 `audit` 等语义块组织，而不是新增只用于展示的 `display` 字段集合。

#### Scenario: Semantic blocks provide list and detail data
- **WHEN** `/api/v1/events` 构造列表或详情摘要
- **THEN** 它 MUST 从 `structured_news`、`quality`、`relevance`、`routing` 和 `audit` 等语义块选择字段
- **AND** `title`、`summary`、tags、reason、next step 和 key fields MUST 保留业务语义
- **AND** read model mapper MAY 决定展示优先级，但 MUST NOT 将中文内容集中到 `display.*` 作为内容真源

#### Scenario: UI hints do not become content source
- **WHEN** 实现者需要表达排序、高亮或字段优先级建议
- **THEN** 可以使用 `presentation_hints`、`ui_hints` 或等价轻量 hint
- **AND** hint MUST NOT 存放标题、摘要、理由、标签正文或下一步建议等中文内容真源
- **AND** 前端 MUST 仍从语义字段读取业务内容

### Requirement: Router Agent single-call constraint MUST remain intact

系统 SHALL 保持 Router Agent intake 对每篇文章最多一次结构化模型调用，不因 v2 schema 或中文输出新增 token-heavy 流程。

#### Scenario: v2 routing remains single call
- **WHEN** worker 处理一个 eligible article item
- **THEN** 它 MUST 构建 bounded JSON-safe context
- **AND** 它 MUST 对该 item 最多执行一次 configured structured model call
- **AND** 它 MUST NOT 为翻译、UI 展示、summary、schema 修复或 route 判断额外执行 tool-call loop、multi-turn agent loop、secondary article fetch、live search 或 chunk-by-chunk model summarization

#### Scenario: Context remains bounded and traceable
- **WHEN** Router Agent v2 模型调用构造 context
- **THEN** context MUST 保留 message identity、source identity、`binding_id`、`raw_event_id`、owner/correlation/causation context、source URL/title、enrichment status 和 bounded article content
- **AND** context MUST 是 JSON-safe
- **AND** context MUST NOT 包含 ORM objects、SQLAlchemy sessions、plugin instances、Event Bus runtime objects、provider clients、secret-bearing runtime objects、provider raw request/response、完整 CoT 或 unbounded RawEvent payload

### Requirement: Router Agent routed persistence MUST store safe v2 key fields and output JSON

系统 SHALL 将 Router Agent v2 outcome 安全持久化到 routed read model，使 `/events` 和 `/runtime` 可以审计真实 AI 输出。

#### Scenario: Routed event persistence stores semantic key fields
- **WHEN** worker 发布 `event.routed`
- **THEN** 它 MUST 幂等写入 `event_intake_routed_events` 或等价 routed read model
- **AND** persisted record MUST 包含 `schema_version`、`raw_event_id`、`event_id`、`analysis_request_id`、`binding_id`、owner identity、request/correlation context、decision、discard_reason、status、summary、key_fields、output_json 和 created timestamp
- **AND** `key_fields` MUST 覆盖 v2 的核心语义摘要，例如中文 title/summary、event type、tags、priority、target industries/topics、relationship、confidence、review/deep-analysis flags 和 schema validation status

#### Scenario: Persisted output excludes unsafe artifacts
- **WHEN** Router Agent output 被持久化或通过 API 返回
- **THEN** `output_json` MUST 是 JSON-safe structured output
- **AND** 它 MUST NOT 包含 provider raw response、完整 prompt、chain-of-thought、secret values、ORM objects、plugin instances、数据库 session、完整正文或 raw payload
- **AND** 超大或不安全字段 MUST 被拒绝、截断或脱敏，并保留安全错误摘要

### Requirement: Router Agent acceptance MUST cover Chinese semantic output and routing decisions

系统 SHALL 用 fixture-based harness 和 fake provider 验证 Router Agent v2 输出契约，不要求 live RSS、live website 或 live model provider。

#### Scenario: Tests cover decision types and language contract
- **WHEN** Router Agent v2 verification 执行
- **THEN** tests MUST 覆盖 `decision=route`、`decision=review`、`decision=discard`、direct/indirect/contextual relevance、spam/irrelevant/low-information discard、degraded RSS-summary-only input、over-budget article content 和 schema-invalid output
- **AND** tests MUST 断言用户可读语义字段默认中文输出
- **AND** tests MUST 断言机器 enum/code 字段保持英文约定

#### Scenario: Tests prove no additional model calls
- **WHEN** fixture-based intake tests 使用 fake provider
- **THEN** 每篇 article item MUST 触发不超过一次 provider invocation
- **AND** tests MUST 证明中文输出、summary 和 routing decision 没有引入第二次模型调用、tool-call loop 或 secondary fetch path
