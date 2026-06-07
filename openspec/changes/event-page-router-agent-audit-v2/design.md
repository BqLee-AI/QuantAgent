## Context

本 change 基于 issue #280 和最新 `origin/main`。旧分支上的 `event-page-router-agent-audit-v1` 实现不可作为真源；当前真实状态是：

- `worker` 已消费 `industry.analysis.requested`，通过 `SingleCallEventIntakeRunner` 产出 Router Agent decision，发布 `event.routed`，并写入 `event_intake_routed_events`。
- Router Agent 当前稳定实现为 `event_intake_decision.v1`，字段已覆盖 `quality`、`industry_relevance`、`structured_news`、`routing`、`audit`，但 prompt 和 schema 没有明确“用户可读语义文本默认中文”的契约。
- `/runtime` 已有 `GET /api/v1/runtime/audit/news`，能聚合 RawEvent、capture、scheduler run 和 latest routed event，用于排查“为什么没有形成事件”。
- `/events`、`/events/all`、`/events/:eventId`、`/events/:eventId/audit` 仍使用 `event-scoring` mock 或旧 audit fixture，不是生产真实业务入口。
- `features/runtime/components/agent/*` 已有 Router Agent 详情弹窗、JSON view 和 key fields，但它们属于 runtime 私有 feature；`/events` 不能直接依赖该私有边界。

核心产品决策：

- `/events` 只展示 Router Agent 处理之后的新闻事件；未处理 RawEvent、pending、routing unavailable 留在 `/runtime`。
- `decision=route|review` 是默认业务列表重点；`decision=discard` 是已处理但默认价值较低，只通过显式筛选或审计模式查看。
- 不做中文 `display` 字段。Router Agent 的语义字段本身应按默认用户语言输出中文；机器字段继续保持英文 enum/code。

## Goals / Non-Goals

**Goals:**

- 把 `/events` 从 mock 页面迁移为真实已路由新闻事件审计入口。
- 新增业务 `/api/v1/events` read model，内部复用 RawEvent、capture、scheduler run、`event_intake_routed_events`，但不直接暴露 runtime audit DTO。
- 定义 Router Agent `event_intake_decision.v2`，保持 single-call intake，同时让用户可读语义字段默认中文。
- 保留 v1 历史记录兼容读取，避免历史 routed record 在 `/events` 中完全不可见。
- 抽取 `features/agent-audit/` 或等价共享边界，供 `/events` 与 `/runtime` 复用 Agent stage panel、detail modal、JSON view、key fields、trace refs。
- 新增 `event.inspect` capability，让业务事件审计与 runtime 排障权限分离。

**Non-Goals:**

- 不重做 RSS、Readability、scheduler、worker、Kafka、RawEvent persistence 或 source binding。
- 不新增业务 `events` 聚合表；V1 使用 `raw_event_id` 作为业务 route 主 ID，并以 latest routed record 作为“已形成业务事件”的准入条件。
- 不实现行业 MainAgent 深度分析、Scoring/Debate、Decision/Approval、broker 或真实交易执行。
- 不实现多语言 locale 策略、翻译缓存或多语言字段矩阵；默认中文输出只适用于当前用户默认语言。
- 不把 `/runtime/audit/news` 直接作为 `/events` 长期公开契约。
- 不把 provider raw response、prompt、CoT、secret、完整正文、raw payload、ORM object 或 plugin instance 暴露给业务 API 或前端默认详情。

## Decisions

### 1. `/events` 只查询 routed read model，不展示 pending RawEvent

采用方案：`/api/v1/events` 的主查询从 `event_intake_routed_events` 出发，按 `raw_event_id` 关联 RawEvent/capture/scheduler 摘要。没有 routed record 的 RawEvent 不进入 `/events`。

理由：

- `/events` 的字段依赖 Router Agent 输出：decision、summary、relevance、target industry/topic、quality、review/discard reason。
- 未被 AI 处理过的新闻对业务用户不是“事件”，属于链路排障问题，应在 `/runtime` 查。
- 从 routed read model 出发可以天然过滤未处理项，并支持默认只看 `route|review`。

