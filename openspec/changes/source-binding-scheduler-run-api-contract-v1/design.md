## Context

issue #226 处在四类真源的交汇处：

- `docs/design/06-source-plugin-design.md` 要求 pull source 由统一 Scheduler 按 `SourceBinding` 调度，插件不自管循环。
- `docs/design/07-industry-package-design.md` 要求行业包通过 `SourceBinding` 引用 source 插件，支持 required/optional 依赖与 template/override。
- `docs/design/08-api-and-websocket-design.md` 要求 API 以 REST 资源为主，副作用放入资源下的 `actions` 路径，实时通道只做刷新提醒而不做状态真源。
- `docs/prd/pages/11-plugin-detail.md` 要求 Source 类型和 Industry 类型插件详情页都能解释 SourceBinding 使用情况、运行错误和最近活动。

相邻 issue 已经把边界拆开：

- #215 收 `SourceBinding Template` 与 `Effective Config` 合成契约。
- #216 收 `SourceBinding` 与 `SchedulerRun` 的持久化模型。
- #217 收 scheduler 以 `SourceBinding` 为主对象的 interval loop。
- #220 收 SourceBinding 在 Plugin Detail 中的治理面展示边界。

本 change 只定义 HTTP / contract 层的 V1 真源，避免 API、前端和调度入口分别发明不同协议。它影响 `apps/api` 与 `packages/core`，因此必须同时满足 `api-architecture-gate.md` 和 `core-and-plugin-architecture-gate.md`：router 保持薄层，service 负责状态与动作编排，DTO 独立于 ORM / plugin DTO / effective config，且公开契约不得泄露 secret 或调度内部实现。

## Goals / Non-Goals

**Goals:**

- 定义 `SourceBinding` V1 的只读资源边界：列表、详情、关联最近 run 历史。
- 定义 `SchedulerRun` V1 的只读资源边界：列表、详情、按 binding 过滤与引用。
- 定义 binding 动作 `pause`、`resume`、`run-now` 的路径、返回、错误和幂等语义。
- 定义 V1 公开 DTO 分层，包括 list/detail/action response、过滤参数、状态枚举和脱敏规则。
- 约束后续实现的分层蓝图：router / schema / service / repository / scheduler entrypoint 的职责与调用方向。
- 约束 capability gate、审计记录、request id 和实时刷新边界，确保高风险动作可回放。

**Non-Goals:**

- 不定义 `SourceBinding Template` / `Effective Config` 的合成算法细节；该部分复用 #215。
- 不定义 ORM、migration、repository SQL、索引或持久化表结构；该部分复用 #216。
- 不定义 scheduler loop、并发窗口、retry/backoff/circuit breaker；该部分复用 #217。
- 不定义 Web UI 布局、前端 query key、组件拆分或 SourceBinding 编辑态；该部分复用 #220。
- 不在本次 V1 暴露 `retry`、`cancel`、`backfill`、批量 enable/disable 或诊断型大接口。

## Decisions

### 1. 资源按 `SourceBinding` / `SchedulerRun` 分开建模，动作附着在 binding 资源下

V1 公开的 REST 资源如下：

```text
GET  /api/v1/source-bindings
GET  /api/v1/source-bindings/{binding_id}
GET  /api/v1/source-bindings/{binding_id}/scheduler-runs

POST /api/v1/source-bindings/{binding_id}/actions/pause
POST /api/v1/source-bindings/{binding_id}/actions/resume
POST /api/v1/source-bindings/{binding_id}/actions/run-now

GET  /api/v1/scheduler-runs
GET  /api/v1/scheduler-runs/{run_id}
```

这样做的原因：

- `SourceBinding` 是配置、归属和运行控制的主对象，天然适合作为动作宿主。
- `SchedulerRun` 是 append-only 运行历史，天然适合作为只读资源，不应在 V1 直接承担控制动作。
- `docs/design/08-api-and-websocket-design.md` 已经要求副作用能力放在 `actions` 路径下，而不是混入 `PATCH` 或 ad hoc `/operate` 接口。

替代方案是做一个 `/scheduler` 或 `/source-bindings/operate` 大接口。该方案会把查询、动作和诊断混成单体协议，也会让 Plugin Detail 与 Runtime Inspect 难以复用稳定字段，因此不采用。

### 2. `SchedulerRun retry` 在本 change 中明确排除出 V1

issue #226 已将 `retry` 标记为待确认项，并建议默认仅预留占位。本 change 采用更严格的 V1 边界：

