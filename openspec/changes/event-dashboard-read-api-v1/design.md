## Context

issue #175 位于标准事件主对象、Dashboard 首屏聚合、后端 REST 契约和持久化 read model 四个边界的交汇处。当前 `main` 已经具备：

- `apps/api`：API v1 protected registration、Cookie Session Auth、capability / CSRF、`ApiResponse[T]` envelope、request id、RawEvent、Runtime Inspect / Audit、Approval、AgentRun、ToolInvocation、SchedulerRun 等路由边界。
- `packages/core`：RawEvent canonical / capture、SourceBinding / SchedulerRun、Event Bus、`event_intake` routed-event read model、Approval persistence / orchestration、notification / runtime 基础能力。
- `packages/agent`：DeepAgents `AgentRuntime` MVP、stream event、tool adapter、artifact store、半导体 MainAgent NVDA fixture。

缺口是标准 Event 与 Dashboard 聚合 REST 契约仍未收住：当前没有 `GET /api/v1/events`、`GET /api/v1/events/{event_id}`、`GET /api/v1/dashboard/summary`，也没有管理台业务事件 read model 真源。

本设计以以下真源为依据：

- issue #175 正文与 2026-06-05 评论：最终范围收窄为后端 only。
- 维护者确认：标准 Event read model 新增 `events` / `event_state_transitions`；`summary_buckets` 首版只做 PRD 必需项；`best_action` 只返回摘要 + `approval_ref`；`health_summary` 只聚合影响判断质量的最小摘要。
- `apps/api/AGENTS.md`：API 只负责 HTTP 边界，router 不承载核心查询、评分、排序、状态机或 ORM 操作。
- `packages/core/AGENTS.md`：Event 是核心运行时主对象；事件状态流转必须支持回放；ORM model 不能直接作为 API DTO。
- `docs/prd/pages/00-dashboard.md`、`02-events-home.md`、`03-event-detail.md`。
- `docs/design/02-core-architecture-and-runtime.md`、`08-api-and-websocket-design.md`。
- 当前 `quantagent.core.events` 已是 Event Bus V1 基础设施边界，README 明确不负责 RawEvent / Event 数据库持久化；标准 Event read model 不能混入该目录的 bus codec、topic、backend 和 publisher 职责。

## Goals / Non-Goals

**Goals:**

- 在 `packages/core` 中定义标准 Event V1 read model、持久化模型、repository / service 查询边界和 Dashboard summary 聚合输入。
- 新增 `events` 当前状态表与 append-only `event_state_transitions` 状态流转表，明确 RawEvent / routed-event / runtime / approval 引用关系。
- 在 `apps/api` 中暴露受保护只读 API：`GET /api/v1/events`、`GET /api/v1/events/{event_id}`、`GET /api/v1/dashboard/summary`。
- 固定 Events list query params、分页、筛选回显、summary buckets、Event detail 摘要结构和 Dashboard 分区状态。
- 保持 REST、数据库和状态流转记录作为业务状态真源；未来实时通道只做刷新提醒。
- 明确失败路径、降级语义、脱敏边界和验证入口，让后续实现 PR 不需要临场决定核心契约。

**Non-Goals:**

- 不修改 `apps/web`，不实现 Dashboard / Events / Event Detail 页面接入、TanStack Query、feature 目录拆分或 mock 迁移。
- 不重复实现 RawEvent canonical / capture 去重、RawEvent API、Runtime Audit news API、Approval actions、AgentRuntime MVP、Agent Debug SSE 或 Web debug chat。
- 不实现完整 Source Plugin 抓取、事件标准化写入全链路、新 worker / scheduler loop、完整 Scoring / Debate、完整 Decision / Policy Gate、真实 Approval amend、真实 broker、真实交易、真实密钥或 live trading。
- 不实现 WebSocket 实时通道；后续实时通道只能触发 REST query invalidation。
- 不生成 static OpenAPI artifact、TypeScript client、Zod schema 或 `packages/contracts` 生成物。

## Decisions

### 1. 标准 Event read model 归属在 `packages/core`

实现应在 `packages/core` 新增独立 read model 子域，或采用等价职责拆分；不得把标准 Event read model 混入现有 `quantagent.core.events` Event Bus 根目录：

