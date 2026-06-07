## ADDED Requirements

### Requirement: `/events` MUST only show Router Agent processed news events

系统 SHALL 将 `/events` 定义为 AI 已筛选新闻事件的业务审计入口；生产路径 MUST 只展示存在 Router Agent routed read model 的新闻事件。

#### Scenario: 未路由 RawEvent 不进入事件页主列表
- **WHEN** 后端存在 RawEvent、RawEventCapture 或 scheduler run，但没有对应 `event_intake_routed_events` 或等价 Router routed read model
- **THEN** `/api/v1/events` MUST NOT 将该新闻返回到 `/events` 主列表
- **AND** 该新闻的 pending、unavailable 或未消费原因 MUST 留在 `/runtime` 排障视图表达

#### Scenario: 已路由新闻进入事件页
- **WHEN** 一条新闻存在可关联 `raw_event_id` 的 Router routed read model
- **THEN** `/api/v1/events` MUST 能够返回该新闻派生的业务事件摘要
- **AND** 列表主对象 MUST 是一篇新闻 / RawEvent 派生业务事件
- **AND** 列表主标题 MUST 使用新闻标题或 Router Agent 结构化标题，而不是 `source.event.captured`、`industry.analysis.requested`、`event.routed` 等 event bus topic

### Requirement: Events list MUST default to route and review decisions

系统 SHALL 让 `/events` 默认优先展示对用户有业务价值的 `route` 和 `review` 决策；`discard` MUST 只能通过显式筛选或审计模式查看。

#### Scenario: 默认列表排除 discard
- **WHEN** 用户未显式传入 `decision=discard`、`decision=all` 或等价审计筛选
- **THEN** `/api/v1/events` MUST 默认返回 `decision=route` 和 `decision=review` 的事件
- **AND** 它 MUST NOT 将 `decision=discard` 混入默认业务主列表

#### Scenario: 显式筛选可以查看 discard
- **WHEN** 授权用户显式请求 `decision=discard` 或启用等价审计筛选
- **THEN** `/api/v1/events` MAY 返回已被 Router Agent 丢弃的新闻事件
- **AND** 每条 discard 事件 MUST 展示结构化 discard reason 或可审计原因摘要
- **AND** discard 事件 MUST NOT 被表达为需要继续行业深度分析的业务事件

### Requirement: Events API MUST expose a business read model separate from runtime audit

系统 SHALL 提供 `/api/v1/events` 业务 read model，内部可以复用 RawEvent 和 routed persistence，但公开契约 MUST 独立于 `/api/v1/runtime/audit/news`。

#### Scenario: Events list endpoint returns safe business summaries
- **WHEN** 授权用户请求 `GET /api/v1/events`
- **THEN** API MUST 返回统一 envelope 包装的事件列表响应
- **AND** 每个 item MUST 至少包含 `raw_event_id`、`routed_event_id`、`schema_version`、title、URL 摘要、source 摘要、published/routed 时间、decision、summary、priority、target industries/topics、relationship summary、Router stage 摘要和 trace refs
- **AND** 列表响应 MUST NOT 包含完整正文、raw payload、完整 Router `output_json`、provider raw response、prompt、CoT、secret、ORM object 或 plugin instance

#### Scenario: Runtime audit DTO 不作为 Events 公开契约
- **WHEN** `/events` 前端加载生产数据
- **THEN** 它 MUST 调用业务 Events API 或等价业务 FeatureApi
- **AND** 它 MUST NOT 直接把 `/api/v1/runtime/audit/news` response shape 当成 `/events` 的长期公开契约
- **AND** 后端 MAY 复用底层 mapper 或 repository，但公开 DTO MUST 表达业务事件语义

### Requirement: Events API MUST support business filters and cursor pagination

系统 SHALL 支持按业务事件和 Router Agent 语义筛选已路由新闻事件，并使用有上限的分页。

