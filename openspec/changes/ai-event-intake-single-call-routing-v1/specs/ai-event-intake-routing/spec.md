## ADDED Requirements

### Requirement: AI intake MUST 对每个文章条目最多执行一次结构化模型调用

系统 SHALL 对来自 `industry.analysis.requested` 的每个 eligible article item 最多执行一次结构化模型调用，然后决定该 item 应被 discard、route 或进入 review。

#### Scenario: 文章 intake 执行一次模型调用
- **WHEN** AI intake consumer 收到一个 eligible `industry.analysis.requested` item
- **THEN** 它 MUST 构建 bounded `IndustryEventContextV1`
- **AND** 它 MUST 对该 item 最多调用一次 configured structured model path
- **AND** 它 MUST 将返回结果校验为 `EventIntakeDecisionV1`
- **AND** 它 MUST NOT 在本 intake 阶段执行 model tool calls、multi-turn agent loops、secondary article fetches 或 chunk-by-chunk model summarization

#### Scenario: Worker 不绕过 AgentRuntime 或 provider 治理
- **WHEN** intake consumer 需要模型决策
- **THEN** 模型调用 MUST 经过 AgentRuntime、provider policy，或经过显式受控且可被后续 AgentRuntime 替换的 provider port
- **AND** worker code MUST NOT 直接实例化 provider SDK clients
- **AND** industry packages MUST NOT 为该 intake decision 直接调用模型 provider

### Requirement: IndustryEventContextV1 MUST 紧凑、JSON-safe 且可追踪

系统 SHALL 提供紧凑的 `IndustryEventContextV1` input snapshot，用足够信息支撑一次 relevance、quality、structure 和 routing 判断，同时避免倾倒 runtime objects 或 unbounded source payloads。

#### Scenario: Context 保留 trace 与 source 状态
- **WHEN** intake context 从 `industry.analysis.requested` payload 构建
- **THEN** 它 MUST 保留可用的 message identity、source-message identity、`binding_id`、owner 或 industry identity、correlation context 和 causation context
- **AND** 它 MUST 保留 source URL、title、可用 published time、source plugin identity 和 enrichment status
- **AND** degraded RSS-summary inputs MUST 被显式标记为 degraded 或 incomplete

#### Scenario: Context 排除不安全 runtime objects
- **WHEN** `IndustryEventContextV1` 被序列化为 model input
- **THEN** 它 MUST 是 JSON-safe
- **AND** 它 MUST NOT 包含 ORM objects、SQLAlchemy sessions、plugin instances、Event Bus publisher/consumer objects、provider clients、secret-bearing runtime objects、完整 provider request/response bodies 或完整 chain-of-thought
- **AND** 在 bounded article 和 industry-scope snapshot 已足够时，它 MUST NOT 包含完整 RawEvent 或完整 plugin manifest

### Requirement: Context 预算 MUST 在模型调用前确定

系统 SHALL 在模型调用前确定 article content limits，并且 SHALL NOT 为 V1 intake decision 使用额外模型调用压缩输入。

#### Scenario: 完整正文符合配置预算
- **WHEN** normalized article content 符合 configured V1 input budget
- **THEN** context MAY 包含完整 normalized article content
- **AND** 它 MUST 记录 content completeness 为 full 或等价状态

#### Scenario: 文章正文超过配置预算
- **WHEN** normalized article content 超过 configured V1 input budget
- **THEN** context MUST 包含 deterministic bounded excerpt 或等价 bounded representation
- **AND** 它 MUST 记录 content length、excerpt 或 completeness metadata
- **AND** intake MUST NOT 先调用一次模型总结 chunks，再调用另一次模型 route 该 item

#### Scenario: 只有 RSS summary 可用
- **WHEN** Readability enrichment 失败，但 RSS title、URL 或 summary 仍可分析
- **THEN** context MUST 使用 RSS-derived title、URL 和 summary form
- **AND** 它 MUST 将输入标记为 degraded 或 RSS-summary-only
- **AND** downstream decisions MUST NOT 将该输入表达为已获得完整 article text

### Requirement: EventIntakeDecisionV1 MUST 用结构化新闻字段表达 discard、route 和 review

系统 SHALL 将每个 AI intake output 校验为 `EventIntakeDecisionV1`，该结构必须同时表达 quality filtering、industry relevance、structured news extraction、routing decision、confidence 和 audit summary。

#### Scenario: Discard 输出结构化且终止深度分析
- **WHEN** 模型判断某个 item 应被 discard
- **THEN** `EventIntakeDecisionV1.decision` MUST 为 `discard`
- **AND** 它 MUST 包含具体 discard reason，例如 spam、irrelevant、duplicate hint、low-information content、unsupported language 或 malformed input
- **AND** 它 MUST 保留 trace context 和短 audit reason
- **AND** 它 MUST 表示 deeper industry analysis 不需要继续执行