```text
packages/core/src/quantagent/core/event_read_model/
  README.md
  models.py          # core domain / read model dataclass 或 Pydantic-free 结构
  service.py         # list/detail/featured/dashboard query orchestration
  repository.py      # repository Protocol，service 依赖接口

packages/core/src/quantagent/core/db/models/
  event.py           # EventORM 与 EventStateTransitionORM

packages/core/src/quantagent/core/db/repositories/
  event_repository.py
```

职责边界：

- `EventORM` / `EventStateTransitionORM` 只负责表字段、索引、约束和 ORM 映射，不放 API DTO、业务方法或序列化逻辑。
- `EventRepository` 只负责查询构造、分页、筛选、排序、状态流转 append-only 写入和统计查询，不承载 HTTP 协议或 API envelope。
- `EventReadModelService` 负责组合 repository 输出、状态摘要、featured events 排序、summary buckets、Dashboard featured events 和 detail 摘要，不依赖 FastAPI 或 API DTO。
- `packages/core` 不依赖 `apps/api`、React、前端类型、具体插件实现或 API envelope。
- `event_read_model/README.md` 必须说明它与 RawEvent、`event_intake`、Event Bus、Approval、Runtime Inspect 的边界；如果实现选择其他目录名，需要在 README 中保留同等边界说明。

替代方案是由 `apps/api` 组合 RawEvent + routed-event 查询生成 `/events` 响应。该方案会让 API router/service 成为业务事件真源，也会把采集、AI intake、运行审计视角冒充标准 Event，因此不采用。

### 2. 新增 `events` 当前状态表与 append-only `event_state_transitions`

首版持久化采用“当前状态主表 + append-only 状态流转表”：

```text
events
  event_id: string primary key
  schema_version: string
  title: string
  summary: text | null
  source_name: string | null
  source_type: string | null
  source_url: string | null
  source_authority: string | null
  published_at: datetime | null
  captured_at: datetime
  current_status: string
  analysis_status: string
  credibility: string | null
  priority_score: number | null
  recommendation_score: number | null
  confidence: number | null
  risk_level: string | null
  risk_direction: string | null
  industries: json
  entities: json
  tags: json
  featured_reason: string | null
  is_featured: boolean
  raw_event_id: string | null
  routed_event_id: string | null
  trace_id: string | null
  correlation_id: string | null
  identity_kind: string
  identity_value: string
  version: integer
  latest_agent_run_id: string | null
  latest_tool_invocation_id: string | null
  approval_id: string | null
  degradation_notices: json
  evidence_summary: json
  industry_impact_summary: json
  best_action_summary: json
  audit_refs: json
  created_at: datetime
  updated_at: datetime

event_state_transitions
  transition_id: string primary key
  event_id: string
  from_status: string | null
  to_status: string
  reason_code: string | null
  reason_summary: text | null
  actor_type: string
  actor_id: string | null
  source_ref: json
  request_id: string | null
  trace_id: string | null
  created_at: datetime
```

受控枚举草案：

- `current_status`: `captured`、`routed`、`analyzing`、`scored`、`decision_ready`、`pending_approval`、`approved`、`rejected`、`failed`、`review_required`、`discarded`。
- `analysis_status`: `pending`、`analyzing`、`scored`、`decision_ready`、`pending_approval`、`failed`、`review_required`、`unavailable`。
- `credibility`: `high`、`medium`、`low`、`conflict`、`unknown`。
- `source_type`: `rss`、`api`、`webhook`、`manual`、`unknown`。
- `risk_level`: `low`、`medium`、`high`、`critical`、`unknown`。
- `risk_direction`: `positive`、`negative`、`mixed`、`neutral`、`unknown`。
- `section status`: `ok`、`empty`、`unavailable`、`error`。

索引草案：

- `events(current_status, captured_at, event_id)`
- `events(analysis_status, captured_at, event_id)`
- `events(source_type, captured_at, event_id)`
- `events(is_featured, priority_score, captured_at, event_id)`
- `events(raw_event_id)`
- `events(routed_event_id)`
- `events(trace_id)`
- unique `events(identity_kind, identity_value)`
- partial unique `events(raw_event_id) WHERE raw_event_id IS NOT NULL` 或当前数据库方言等价约束。
- partial unique `events(routed_event_id) WHERE routed_event_id IS NOT NULL` 或当前数据库方言等价约束。
- `event_state_transitions(event_id, created_at, transition_id)`

