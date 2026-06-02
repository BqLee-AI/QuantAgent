## 背景

#260 已经建立 source ingestion 到 `industry.analysis.requested` 的 handoff：RSS capture 先成为事实，worker 再做可选 Readability enrichment 或 degraded continuation，最后发布结构化 analysis request。#266 要补的是下一段缺口：一个 consumer 判断文章是否值得进入更深的行业分析。

相关真源约束如下：

- `docs/prd/03-functional-modules.md` 定义主链路为 Source Plugin -> Event Bus -> Router Agent -> Industry Plugin / AgentRuntime -> Scoring / Decision / Policy Gate。
- `docs/design/02-core-architecture-and-runtime.md` 已包含 `event.routed`、`industry.analysis.requested` 和 schema 化 `RoutingDecision`。
- `docs/design/05-agent-workflow-design.md` 要求 Agent 输入输出 schema 化，并将 provider / tool execution 约束在 AgentRuntime / ToolRegistry 边界。
- `apps/worker/README.md` 将 worker 固定为 composition root，不能让 worker 承载 event protocol 或行业业务逻辑。
- `packages/agent/AGENTS.md` 禁止绕过 AgentRuntime 直接调用 provider，也禁止保存完整 chain-of-thought 或 provider raw response。
- `packages/core/src/quantagent/core/events/README.md` 要求新 topic 先有 spec/design 真源；`event.routed` 已存在，适合作为 V1 路由决策输出 topic。
- `openspec/changes/event-scoring-v1/` 要求后续 scoring 和 Web 消费结构化 priority / confidence / degradation 信号，而不是自然语言总结。

本 design 有意只定义一个窄 intake 阶段。它不是完整行业分析，只支付最多一次模型调用，用于判断 stop、route 或 review。

## 目标 / 非目标

**目标：**

- 为每个 `industry.analysis.requested` article item 定义 single-call AI intake workflow。
- 定义 `IndustryEventContextV1`，作为传给模型的紧凑 JSON-safe context。
- 定义 `EventIntakeDecisionV1`，作为覆盖 discard / route / review 的 schema-validated 模型输出。
- 保留 traceability，使 routed / discarded / review 结果能追溯到 `industry.analysis.requested`、`source.event.captured`、`binding_id` 和存在时的 RawEvent / source identity。
- 使用 `event.routed` 作为 V1 triage / routing 输出 topic。
- 模型调用必须走 AgentRuntime / provider policy，或走可被 AgentRuntime 替换的受控 provider port，并支持 fake-provider harness。
- 给 worker、agent、core、contracts、prompts 和测试提供实现文件边界，但不要求 AgentRuntime 必须先完整落地。

**非目标：**

- 不做 multi-step Agent loop、tool-call loop、RAG retrieval、二次网页抓取、模型分块总结或 live search。
- 不实现完整 `IndustryAnalysis`、scoring/debate、Decision / Policy Gate、Approval、Notification、broker 或交易计划执行。
- V1 不要求新增持久化表；审计可以先通过 event payload、现有 / 未来 audit sink 或 model invocation log 表达。若实现 PR 要新增持久化，需要单独说明 persistence 决策。
- 不定义完整 multi-industry ontology registry。V1 可以使用 enabled industry package scope snapshot，并以半导体作为主要 fixture。
- 不允许 prompt-only policy。context shape、output schema、discard reason、routing semantics 和 safety constraints 必须存在于代码 / schema 契约中。

## 决策

### 1. 使用 `event.routed` 作为 V1 AI intake 输出 topic

intake consumer SHALL 消费 `industry.analysis.requested`，并为每个成功处理的 article item 向 `event.routed` 发布一个结构化 outcome。

`event.routed` payload 表达 triage，不表达最终行业分析：

```text
event.routed payload
  schema_version: "event_intake_decision.v1"
  trace
  decision                  # discard | route | review
  discard_reason
  quality
  industry_relevance[]
  structured_news
  routing
  audit
```