- `SchedulerRun` V1 只提供只读列表与详情。
- 不公开 `POST /api/v1/scheduler-runs/{run_id}/actions/retry`。
- `retry` 留给后续 change，在 scheduler 幂等、重放安全、actor 审计和 failure classification 收稳后单独定义。

这样做的原因：

- 当前真源还没有把 run replay 的幂等策略、RawEvent 去重、副作用回放和权限边界定义完整。
- 过早把 `retry` 公开成 API action，会让 API 契约强行承诺尚未稳定的调度行为。

替代方案是直接把 `retry` 做成 V1 动作。该方案会把 #217 与后续 RawEvent / Event Bus 边界提前耦合进本 change，因此不采用。

### 3. 公开 DTO 只暴露 summary/detail，不直接返回 `effective_config` 全量内容

V1 需要四类公开 DTO：

- `SourceBindingSummary`
- `SourceBindingDetail`
- `SchedulerRunSummary`
- `SchedulerRunDetail`

另有三类动作 response：

- `SourceBindingPauseAccepted`
- `SourceBindingResumeAccepted`
- `SourceBindingRunNowAccepted`

字段草案如下。

`SourceBindingSummary`：

- `id`
- `source_plugin_id`
- `source_plugin_name`
- `owner_type`
- `owner_id`
- `owner_name`
- `status`
- `blocked_reason`
- `schedule_summary`
- `last_run_ref`
- `next_run_at`
- `health_summary`
- `allowed_actions`

`SourceBindingDetail` 在 summary 基础上增加：

- `effective_config_summary`
- `config_version`
- `config_validation_status`
- `rate_limit_policy_summary`
- `retry_policy_summary`
- `last_error_summary`
- `audit_refs`
- `recent_run_refs`

`effective_config_summary` 只允许暴露：

- source-specific 非敏感摘要字段
- `secret_fields_masked`
- `last_validated_at`
- `config_source_refs`

禁止暴露：

- secret 明文
- source-specific 原始认证头
- 内部路径
- scheduler 运行时注入对象

`SchedulerRunSummary`：

- `id`
- `binding_id`
- `source_plugin_id`
- `trigger_mode`
- `status`
- `started_at`
- `finished_at`
- `duration_ms`
- `attempt_index`
- `captured_count`
- `failure_summary`

`SchedulerRunDetail` 在 summary 基础上增加：

- `request_id`
- `actor`
- `correlation_id`
- `binding_snapshot_ref`
- `output_summary`
- `error_code`
- `error_stage`
- `error_retryable`
- `audit_ref`

这样做的原因：

- API DTO 必须独立于 ORM model、plugin DTO 和内部领域对象。
- Plugin Detail 需要理解 binding/run 状态，但不应该看到完整 `effective_config`。
- list/detail 分层能避免列表页背着大量内部字段，也便于后续 `packages/contracts` 生成。

替代方案是把 `effective_config` blob 或 ORM shape 直接公开。该方案违背 root `AGENTS.md`、`api-architecture-gate.md` 和 `core-and-plugin-architecture-gate.md` 的分层要求，因此不采用。

### 4. list 与关联读取统一使用 cursor 风格，过滤字段保持显式

V1 的查询入口：

- `GET /api/v1/source-bindings?owner_type=&owner_id=&source_plugin_id=&status=&cursor=&limit=`
- `GET /api/v1/source-bindings/{binding_id}/scheduler-runs?status=&trigger_mode=&cursor=&limit=`
- `GET /api/v1/scheduler-runs?binding_id=&status=&trigger_mode=&started_after=&started_before=&cursor=&limit=`

决策：

- run 列表与 binding 关联 run 历史使用 cursor 分页，符合 `docs/design/08-api-and-websocket-design.md` 对事件/运行时类资源的建议。
- `source-bindings` 列表允许统一 cursor + limit，不引入 page/page_size 双轨。
- filter 字段只允许公开稳定维度：`status`、`owner_type`、`source_plugin_id`、`trigger_mode`、时间窗口，不公开内部调度索引字段。

替代方案是让每个查询自由选择 page/page_size 或 ad hoc filter blob。该方案会让前后端和后续 contracts 难以收敛，因此不采用。

### 5. 动作响应统一返回 accepted envelope，而不是等待调度完成

三个 binding action 都返回 `ApiResponse<T>`：

- `pause` / `resume` 返回动作已接受的 binding 状态摘要与 `audit_ref`
- `run-now` 返回动作已接受的 `binding_id`、`accepted_at`、`requested_run_ref`

`run-now` 不等待实际执行完成，原因：

