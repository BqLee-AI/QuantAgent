## 1. 实现前真源与边界确认

- [x] 1.1 确认实现分支基于最新 `origin/main`，读取 issue #280 正文与全部评论，尤其是 `/events` 只展示 routed 事件、语义字段默认中文、不要新增中文 `display` 层的修正。
- [x] 1.2 读取并对照本 change 的 `proposal.md`、`design.md`、三份 specs，以及 `AGENTS.md`、`apps/web/AGENTS.md`、`apps/api/AGENTS.md`、`apps/worker/AGENTS.md`、`packages/core/AGENTS.md`。
- [x] 1.3 读取 `.agents/skills/references/engineering-quality-gate.md`、`openspec-chinese-artifact-gate.md`、`web-architecture-gate.md`、`web-file-responsibility-and-feature-structure.md`、`api-architecture-gate.md`、`core-and-plugin-architecture-gate.md`，并把目录/文件职责落实到实现计划。
- [x] 1.4 盘点当前真实实现：`event_intake_decision.v1`、`event_intake_routed_events`、`RuntimeAuditNewsQueryService`、`features/runtime/components/agent/*`、`features/events/event-center`、`features/events/event-detail`、`features/event-audit`，确认哪些可复用、哪些必须退出生产路径。

## 2. 后端 Events API 与权限

- [x] 2.1 新增 `event.inspect` capability，更新 API auth capability 常量、development actor 默认能力、前端 route policy 或 capability 定义，并补权限测试。
- [x] 2.2 新增 `apps/api/src/quantagent/api/schemas/events.py`，定义 `EventListResponse`、`EventListItemResponse`、`EventDetailResponse`、`EventAgentStageResponse`、Router output detail response、trace refs、timeline、安全详情、分页和筛选 DTO；DTO 不引用 ORM。
- [x] 2.3 新增 `apps/api/src/quantagent/api/services/events.py`，从 `event_intake_routed_events` 出发聚合 RawEvent/capture/scheduler 摘要，默认仅返回 `route|review`，显式筛选才返回 `discard`。
- [x] 2.4 在 core repository 中补充必要的 routed event 查询方法，例如按 decision/time cursor 分页、按 raw_event_id 查 latest、按 routed_event_id 查 output；查询必须有 limit、排序和必要索引利用，不做无界 `.all()`。
- [x] 2.5 新增 `apps/api/src/quantagent/api/routers/v1/events.py`，保持 router 薄层，只做参数、DI、`event.inspect`、`ApiResponse` 和错误映射。
- [x] 2.6 更新 `routers/v1/register.py` 注册 events router，确保 OpenAPI envelope、tags 和受保护路由行为正确。
- [x] 2.7 API 列表响应不得返回完整正文、raw payload、完整 Router `output_json`、provider raw response、prompt、CoT、secret、ORM object 或 plugin instance。
- [x] 2.8 API 详情 endpoint 返回单条已路由新闻业务摘要、Router Agent stage、trace refs 和安全详情；完整 Router output JSON 通过按需 detail endpoint 获取。
- [x] 2.9 API tests 覆盖：route/review 默认返回、discard 显式筛选、无 routed record 不返回、列表无敏感字段、detail output 按需、`event.inspect` 权限、`runtime.inspect` 不能替代 `event.inspect`、筛选和分页。

## 3. Router Agent v2 与 Worker 持久化

- [x] 3.1 在 `packages/core/src/quantagent/core/event_intake/decision.py` 或等价边界新增 `EVENT_INTAKE_DECISION_SCHEMA_VERSION_V2`、v2 dataclass/parser/validator，并保留 v1 parser/mapper。
- [x] 3.2 更新 Router Agent prompt/context 组装，明确用户可读语义字段默认中文；机器 enum/code 保持英文；不得要求模型输出 `display` 文本对象。
- [x] 3.3 更新 fake provider fixtures 和 schema-invalid fallback，覆盖 v2 route/review/discard、direct/indirect/contextual relevance、degraded RSS-summary-only、over-budget excerpt、中文语义字段和英文机器 code。
- [x] 3.4 更新 `SingleCallEventIntakeRunner` 或其 provider port，使 v2 仍保持每篇文章最多一次模型调用，不新增 tool-call loop、多轮调用、二次抓取或模型分块总结。
- [x] 3.5 更新 `event_intake/persistence.py` 的 key fields mapper，持久化 v2 中文 title/summary、event type、tags、priority、target industries/topics、relationship、confidence、review/deep-analysis flags 和 schema validation status。
- [x] 3.6 确认 `output_json` 持久化仍只保存 JSON-safe structured output，不保存 provider raw response、prompt、CoT、secret、完整正文或 raw payload；必要时补脱敏/大小保护和中文注释。
- [x] 3.7 Worker tests 覆盖 `industry.analysis.requested -> event.routed -> event_intake_routed_events`，确认 v2 persisted record、v1 compatibility、schema invalid fallback、幂等写入和 provider invocation count。
- [x] 3.8 Core tests 覆盖 v2 validation consistency：discard reason、route target、review uncertainty、degraded marker、中文语义字段存在、机器 code 稳定。

## 4. Shared Agent Audit 前端边界