理由：

- `event.routed` 已经是 `kafka-event-bus-v1` 的 stable topic；复用它可以避免提前新增 `industry.event.triaged` 等 topic。
- 该输出在语义上属于 routing / triage，发生在 `industry.analysis.completed` 之前。
- 下游行业分析 consumer 可以订阅 `event.routed`，只处理 `decision=route` 或被策略允许的 review case。

备选方案：

- 新增 `industry.event.triaged` 和 `industry.analysis.discarded`。优点是显式，缺点是在 V1 未证明链路前扩大稳定 topic 面。
- 复用 `industry.analysis.requested` 并修改 payload。缺点是 request 和 decision 混在一起，事件因果关系难审计。

### 2. worker 保持薄入口，复用逻辑放到 agent/core 边界

建议实现目录蓝图：

```text
apps/worker/src/quantagent/worker/
  main.py
  consumer/
    analysis_request_handler.py     # 消费 industry.analysis.requested 并调用 intake service

packages/agent/src/quantagent/agent/event_intake/
  __init__.py
  README.md
  context.py                        # IndustryEventContextV1 model 和 builder-facing types
  decision.py                       # EventIntakeDecisionV1 和 validation helper
  runner.py                         # single-call intake runner；provider / AgentRuntime port 边界
  policy.py                         # routing policy、budget、discard thresholds
  prompt.py                         # 从 bounded context 组装 prompt；如果不放 packages/prompts

packages/core/src/quantagent/core/event_intake/
  __init__.py
  README.md
  publisher.py                      # 发布 event.routed
  trace.py                          # worker/agent 可复用 trace/correlation helper
  industry_scope.py                 # enabled industry package scope snapshot shape

packages/contracts/schemas/
  ai-event-intake-routing-v1.schema.json   # 可选；若实现选择 JSON Schema 作为真源

packages/prompts/src/quantagent/prompts/
  event_intake_v1.md                # 可选 bounded prompt template；policy 不能只放这里
```

`apps/worker` 只负责 runtime composition：settings、event bus runtime、consumer subscription、handler wiring 和 shutdown。它不能定义 prompt text、schema 字段、provider selection、行业相关性规则或直接 provider SDK 调用。

`packages/agent` 是 context / decision / runner 的优先落点，因为这是 Agent workflow 边界。若 V1 因 package scaffolding 成本选择先放 core-owned port，实现 PR 必须说明原因，并保持接口可迁移到 `packages/agent`。

`packages/core` 负责 event / publisher 和 trace helper，因为 worker、scheduler 和 future runtime services 共享 Event Bus 契约。

### 3. `IndustryEventContextV1` 是紧凑 snapshot，不是 RawEvent 或 runtime object dump

context SHALL 是 JSON-safe，只包含一次判断需要的信息：

```text
IndustryEventContextV1
  schema_version
  trace
    message_id
    source_message_id
    analysis_request_id
    raw_event_id?
    binding_id
    source_event_id?
    request_id?
    correlation_id?
    causation_id?
  source
    plugin_id
    binding_id
    feed_name?
    source_name?
    source_tier?
    url
    published_at?
    author?
    language?
    enrichment_status              # not_needed | succeeded | failed_degraded
    degraded_reason?
  article
    title
    rss_summary?
    body_excerpt?
    body_content_available
    content_length_chars?
    excerpt_start?
    excerpt_end?
    content_completeness            # full | rss_summary_only | excerpted | unknown
  industry_candidates[]
    industry_id
    display_name
    direct_scope_terms[]
    indirect_scope_terms[]
    entity_hints[]
    exclusion_terms[]
    route_target
  routing_policy
    allowed_decisions[]             # discard | route | review
    minimum_route_confidence
    review_confidence_threshold
    spam_definitions[]
    low_information_definitions[]
    no_trade_advice
    tool_calls_allowed=false
  budget
    max_input_chars
    max_body_chars
    max_output_items
```

