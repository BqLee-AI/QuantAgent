# Runtime 审计

`features/runtime` 负责 `/runtime` 的 RawEvent 新闻审计视图。页面主对象是一篇新闻 / RawEvent，生产路径通过后端 `GET /api/v1/runtime/audit/news` 读取真实 read model，不使用前端 fixture 作为正常数据源。Router Agent 输出只来自后端持久化的 routed-event read model；没有真实记录时必须显示 unavailable。

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
- `components/agent/`: 可复用 Agent 处理详情组件。右侧详情只展示摘要和入口，Router Agent / 行业 MainAgent 的重内容放进独立弹窗。
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

`RuntimeAuditAgentStagePanel` 展示每个 Agent stage 的摘要、关键字段和详情入口；`RuntimeAuditAgentDetailModal` 展示新闻标题、URL、列表级内容预览、Agent 关键字段和完整结构化 `output_json`。

后续行业 MainAgent 如果以 ChatAPP 形态输出 Markdown、消息流、toolcall 或 artifact，应继续扩展 `components/agent/` 下的详情弹窗族，不要把聊天渲染、toolcall 渲染和 JSON 展开逻辑塞回 `/runtime` page 或右侧详情主体。

## 安全边界

详情视图只能展示后端返回的 `safe_details`、列表级 `content_preview` 和已持久化的结构化 Agent `output_json`。新增字段时必须先经过后端 allowlist 或 `runtime-audit-sanitize.ts` 等价脱敏，不能把 provider raw response、CoT、secret-bearing config、ORM object、plugin instance、完整正文或 raw payload 直接传给组件。
