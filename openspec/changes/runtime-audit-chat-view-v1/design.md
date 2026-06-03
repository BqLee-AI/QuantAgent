## 背景与修订取舍

本 change 承接 #270，并在 PR #271 的初版实现后继续修订。初版 `/runtime` 已把多面板 dashboard 改成审计流，但数据仍来自前端 fixture；用户明确指出这不满足“运行态页面接真实后端”的目标。

本轮锁定新的 V1 边界：

- `/runtime` 的左侧主单位是“一篇新闻 / RawEvent”，不是 Event topic、analysis request 或 trace session。
- 后端新增真实只读 read model：`GET /api/v1/runtime/audit/news`。
- V1 新增 Router Agent 结构化输出的安全 read model，用于把 `event.routed` / `EventIntakeDecisionV1` 关联回 RawEvent；如果没有真实持久化事实，页面必须显示 `pending` 或 `unavailable`，不能用 fixture 伪造 `route/review/discard`。
- 完整正文和 raw payload 仍只能通过 RawEvent detail 类接口按 ID 获取；runtime audit news 列表和右侧默认详情不返回完整内容。

## 后端 API 蓝图

新增 API：

```text
GET /api/v1/runtime/audit/news
```

职责：

- 按 RawEvent 聚合返回新闻维度的运行态审计摘要。
- 只读，不触发 worker、scheduler、AI 或 route 重放。
- 使用 `runtime.inspect` capability。
- 返回统一 `ApiResponse[RuntimeAuditNewsListResponse]` envelope。

查询参数：

- `keyword`: 匹配 title、canonical_url 或 content preview 的轻量筛选。
- `binding_id`: 使用 `raw_events.first_binding_id` 或 capture 归属筛选。
- `source_plugin_id`: 使用 `raw_events.source_plugin_id` 筛选。
- `status`: 当前新闻审计状态，例如 `captured`、`linked`、`pending`、`unavailable`。
- `current_stage`: 当前阶段，例如 `captured`、`persisted`、`scheduler_linked`、`ai_intake_unavailable`。
- `trace_id` / `request_id`: 从 RawEvent metadata 或 capture request_id 中筛选。
- `time_from` / `time_to`: 按 `published_at` 退化到 `last_captured_at` 的有效时间筛选。
- `cursor` / `limit`: 游标分页，limit 上限不超过 100。

响应模型：

```text
RuntimeAuditNewsListResponse
  items: RuntimeAuditNewsItem[]
  next_cursor: string | null
  generated_at: datetime

RuntimeAuditNewsItem
  raw_event_id
  title
  canonical_url
  url_host
  source_plugin_id
  source_name
  author
  published_at
  first_captured_at
  last_captured_at
  content_preview
  status
  current_stage
  focus_stage
  trace
  timeline
  agent_stages
  safe_details

RuntimeAuditNewsTimelineStep
  step_id
  label
  status
  occurred_at
  summary
  refs

RuntimeAuditAgentStage
  stage_id
  agent_name
  agent_type
  status
  summary
  key_fields
  output_json
  refs
  unavailable_reason
```

Router Agent 持久化 read model：

```text
event_intake_routed_events
  event_id
  schema_version
  raw_event_id
  source_message_id
  analysis_request_id
  binding_id
  owner_type / owner_id
  request_id / correlation_id
  decision / discard_reason / status
  summary
  output_json
  key_fields
  provider_invocation_count
  invocation_metadata
  created_at
```

职责边界：

- `packages/core` 只提供 ORM、repository 和 store port；不依赖 API、worker 或前端。
- worker 在发布 `event.routed` 后通过 store 写入安全结构化输出，并使用 `event_id` 幂等避免重复写入。
- scheduler 在发布 `source.event.captured` 前，把 RawEvent trace 字段补到 item metadata，使 worker 构建 context 时能带上 `raw_event_id`。
- `/runtime` API 查询最新的 `event_intake_routed_events.raw_event_id` 记录，把它映射为 Router Agent stage 和 timeline 成功/失败节点。

安全边界：

- 列表和默认详情不返回 `content`、`raw_payload`、provider raw response、prompt、CoT、secret、ORM object 或 plugin instance。
- `safe_details` 只返回 allowlisted metadata 摘要，例如 `feed`、`source`、`provider`、`payload_truncated`、`dedupe_strategy`、`duplicate_capture_count`。
- AI / route 阶段没有真实持久化事实时，timeline step 必须是 `unavailable`，summary 说明“暂无持久化 read model”，不得伪造路由结果。
- Agent 输出使用 `agent_stages` 表达；Router Agent / MainAgent 均以阶段形式出现。Router Agent 持久化存在时，允许展示 `event.routed` 结构化 `output_json` 与 allowlisted `key_fields`；不存在时 `output_json` 为 `null` 并写明 `unavailable_reason`。
- `output_json` 不能包含 provider raw response、CoT、secret 或 unbounded article content。`event.routed` payload 本身只保留结构化 decision、source/article 状态、quality、routing、audit 摘要。