builder 不得包含 ORM model、SQLAlchemy session、plugin instance、secret-bearing runtime object、完整 plugin manifest、provider request/response body，或在有 bounded article snapshot 时仍塞入完整 RawEvent payload。

### 4. 预算在模型调用前确定

context builder SHALL 在模型调用前确定正文预算：

- 如果 full content 在 `max_body_chars` 内，传入 normalized body。
- 如果 full content 超预算，传入确定性的 bounded excerpt，并记录 `content_completeness=excerpted`。
- 如果 Readability 失败且只有 RSS summary，传入 title + RSS summary，并记录 `content_completeness=rss_summary_only` 和 degraded reason。
- 不允许先用模型总结 chunks，再用另一次模型路由。这违反 #266 的 single-call 约束。

V1 可以先使用字符预算而非 token 精确预算。实现仍应记录配置的字符限制和观测长度，方便后续 token-aware policy 替换而不改变 payload shape。

### 5. `EventIntakeDecisionV1` 是 intake 阶段唯一接受的模型输出

模型输出 SHALL 在发布前通过严格 schema 校验。建议字段：

```text
EventIntakeDecisionV1
  schema_version
  trace
  decision                         # discard | route | review
  discard_reason                   # spam | irrelevant | duplicate_hint | low_information | unsupported_language | malformed | not_discarded
  quality
    is_spam
    noise_flags[]
    content_completeness
    enrichment_status
    confidence
  industry_relevance[]
    industry_id
    relationship                   # direct | indirect | contextual | none
    relevance_score
    reason_summary
  structured_news
    canonical_title
    short_summary
    bullet_summary[]
    event_type
    entities[]
    companies[]
    tickers[]
    technologies[]
    products[]
    locations[]
    numbers[]
    time_horizon
    source_facts[]
    uncertainties[]
  routing
    target_industries[]
    target_topics[]
    priority                       # low | normal | high | urgent
    requires_deep_analysis
    requires_human_review
    dedupe_key_hint?
  audit
    reason_summary
    evidence_field_refs[]
    schema_validation_status
```

validator 必须检查一致性：

- `decision=discard` 要求 `discard_reason` 不能是 `not_discarded`，且 `requires_deep_analysis=false`。
- `decision=route` 要求至少一个 target industry，且至少一个 relevance entry 的 `relationship=direct|indirect|contextual`。
- `decision=review` 要求 `requires_human_review=true` 或 confidence 低于 route threshold。
- degraded input 必须保留 `quality.enrichment_status=failed_degraded` 或等价标记，不得伪装完整正文。

### 6. single-call runner 使用受控 provider 边界

runner 可以采用两个 V1 可接受形态之一：

- AgentRuntime-backed path：在 AgentRuntime 可用时使用项目 AgentRuntime / provider policy。
- Controlled fake/provider port path：定义类似 `StructuredModelInvoker` 的 protocol，接收 bounded context 和 schema name，返回 JSON output，后续可替换为 AgentRuntime。

两种形态都必须保证：

- 每个 article intake attempt 最多一次 provider invocation；
- 无 provider tool call；
- 无 plugin / tool execution；
- worker 或 industry package 不直接创建 provider SDK client；
- 记录足够审计的结构化 invocation metadata：model / preset key（如已知）、status、token usage（如可用）、safe error summary、trace id。

### 7. 失败和降级语义必须结构化

V1 result matrix：

| Failure | Result | Event behavior |
| --- | --- | --- |
| context malformed before model | 不调用模型；如 event contract 允许，发布或记录 reason=`malformed` 的 review/failure outcome | 不进入 deep analysis |
| provider unavailable / timeout | 结构化 runtime failure 或 review outcome；是否 retryable 由 provider policy 决定 | 不静默吞掉 |
| model output invalid schema | 结构化 validation failure；只允许 deterministic 的非模型修复尝试 | 不进入 deep analysis |
| unsupported language | 按 policy 产生 `decision=discard` 或 `review` | 保留 reason |
| over-budget body | 确定性 excerpt，不增加模型调用 | 仍可 route/discard/review |
| degraded RSS-only content | 传入 title + summary 和 degraded marker | 输出保留 degraded marker |

