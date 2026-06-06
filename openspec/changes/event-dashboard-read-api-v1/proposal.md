## Why

截至 2026-06-05，后端已经具备 API v1 protected registration、Cookie Session Auth、`ApiResponse[T]` envelope、RawEvent、`event_intake` routed-event、Runtime Inspect / Audit、Approval persistence / API、AgentRun 和 ToolInvocation 等相邻能力，但仍没有标准 `GET /api/v1/events`、`GET /api/v1/events/{event_id}` 和 `GET /api/v1/dashboard/summary`。

如果继续让 RawEvent、Runtime Audit、Approval 或 AgentRun 这些采集 / 审计 / 运行时视角各自承担事件页数据来源，后端契约会漂移，后续管理台也会被迫自行拼装 DTO。#175 现在只收后端：建立标准 Event read model 与 Dashboard 聚合 API V1，作为后续 Web 接入真实 REST 快照的真源。

## What Changes

- 在 `packages/core` 中新增标准 Event V1 read model 边界，采用 `events` 当前状态表与 append-only `event_state_transitions` 状态流转表。
- 明确 RawEvent、`event_intake` routed-event 与标准 Event 的关系：
  - RawEvent 是采集与审计事实。
  - `event_intake` routed-event 是 AI intake / routing 输出。
  - 标准 Event 是管理台业务事件 read model 真源。
- 在 `apps/api` 中新增受保护只读 REST API：
  - `GET /api/v1/events`
  - `GET /api/v1/events/{event_id}`
  - `GET /api/v1/dashboard/summary`
- `GET /api/v1/events` 支持 `time_range`、`industry`、`credibility`、`analysis_status`、`source_type`、`sort`、`cursor`、`limit`，并返回列表项、分页游标、当前筛选回显和首版 `summary_buckets`。
- 首版 `summary_buckets` 只覆盖 PRD 必需项：`new_count`、`featured_count`、`analyzing_count`、`failed_or_review_count`，可选 `pending_approval_count`；不做复杂行业分布、来源分布或趋势环比。
- `GET /api/v1/events/{event_id}` 返回事实、评分、行业影响、最佳动作摘要、审批引用、运行摘要、证据摘要、降级提醒和审计引用；`best_action` 只返回摘要与 `approval_ref`，不返回完整 `DecisionResult`。
- `GET /api/v1/dashboard/summary` 返回 `featured_events`、`approval_summary`、`health_summary`、`entry_metrics` 分区；每个分区可独立表达 `ok`、`empty`、`unavailable` 或 `error`，避免局部依赖失败拖垮整个 summary。
- `health_summary` 首版只聚合影响判断质量的最小摘要：`status` 与 `items[]`，item 包含 `kind`、`severity`、`title`、`summary`、`affected_event_id`、`request_id`、`trace_id`、`runtime_ref`。
- 所有 API 响应使用现有 `ApiResponse[T]` envelope，并通过 `STANDARD_API_V1_ROUTER_REGISTRATIONS` protected boundary 注册。
- 本 change 只生成后端 OpenSpec 契约与实现蓝图；前端页面接入、TanStack Query、mock 迁移、Web 目录拆分和 Web 测试由后续 issue / change 承接。

## Capabilities

### New Capabilities

- `event-dashboard-read-api-v1`: 覆盖标准 Event read model、Events list/detail API、Dashboard summary API、Dashboard 分区降级语义、API envelope / protected boundary、脱敏与非交易执行边界。

### Modified Capabilities

- 无。现有 RawEvent、Runtime Inspect / Audit、Approval、AgentRun 和 ToolInvocation 能力作为输入或相邻只读视角复用，本 change 不修改它们的 stable requirement。

## Impact

- 影响路径：
  - `packages/core/**`：新增标准 Event domain/read model、ORM、repository/service、migration 和 core tests。
  - `apps/api/**`：新增 Events / Dashboard API DTO、API service、v1 router、protected registration、OpenAPI/runtime tests 和 README 说明。
  - `openspec/changes/event-dashboard-read-api-v1/**`：本 change 的 proposal、design、spec 和 tasks。
- 不影响路径：
  - `apps/web/**` 不在本 issue 内修改。
  - `packages/agent/**` 不在本 issue 内修改。
  - 不新增 static OpenAPI artifact、TypeScript client、Zod schema 或 `packages/contracts` 生成产物，除非后续 issue 单独要求。
- 风险边界：
  - 标准 Event read model 不能被 RawEvent API、Runtime Audit news API 或 Agent Debug SSE 冒充。
  - Dashboard REST summary 不能用 sample/mock 静默填充为真实业务数据；未接通分区必须受控返回 `unavailable`、`empty` 或 `error`。
  - `best_action` 和评分字段只能表达分析建议与审批入口，不能表达真实执行成功、交易授权依据或绕过 Decision / Policy Gate。