- [x] 4.1 新增 `apps/web/src/features/agent-audit/README.md`，说明职责、公开入口、展示模型、子目录职责、安全边界、不负责后端请求、不负责业务 API mapping、不渲染 provider raw response/full article。
- [x] 4.2 新增 `features/agent-audit/types/agent-audit.types.ts`，定义 `AgentAuditSubject`、`AgentAuditStage`、key field、trace ref、status、stage kind 等稳定展示模型。
- [x] 4.3 新增或迁移 `AgentStagePanel`、`AgentStageDetailModal`、`AgentKeyFields`、`AgentJsonView`、`AgentTraceRefs` 和 states 组件；组件只接展示模型，不接 `ApiResponse`、runtime 私有 DTO 或 ORM。
- [x] 4.4 新增 `features/agent-audit/utils/agent-audit-format.ts` 与 `agent-audit-sanitize.ts`，集中处理 label、status tone、safe JSON 和敏感字段兜底。
- [x] 4.5 为 shared Agent audit 组件补单测，覆盖 Router Agent output JSON、unavailable/masked 状态、key fields、trace refs 和不渲染敏感字段。

## 5. Events 前端真实 API 接入

- [x] 5.1 重组 `apps/web/src/features/events/README.md`，说明 `/events` 是已路由新闻事件业务入口，不负责 runtime 排障、审批执行、mock scoring 或 RawEvent pending inbox。
- [x] 5.2 新增 `features/events/api/events.api.ts` 和 `events.contracts.ts`，封装 `/api/v1/events`、detail、Agent stage/output detail endpoint；使用 `BaseApi`，不在组件里裸 fetch。
- [x] 5.3 新增 `features/events/queries/events.keys.ts`、`use-event-list.ts`、`use-event-detail.ts`、`use-event-agent-stage.ts`，通过 `useApis()` 读取稳定 API 实例。
- [x] 5.4 新增 `features/events/hooks/use-event-filters.ts`、`use-event-list-page.ts`、`use-event-detail-page.ts`，组合筛选、分页、选中项、权限态、错误态和 Agent detail modal 状态。
- [x] 5.5 实现 `features/events/components/page/EventListPage.tsx`、filters、event list、states；列表主对象为已路由新闻事件，默认 route/review，discard 仅显式筛选。
- [x] 5.6 实现 `features/events/components/page/EventDetailPage.tsx` 与 `EventAuditPage.tsx`，展示新闻事实、Router Agent stage、关键语义字段、timeline、trace refs、安全详情，并复用 `features/agent-audit` 弹窗查看完整 output JSON。
- [x] 5.7 更新 route 文件：`/events`、`/events/all`、`/events/$eventId`、`/events/$eventId/audit` 只做 TanStack Router 入口、search/path params 和页面组合。
- [x] 5.8 移除生产路径对 `event-scoring` mock、`event-audit` mock 和 runtime fixture 的依赖；fixture 仅保留在 tests/debug/demo，并在 README 标注边界。
- [x] 5.9 Web tests 覆盖 Events API contract mapper、query params、default decision filter、discard explicit filter、not found/unavailable、Router output modal、JSON view、安全字段、route policy。

## 6. Runtime 收敛与复用

- [x] 6.1 将 `features/runtime/components/agent/*` 迁移或包裹到 `features/agent-audit`，runtime page 通过 mapper 转换为 shared `AgentAuditSubject/Stage`。
- [x] 6.2 更新 `features/runtime/README.md`，明确 `/runtime` 看“为什么没有形成事件”：RawEvent captured/pending、AI unavailable、模型失败、Kafka/worker/scheduler 排障；业务事件阅读入口是 `/events`。
- [x] 6.3 Runtime UI 可保留 Router Agent output 排障展示，但不得复制 `/events` 的业务筛选、阅读顺序或 mock 业务结果。
- [x] 6.4 Runtime tests 更新 shared component import 和 mapper，覆盖 pending/unavailable 仍在 `/runtime`、已 routed 可跳转 `/events/{raw_event_id}`。

## 7. 验证与收口

- [x] 7.1 运行 `openspec validate event-page-router-agent-audit-v2 --type change --strict --json`。
- [x] 7.2 运行 API targeted tests：events router/service、auth capability、OpenAPI envelope；必要时 `cd apps/api && uv run python -m unittest discover -s src`。
- [x] 7.3 运行 core/worker targeted tests：Router v2 schema、single-call fake provider、persistence key fields、analysis request handler。
- [x] 7.4 运行 Web targeted unit tests：events、agent-audit、runtime mapper、route policy；并运行 `bun run --cwd apps/web lint` 和 `bun run --cwd apps/web build`。
- [x] 7.5 使用 seeded RawEvent + EventIntakeRoutedEvent 或真实 RSS backtest 数据做 smoke：确认 `/events` 能看到 Router Agent 输出，未 routed 新闻只在 `/runtime` 排障视图出现。
- [x] 7.6 检查 `rg "event-scoring|event-audit.mock|runtime-audit-fixtures" apps/web/src/features/events apps/web/src/routes/_app/\\(workspace\\)/events`，确认生产 events 路径不再依赖 mock。
- [ ] 7.7 PR 说明写清 issue #280、OpenSpec change、为什么不做 `display` 字段、为什么 `/events` 只展示 routed、验证结果、未验证风险和后续 MainAgent 非目标。
