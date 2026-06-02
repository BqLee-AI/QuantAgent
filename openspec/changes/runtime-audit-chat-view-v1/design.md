## 背景与取舍

本 change 承接 #270。它不是重新定义 Runtime Inspect API，也不实现后端审计持久化；它只把 `/runtime` 的首版页面行为从 PR #257 的多面板 Runtime Dashboard 收敛为可审计的 Chat App 风格运行流。

已有真源之间存在一个产品形态冲突：

- `docs/prd/pages/07-runtime-dashboard.md` 与 `runtime-inspect-api-v1` 倾向于 health + 多资源列表，适合排障。
- #270 和产品反馈要求首屏更纯粹，像 chat / timeline 一样解释一次 Agent 判断，减少占位内容和技术对象堆叠。

本设计采用后者作为新的 `/runtime` 首屏方向，同时保留前者作为数据资源和后续诊断展开能力。也就是说，Runtime Inspect 资源仍然有价值，但页面首屏不再把它们全部铺成表格。

## 用户任务

Runtime audit chat V1 只服务三个任务：

- 从 event_id / trace_id / 最近运行中找到一次 Agent 判断过程。
- 顺着审计消息流理解系统为什么 discard、review 或 route。
- 在不暴露敏感 raw payload 的前提下查看关键结构化字段、错误和降级状态。

首个样例固定为 Router Agent / AI intake：

```text
industry.analysis.requested
  -> IndustryEventContextV1 built
  -> single-call structured model intake
  -> EventIntakeDecisionV1 validated
  -> decision: discard | review | route
  -> event.routed published
```

## 页面信息架构

### 首屏结构

```text
/runtime
  Header
    title: Runtime 审计
    compact health/status strip
    manual refresh
  FilterBar
    event_id
    trace_id
    decision
    status
    industry
    time range
  AuditConversation
    AuditMessageGroup[]
      source/request message
      context-build message
      model-intake message
      decision message
      publish / failure message
  DetailDrawer or InlineDisclosure
    selected message details
    trace context
    sanitized payload summary
```

首屏不再默认展示 AgentRun、ToolInvocation、SchedulerRun、RuntimeError 四张资源表。需要保留这些对象时，作为消息详情里的关联引用、折叠区或后续诊断入口。

### 审计消息类型

```text
RuntimeAuditMessage
  id: string
  group_id: string
  occurred_at: datetime | null
  actor_type: "source" | "worker" | "agent" | "model" | "event_bus" | "system"
  stage:
    "analysis_requested"
    "context_built"
    "model_invoked"
    "decision_validated"
    "event_routed_published"
    "discarded"
    "review_requested"
    "failed"
  status: "success" | "warning" | "error" | "pending" | "unavailable"
  title: string
  summary: string
  trace:
    event_id?: string
    trace_id?: string
    request_id?: string
    correlation_id?: string
    source_message_id?: string
    analysis_request_id?: string
    routed_event_id?: string
  decision?: "discard" | "route" | "review"
  priority?: "low" | "normal" | "high" | "urgent"
  badges[]:
    "degraded"
    "rss_summary_only"
    "schema_invalid"
    "provider_failed"
    "partial_unavailable"
  evidence_refs[]:
    field_path: string
    label: string
  safe_details: object | null
  related_refs[]:
    kind: "agent_run" | "tool_invocation" | "scheduler_run" | "runtime_error" | "event_topic"
    id: string
    label: string
```

`safe_details` 只能接收已脱敏摘要或结构化字段，不接收完整 API envelope、ORM object、provider raw response、完整 prompt、完整文章正文或 plugin instance。

### Router Agent 样例字段

Router Agent 消息必须能展示：

- 输入 topic：`industry.analysis.requested`
- 输出 topic：`event.routed`
- `decision`: `discard | review | route`
- `discard_reason`: spam、irrelevant、duplicate_hint、low_information、unsupported_language、malformed、not_discarded
- `industry_relevance[]`: industry_id、relationship、relevance_score、reason_summary
- `structured_news`: canonical_title、short_summary、entities、companies、technologies、products、source_facts、uncertainties
- `routing`: target_industries、target_topics、priority、requires_deep_analysis、requires_human_review
- `quality`: enrichment_status、content_completeness、confidence、noise_flags
- trace：message_id、source_message_id、binding_id、raw_event_id、correlation_id、causation_id

这些字段来自 `EventIntakeDecisionV1` / `IndustryEventContextV1` 语义，不从自然语言日志中反向解析。

## 数据来源与 API 取舍

### V1 可接受数据来源

后续实现可以二选一：

- 使用已有 Runtime Inspect / events / model invocation 只读资源组合出审计消息。
- 在生产 API 尚未稳定时，使用 `features/runtime` 内受控 fixture 或 mock read model 先验证页面形态。

如果采用 fixture，必须满足：

- UI 明确为 fixture / mock harness，不声称生产审计链路已完整可查。
- fixture 覆盖 route、discard、review、degraded、schema validation failure。
- fixture 不包含真实 secret、真实 raw prompt 或生产 payload。

### 不新增后端写入或控制

本 change 不新增后端 endpoint。若后续实现需要新增专用 read endpoint，例如：

```text
GET /api/v1/runtime/audit-messages
GET /api/v1/runtime/audit-messages/{group_id}
```