本 change 不要求新增数据库表。但每个 outcome 都必须能通过 `event.routed`、runtime failure event、现有 model invocation log 或 future audit sink 审计。实现 PR 必须说明采用哪一个。

### 8. industry scope snapshot 必须受限且显式

industry candidates 应来自 enabled industry package metadata 或受控 registry snapshot，而不是把完整 plugin README 读入模型 context。

半导体 V1 fixture 至少覆盖：

- direct：semiconductor、memory、DRAM、NAND、HBM、foundry、advanced packaging、wafer capacity、lithography、chip equipment；
- indirect：AI server demand、hyperscaler AI capex、memory bandwidth bottleneck、GPU supply chain、data center buildout、packaging capacity；
- exclusion/noise：generic consumer gadget review、unrelated stock promotion、没有半导体事实的 SEO keyword stuffing。

### 9. prompt asset 可选，schema 和 policy 必须存在

如果实现新增 prompt asset，应放在 `packages/prompts` 或 package-local prompt module，并补 README note。discard reason、target topic、no-trade-advice rule 和 output schema 不能只存在于 prompt 文本。

## 风险 / 取舍

- [Risk] `event.routed` 可能因多个 router stage 复用而变宽。  
  Mitigation：设置 `payload.schema_version="event_intake_decision.v1"` 并校验 payload；后续 router stage 可以使用不同 schema version。

- [Risk] 一次模型调用对复杂文章的准确度不如多步分析。  
  Mitigation：本阶段只决定 discard / route / review。复杂但相关的文章应进入 deeper analysis，而不是在 intake 完成完整分析。

- [Risk] deterministic excerpt 可能漏掉长文关键事实。  
  Mitigation：记录 `content_completeness=excerpted`、保留 source URL 和 trace，并允许在信息不足时输出 `review` 或带 uncertainty 的 `route`。

- [Risk] AgentRuntime 未可用时，实现者可能想在 worker 里裸调 provider SDK。  
  Mitigation：要求受控 provider port / fake harness，并保持 worker 仅为 composition root。

- [Risk] discard 过激会丢掉间接高价值半导体事件。  
  Mitigation：spec 要求 direct 和 indirect relevance 场景；fixture tests 必须覆盖 AI infra 和 memory demand 间接事件。

- [Risk] 保存 prompt 或完整 provider response 可能泄露敏感策略或 source context。  
  Mitigation：只保存 schema-safe output、短 audit reason、安全 model metadata 和可用 token usage；不保存完整 chain-of-thought。

## 迁移计划

1. 提交本 OpenSpec-only PR，关联 #266。
2. 评审通过后，先实现 schema / context / result model 和 fake-provider harness。
3. 在 worker composition root 后接入 `industry.analysis.requested` consumer 和 `event.routed` publisher。
4. 接入受控 provider / AgentRuntime path。
5. 补 fixture coverage 和 README 启动说明。
6. 回滚方式：禁用或不启动新的 intake consumer；上游 `industry.analysis.requested` 发布保持不变。

## 未决问题

- `IndustryEventContextV1` / `EventIntakeDecisionV1` 是否立即以 `packages/contracts/schemas/` JSON Schema 为真源，还是先用 Python model + contract tests 承担真源，后续再补 JSON Schema。
- discard / review outcome 是否最终需要独立事件状态表。V1 只要求 outcome 可审计，不要求新增持久化模型。
- V1 是否读取全部 enabled industry packages 作为候选，还是在更广行业包 scope metadata 稳定前只使用半导体候选。
