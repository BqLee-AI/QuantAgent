## 背景

Runtime Inspect V1 面向 issue #222 的 API/OpenSpec 收口，不负责实现 runtime 逻辑本身。它的任务是把 Runtime Dashboard、AgentRun 详情、ToolInvocation 详情和后续 SchedulerRun 只读观察所需的对象、过滤维度、脱敏边界和失败语义定义清楚。

本设计以以下真源为依据：

- issue #222：定义 Runtime Inspect V1 的问题陈述、目标、非目标和验收。
- issue #218：前端 `/runtime` 页面只读观察面和局部失败要求。
- issue #226：`SchedulerRun` 与 `SourceBinding` 契约后续需要复用字段命名。
- issue #175：REST 为只读快照真源、Dashboard/前端不能自行发明 DTO。
- issue #43：实时通道只负责状态变化通知，不替代 REST 查询。
- `docs/design/08-api-and-websocket-design.md`
- `docs/design/09-frontend-architecture-design.md`
- `docs/prd/pages/07-runtime-dashboard.md`

## 目标与非目标

目标：

- 以资源优先方式定义 Runtime Inspect V1，只读查询按对象拆资源，而不是大而全的 dashboard 聚合接口。
- 定义共享过滤维度、跨资源追踪字段和 list / detail DTO 边界。
- 定义 health 摘要、局部 unavailable、错误 envelope 和脱敏规则。
- 定义 API/router、future service、repository/read provider 的职责边界。

非目标：

- 不实现任何业务代码、持久化模型、scheduler 动作或实时协议。
- 不定义完整数据库 schema 或 provider-specific 结构。
- 不替代 #226 对 `SchedulerRun` write/action 契约的收口。

## 分层与目录蓝图

后续实现建议按以下边界落地：

```text
apps/api/src/quantagent/api/
  schemas/
    runtime_inspect.py
  services/
    runtime_inspect_service.py
  repositories/
    runtime_inspect_repository.py
  routers/v1/
    runtime_health.py
    agent_runs.py
    tool_invocations.py
    scheduler_runs.py
    runtime_errors.py

packages/core/... 或其他 runtime package
  runtime_inspect/
    models.py
    services.py
    repositories.py
```

职责：

- `routers/v1/**`：只处理 HTTP 参数、分页、状态码、response envelope 和 DI。
- `schemas/runtime_inspect.py`：API request/response DTO，独立于 ORM 和内部对象。
- `services/runtime_inspect_service.py`：编排 list/detail 查询、partial unavailable 归一化、权限/capability 边界和脱敏。
- `repositories/runtime_inspect_repository.py`：只负责 read model 查询，不直接暴露 ORM shape 给 router。
- `packages/core` 或对应 runtime package：沉淀共享 read model、future repository port 和 provider seam；不让 `apps/api` 成为运行时状态真源。

之所以保留 `service` / `repository` seam，是因为本 change 涉及多对象只读 read model、partial unavailable 和脱敏，不适合把查询逻辑堆进 router。

## 资源路径

Runtime Inspect V1 采用“按主对象拆资源 + 共享过滤维度”：

```text
GET /api/v1/runtime/health

GET /api/v1/runtime/errors
GET /api/v1/runtime/errors/{error_id}

GET /api/v1/agents/runs
GET /api/v1/agents/runs/{run_id}

GET /api/v1/tools/invocations
GET /api/v1/tools/invocations/{invocation_id}

GET /api/v1/scheduler-runs
GET /api/v1/scheduler-runs/{run_id}
```

不采用 `/api/v1/runtime/inspect` 单接口，原因：

- `AgentRun`、`ToolInvocation`、`SchedulerRun`、`RuntimeError` 生命周期不同，DTO 不应被抹平。
- 详情页需要稳定 detail 资源，不能反向依赖 dashboard 聚合体。
- 局部失败语义必须可定位到具体资源，而不是整包失败。