- scheduler 执行可能较慢，HTTP 请求不应绑住运行时主流程。
- `docs/design/08-api-and-websocket-design.md` 已要求实时通道只负责状态变化提醒；客户端可以在 action accepted 后轮询或监听刷新。
- 这让 API 只承诺“命令已被接受并记录审计”，而不是承诺“执行已成功”。

替代方案是让 `run-now` 同步返回完整 `SchedulerRunDetail` 或执行结果。该方案会耦合 HTTP 生命周期与 scheduler/runtime 实现，也会放大超时与幂等问题，因此不采用。

### 6. 动作幂等语义按当前 binding 状态定义，router 只做传输层映射

后续实现必须遵循以下职责分层：

```text
apps/api routers/v1/source_bindings.py
  -> schemas/source_bindings.py
  -> core service: SourceBindingQueryService / SourceBindingActionService
  -> core repository interfaces / scheduler dispatch port
```

router 只负责：

- 读取 path/query/body DTO
- 注入 request context、actor、request id
- 调用 service
- 包装 `ApiResponse[T]`
- 把领域错误映射成 HTTP 状态码

service 负责：

- 校验 capability / permission
- 校验状态流转是否合法
- 生成审计动作
- 调用 scheduler dispatch port 或更新 binding 状态

幂等语义：

- 对已 `paused` 的 binding 再次 `pause` 返回成功 envelope，状态保持 `paused`，并可标识 `already_in_target_state=true`
- 对已 `active` 的 binding 再次 `resume` 返回成功 envelope，状态保持 `active`
- `run-now` 每次请求都必须产生独立 `request_id` 与审计记录；如果后续实现引入幂等 key，应在单独 change 中定义

替代方案是让 router 直接改表或直接调 scheduler app。该方案违反 API 薄层和 core 依赖方向要求，因此不采用。

### 7. capability、错误 envelope 与审计是 V1 强约束

所有查询与动作都必须走统一 envelope：

```text
ApiResponse<T>
  code
  data
  msg
  error
```

V1 约束：

- 所有响应必须带 `X-Request-ID`
- 错误 `error` 中必须回显 `request_id`
- capability 不足时返回统一的 permission-denied error code
- 非法状态流转返回专用 error code，例如 `SOURCE_BINDING_STATE_INVALID`
- binding 不存在 / run 不存在返回稳定 not-found error code
- source plugin 不可运行、config invalid、dependency blocked 等错误必须结构化表达，不能返回自由文本堆栈
- 所有动作都必须产生日志与审计记录，至少包含 `actor`、`action`、`target_type`、`target_id`、`result`、`request_id`

这样做的原因：

- root `AGENTS.md` 和 gates 都要求高风险动作可审计、错误可枚举、日志脱敏。
- Plugin Detail 和后续 Runtime Inspect 需要稳定解释 blocked reason 与 last error。

### 8. 实时通道只发送刷新提醒，不扩展业务真源

本 change 不新增 WebSocket 契约 requirement，但明确与实时通道的关系：

- binding 状态变化或 run 状态变化可以在后续通过 topic 通知前端刷新
- REST 列表/详情仍是状态真源
- action response 不依赖实时消息才能判定是否 accepted

这样做的原因是保持 `docs/design/08-api-and-websocket-design.md` 的核心原则，避免前端或运维台把 socket 消息误当作 binding/run 的主事实来源。

## Risks / Trade-offs

- [Risk] `SourceBindingDetail` 摘要字段过少，后续前端仍可能申请更多字段。
  -> Mitigation：先按 Plugin Detail V1 的只读需求收口摘要字段，新增字段必须走后续 change，不允许临时把内部对象透传。

- [Risk] 不做 `retry` 可能让运维入口初期只能查看失败 run，不能立即重放。
  -> Mitigation：本 change 明确只收只读与基础动作，后续在 scheduler 幂等边界稳定后独立开 change。

- [Risk] `run-now accepted` 与执行结果分离后，调用方需要额外刷新或监听。
  -> Mitigation：这是刻意的协议取舍，用更清晰的 accepted 语义换取更稳定的异步执行边界。

- [Risk] owner 维度未来可能扩展到 industry package 之外。
  -> Mitigation：DTO 公开 `owner_type` / `owner_id`，但 V1 仅承诺现有受支持 owner 的可读语义，具体枚举扩展由后续 change 控制。

- [Risk] 当前设计没有把 Web 目录、query key 或 OpenAPI 生成文件写进本 change。
  -> Mitigation：这是 OpenSpec-only PR，保持只定义 API/core 合约；前端文件规划由 #220 对齐同一资源契约再展开。
