## Context

仓库当前已经有几块直接相关的真源：

- `docs/design/06-source-plugin-design.md` 已明确 Source Plugin 只负责抓取、标准化，pull source 必须由 scheduler 调度，source output 先进入平台事实层，再进入后续事件链路。
- `docs/design/07-industry-package-design.md` 已明确行业包通过 `source_bindings` 声明 required / optional source dependencies，且行业包不能直接绕过 AgentRuntime、Event Bus 或 Decision。
- `docs/prd/02-industry-scenarios.md` 已明确半导体 / 内存行业包是正式目标场景，首批 source 需要覆盖 AI 论文、厂商公告和行业新闻。
- `worker-route-captured-source-event-by-binding-owner-v1` 已把 worker 路由的一级真源固定为 `binding_id`，并要求 V1 通过受控 seam 调用行业入口。
- `source-binding-effective-config-contract-v1`、`source-binding-scheduler-run-persistence-v1`、`scheduling-event-bus-bridge-v1`、`raw-event-persistence-dedupe-binding-v1` 已分别收口模板契约、binding/run 真源、capture publish 契约和 RawEvent 事实层边界。

当前缺口不在单个基础件，而在“这些基础件如何拼成第一条可运行的半导体主链路”。本 change 只解决这条链路的行为和边界，不实现代码；但它必须给后续实现留出目录蓝图、topic 语义、数据流、失败路径和验证入口，否则实现阶段仍会重新发明关键判断。

## Goals / Non-Goals

**Goals:**

- 定义半导体 / 内存行业包在 V1 的最小 source dependency：RSS required、Readability optional。
- 定义首批 RSS 模板资产的分层：baseline required feeds 与 optional expansion feeds。
- 定义 `source.event.captured` 之后的 enrichment 编排位置，并把 Readability 保持为受控平台 seam，而不是 RSS 插件内嵌逻辑。
- 定义分析入口选择：worker 在完成 owner 路由与 enrichment 编排后发布 `industry.analysis.requested`。
- 定义 degradation 语义：Readability 失败时，如何继续消费 RSS 摘要并明确标记降级状态。
- 定义 RSS capture 真源与 enrichment 后分析输入之间的先后关系和 traceability 约束。
- 指定后续实现需要落在哪些目录边界、哪些模块承担什么职责，以及最小 harness 如何证明主链路成立。

**Non-Goals:**

- 不实现完整 Router Agent、IndustryAnalysis 结构、AgentRuntime 执行、Decision / Policy Gate、Approval 或 broker 行为。
- 不在本 change 内同时设计多行业共用 enrichment pipeline 的完全通用框架；先收住半导体主链路的最小 seam。
- 不定义复杂 source ranking、analysis prioritization、source credibility scoring、Jina fallback 或 Playwright crawler。
- 不把正文增强结果的双层持久化模型一次做满；V1 只要求保留 RSS capture 事实层并让 analysis 输入可带 enrichment 结果。
- 不把 worker 变成行业分析总控层，也不把行业包变成运行时编排器。

## Decisions

### 1. 半导体行业包通过 `source_bindings` 声明 RSS required + Readability optional

后续正式实现应围绕如下资产收敛：

```text
plugins/industries/semiconductor-industry/
  plugin.yaml
  config.schema.json
  README.md
  templates/
    source_bindings/
      rss.baseline.yaml
      rss.expansion.yaml
      readability.default.yaml
```

职责：

- `plugin.yaml` 只声明 source 依赖元信息，不承载运行态字段或 secret 明文。
- `rss.baseline.yaml` 承接默认 required / default-enabled 的高稳定公开源。
- `rss.expansion.yaml` 承接 optional 的更广行业新闻 / 评论源模板。
- `readability.default.yaml` 只表达可选正文增强相关覆盖，不表达 owner、run、binding 状态。

原因：

- 这与 `docs/design/07-industry-package-design.md` 已有的 `source_bindings` 边界一致。
- `required` / `optional` 的区别需要先在模板层显式收住，否则后续 UI/API/worker 都会重新发明启用语义。
- V1 不能把所有源都默认启用，否则 Readability 失败率、噪音和 fixture 复杂度都会放大。

### 2. 首批 RSS 覆盖范围采用“baseline required + expansion optional”

推荐模板分层：