替代方案：

- 从 RawEvent 出发再左连接 routed record：能展示 pending，但违背产品决策，并把 `/events` 变成 RawEvent inbox。
- 直接复用 `/runtime/audit/news`：实现快，但业务契约被 runtime DTO 绑死。

### 2. V1 使用 `raw_event_id` 作为业务 route 主 ID，不新增业务 `events` 表

API route 使用：

```text
GET /api/v1/events
GET /api/v1/events/{raw_event_id}
GET /api/v1/events/{raw_event_id}/agent-stages/{stage_id}
GET /api/v1/events/{raw_event_id}/router-output/{routed_event_id}
```

`raw_event_id` 是 URL 主 ID；`routed_event_id` 或 `event.routed` message id 用于定位具体 Router Agent output detail。若一条 RawEvent 有多条 routed record，列表和详情默认取 latest，详情响应保留 `routed_event_id` 供打开完整 JSON。

理由：

- RawEvent 已是 source 事实真源，`event_intake_routed_events.raw_event_id` 已存在。
- 新增业务聚合表会扩大迁移和幂等范围，当前阶段还没有 MainAgent/Decision 等需要独立事件生命周期表的事实。

### 3. 新增业务 Events API，router 薄层、service 聚合 read model

建议后端文件规划：

```text
apps/api/src/quantagent/api/
  schemas/events.py
  services/events.py
  routers/v1/events.py
  routers/v1/register.py
```

职责：

- `routers/v1/events.py`：解析 query/path、校验 `event.inspect`、注入 session/request、返回 `ApiResponse[T]`。
- `schemas/events.py`：公开 DTO、分页、筛选、stage、trace、安全 detail，不引用 ORM。
- `services/events.py`：从 `EventIntakeRoutedEventORM` 查询 routed record，关联 RawEvent/capture/scheduler 摘要，生成业务展示 read model。
- 如果 routed 查询在 API 与 worker/runtime 间继续复用，可在 `packages/core/db/repositories/event_intake_repository.py` 补充 repository 方法；API service 不能直接把 ORM 返回给 router。

列表查询参数草案：

```text
keyword
decision                 # route | review | discard | all，默认 route,review
include_discard=false
binding_id
source_plugin_id
industry_id
target_topic
priority
relationship             # direct | indirect | contextual | none
status                   # success | failed
trace_id
request_id
time_from
time_to
cursor
limit                    # 默认 20，上限 100
```

列表响应草案：

```text
EventListResponse
  items: EventListItem[]
  next_cursor
  generated_at

EventListItem
  raw_event_id
  routed_event_id
  schema_version
  title
  url
  url_host
  source_name
  source_plugin_id
  published_at
  routed_at
  decision
  discard_reason
  status
  summary
  event_type
  tags
  priority
  relationship_summary
  target_industries
  target_topics
  quality
  trace
  timeline
  router_stage_summary
```

列表不返回完整 `output_json`、完整正文、`raw_payload`。`summary`、`title`、`tags` 等用户可读语义字段来自 Router Agent semantic fields，默认中文。

### 4. Router Agent v2 不新增 `display` 文本层

`event_intake_decision.v2` 推荐结构：

