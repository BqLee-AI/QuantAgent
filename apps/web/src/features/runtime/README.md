# Runtime 审计

`features/runtime` 负责 `/runtime` 的 RawEvent 运行态排障视图。页面主对象是一篇新闻 / RawEvent，生产路径通过后端 `GET /api/v1/runtime/audit/news` 读取真实 read model，不使用前端 fixture 作为正常数据源。它回答“为什么没有形成业务事件”：RawEvent captured/pending、AI intake unavailable、模型失败、Kafka/worker/scheduler 断点和 trace 线索。

业务用户阅读 AI 已筛选事件的入口是 `/events`。`/runtime` 可以展示已持久化 Router Agent output 作为排障证据，也可以跳转到 `/events/{raw_event_id}`，但不复制 `/events` 的业务筛选、阅读顺序或 mock 业务结果。

## 入口

- route: `src/routes/_app/(workspace)/runtime/index.tsx`
- page: `components/page/RuntimeAuditPage.tsx`
- page hook: `hooks/use-runtime-audit-page.ts`
- runtime API registry: `app/runtime/runtime.factory.ts`

## 子目录职责

- `api/`: Runtime audit news endpoint contract 和 `BaseApi` 封装。
- `queries/`: TanStack Query key 和 query hook，通过 `useApis().runtimeAudit` 读取。
- `hooks/`: 页面筛选、选中 RawEvent、刷新和派生状态。
- `components/`: page、filter bar、news list、detail、health strip 和状态视图。
- `components/agent/`: Runtime 到共享 Agent 审计组件的适配器。实际 panel、modal、JSON view、key fields 和 trace refs 来自 `features/agent-audit/`。
- `types/`: RawEvent 新闻审计 DTO、filter、timeline、trace 与安全详情类型。
- `utils/`: 格式化、脱敏、测试 fixture 构造和筛选纯函数。

## 不负责

- 不做通用聊天机器人，不允许用户自由 prompt 驱动模型或 tool。
- 不伪造 `event.routed`、`route/review/discard` 或尚未持久化的 AI decision；真实 Router output 可展示 `routed`、`ai_intake_routed`、`route_decided`。
- 不触发 scheduler、worker、AI 重放或 RawEvent 正文抓取。
- 不展示 raw prompt、完整 chain-of-thought、provider raw response、secret、未脱敏工具输入输出、完整正文或 `raw_payload`。

## Fixture 边界

`utils/runtime-audit-fixtures.ts` 只用于单测、Playwright mock 或本地 harness。生产页面数据路径必须走 `RuntimeAuditApi.listAuditNews()`，由 shared API client 调用后端 read model。

## Agent 详情组件

`RuntimeAuditAgentStagePanel` 只把 `RuntimeAuditNewsItem.agent_stages` 转成 `AgentAuditSubject/AgentAuditStage`，再交给 `features/agent-audit` 渲染。Runtime 不维护第二套私有 Agent detail modal、JSON view 或 key fields 组件，避免 `/events` 与 `/runtime` 的审计展示分叉。

后续行业 MainAgent 如果以 ChatAPP 形态输出 Markdown、消息流、toolcall 或 artifact，应继续扩展 `features/agent-audit` 的共享详情边界，不要把聊天渲染、toolcall 渲染和 JSON 展开逻辑塞回 `/runtime` page 或右侧详情主体。

## 安全边界

详情视图只能展示后端返回的 `safe_details`、列表级 `content_preview` 和已持久化的结构化 Agent `output_json`。新增字段时必须先经过后端 allowlist 或 `runtime-audit-sanitize.ts` 等价脱敏，不能把 provider raw response、CoT、secret-bearing config、ORM object、plugin instance、完整正文或 raw payload 直接传给组件。