#### Scenario: 业务筛选传递到后端 read model
- **WHEN** 用户在 `/events` 使用筛选
- **THEN** 前端 MUST 将 keyword、decision、binding_id、source_plugin_id、industry_id、target_topic、priority、relationship、status、trace_id、request_id、time range、cursor 和 limit 中已支持的参数传给 `/api/v1/events`
- **AND** 后端 MUST 在真实 read model 上应用筛选，而不是只在前端本地过滤 fixture
- **AND** 无效或空筛选值 MUST NOT 造成页面崩溃

#### Scenario: 分页有安全上限
- **WHEN** 用户请求事件列表
- **THEN** `/api/v1/events` MUST 使用 cursor pagination 或等价稳定分页
- **AND** `limit` MUST 有服务端上限
- **AND** 查询 MUST NOT 无限制扫描并返回全部 routed event 记录

### Requirement: Event detail MUST show Router Agent output and trace without leaking unsafe payloads

系统 SHALL 让 `/events/{raw_event_id}` 围绕单条已路由新闻展示 Router Agent 对它做了什么、输出了什么、为什么 route/review/discard。

#### Scenario: Event detail organizes information by news and Agent stage
- **WHEN** 用户打开 `/events/{raw_event_id}`
- **THEN** 页面 MUST 展示新闻事实摘要、Router Agent 决策摘要、关键语义字段、timeline、trace refs 和安全详情
- **AND** Router Agent stage MUST 展示 decision、summary、quality、relevance、target industries/topics、priority、review/discard reason 和详情入口
- **AND** 页面 MUST 保持新闻 / RawEvent 派生业务事件为主对象，不以 event bus topic 为详情主对象

#### Scenario: Full Router output is loaded on demand
- **WHEN** 用户打开 Router Agent stage 详情或完整 JSON
- **THEN** 前端 MUST 按 `raw_event_id` 和 stage/routed event identity 请求完整结构化 Router output
- **AND** 列表接口 MUST NOT 默认携带完整 Router output JSON
- **AND** 详情响应 MUST 只包含安全的结构化 Agent output，不包含 provider raw response、prompt、CoT、secret、完整正文、raw payload、ORM object 或 plugin instance

### Requirement: Events page MUST use real API data in production

系统 SHALL 移除 `/events` 生产路径对 `event-scoring` mock 或 runtime fixture 的依赖。

#### Scenario: Production events routes do not call scoring mock
- **WHEN** 正常应用运行并打开 `/events`、`/events/all`、`/events/{raw_event_id}` 或 `/events/{raw_event_id}/audit`
- **THEN** 前端 MUST 通过 runtime `apis`、FeatureApi 和 TanStack Query 读取真实 Events API
- **AND** 它 MUST NOT 从 `event-scoring` mock、event-audit mock 或 runtime fixture 构造生产页面数据
- **AND** fixture MAY 仅作为单测、Playwright mock、debug/demo 或 harness 输入保留

#### Scenario: Missing routed output is not fabricated
- **WHEN** 后端没有返回 Router output 或 routed read model 不存在
- **THEN** `/events` MUST 显示明确的 unavailable、not found 或权限状态
- **AND** 它 MUST NOT 用自然语言 mock、fixture 或前端推断伪造 `route`、`review`、`discard`、summary、target industry 或 reason

### Requirement: Events API and page MUST use `event.inspect`

系统 SHALL 将业务事件审计权限与运行态排障权限分离。

#### Scenario: Events endpoint requires event inspect
- **WHEN** 调用方缺少 `event.inspect`
- **THEN** `/api/v1/events`、`/api/v1/events/{raw_event_id}` 和 Router output detail endpoint MUST 返回既有受保护路由的权限错误
- **AND** 错误响应 MUST NOT 泄露事件摘要、trace refs 或 Router output

#### Scenario: Runtime inspect does not imply event inspect
- **WHEN** actor 只有 `runtime.inspect` 但没有 `event.inspect`
- **THEN** actor MAY 访问 `/runtime` 排障数据
- **AND** actor MUST NOT 因为拥有 runtime 排障权限而自动访问 `/events` 业务事件审计 API