#### Scenario: Route 输出识别目标行业
- **WHEN** 模型判断某个 item 应被 route
- **THEN** `EventIntakeDecisionV1.decision` MUST 为 `route`
- **AND** 它 MUST 包含至少一个 target industry
- **AND** 它 MUST 包含能区分 direct、indirect、contextual 或 none relationship 的 industry relevance entries
- **AND** 它 MUST 在可用时包含 structured news fields，例如 canonical title、summary、entities、companies、technologies、products、metrics、source facts、uncertainties 和 priority

#### Scenario: Review 输出保留不确定性
- **WHEN** 模型无法高置信 discard 或 route 某个 item
- **THEN** `EventIntakeDecisionV1.decision` MUST 为 `review`
- **AND** 它 MUST 保留 uncertainty 或 low-confidence reason
- **AND** 它 MUST 表示是否需要 human review 或 lower-priority downstream analysis

### Requirement: AI intake MUST 识别直接和间接行业相关性

系统 SHALL 判断 item 与 enabled industry package scopes 是 direct、indirect、contextual 还是 unrelated。

#### Scenario: 半导体直接相关内容进入 route
- **WHEN** article 涉及 semiconductor、memory、DRAM、NAND、HBM、foundry、advanced packaging、wafer capacity、lithography 或 chip equipment facts
- **THEN** intake decision MUST 能够将 semiconductor relevance 标记为 direct
- **AND** 当 quality 和 confidence thresholds 满足时，它 MUST 能够将 item route 到 semiconductor industry target

#### Scenario: 半导体间接相关内容不会被当作无关内容丢弃
- **WHEN** article 涉及 AI server demand、hyperscaler AI capital expenditure、memory bandwidth bottlenecks、GPU supply chain constraints、data-center buildout 或 packaging capacity，并对 semiconductor demand 或 supply 有实质影响
- **THEN** intake decision MUST 能够将 semiconductor relevance 标记为 indirect 或 contextual
- **AND** 它 MUST NOT 仅因文章没有 literal word semiconductor 就 discard 该 item

#### Scenario: 无关或噪音内容被 discard
- **WHEN** article 与 enabled industry scopes 无关、属于 spam、SEO noise、无 industry facts 的 generic gadget review 或 low-information content
- **THEN** intake decision MUST 能够 discard 该 item
- **AND** 它 MUST 包含 structured discard reason 和 audit summary

### Requirement: AI intake outcomes MUST 可审计且安全

系统 SHALL 为 discard、route 和 review outcomes 保留 audit-ready reasons 与 trace context，同时不保存敏感或不安全模型 artifacts。

#### Scenario: Outcome 保留 audit-safe explanation
- **WHEN** intake outcome 被产出
- **THEN** 它 MUST 包含 concise reason summary 和 input-field references 或等价 evidence pointers
- **AND** 它 MUST 保留 source trace context，以支持 replay 或 investigation
- **AND** 它 MUST NOT 包含完整 chain-of-thought、包含 private context 的完整 prompt text、provider raw responses、secrets、plugin instances 或 ORM objects

#### Scenario: Schema validation failure 被显式处理
- **WHEN** model output 未通过 `EventIntakeDecisionV1` validation
- **THEN** 系统 MUST 产出 structured validation failure 或 review/failure outcome
- **AND** 它 MUST NOT 像 validation 成功一样静默 route 该 item 到 deep analysis
- **AND** 它 MUST 保留适用于 logs 或 audit 的 safe error summary

### Requirement: AI intake acceptance MUST 使用 fixture-based harness 和 fake provider

系统 SHALL 使用 controlled fixtures 和 fake structured provider 验证 V1 intake 行为，不要求 live model providers、live RSS feeds 或 live article websites。

#### Scenario: Harness 证明 single-call 行为
- **WHEN** fixture-based intake tests 使用 fake provider 运行
- **THEN** 每个 article item MUST 触发不超过一次 provider invocation
- **AND** tests MUST 证明没有 tool-call loop 或 secondary fetch path

#### Scenario: Harness 覆盖相关性和降级场景
- **WHEN** V1 intake verification 执行
- **THEN** fixtures MUST 覆盖 direct semiconductor relevance、indirect AI-infrastructure relevance、unrelated content、spam 或 SEO noise、degraded RSS-summary-only input、over-budget article content 和 schema-invalid model output
- **AND** verification MUST 断言 discard、route、review、degraded marker、trace preservation 和 structured validation behavior