关键约束：

- `event_state_transitions` MUST append-only；不得通过 update 覆盖历史状态。
- 状态更新必须在同一事务内更新 `events.current_status` / `updated_at` 并追加 transition。
- `events.identity_kind` / `identity_value` 是标准 Event 幂等身份，不是展示字段；首版 identity 选择顺序固定为：非空 `raw_event_id` 优先，其次非空 `routed_event_id`，最后才允许使用 materializer 输入中显式提供的稳定外部 identity。不得用 request_id、trace_id、当前时间或随机数作为唯一身份来源。
- `event_id` 必须由稳定 identity 派生，或在首次创建后通过 unique identity 重读复用；同一 RawEvent / routed-event / analysis summary 重复 materialize 必须返回同一个标准 Event。
- materializer 遇到 `identity_kind` / `identity_value`、`raw_event_id` 或 `routed_event_id` 唯一冲突时，必须在同一事务语义下重读既有 Event 并按幂等规则合并摘要，不得创建第二条标准 Event。
- repository 更新同一 Event 状态时必须按 `event_id` 串行化：优先使用 `SELECT ... FOR UPDATE`；若目标数据库或测试方言不支持行锁，必须使用 `version` 条件更新或等价乐观锁重试，避免并发写入导致 `current_status` 与 transition history 不一致。
- 相同 `event_id`、`to_status`、`source_ref` / `request_id` 的重复状态写入是幂等 no-op 或返回既有 transition，不得追加无意义重复 transition。
- 状态流转不得无序回退；只有 `reason_code` 明确表达人工复核、重新分析或回滚语义时，才允许从较后阶段回到较早阶段，并必须记录 transition reason。
- `dry_run_executed` 只允许作为兼容历史数据的状态名保留，不作为 #175 新增状态流转目标；#175 不实现 broker、dry-run 执行或真实交易执行。
- 首版允许 `best_action_summary`、`industry_impact_summary`、`evidence_summary` 等 JSON 摘要字段承载 read model 快照，避免把完整 Decision / Policy Gate / provider raw response 拉进本 issue。
- 所有 JSON 摘要字段只保存可公开摘要、引用和降级原因；不得保存完整 prompt、完整模型推理链、provider raw response、secret、broker credential 或私有策略。

替代方案是只用 RawEvent + routed-event 组合查询。该方案无法表达标准 Event 当前状态、状态流转回放、Dashboard priority 和 detail 摘要的稳定业务真源，因此不采用。

### 3. 标准 Event 通过 materializer 写入，不由 API 查询临时拼装

标准 Event read model 需要明确写入 / materialization 边界，避免实现时只建表和只读 API，或把写入临时塞进 router。

实现应新增或等价拆分：

```text
packages/core/src/quantagent/core/event_read_model/
  materializer.py     # RawEvent / routed-event / analysis / approval 摘要到 Event read model 的写入边界
```

职责：

- `EventReadModelMaterializer` 接收已经持久化的 RawEvent、`event_intake` routed-event、analysis summary、approval ref 或 runtime summary 输入，生成或更新标准 Event read model。
- materializer 只依赖 core repository / domain model，不依赖 FastAPI、API DTO、前端类型或具体插件实现。
- materializer upsert `events` 当前状态时，状态变化必须通过 repository 在同一事务内追加 `event_state_transitions`。
- materializer 调用 repository 时必须传入稳定 identity；没有 `raw_event_id`、`routed_event_id` 或显式稳定外部 identity 的输入应被拒绝或标记为不可 materialize，不得创建随机 Event。
- 首版必须提供显式可测试的 materializer service seam；只有在当前 RawEvent capture / `event_intake` routed-event 持久化链路已有清晰 service 调用点时才接入同步 materialization，不为接入 materializer 新增 worker / scheduler loop 或事件消费框架。
- 如果实现阶段发现现有写入链路接入会扩大范围，应保留 materializer service 与 repository 测试，Events / Dashboard API 仍只读取标准 Event read model；未 materialized 的历史数据表现为真实空态或分区降级，不能回退到 RawEvent / Runtime Audit 临时拼装。
- 历史 RawEvent / routed-event backfill 不在 #175 默认执行；如需要批量补历史 Event，另开 backfill / replay issue，单独定义分批、幂等和回滚策略。