```text
EventIntakeDecisionV2
  schema_version = "event_intake_decision.v2"
  trace
  decision                         # route | review | discard
  discard_reason                   # 英文 enum/code
  quality
    is_spam
    noise_flags[]                  # 英文 code 或稳定短码
    content_completeness
    enrichment_status
    confidence
    reason_summary                 # 中文
    risk_flags[]                   # code + 中文 label 可拆
  relevance
    industry_id
    relationship                   # direct | indirect | contextual | none
    relevance_score
    reason_summary                 # 中文
  structured_news
    canonical_title                # 中文标题；原文标题保留在 source/article snapshot
    short_summary                  # 中文
    bullet_summary[]               # 中文
    event_type                     # 稳定 code
    event_type_label               # 中文
    tags[]                         # 结构：code + label，label 中文
    entities[]
    companies[]
    tickers[]
    technologies[]
    products[]
    locations[]
    numbers[]
    time_horizon
    source_facts[]                 # 中文可读事实摘录，保留事实引用
    uncertainties[]                # 中文
  routing
    target_industries[]
    target_topics[]                # 可包含 code + 中文 label
    priority                       # low | normal | high | urgent
    requires_deep_analysis
    requires_human_review
    next_step_hint                 # 中文
    reason_summary                 # 中文
    dedupe_key_hint
  audit
    reason_summary                 # 中文
    evidence_field_refs[]
    schema_validation_status
    source_language?
    output_language="zh-CN"
```

关键约束：

- 不定义 `display.headline`、`display.summary_markdown`、`display.badges` 作为内容真源。
- API read model 可以从 `structured_news.canonical_title`、`structured_news.short_summary`、`routing.reason_summary`、`quality.reason_summary` 等语义字段选择列表展示字段。
- 机器字段用英文 enum/code，便于筛选、回测和数据分析；中文 label 是同一语义块的可读字段，不是 UI-only 字段。
- v1 record 读取时通过 mapper 产生最小业务摘要：`canonical_title` 可能缺失时回退 RawEvent title，`summary` 回退 v1 `structured_news.short_summary` 或 audit reason，字段缺失显示 `not_provided` 或 `unavailable`。

### 5. Worker 和 persistence 继续保持 single-call 与安全输出

`SingleCallEventIntakeRunner` 的 single-call 约束保留：每篇文章最多一次结构化模型调用，不调用 tool、不二次抓取、不分块总结。

实现影响：

- 更新 prompt，明确“用户可读语义文本默认使用中文；不要新增 display 字段；机器字段保持指定 enum/code”。
- 更新 schema validation：接受 v2，兼容 v1；schema invalid 仍进入 structured failure/review/discard 路径，不静默 route。
- 更新 `_key_fields()` 或等价 mapper，把 v2 的核心字段写入 `event_intake_routed_events.key_fields`，便于列表查询和 UI 摘要。
- `output_json` 仍只保存结构化 Agent output，不保存 provider raw response、prompt、CoT 或 unbounded article content。

### 6. 新增 `features/agent-audit/` 共享前端边界

建议前端目录规划：

```text
apps/web/src/features/agent-audit/
  README.md
  components/
    AgentStagePanel.tsx
    AgentStageDetailModal.tsx
    AgentKeyFields.tsx
    AgentJsonView.tsx
    AgentTraceRefs.tsx
    states/
  types/
    agent-audit.types.ts
  utils/
    agent-audit-format.ts
    agent-audit-sanitize.ts
```

`features/agent-audit` 接收稳定展示模型：

```text
AgentAuditSubject
  subject_id
  title
  url
  source
  content_preview
  trace

AgentAuditStage
  stage_id
  stage_kind             # router_agent | industry_main_agent | ...
  status
  title
  summary
  key_fields
  output_json?
  refs
  unavailable_reason?
```

约束：

- 组件不接收 `ApiResponse`、ORM、runtime 私有 DTO、provider raw response 或 full raw payload。
- `/runtime` 和 `/events` 各自 mapper 到 `AgentAuditSubject/Stage`，共享展示组件。
- Router Agent 弹窗展示新闻标题、URL、content preview、关键字段、完整结构化 output JSON 和 refs。
- 后续行业 MainAgent 可以扩展为 Markdown/chat/toolcall 渲染，但仍在共享 Agent audit 边界下，不塞进 `/events` page 主体。

### 7. `/events` 前端按业务 feature 重组

建议目录：

