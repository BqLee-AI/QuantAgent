## ADDED Requirements

### Requirement: Standard Event read model SHALL be the Events API source of truth
系统 SHALL 以标准 Event read model 作为管理台 `/api/v1/events` 与 `/api/v1/events/{event_id}` 的业务真源，并将 RawEvent、`event_intake` routed-event、Runtime Audit、Approval、AgentRun 和 ToolInvocation 作为引用或摘要输入，而不是让这些相邻视角冒充标准 Event。

#### Scenario: Events API reads from standard Event model
- **WHEN** 已认证调用方请求 `GET /api/v1/events`
- **THEN** API 返回来自标准 Event read model 的事件列表
- **AND** 列表项包含标准 `event_id`、事实摘要、当前状态、分析状态、评分摘要、行业摘要和 trace 引用
- **AND** API 不把 RawEvent API、Runtime Audit news API、Agent Debug SSE 或前端 mock 作为 `/events` 的业务状态真源

#### Scenario: Event references source and routed facts
- **WHEN** 标准 Event 由 RawEvent 和 routed-event 输入形成
- **THEN** Event read model 保留 `raw_event_ref`、`routed_event_ref`、`trace_id` 或 `correlation_id` 等追踪引用
- **AND** RawEvent 仍表达采集事实，routed-event 仍表达 AI intake / routing 输出
- **AND** 标准 Event 当前状态和管理台摘要由 Event read model 提供

### Requirement: Event state transitions SHALL be append-only
系统 SHALL 新增或维护 `event_state_transitions` append-only 状态流转记录，用于事件详情状态摘要、审计追踪和后续回放；历史状态不得被覆盖更新。

#### Scenario: State change appends transition
- **WHEN** 标准 Event 当前状态从一个状态变更到另一个状态
- **THEN** 系统更新 `events.current_status` 与 `updated_at`
- **AND** 系统追加一条 `event_state_transitions` 记录，包含 `event_id`、`from_status`、`to_status`、原因摘要、actor 或模块、request / trace 引用和 `created_at`
- **AND** 当前状态更新与 transition 追加在同一事务边界内完成

#### Scenario: State history is recoverable
- **WHEN** 后端查询某个 `event_id` 的详情状态摘要
- **THEN** 系统可以按 `created_at` 与稳定 id 顺序恢复该事件状态流转摘要
- **AND** 历史 transition 不通过 update 覆盖
- **AND** 未知或不完整的上游阶段以受控降级摘要表达，而不是删除或改写历史 transition

### Requirement: Event materializer SHALL populate the standard Event read model
系统 SHALL 通过 core materializer 或等价 service seam 将 RawEvent、`event_intake` routed-event、analysis summary、approval ref 和 runtime summary 写入标准 Event read model；Events API 不得在读取时临时组合相邻表冒充标准 Event。

#### Scenario: Materialize Event from source and routed facts
- **WHEN** RawEvent capture 或 `event_intake` routed-event 已经持久化
- **THEN** core materializer 生成或更新对应标准 Event read model
- **AND** materializer 保留 RawEvent / routed-event 引用、事实摘要、routing 摘要、trace 引用和受控降级信息
- **AND** materializer 不依赖 FastAPI、API DTO、前端类型或具体插件实现
- **AND** materializer seam 可以被 core 单元测试直接调用，不要求 #175 新增 worker、scheduler loop 或事件消费框架

#### Scenario: Materializer is idempotent by stable identity
- **WHEN** 相同 RawEvent、routed-event 或 analysis summary 因重试被重复 materialize
- **THEN** 系统通过稳定 `identity_kind` / `identity_value` 找到同一个标准 Event
- **AND** 非空 `raw_event_id` 或 `routed_event_id` 与标准 Event 的关系保持唯一，或使用数据库方言等价唯一约束实现
- **AND** 唯一冲突后 repository 重读既有 Event 并合并摘要，不创建第二条标准 Event
- **AND** 没有 `raw_event_id`、`routed_event_id` 或显式稳定外部 identity 的输入不得创建随机 Event

#### Scenario: Materialization appends transition on status change
- **WHEN** materializer 导致标准 Event 当前状态变化
- **THEN** repository 在同一事务内更新 `events.current_status` 并追加 `event_state_transitions`
- **AND** transition 包含状态变化原因、actor 或模块、source ref、request id 或 trace id
- **AND** 失败时不得用 mock 或 sample provider 补齐标准 Event 数据

#### Scenario: Concurrent or duplicate state updates are controlled
- **WHEN** 多个 materializer、analysis、approval 或 runtime 摘要并发更新同一标准 Event
- **THEN** repository 按 `event_id` 使用 row lock、version 条件更新或等价机制串行化状态写入
- **AND** 相同 `to_status` 与相同 `source_ref` / `request_id` 的重试写入为幂等 no-op 或返回既有 transition
- **AND** 状态不得无序回退，除非 `reason_code` 明确表达人工复核、重新分析或回滚语义
- **AND** `events.current_status` 与 `event_state_transitions` history 保持一致