```text
baseline required/default-enabled:
  - 官方厂商新闻源（例如 Samsung、SK hynix、Micron、TSMC 等高稳定 newsroom/feed）
  - AI 论文公开源（例如与 AI / memory demand 相关的稳定公共 feed）
  - 少量高稳定行业新闻源

expansion optional:
  - 更广的行业评论 / 聚合新闻 / 分析师观点源
```

约束：

- baseline feeds 需要适合默认启用、fixture 化和本地受控验证。
- expansion feeds 可以保留模板，但 V1 不要求默认启用。
- 本 change 不锁死具体 URL 列表，只锁“分层原则和 required/optional 语义”；具体 feed 名单应在后续实现或 supporting design note 中补齐。

原因：

- 相比“全部默认启用”，这种分层更能控制噪音和失败率。
- 相比“只做基础源”，它又保留了行业包继续扩展信息面的入口，不需要后续推翻模板层设计。

### 3. `source.event.captured` 先发布 RSS capture，再由 worker 在后置阶段决定是否做 Readability enrichment

V1 调用链：

```text
SourceBinding (semiconductor owner)
  -> scheduler trigger RSS source.fetch
  -> publish source.event.captured
  -> worker consumes captured event
  -> decide if enrichment needed
  -> invoke controlled Readability seam when needed
  -> publish industry.analysis.requested
```

约束：

- scheduler 不同步抓正文，不让 Readability 成为 capture publish 前置条件。
- RSS source 插件不直接 import / invoke Readability。
- worker 不直接 import `plugins/sources/readability-source`；它只能依赖 core-owned enrichment seam / port。

后续实现建议目录：

```text
packages/core/src/quantagent/core/worker_routing/
  enrichment_models.py        # 可选，若现有 models.py 不够表达 enriched/degraded 状态
  enrichment_service.py       # Readability 调用编排与降级语义
  analysis_request_publisher.py
```

如果实现者认为文件数过多，也至少要保证 enrichment 编排和 owner routing 不混在同一个 handler 文件。

原因：

- 这比 scheduler 内联 enrichment 更符合当前 scheduler/worker 边界。
- 这也比把正文增强推迟到行业入口后再做更容易在 V1 落地。
- worker 已经掌握 `binding_id -> owner` 路由上下文，是最自然的后置 enrichment 决策点。

### 4. Readability 失败采用“显式降级继续消费 RSS 摘要”，不阻断主链路

对需要正文增强的条目，enrichment 结果模型至少要区分：

```text
enrichment_status:
  - not_needed
  - succeeded
  - failed_degraded
```

当正文增强失败时：

- 仍允许后续分析消费 RSS 的 title / url / summary / metadata。
- 必须显式附带 `content_enrichment_failed` 或等价结构化标记。
- 下游 analysis request 不能把 degraded 输入伪装成“已拿到完整正文”。

原因：

- 如果一失败就丢弃，会让高价值短讯和公告类条目丢失过多。
- V1 重点是跑通主链路，不是用最激进的输入质量策略阻塞链路。

### 5. 分析入口在 V1 采用 `industry.analysis.requested` topic，而不是 direct gateway handoff

本 change 明确采用 `topic` 方案：

```text
worker
  -> publish industry.analysis.requested
  -> downstream analysis consumer / AgentRuntime handles later
```

这意味着后续实现必须同步更新：

```text
packages/core/src/quantagent/core/events/topics.py
packages/core/src/quantagent/core/events/README.md
packages/core/tests/test_event_bus_contract.py
packages/core/tests/test_event_bus_memory.py  # 如涉及允许 topic 集合断言
```

约束：

- `industry.analysis.requested` 的 payload 必须是 JSON-safe、可审计、带 owner identity 与 trace context。
- worker 不得继续直接调用具体半导体分析实现作为最终 handoff。
- 如果仍保留 `IndustryGateway` 作为过渡 seam，它也只能承担 topic publish adapter 或受控 publisher 的角色，而不是 direct business execution。

原因：

- 这与设计文档中已有 topic 语义一致。
- 它比 direct service handoff 更利于后续审计、回放和 AgentRuntime consumer 接线。
- 既然用户已经明确锁定“问题 2 采用 topic 方案”，本 change 必须把 topic 变更上升为 stable contract 变更，而不是留在实现细节里。