文件规划：

```text
apps/api/src/quantagent/api/
  routers/v1/runtime_audit.py
  schemas/runtime_audit.py
  services/runtime_audit.py
```

`routers/v1/runtime_audit.py` 只处理 HTTP 参数、依赖注入和 `ApiResponse` 包装。`services/runtime_audit.py` 负责查询 RawEvent / capture / scheduler run / Router output 可确认事实并映射 DTO。RawEvent 聚合查询保留在 API 私有 service；Router output 持久化使用 core repository/store，因为它由 worker 写入、API 读取，是跨 app 共享审计 read model。

## 前端蓝图

`features/runtime` 继续保留分层，但从 message/topic 模型改为 news audit 模型：

- `api/`: `RuntimeAuditApi` 改为 `BaseApi` endpoint，调用 `/runtime/audit/news`。
- `types/`: 定义 `RuntimeAuditNewsItem`、`RuntimeAuditNewsTimelineStep`、filters、safe details。
- `queries/`: query key 以 news filters 为资源边界。
- `hooks/`: 页面 hook 组合筛选、selected raw_event_id、refresh 和错误状态。
- `components/filters`: 顶部筛选支持 keyword、binding、plugin、stage/status、trace/request、time range。
- `components/conversation`: 改名语义仍可保留，但渲染左侧新闻列表；每条新闻显示标题、副信息和压缩 timeline。
- `components/details`: 右侧按新闻组织为新闻摘要、当前进度、Timeline、Trace、安全详情。
- `components/agent`: 复用型 Agent 处理详情组件。右侧详情只展示摘要和入口，Router Agent / 行业 MainAgent 等重内容通过独立弹窗承载。

Agent 详情组件边界：

- `RuntimeAuditAgentStagePanel`: 展示每个 Agent stage 的状态摘要、关键字段和详情入口。
- `RuntimeAuditAgentDetailModal`: 展示新闻标题、URL、content preview，可折叠展开的列表级内容预览、Agent 重要字段和完整结构化 output JSON。
- V1 不引入 ChatApp 渲染依赖；但组件模型预留 `agent_type=industry_main_agent`，后续可在同一弹窗族中加入 Markdown、消息流、toolcall 和 artifact 渲染，不改左侧新闻列表主单位。
- 详细弹窗不能展示未脱敏正文、provider raw response、CoT、secret 或 raw payload。完整正文仍需后端 RawEvent detail 类接口另行按 ID 拉取。

首屏结构：

```text
Header + compact status
FilterBar
Main
  Left: News audit list
    title
    source / published_at / host
    current_stage + focus_stage badge
    compressed timeline
  Right: selected news detail
    新闻摘要
    当前进度
    Timeline
    Trace
    Agent 处理
      Router Agent: 重要字段 + 完整 output JSON / unavailable
      MainAgent: 预留阶段 / unavailable
    安全详情
```

## 状态与失败路径

- `loading`: 只遮蔽列表区域，筛选区保持可见。
- `empty`: 区分无 RawEvent、当前筛选无结果。
- `permission denied`: 展示 request id / trace id。
- `partial unavailable`: RawEvent 可展示，AI/route 阶段显示 unavailable step。
- `backend unavailable`: 使用统一错误态，不回退到前端 fixture。
- `route decision unavailable`: 显示真实缺口，不渲染 `route/review/discard` mock。
- `route decision available`: 显示 `ai_intake_routed` / `route_decided` timeline step、Router Agent 重要字段和完整结构化 JSON viewer。
- `agent output unavailable`: Agent 卡片仍展示阶段、状态和缺口；只有后端返回 `output_json` 时才展示完整 JSON viewer。

## 验证策略

- API tests 覆盖真实 RawEvent 列表、无正文泄露、AI/route unavailable step、真实 Router Agent output_json、筛选和权限。
- Core/worker tests 覆盖 `event_intake_routed_events` ORM metadata、store 幂等写入、worker 发布 `event.routed` 后写入、scheduler 发布的 item metadata 带 RawEvent trace。
- Web unit tests 覆盖 API contracts、query params、timeline label、safe detail。
- Web unit tests 覆盖 Agent stage label、Router 重要字段、完整 JSON viewer 和 unavailable 状态。
- Playwright e2e 使用真实 `uv run api` 和 seeded RawEvent 验证 `/runtime` 左侧按新闻显示、筛选生效、右侧不展示完整正文/raw payload。
- Regression 继续运行 OpenSpec、Web unit、lint、build。