#### Scenario: Historical backfill is explicit follow-up
- **WHEN** 仓库已有历史 RawEvent 或 routed-event 需要补入标准 Event
- **THEN** #175 默认不执行自动 backfill
- **AND** 批量补历史数据需要后续 issue / change 定义分批、幂等和回滚策略

### Requirement: Events list API SHALL support V1 filters sorting pagination and buckets
系统 SHALL 暴露受保护的 `GET /api/v1/events`，支持 V1 查询参数、稳定排序、cursor 分页、筛选回显和首版 summary buckets。

#### Scenario: List events with filters and pagination
- **WHEN** 已认证调用方请求 `GET /api/v1/events` 并传入 `time_range`、`industry`、`credibility`、`analysis_status`、`source_type`、`sort`、`cursor` 或 `limit`
- **THEN** API 返回 `ApiResponse` envelope
- **AND** `data.items` 是 cursor-paginated Event list items
- **AND** `data.next_cursor` 表示下一页游标或为空
- **AND** `data.filters` 回显规范化后的当前筛选条件
- **AND** `time_range` 固定接受 `today`、`24h`、`7d`、`30d`，默认 `24h`
- **AND** `industry` 使用 repeated query parameter 并在 `data.filters.industry` 回显为 string array
- **AND** `credibility` 固定接受 `high`、`medium`、`low`、`conflict`、`unknown`
- **AND** `analysis_status` 固定接受 `pending`、`analyzing`、`scored`、`decision_ready`、`pending_approval`、`failed`、`review_required`、`unavailable`
- **AND** `source_type` 固定接受 `rss`、`api`、`webhook`、`manual`、`unknown`
- **AND** `limit` 默认 `20`，最大 `100`，超过最大值时按 API 参数校验返回错误 envelope
- **AND** 查询逻辑位于 API service / core service / repository 边界，不位于 router

#### Scenario: Summary buckets cover V1 product essentials
- **WHEN** `GET /api/v1/events` 返回列表响应
- **THEN** `data.summary_buckets` 至少包含 `new_count`、`featured_count`、`analyzing_count` 和 `failed_or_review_count`
- **AND** `pending_approval_count` 可以作为 V1 可选字段返回
- **AND** V1 不要求行业分布、来源分布、趋势环比或复杂 BI 统计

#### Scenario: Sort modes are stable
- **WHEN** 调用方使用 `sort=mixed`、`sort=latest` 或 `sort=priority`
- **THEN** 后端返回稳定排序结果，并用 `event_id` 或等价稳定字段打破平手
- **AND** `latest` 优先使用发布时间或采集时间
- **AND** `priority` 优先使用 Event read model 中的优先级摘要
- **AND** `mixed` 的最新 + 高价值混合排序在 core / service 层定义，不在 router 中临时计算

### Requirement: Event detail API SHALL expose decision-page summaries
系统 SHALL 暴露受保护的 `GET /api/v1/events/{event_id}`，返回事件详情 / 决策页所需的事实、评分、行业影响、最佳动作、审批、运行、证据、降级和审计摘要。

#### Scenario: Read Event detail summary
- **WHEN** 已认证调用方请求存在的 `GET /api/v1/events/{event_id}`
- **THEN** API 返回 `ApiResponse` envelope
- **AND** `data` 至少包含 `fact_summary`、`score_summary`、`industry_impact`、`best_action`、`approval_ref`、`runtime_summary`、`evidence_summary`、`degradation_notices`、`audit_refs` 和 `state_summary`
- **AND** 响应不直接返回 ORM model、core domain object、provider raw response 或完整模型推理链

#### Scenario: Best action is summary only
- **WHEN** Event detail 返回 `best_action`
- **THEN** `best_action` 只包含 `title`、`action_hint`、`recommendation_score`、`confidence`、`risk_level`、`risk_direction`、`approval_ref`、`status` 或 `unavailable_reason`
- **AND** API 不返回完整 `DecisionResult`、完整 Policy Gate payload、完整 prompt、完整推理链、broker credential 或真实交易执行结果
- **AND** `approval_ref` 只表达审批入口或关联引用，不表达真实执行完成

#### Scenario: Unknown Event returns structured not found
- **WHEN** 已认证调用方请求不存在的 `event_id`
- **THEN** API 返回 404 错误 envelope
- **AND** 错误 payload 包含 `error.request_id`
- **AND** 响应不暴露数据库查询细节、内部路径、连接串、secret 或 traceback

### Requirement: Dashboard summary API SHALL provide independently degradable sections
系统 SHALL 暴露受保护的 `GET /api/v1/dashboard/summary`，返回 Dashboard 首屏需要的 `featured_events`、`approval_summary`、`health_summary` 和 `entry_metrics` 分区；每个分区 SHALL 独立表达 `ok`、`empty`、`unavailable` 或 `error`。