## 共享过滤与关联字段

### 共享过滤维度

支持的共享过滤维度：

- `event_id`
- `trace_id`
- `plugin_id`
- `status`
- `time_from`
- `time_to`

按资源附加的可选过滤：

- `severity`：仅 `runtime/errors`
- `run_type`：仅 `agents/runs`
- `tool_id`
- `risk_level`：仅 `tools/invocations`
- `trigger_type`：仅 `scheduler-runs`
- `component`：仅 `runtime/errors`

分页：

- list 资源统一采用分页参数，例如 `page`、`page_size`
- `page_size` 必须有安全上限
- detail 资源不接受分页

### 关联字段真源

为保证跨页面追踪和 Runtime Dashboard 筛选一致，以下字段命名必须稳定：

- `event_id`：关联事件主对象
- `trace_id`：关联同一条处理链路
- `request_id`：API/request 级观测 id
- `correlation_id`：同一次运行链路的跨对象关联 id
- `plugin_id`：来源插件或工具所属插件
- `agent_run_id`：工具调用关联的 AgentRun
- `scheduler_run_id`：由调度触发时的 SchedulerRun 引用

`SchedulerRun` 若在 issue #226 后续 change 中定义更多字段，Runtime Inspect 只能复用命名或裁剪，不允许另起别名。

## DTO 草案

### RuntimeHealthSummary

```text
RuntimeHealthSummary
  active_agent_run_count: integer
  recent_failed_agent_run_count: integer
  recent_failed_tool_invocation_count: integer
  runtime_error_severity_summary:
    critical: integer
    warning: integer
    info: integer
  backend_status:
    api: "healthy" | "degraded" | "unavailable"
    scheduler: "healthy" | "degraded" | "unavailable" | "not_configured"
    worker: "healthy" | "degraded" | "unavailable" | "not_configured"
  websocket_status_hint: "connected" | "degraded" | "unknown"
  generated_at: datetime
```

约束：

- `RuntimeHealthSummary` 是结构化摘要，不暴露底层连接串、secret 或 provider 原始探针结果。
- `websocket_status_hint` 只表达观察提示，不把实时连接状态当业务真源。

### AgentRunSummary / AgentRunDetail

```text
AgentRunSummary
  run_id: string
  event_id: string | null
  trace_id: string | null
  correlation_id: string | null
  run_type: string
  status: string
  provider_policy: string | null
  model_used: string | null
  token_usage_summary: object | null
  cost_estimate_summary: object | null
  started_at: datetime | null
  ended_at: datetime | null
  duration_ms: integer | null
  error_summary: object | null

AgentRunDetail extends AgentRunSummary
  input_summary: object | null
  output_summary: object | null
  related_tool_invocation_refs: array
  scheduler_run_ref: object | null
```

约束：

- detail 只允许 `input_summary` / `output_summary`，V1 不开放 raw prompt、完整模型推理链或 provider 原始 payload。
- `token_usage_summary` 和 `cost_estimate_summary` 仅作为结构化摘要，不承诺账单真源语义。

### ToolInvocationSummary / ToolInvocationDetail

```text
ToolInvocationSummary
  invocation_id: string
  agent_run_id: string | null
  event_id: string | null
  trace_id: string | null
  correlation_id: string | null
  tool_id: string
  plugin_id: string | null
  risk_level: string | null
  status: string
  retry_count: integer
  started_at: datetime | null
  ended_at: datetime | null
  duration_ms: integer | null
  error_summary: object | null

ToolInvocationDetail extends ToolInvocationSummary
  input_summary: object | null
  output_summary: object | null
  approval_ref: object | null
```

约束：

- 工具输入输出默认只给脱敏摘要。
- 如需要更细粒度参数，必须由后续 capability / permission change 单独定义；V1 不开放 raw。

### SchedulerRunSummary / SchedulerRunDetail

