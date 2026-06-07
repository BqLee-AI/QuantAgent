## Why

当前最新 `origin/main` 已经具备 RSS/RawEvent、`industry.analysis.requested`、Router Agent single-call intake、`event.routed` 和 `event_intake_routed_events` 持久化基础；但 `/events` 生产页面仍使用 `event-scoring` mock，无法作为真实新闻处理审计入口。

本 change 基于 issue #280 收住最新产品决策：`/events` 只展示已经经过 Router Agent 处理的新闻事件，用户可读语义字段默认输出中文；`/runtime` 继续负责未处理、未入队、未消费、模型失败和 Kafka/worker/scheduler 排障，不再承担业务新闻事件主入口。

## What Changes

- 新增业务 `/events` read model 契约：`GET /api/v1/events` 只返回已存在 Router routed read model 的新闻事件，默认优先 `decision=route|review`，`discard` 仅通过显式筛选或审计模式查看。
- 新增业务事件详情契约：`GET /api/v1/events/{raw_event_id}` 返回单条已路由新闻的业务摘要、Router Agent stage、trace refs 和安全详情；列表和默认详情不返回完整正文、raw payload、provider raw response、prompt、CoT 或 secret。
- 新增 Router Agent output detail 契约：完整结构化 Router output JSON 通过按需详情 endpoint 获取，不能进入列表接口默认响应。
- 升级 Router Agent 输出契约到 `event_intake_decision.v2`，保留 v1 历史读取兼容；v2 仍保持 single-call intake，不新增 tool-call loop、多轮模型调用、二次抓取或模型分块总结。
- Router Agent prompt/schema MUST 要求用户可读语义文本默认使用中文，例如标题、摘要、标签说明、理由、下一步建议；机器稳定字段继续使用英文 enum/code。
- 不新增“中文 display 层”。中文文本属于 `structured_news`、`quality`、`relevance`、`routing`、`audit` 等语义字段本身；API read model 可以挑选这些语义字段生成列表/详情摘要，但不能把中文内容集中进只用于展示的 `display` 字段。
- 新增跨页面 Agent 审计展示边界，供 `/events` 与 `/runtime` 共享 Router Agent stage panel、detail modal、JSON view、key fields、trace refs；`/events` 不得直接 import runtime 私有弹窗。
- 明确 `/runtime` 职责：展示 captured/pending/unavailable 和运行态排障事实；未路由 RawEvent 不进入 `/events` 主列表。
- 新增 `event.inspect` capability 作为业务事件审计权限；`/runtime` 继续使用 `runtime.inspect`。

## Capabilities

### New Capabilities

- `event-page-router-agent-audit`: 定义 `/events` 真实已路由新闻事件业务审计入口、`/api/v1/events` read model、列表/详情/Router output detail、安全字段和权限边界。
- `router-agent-output-v2`: 定义 Router Agent `event_intake_decision.v2` 输出契约、中文语义字段、v1 兼容读取、single-call 约束和持久化 key fields。
- `agent-audit-shared-ui`: 定义跨 `/events` 与 `/runtime` 的 Agent stage 展示模型、详情弹窗、JSON view、key fields、trace refs 和安全展示边界。

### Modified Capabilities

- 无 stable capability 修改。本轮相关的 `runtime-audit-chat-view-v1`、`ai-event-intake-single-call-routing-v1` 和 `web-p0-mainflow-pages` 仍是未归档 change 或阶段性 change；本 change 通过新增 capability 收住最新 main 上的真实实现边界，并在实现 PR 中同步更新对应未归档 change 的 tasks/notes（如有需要）。

## Impact

- 后端 API：新增 `/api/v1/events`、`/api/v1/events/{raw_event_id}`、Router output detail endpoint、schema/service/router/权限测试和 v1 route 注册。
- Core/Worker：新增或扩展 `EventIntakeDecisionV2`、prompt/schema validation、v1 compatibility mapper、`event_intake_routed_events` key fields/output safe persistence，以及 worker routed output 写入测试。
- Web：`/events`、`/events/all`、`/events/:eventId`、`/events/:eventId/audit` 切真实业务 API；`event-scoring` mock 退出生产数据路径；新增 `features/agent-audit/` 共享组件边界并重构 runtime 私有 Agent 组件复用。
- Auth：新增 `event.inspect` capability，开发 actor 默认包含；`runtime.inspect` 不再作为业务 `/events` 的权限。
- 安全：列表和默认详情必须脱敏并按需加载完整 Router output；不暴露完整正文、raw payload、provider raw response、prompt、CoT、secret、ORM object 或 plugin instance。
- 验证：OpenSpec strict、core/worker schema 与 persistence tests、API router/service tests、Web unit/lint/build、必要 seeded data 或 Playwright smoke。