输入输出草案：

```text
EventMaterializationInput
  identity_kind
  identity_value
  raw_event_ref
  routed_event_ref
  fact_summary
  routing_summary
  analysis_summary
  approval_ref
  runtime_refs
  trace_id
  correlation_id
  occurred_at

EventMaterializationResult
  event_id
  created: boolean
  previous_status
  current_status
  transition_id
  degradation_notices
```

失败路径：

- RawEvent 存在但 routed-event 缺失时，materializer 可创建 `current_status=captured`、`analysis_status=pending` 的标准 Event，并通过 `degradation_notices` 表达分析未接通。
- routed-event 标记 discard 时，materializer 可以不生成 featured Event，但若生成标准 Event，必须以受控状态和原因摘要表达 discard / review。
- 相同输入重复 materialize 时，如果核心摘要无变化且状态未变化，materializer 返回既有 Event 与既有状态摘要，不追加 transition。
- materializer 不得吞掉写入失败；调用方应记录错误并让 Dashboard / Events API 对未 materialized 数据保持真实空态或 unavailable，不用 mock 补齐。

替代方案是由 `/events` 查询时组合 RawEvent + routed-event。该方案无法建立稳定状态流转，也会让读 API 临时承担业务 materialization，因此不采用。

### 4. Events list 契约锁定筛选、排序、分页与最小 summary buckets

公开路径：

```text
GET /api/v1/events
```

query params：

- `time_range`: 固定为 `today`、`24h`、`7d`、`30d`，默认 `24h`。
- `industry`: 使用 repeated query parameter，例如 `industry=semiconductor&industry=ai-infra`；API DTO 回显规范化后的 string array。
- `credibility`: `high`、`medium`、`low`、`conflict`、`unknown`。
- `analysis_status`: `pending`、`analyzing`、`scored`、`decision_ready`、`pending_approval`、`failed`、`review_required`、`unavailable`。
- `source_type`: `rss`、`api`、`webhook`、`manual`、`unknown`。
- `sort`: `mixed`、`latest`、`priority`。
- `cursor`: opaque cursor。
- `limit`: 默认 `20`，最大 `100`；超过最大值返回 400 或按 API 既有参数校验策略拒绝，不静默放大查询。

response data 草案：

```text
EventListResponse
  items: EventListItem[]
  next_cursor: string | null
  filters: EventListFiltersEcho
  summary_buckets: EventSummaryBuckets
  generated_at: datetime

EventSummaryBuckets
  new_count: integer
  featured_count: integer
  analyzing_count: integer
  failed_or_review_count: integer
  pending_approval_count: integer | null

EventListItem
  event_id
  title
  summary
  source
    name
    authority
  source_type
  source_url
  published_at
  captured_at
  current_status
  analysis_status
  credibility
  priority_score
  recommendation_score
  confidence
  risk_level
  risk_direction
  industries
  featured_reason
  trace_ref
  raw_event_ref
  routed_event_ref
  degradation_notices
```

排序语义：

- `latest` 按 `published_at` / `captured_at` 倒序，并用 `event_id` 稳定打破平手。
- `priority` 按 `priority_score` / `captured_at` / `event_id` 稳定排序。
- `mixed` 用后端 service 定义的 “最新 + 高价值混合” 稳定排序，不能在 router 中计算。

`summary_buckets` 首版只覆盖 PRD 必需项，不做行业分布、来源分布、趋势环比或复杂 BI 统计。

### 5. Event detail 只暴露决策页必需摘要

公开路径：

```text
GET /api/v1/events/{event_id}
```

response data 草案：