```text
SchedulerRunSummary
  run_id: string
  binding_id: string | null
  plugin_id: string | null
  trigger_type: string
  status: string
  started_at: datetime | null
  ended_at: datetime | null
  duration_ms: integer | null
  error_summary: object | null

SchedulerRunDetail extends SchedulerRunSummary
  event_ref: object | null
  captured_count_summary: object | null
```

约束：

- Runtime Inspect 只定义 runtime 观察所需最小摘要字段。
- detail 字段命名必须与 future `source-binding-scheduler-run-api-contract-v1` 保持一致；如后者扩展字段，本 change 以兼容扩展为前提。

### RuntimeErrorSummary / RuntimeErrorDetail

```text
RuntimeErrorSummary
  error_id: string
  component: string
  severity: string
  status: string
  error_code: string
  error_message_summary: string
  provider: string | null
  provider_policy: string | null
  trace_id: string | null
  event_id: string | null
  plugin_id: string | null
  created_at: datetime

RuntimeErrorDetail extends RuntimeErrorSummary
  details_summary: object | null
  related_refs: object | null
```

约束：

- `error_message_summary` 和 `details_summary` 必须脱敏，不暴露 stack trace、secret、完整 prompt、连接串或本地路径。
- V1 只读，不定义 ack / ignore / resolve 动作。

## REST 真源与 partial unavailable

### REST 与实时通道关系

- REST 快照是业务状态真源。
- WebSocket 或其他实时通道只负责通知“有变化，建议 refresh”。
- detail 页和 Runtime Dashboard 初始化必须先读 REST。

### partial unavailable 语义

由于 Runtime Dashboard 会并发拉取多个资源，V1 需要区分：

- `empty`：资源可读，但当前无数据。
- `unavailable`：该资源读模型或下游 provider 暂不可用。
- `error`：请求本身失败，例如参数错误、权限不足、未知资源。

约束：

- 单个 list/detail 资源的失败不应强制要求 API 再提供大聚合兜底接口。
- `GET /api/v1/runtime/health` 可以聚合多来源摘要，但当某个来源不可用时，应返回受控 `degraded` / `unavailable` 摘要，而不是泄露内部异常。
- `404`、`401`、`403`、`422` 等仍走统一 API envelope；resource provider unavailable 走受控 service-unavailable 语义。

## 脱敏与安全边界

必须脱敏或禁止返回：

- 完整 prompt
- 完整模型推理链
- 工具原始敏感参数和原始输出
- secret、token、cookie、credential reference 的明文值
- provider 原始异常栈、连接串、本地文件路径
- 可能绕过 capability gate 的详细内部参数

允许返回：

- 结构化摘要字段，例如 `input_summary`、`output_summary`、`error_summary`
- provider/model 的受控名称
- token/cost 的摘要统计
- 与排障直接相关但已脱敏的 details

如果后续需要“展开更详细参数”，必须由单独 capability / permission change 收口，并保留后端二次校验。

## 与相关 issue 的衔接

- issue #218：前端 Runtime Dashboard 依据本 change 的资源拆分和 partial failure 语义实现 query 与状态视图。
- issue #226：`SchedulerRun` 命名与 detail 字段以其后续契约真源为准，本 change 只定义 runtime 观察子集。
- issue #175：延续“REST 是快照真源、前端不能自行发明 DTO”的原则。
- issue #43：实时通道继续只做刷新提示；本 change 不改现有实时协议方向。

## 验证策略

OpenSpec-only PR 必须：

- 运行 `openspec validate runtime-inspect-api-v1 --type change --strict --json`

后续实现 PR 最小验证应覆盖：

- list/detail 资源的成功响应 envelope 和 OpenAPI 契约。
- 共享过滤维度和资源特定过滤维度。
- `404` / `401` / `403` / provider unavailable / partial degraded 语义。
- summary/detail 脱敏断言。
- `SchedulerRun` 字段命名与后续契约变更的一致性检查。