#### Scenario: Dashboard summary returns featured events and metrics
- **WHEN** 已认证调用方请求 `GET /api/v1/dashboard/summary`
- **THEN** API 返回 `ApiResponse` envelope
- **AND** `featured_events` 来自标准 Event read model
- **AND** `entry_metrics` 至少包含新事件数、重点事件数、分析中事件数、分析失败或待复核事件数，并可包含待审批事件数
- **AND** `approval_summary` 复用现有 Approval 持久化或查询边界，只返回待处理数量、即将过期数量和摘要条目
- **AND** `health_summary` 只返回影响判断质量的最小摘要，不要求 Runtime / AgentRun / ToolInvocation 全量详情
- **AND** Dashboard summary 不从 WebSocket、前端 mock、Runtime Audit fixture 或 API sample provider 获得业务主状态

#### Scenario: Dashboard sections degrade independently
- **WHEN** Approval 或 Runtime 相关依赖不可用
- **THEN** 在认证和请求校验成功时，API 返回 HTTP 200 + 成功 `ApiResponse` envelope
- **AND** 对应 `approval_summary` 或 `health_summary` 分区返回 `unavailable` 或 `error`
- **AND** `featured_events` 和 `entry_metrics` 仍可在 Event read model 可用时返回 `ok` 或 `empty`
- **AND** 单个分区失败不会导致整个 Dashboard summary 响应失败，除非基础认证、请求校验、数据库 session 或 Dashboard service 本身不可恢复
- **AND** 局部失败只体现在 section `status`、`reason` 和 `updated_at` 中，不把整体 `ApiResponse.code` 改为失败

#### Scenario: Event read model unavailable does not hide independent sections
- **WHEN** Event read model 查询不可用，但基础认证和请求解析成功
- **THEN** API 返回 HTTP 200 + 成功 `ApiResponse` envelope
- **AND** `featured_events` 与 `entry_metrics` 分区返回 `unavailable` 或 `error`
- **AND** `approval_summary` 与 `health_summary` 仍尽量返回真实摘要或各自的 `empty`、`unavailable`、`error` 状态
- **AND** API 不用 RawEvent、Runtime Audit fixture、WebSocket 或 sample provider 静默填充 Event 分区

#### Scenario: Health summary is minimal quality-impact summary
- **WHEN** Dashboard summary 返回 `health_summary`
- **THEN** `health_summary` 包含整体 `status` 与 `items[]`
- **AND** 每个 item 至少可表达 `kind`、`severity`、`title`、`summary`、`affected_event_id`、`request_id`、`trace_id` 和 `runtime_ref`
- **AND** V1 只聚合影响判断质量的 runtime health、runtime errors、tool / agent failure 摘要
- **AND** V1 不把完整 Runtime dashboard、完整 Runtime errors 列表、AgentRun 详情或 ToolInvocation 详情搬进 Dashboard summary

### Requirement: Event and Dashboard APIs SHALL use protected ApiResponse V1 boundary
系统 SHALL 通过现有 API v1 protected registration 暴露 Events 与 Dashboard routes，并对成功和错误响应使用统一 `ApiResponse[T]` envelope。

#### Scenario: Anonymous access is rejected
- **WHEN** 匿名调用方请求 `GET /api/v1/events`、`GET /api/v1/events/{event_id}` 或 `GET /api/v1/dashboard/summary`
- **THEN** API 返回统一 401 错误 envelope
- **AND** 错误 payload 包含 `error.request_id`
- **AND** route 通过 `STANDARD_API_V1_ROUTER_REGISTRATIONS` protected boundary 注册

#### Scenario: OpenAPI shows envelope response models
- **WHEN** 调用方读取 `/openapi.json`
- **THEN** 新增 routes 的成功响应建模为 `ApiResponse[T]`
- **AND** route tags 能区分 events 与 dashboard 资源
- **AND** API DTO 独立于 ORM model、core read model 和内部 repository shape

#### Scenario: Responses are redacted
- **WHEN** Events 或 Dashboard API 返回成功或错误响应
- **THEN** 响应不暴露 secret、真实 token、私有策略、完整模型推理链、完整 prompt、数据库连接串、本地 runtime 路径、broker credential 或 provider raw response
- **AND** 评分字段不得命名或描述为执行通过率、交易授权依据或真实收益胜率
- **AND** `best_action_summary`、`industry_impact_summary`、`evidence_summary` 或等价 JSON 摘要字段只返回可公开摘要、引用和降级原因

### Requirement: Implementation SHALL preserve API and core layering
系统 SHALL 将 Event / Dashboard 的核心查询、排序、状态摘要、summary buckets 和局部分区降级放在 service / repository 边界内，router 只处理 HTTP 参数、依赖注入、状态码、envelope 和错误映射。

#### Scenario: Router remains thin
- **WHEN** 实现新增 `events` 或 `dashboard` router
- **THEN** router 不直接调用 `session.execute()`、不直接查询 ORM、不计算评分、不写状态流转、不拼接 Dashboard 分区业务逻辑
- **AND** router 只调用 API service 并返回 `ApiResponse[T]`

#### Scenario: Core does not depend on API or frontend
- **WHEN** 实现新增 core Event read model、repository 或 service
- **THEN** `packages/core` 不 import `fastapi`、`starlette`、`apps.api`、React、前端类型或具体插件实现
- **AND** core 不返回 API envelope、HTTP 状态码或 API response DTO
- **AND** ORM model 不直接作为 API response model 返回