```text
EventDetailResponse
  event_id
  fact_summary
  score_summary
  industry_impact
  best_action
  approval_ref
  runtime_summary
  evidence_summary
  degradation_notices
  audit_refs
  state_summary

EventFactSummary
  title
  summary
  source
  source_type
  source_authority
  source_url
  published_at
  captured_at
  current_status
  credibility
  verification_status
  conflict_summary
  raw_event_ref
  routed_event_ref

EventScoreSummary
  priority_score
  credibility
  recommendation_score
  confidence
  analysis_status
  featured_reason

EventBestActionSummary
  title
  action_hint
  recommendation_score
  confidence
  risk_level
  risk_direction
  approval_ref
  status
  unavailable_reason

EventRuntimeSummary
  agent_run_count
  latest_agent_run_ref
  latest_tool_invocation_ref
  latest_analysis_status
  has_critical_tool_failure
  request_id
  trace_id
```

约束：

- `best_action` 首版只返回摘要与 `approval_ref`，不得返回完整 `DecisionResult`、完整 Policy Gate payload、完整模型推理链或 broker 执行结果。
- `approval_ref` 只表达审批入口引用，不表达真实执行完成。
- `state_summary` 来自 `event_state_transitions` 摘要，用于详情页状态回放入口。
- 未接通的行业影响、best action、runtime 摘要必须通过 `status` / `unavailable_reason` / `degradation_notices` 受控表达，不能用 mock 假装真实数据。

### 6. Dashboard summary 聚合分区独立降级

公开路径：

```text
GET /api/v1/dashboard/summary
```

response data 草案：

```text
DashboardSummaryResponse
  featured_events: DashboardSection[EventListItem[]]
  approval_summary: DashboardSection[DashboardApprovalSummary]
  health_summary: DashboardSection[DashboardHealthSummary]
  entry_metrics: DashboardSection[DashboardEntryMetrics]
  generated_at: datetime

DashboardSection[T]
  status: "ok" | "empty" | "unavailable" | "error"
  data: T | null
  reason: string | null
  updated_at: datetime | null

DashboardApprovalSummary
  pending_count
  expiring_soon_count
  top_items

DashboardHealthSummary
  status: "ok" | "degraded" | "unavailable" | "error"
  items: DashboardHealthItem[]

DashboardHealthItem
  kind
  severity
  title
  summary
  affected_event_id
  request_id
  trace_id
  runtime_ref

DashboardEntryMetrics
  new_count
  featured_count
  analyzing_count
  failed_or_review_count
  pending_approval_count
```

聚合规则：

- `featured_events` 来自标准 Event read model，不来自 Runtime Audit news、RawEvent fixture 或 API sample provider。
- `approval_summary` 复用已存在 Approval persistence / repository / service 查询边界；若当前没有专用 summary 方法，实现可以在 API service 内做薄聚合，或在依赖不可用时返回受控 `unavailable` / `error`，但不得重新实现 approve / reject / request-reanalysis actions。
- `health_summary` 只聚合影响判断质量的最小摘要，可来自现有 runtime health、runtime errors、AgentRun / ToolInvocation 摘要查询；缺少某个查询入口时对应 item 缺省或分区降级，不把完整 Runtime dashboard 搬进 Dashboard summary。
- 任一分区依赖不可用时，该分区返回 `unavailable` 或 `error`，其他分区仍可返回 `ok` 或 `empty`。
- 基础认证和请求解析通过后，即使 Event read model、Approval 或 Runtime 的局部分区查询不可用，也优先返回 HTTP 200 + `ApiResponse.success(DashboardSummaryResponse)`；局部失败只体现在对应 `DashboardSection.status`、`reason` 和 `updated_at` 中。
- 只有认证失败、请求参数校验失败、响应 DTO 无法构造、数据库 session 完全不可用或 Dashboard service 自身不可恢复时，才返回错误 envelope；不得因为单个分区失败把整个 Dashboard summary 返回 500 或 `ApiResponse.code != 0`。
- Event read model 不可用时，`featured_events` 与 `entry_metrics` 分区标记为 `unavailable` 或 `error`，`approval_summary` 与 `health_summary` 仍尽量独立返回真实摘要或自身降级状态。

替代方案是让 Dashboard 直接调用多个现有 API 并在前端拼装。该方案会让前端继续发明 DTO，且无法统一局部分区降级语义，因此不采用。

### 7. API 层只做 DTO、DI、envelope 和错误映射

API 侧新增或等价拆分：

```text
apps/api/src/quantagent/api/
  schemas/
    events.py
    dashboard.py
  services/
    event_api.py
    dashboard_api.py
  routers/v1/
    events.py
    dashboard.py
```

