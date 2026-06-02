## 为什么现在做

PR #257 已按 #218、`runtime-inspect-api-v1` 和 `docs/prd/pages/07-runtime-dashboard.md` 实现了 `/runtime` Runtime Dashboard V1：health 摘要、筛选区、AgentRun / ToolInvocation / SchedulerRun / RuntimeError 多个只读面板。该方向满足早期“运行态排障仪表盘”的真源，但产品反馈指出当前页面占位内容过多、结构显得混乱、信息量过重。

现在需要把 `/runtime` 首版体验收敛成一个更纯粹的可审计界面：像常规 chat app 或运行时间线一样，让用户顺着一次事件或一次 Agent 运行的消息流，理解输入、判断、路由、失败和输出，而不是一屏面对多个技术对象列表。

这个反馈发生在 PR #257 尚未合并时。若继续直接合并现有页面层，后续会在主线上留下两个互相冲突的 Runtime 方向：一个是多资源排障 dashboard，一个是事件 / Agent 审计流。因此本 change 先为 #270 收住新的页面行为和实现蓝图，再决定如何处理 #257。

## 当前缺口

- `/runtime` 的页面目标已经从“多面板运行态仪表盘”转为“Chat App 风格审计流”，但 OpenSpec 还没有记录这个产品取舍。
- PR #257 中可复用的 Runtime Inspect contracts / query 分层，与需要替换的多面板页面层尚未明确区分。
- Router Agent / AI intake 已经有 `industry.analysis.requested -> event.routed` 的结构化链路，但前端缺少首个可审计展示样例。
- Runtime 审计展示需要保留 trace、request id、decision、degraded 状态和 route target，同时不能泄露 raw prompt、完整 chain-of-thought、provider raw response、secret 或未脱敏 payload。
- 如果实现者直接从自然语言日志中拼 UI，容易绕过 `EventIntakeDecisionV1` / Runtime Inspect 等结构化真源。

## 本轮目标

- 将 `/runtime` 首屏定义为审计聊天流，而不是默认铺开 health、AgentRun、ToolInvocation、SchedulerRun、RuntimeError 四类列表。
- 定义 Runtime audit chat 的信息架构：轻筛选、消息/步骤流、结构化摘要、可折叠详情、trace/request/correlation context 和安全脱敏。
- 以 Router Agent 作为第一种筛选案例，展示 `industry.analysis.requested -> single-call AI intake -> discard/review/route -> event.routed` 的审计过程。
- 明确 #257 的处理策略：不建议按当前多面板页面层直接合并；实现应复用其中仍正确的 Runtime Inspect contracts、TanStack Query 分层、REST snapshot 和 partial unavailable 思路。
- 明确首版可以使用 fixture / mock read model 验证页面形态，但不能把 fixture 伪装成生产审计数据。

## 非目标

- 不做通用聊天机器人；Runtime 页不允许用户自由发 prompt 驱动模型或 tool 执行。
- 不新增 scheduler trigger、retry、pause、cancel、ack、resolve 等写操作。
- 不做 APM、日志搜索平台、实时监控墙或完整 trace 平台。
- 不要求一次覆盖所有 Agent 类型；首个验收样例只聚焦 Router Agent / AI intake 路由链路。
- 不新增后端生产持久化表、审计数据库或完整 audit read model；若实现需要这些能力，应单独开后端/API change。
- 不展示完整 prompt、完整模型推理链、provider raw response、secret、未脱敏工具输入输出或完整原始文章正文。

## 影响范围

- `apps/web/**`：后续实现应调整 `/runtime` route 与 `features/runtime/**` 页面形态、hooks、components、types、utils 和 README。
- `openspec/changes/runtime-inspect-api-v1/`：仍作为 Runtime Inspect 只读资源、字段命名、REST 真源和脱敏边界的输入，不被本 change 废弃。
- `openspec/changes/ai-event-intake-single-call-routing-v1/`：提供 Router Agent 首个审计样例的结构化语义，尤其是 `EventIntakeDecisionV1`、`decision=discard|route|review`、degraded marker 和 `event.routed`。
- PR #257：作为未合并输入；页面层应被重评估，不应因本 change 被默认合并。

## 风险边界

- 如果只改 UI 文案，不改变信息架构，页面仍会保留多面板堆叠问题。
- 如果把 Runtime audit chat 做成真正可对话的模型入口，会绕过 AgentRuntime、ProviderPolicy、ToolRegistry 和审计边界。
- 如果审计流依赖 raw log 或 raw provider response，会破坏脱敏边界和结构化审计能力。
- 如果不记录 #257 处理策略，后续可能同时维护 dashboard 首屏和 audit chat 首屏，导致用户路径和实现职责分裂。