必须单独补 API/OpenSpec change，定义 router/service/repository、DTO、分页、脱敏、权限和 audit read model。前端实现不得先硬编码生产 endpoint。

## 前端目录蓝图

后续实现建议写入：

```text
apps/web/src/routes/_app/(workspace)/runtime/index.tsx

apps/web/src/features/runtime/
  README.md
  api/
    runtime-audit.api.ts
    runtime-audit.contracts.ts
    runtime-inspect.api.ts              # 可复用 PR #257 已有方向
    runtime-inspect.contracts.ts
  queries/
    runtime-audit.keys.ts
    use-runtime-audit-groups.ts
    use-runtime-audit-messages.ts
    use-runtime-health.ts               # 仅 compact status strip
  hooks/
    use-runtime-audit-page.ts
    use-runtime-audit-filters.ts
    use-runtime-audit-selection.ts
  components/
    page/
      RuntimeAuditPage.tsx
    filters/
      RuntimeAuditFilterBar.tsx
    conversation/
      RuntimeAuditConversation.tsx
      RuntimeAuditMessageGroup.tsx
      RuntimeAuditMessage.tsx
    details/
      RuntimeAuditDetailDrawer.tsx
      RuntimeAuditTracePanel.tsx
      RuntimeAuditSafeDetails.tsx
    states/
      RuntimeAuditEmptyState.tsx
      RuntimeAuditErrorState.tsx
      RuntimeAuditLoadingState.tsx
      RuntimeAuditPermissionState.tsx
    health/
      RuntimeCompactHealthStrip.tsx
  types/
    runtime-audit.types.ts
  utils/
    runtime-audit-format.ts
    runtime-audit-sanitize.ts
    runtime-audit-fixtures.ts            # 仅 fixture harness 使用
```

职责要求：

- route 只做 search params 校验和页面挂载，不创建 API、不写 query、不写 JSX 主体。
- `api/` 只封装 endpoint、params、response contracts；如果首版是 fixture，不得伪造生产 endpoint 名称。
- `queries/` 只封装 TanStack Query 和 query key，通过 runtime `apis` 访问业务 API。
- `hooks/` 组合筛选、选中消息、刷新和派生状态，不处理底层 HTTP。
- `components/` 只接收稳定 props，不能透传完整 API envelope。
- `utils/` 只做纯格式化、脱敏和 fixture 转换。
- `README.md` 必须说明 Runtime audit chat 负责什么、不负责什么、哪些组件不能展示 raw payload。

## PR #257 处理策略

实现前必须先审核 #257，并形成明确结论：

- 可复用：Runtime Inspect API contracts、query keys、query hooks、error / unavailable / permission state、REST snapshot 和脱敏字段。
- 需要替换：`RuntimeDashboardPage` 的多面板首屏、AgentRun / ToolInvocation / SchedulerRun / RuntimeError 四表首屏展示、长说明式占位文案。
- 可降级保留：health 摘要只能作为 compact status strip 或详情折叠，不作为首屏主体。

后续 PR 不能在主线上同时保留两个 `/runtime` 首屏方向。若继续使用 #257 分支，PR body 必须更新并说明页面层如何按本 change 改造；若另起 PR，应说明如何处理 #257。

## 安全与脱敏

Runtime audit chat 只能展示结构化摘要和证据引用：

- 允许：decision、confidence、reason summary、source facts、safe error summary、token/cost summary、trace id、request id、topic name、safe field refs。
- 禁止：完整 prompt、完整 chain-of-thought、provider raw response、secret、cookie、token、连接串、SQLAlchemy/ORM object、plugin instance、完整原始文章正文、未脱敏工具输入输出。

详情抽屉中如需要展示 payload-like 内容，必须经 `runtime-audit-sanitize.ts` 或后端等价脱敏结果处理。安全边界需要中文注释说明为什么不能直接展示 raw details。

## 状态与失败路径

- `loading`: 显示正在读取审计流，不用全局大 spinner 阻断筛选区。
- `empty`: 区分没有运行数据、当前筛选无结果、fixture 未启用。
- `permission denied`: 显示 capability / auth 失败和 request id。
- `partial unavailable`: 消息流仍可展示已有节点，并在缺失阶段显示 unavailable message。
- `provider/model failure`: 展示 safe error summary，不展示 provider raw exception。
- `schema validation failure`: 展示 validation failure 节点，并明确该 item 没有静默进入 route。
- `degraded input`: 对 RSS-summary-only / Readability failure 输入显示 degraded badge。

## 验证策略

OpenSpec 阶段：

- `openspec validate runtime-audit-chat-view-v1 --type change --strict --json`

实现阶段最小验证：

- `bun run --cwd apps/web test:unit -- runtime-audit`
- 覆盖 `runtime-audit-format`、`runtime-audit-sanitize`、filter params、Router Agent 三类 fixture。
- `bun run --cwd apps/web lint`
- 如果 route 或 runtime factory 有变化，跑 `bun run --cwd apps/web build`，并说明是否存在 main 上既有 build 阻断。

人工验收：

- Router Agent fixture 中 route、discard、review、degraded、schema invalid 五类结果能在同一审计流中区分。
- 首屏不能退回四张资源表格。
- 详情抽屉不能展示 raw prompt、CoT、provider raw response 或 secret。