职责：

- `schemas/events.py` / `schemas/dashboard.py` 定义 API request / response DTO、query enum、section status、OpenAPI 描述，不引用 ORM model。
- `services/event_api.py` / `services/dashboard_api.py` 从请求级 `Session` 组装 core repository / service，把 core read model 映射为 API DTO，并处理部分依赖不可用的分区降级。
- `routers/v1/events.py` / `routers/v1/dashboard.py` 只处理 HTTP path/query、DI、`ApiResponse.success(...)`、领域错误映射和 response_model。
- `routers/v1/register.py` 通过 `STANDARD_API_V1_ROUTER_REGISTRATIONS` 注册为 protected routes。

不得：

- router 内直接 `session.execute()`、查询 ORM、计算评分、排序、状态流转或聚合 Dashboard。
- API DTO 直接返回 SQLAlchemy ORM、core domain object 或 provider raw response。
- 在 API sample provider 中硬编码假数据作为 `/events` 或 Dashboard 真源。

### 8. 不引入缓存，不新增跨端生成物

首版以数据库索引、受控筛选和分页保证查询边界；没有性能瓶颈证据前不引入缓存。若后续真实数据量证明 Dashboard summary 或 Events list 需要缓存，应由单独 change 说明缓存内容、失效策略、一致性级别和内存上限。

虽然 `docs/design/08-api-and-websocket-design.md` 提到长期 `packages/contracts` / OpenAPI 生成方向，但当前仓库 API 包尚未引入 static OpenAPI artifact、generated client、TypeScript types 或 Zod schema。本 change 不局部引入生成链路；runtime `/openapi.json` 与 OpenSpec spec 作为 V1 契约依据。

## Risks / Trade-offs

- [Risk] 新增 `events` 表会引入 RawEvent / routed-event 到标准 Event 的同步责任。→ Mitigation：本 change 固定 materializer seam、引用字段和 read model 边界；RawEvent / routed-event 仍是输入，不是 `/events` 真源。
- [Risk] 首版摘要字段过宽会偷带完整 Decision / Policy Gate。→ Mitigation：`best_action` 只允许摘要 + `approval_ref`，完整 `DecisionResult`、Policy Gate payload 和 broker 结果明确非目标。
- [Risk] Dashboard summary 容易演变成 Runtime 大盘。→ Mitigation：`health_summary` 只保留影响判断质量的最小 `items[]`，完整 Runtime health/errors/agent/tool 详情继续由 Runtime Inspect 资源承担。
- [Risk] Summary buckets 以后需要行业分布、来源分布或趋势。→ Mitigation：V1 只锁 PRD 必需项，扩展统计由后续 issue/change 添加，不破坏现有字段。
- [Risk] Migration 可能需要生产 backfill。→ Mitigation：V1 migration 只创建 schema；历史 RawEvent/routed-event backfill 如需批处理必须单独设计分批、幂等和回滚策略，不在本 OpenSpec 文档 PR 中执行。

## Migration Plan

1. OpenSpec-only PR 先提交 `openspec/changes/event-dashboard-read-api-v1/**`，不混入实现代码、依赖升级或格式化。
2. 维护者明确评论“没问题”或批准后，进入实现 PR。
3. 实现 PR 新增 Alembic migration 创建 `events` 与 `event_state_transitions`，并确保 migration 可解析；数据库可用时验证 upgrade / downgrade。
4. 实现 core Event read model repository / service，再接 API DTO / service / router。
5. 部署时先运行 `uv run quantagent-db upgrade`；回滚时使用对应 downgrade 回退本 change migration。
6. 如生产或本地已有 RawEvent / routed-event 历史数据，本 change 不默认做自动 backfill；需要时另开批处理 / replay issue。

## Open Questions

无。V1 决策已锁定：

- 标准 Event read model 新增 `events` / `event_state_transitions`。
- `event_state_transitions` append-only。
- `summary_buckets` 只做 PRD 必需项。
- `best_action` 只返回摘要 + `approval_ref`。
- `health_summary` 只聚合影响判断质量的最小摘要。
- 本 issue 后端 only，前端接入后续另开 issue / change。