```text
apps/web/src/features/events/
  README.md
  api/
    events.api.ts
    events.contracts.ts
  queries/
    events.keys.ts
    use-event-list.ts
    use-event-detail.ts
    use-event-agent-stage.ts
  hooks/
    use-event-list-page.ts
    use-event-detail-page.ts
    use-event-filters.ts
  components/
    page/
      EventListPage.tsx
      EventDetailPage.tsx
      EventAuditPage.tsx
    filters/
    event-list/
    detail/
    states/
  types/
    events.types.ts
  utils/
    event-labels.ts
    event-contract-mappers.ts
```

route 文件只做 `createFileRoute`、search/path params 和页面组合。生产路径不能 import `event-scoring` mock；fixture 只能留在 tests/harness。

### 8. `/runtime` 保持排障职责

实现阶段不要求删除 `/runtime` 现有 RawEvent audit 能力，但必须调整边界：

- `/runtime` 展示未处理 RawEvent、AI intake unavailable、模型失败、Kafka/worker/scheduler 问题。
- `/runtime` 可展示 Router Agent output 用于排障，但不得成为业务事件主入口。
- `/runtime` 复用 `features/agent-audit` 组件，不复制私有 modal 形成第二套。

### 9. 权限边界

新增 `event.inspect`：

- `/api/v1/events*` 使用 `event.inspect`。
- `/runtime` 继续使用 `runtime.inspect`。
- 本地 development actor 默认包含 `event.inspect`，避免默认开发启动看不到事件页。
- 如果实现阶段发现 capability registry 没有稳定声明位置，需要在 API auth capability 常量、前端 route policy 和测试中同步登记，不允许只在 router 里写字符串。

## Risks / Trade-offs

- [Risk] v1 和 v2 routed record 同时存在，字段形状不一致。
  → Mitigation：API mapper 明确 v1 fallback，缺失字段用 `not_provided/unavailable`，并在详情中显示 `schema_version`。

- [Risk] 默认只展示 routed 事件会让用户误以为没有新抓取新闻。
  → Mitigation：空态说明“只有 Router Agent 处理后的新闻进入事件页”，并提供进入 `/runtime` 的排障入口。

- [Risk] 中文输出依赖 prompt，模型可能仍返回英文。
  → Mitigation：schema 不因英文直接失败，但 tests 使用 fake provider 覆盖中文字段要求；prompt 与 acceptance 明确关键用户可读字段应为中文，后续可加语言质量检查。

- [Risk] `output_json` 体积可能较大。
  → Mitigation：列表不返回完整 JSON；详情按需拉取；API 对 output JSON 继续执行 safe allowlist / size guard。

- [Risk] 抽共享 `agent-audit` 可能影响 runtime 已有页面。
  → Mitigation：先抽展示模型和纯组件，再由 runtime/events 各自 mapper；不改变 runtime API 契约作为前置条件。

- [Risk] `/events/:eventId/audit` 旧 mock 审计页与新业务 Agent stage 语义冲突。
  → Mitigation：生产 route 改接真实 business read model；旧 mock 只能留在 tests/demo/debug，不进入正式导航。

## Migration Plan

1. OpenSpec-only PR 审核通过后进入实现 PR。
2. 后端先新增 `/api/v1/events` read model 与 `event.inspect`，不删除 runtime audit endpoint。
3. Core/worker 增加 v2 schema/prompt/key fields，同时保留 v1 兼容读取。
4. Web 新增 `features/agent-audit`，先让 runtime 组件迁移到共享模型，再让 `/events` 切真实 API。
5. `/events` 生产路径停止使用 `event-scoring` mock；保留 mock 仅用于单测 fixture 或 debug/demo。
6. 验证通过后，在 PR 说明中标注 v1 历史记录兼容行为、未实现 MainAgent/Decision 的非目标和本地 smoke 结果。

Rollback：

- 若 Web 真实 API 接入存在风险，可先保持 route feature flag 或保留 mock fixture 仅用于测试；生产默认仍不得静默回退 mock。
- 若 v2 schema provider 输出不稳定，可继续读取 v1 routed records，但 OpenSpec 要求的中文语义字段需要在 prompt/schema 后续修复，不能通过 `display` 字段规避。
