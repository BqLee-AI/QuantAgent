## 1. OpenSpec 修订

- [x] 1.1 将 change 从 fixture Router Agent showcase 修订为真实 RawEvent 新闻审计流。
- [x] 1.2 明确 V1 不新增 `event.routed` 持久化，不伪造 route/review/discard。
- [x] 1.3 运行 `openspec validate runtime-audit-chat-view-v1 --type change --strict --json`。

## 2. 后端 read model

- [x] 2.1 新增 `apps/api/src/quantagent/api/schemas/runtime_audit.py`，定义 Runtime audit news list/item/timeline/trace/safe detail DTO。
- [x] 2.2 新增 `apps/api/src/quantagent/api/services/runtime_audit.py`，从 `raw_events`、`raw_event_captures`、`scheduler_runs` 组合新闻审计摘要。
- [x] 2.3 新增 `apps/api/src/quantagent/api/routers/v1/runtime_audit.py`，暴露 `GET /api/v1/runtime/audit/news`，使用 `runtime.inspect` capability 和 `ApiResponse`。
- [x] 2.4 在 v1 router register 中注册 runtime audit router。
- [x] 2.5 补 API tests：RawEvent 返回新闻维度、不泄露 content/raw_payload、AI/route unavailable、筛选、权限。

## 3. 前端接真实 API

- [x] 3.1 将 `RuntimeAuditApi` 改为 `BaseApi` endpoint，删除生产路径中的 fixture 调用。
- [x] 3.2 更新 runtime audit contracts/types 为新闻维度模型和后端 query params。
- [x] 3.3 更新 query keys/hooks/page hook，按 backend filters 查询和选中 `raw_event_id`。
- [x] 3.4 更新 FilterBar，支持 keyword、binding_id、source_plugin_id、status/current_stage、trace_id、request_id、time range。
- [x] 3.5 更新左侧列表为新闻列表 + 压缩 timeline，不再展示 topic message group。
- [x] 3.6 更新右侧详情为新闻摘要、当前进度、Timeline、Trace、安全详情。
- [x] 3.7 更新 README，说明正常运行接后端，fixture 仅用于测试。

## 4. 验证

- [x] 4.1 更新 Web unit tests，覆盖 query params、safe details、timeline label、RawEvent-backed fixture。
- [x] 4.2 更新 Playwright e2e，使用真实 API seeded RawEvent 验证 `/runtime`。
- [x] 4.3 运行 API unittest 覆盖新增 router/service。
- [x] 4.4 运行 Web unit、lint、build 和 `git diff --check`。

## 5. Agent 输出审计补强

- [x] 5.1 扩展 Runtime audit API DTO/read model，返回可扩展的 `agent_stages`，真实缺口显示 unavailable。
- [x] 5.2 前端详情新增可复用 Agent 处理弹窗组件，右侧只展示关键字段和详情入口，弹窗展示 Router 重要字段、完整 JSON viewer 和 MainAgent 预留阶段。
- [x] 5.3 调窄左侧新闻列表，右侧作为主要新闻处理审计区。
- [x] 5.4 更新 fixture、unit/e2e/README，覆盖 Router output JSON、重要字段 UI 和 unavailable 生产语义。
- [x] 5.5 重新运行 OpenSpec、API、Web 和 e2e 验证。

## 6. 真实 Router Agent 输出持久化

- [x] 6.1 在 `packages/core` 新增 `event_intake_routed_events` ORM、migration、repository 和 store port，保存安全结构化 `event.routed` 输出。
- [x] 6.2 让 scheduler 在发布 `source.event.captured` 前，把 RawEvent trace metadata 补入 source item，确保 worker context 能拿到 `raw_event_id`。
- [x] 6.3 让 worker 在发布 `event.routed` 后写入 routed-event read model，并覆盖正常 item 与 malformed fallback。
- [x] 6.4 让 `/api/v1/runtime/audit/news` 查询最新 routed-event read model，Router Agent stage 展示真实 `output_json` / `key_fields`，无记录时继续 unavailable。
- [x] 6.5 同步 Web stage 类型、筛选选项和 README，允许展示 `ai_intake_routed` / `route_decided`。
- [x] 6.6 补 core、worker、scheduler、API、Web 单测，并重新运行 OpenSpec、Python、Web 和 diff 验证。