### 6. RSS capture 事实层先于 enrichment-dependent analysis input 存在

本 change 固定顺序：

```text
RSS source output
  -> source capture fact exists
  -> optional enrichment
  -> downstream analysis request may contain enriched content
```

语义：

- enrichment 不能成为 RSS capture 事实层存在的前提。
- 下游 analysis input 可以在事实层基础上附带 enriched article content。
- V1 不要求一次把 enriched state 的双层持久化模型做满，但要求 traceability：analysis request 必须能追溯回原始 captured event / request identity。

原因：

- 这与 `docs/design/06-source-plugin-design.md` 和 `raw-event-persistence-dedupe-binding-v1` 的事实层边界一致。
- 如果先 enrichment 再决定 capture 是否存在，会让 RSS 原始发现事实在 Readability 失败时消失。

## Data Flow And Interfaces

### 1. worker enrichment 输入

worker 在处理半导体 owner 的 captured event 时，至少需要这些输入：

```text
message_id
binding_id
request_id
plugin_id
payload.items[]
payload.metadata
correlation_id
causation_id
```

条目级决策至少要判断：

- 是否存在可读 URL
- RSS summary / content 是否已经足够
- 当前 binding / owner 是否要求该源默认尝试正文增强

### 2. enrichment 结果到 analysis request 的最小语义

后续实现不必一次锁死完整 DTO，但至少要保证 analysis-request payload 可表达：

```text
owner_type
owner_id
binding_id
source_message_id
request_id
items[]
  - url
  - title
  - summary_or_content
  - enrichment_status
  - enrichment_error_code?   # failed_degraded 时
  - source_metadata
```

约束：

- `summary_or_content` 可以是 RSS 摘要，也可以是 enriched 正文。
- `enrichment_status` 必须让 downstream consumer 能区分 degraded vs full-content。
- payload 不能包含 ORM model、插件实例、secret-bearing request headers 或 host-only 对象。

### 3. Event Bus contract change

本 change 对 stable topic contract 的要求是：

- `industry.analysis.requested` 成为这条主链路中的正式下游 handoff topic。
- 相关 stable topic policy、README 和 contract tests 必须与实现同步更新。
- topic 不得只在 worker 实现代码中出现而没有 contract change。

## Risks / Trade-offs

- [Risk] 采用 topic 方案会扩大本轮 contract 变更面。  
  Mitigation：把 topic 变更集中收口在本 change，明确属于 stable contract 更新，而不是让实现 PR 临时加字符串。

- [Risk] worker 后置 enrichment 会让 worker 职责变重。  
  Mitigation：把 enrichment 保持在 core-owned seam，worker app 只做消费编排，不直接内嵌 Readability 细节。

- [Risk] degraded 路径如果标记不清，下游会把 RSS 摘要误当全文。  
  Mitigation：在 spec 中把 `enrichment_status` 固定为必需语义。

- [Risk] 首批 RSS feed 若过多，会导致 fixture 和验证复杂度膨胀。  
  Mitigation：V1 只要求 baseline required + expansion optional 的分层，不要求一次把所有来源默认启用。

- [Risk] 若后续 RawEvent 实现没有复用“capture 先于 enrichment”的顺序，可能与本 change 冲突。  
  Mitigation：在 tasks 和 PR 证据链中显式要求与 `raw-event-persistence-dedupe-binding-v1` 对齐。

## Migration Plan

1. 先提交本 OpenSpec-only PR，只包含 `semiconductor-rss-readability-ingestion-main-chain-v1/**`。
2. 维护者明确评论“没问题”或批准后，再进入实现 PR。
3. 实现 PR 先补半导体行业包模板资产和 required/optional source dependency。
4. 再补 worker enrichment seam 与 degraded metadata。
5. 再补 `industry.analysis.requested` topic contract 和 publisher 行为。
6. 最后补最小 harness，证明 scheduler -> captured -> enrich/degrade -> analysis requested 主链路成立。

## Open Questions

- baseline required feeds 的具体 URL 白名单是否由实现 PR 直接确定，还是需要先补 supporting design note；本 change 先只固定分层原则。
- `industry.analysis.requested` 的最终 payload 字段是否要在后续 AgentRuntime / industry consumer change 中进一步稳定；本 change 先固定 owner identity、traceability 和 degraded status 这些最低要求。
