## 为什么现在做

Issue #222 已经把 Runtime 页面和后续实现依赖的主对象收束为 `AgentRun`、`ToolInvocation`、`SchedulerRun`、`RuntimeError` 和 `RuntimeHealth`。`docs/prd/pages/07-runtime-dashboard.md` 明确 Runtime 页是解释和排障页，`docs/design/08-api-and-websocket-design.md` 明确 REST 是状态真源、实时通道只做刷新提示，`docs/design/09-frontend-architecture-design.md` 明确 `/runtime` 需要围绕这些对象建立稳定的只读查询入口。

但当前仓库还没有一份专门约束 Runtime Inspect 只读契约的 OpenSpec change。继续推进会导致：

- Web 先自行发明 `AgentRun`、`ToolInvocation`、`RuntimeError` 和 health DTO。
- `SchedulerRun` 在 runtime 视角与 scheduler 视角下出现不同字段命名。
- API router 容易临时拼出 dashboard 聚合接口，把多对象查询、脱敏和失败语义混在一起。
- 调试场景容易把完整 prompt、工具原始参数、secret 或 provider 原始错误直接暴露给前端。

本 change 先收住 Runtime Inspect V1 的只读资源、过滤维度、字段分层、脱敏边界和 partial unavailable 语义，为 issue #218 的 Runtime Dashboard 和 issue #226 的 SchedulerRun 契约提供同一条真源。

## 当前缺口

- 缺少 Runtime Inspect 的稳定资源族和路径约定。
- 缺少 list / detail / summary DTO 的字段边界，前端无法稳定建 query 与空态。
- 缺少跨资源关联字段真源，例如 `event_id`、`trace_id`、`plugin_id`、`correlation_id`、`request_id`。
- 缺少 health、error 和 run 查询在局部失败下的统一语义。
- 缺少敏感字段脱敏与 V1 非目标的明确约束。

## 本轮目标

- 定义 Runtime Inspect V1 的只读资源族与路径。
- 定义 `RuntimeHealthSummary`、`AgentRunSummary/Detail`、`ToolInvocationSummary/Detail`、`SchedulerRunSummary/Detail`、`RuntimeErrorSummary/Detail` 的最小字段边界。
- 定义共享过滤维度与资源间关联字段。
- 定义 REST 快照、实时刷新提示和 partial unavailable 的关系。
- 定义 API 层与未来 service / repository / runtime provider 的职责边界。
- 为后续 OpenAPI / contracts / Web query key 留出稳定命名。

## 非目标

- 不实现 AgentRuntime、Tool runtime、scheduler loop、runtime error 持久化或健康检查逻辑本身。
- 不定义 WebSocket subscribe 协议、断线回放或实时消息 envelope 细节；这些沿用既有设计边界。
- 不新增 rerun、cancel、retry、approve、plugin control 或其他写操作。
- 不做完整 APM、日志搜索、trace 平台或监控墙。
- 不开放完整 prompt、完整模型推理链、工具原始敏感输入输出、secret 或 provider 原始异常。
- 不把 Runtime Inspect 收敛成单个“万能 dashboard 接口”。

## 影响范围

- 后续实现主要落在 `apps/api` 的 inspect 只读 route / schema 边界，以及 `packages/core` 或其他 runtime package 的 read service / repository seam。
- `apps/web` 的 Runtime Dashboard、AgentRun 详情和 ToolInvocation 详情会以本 change 为字段真源。
- `SchedulerRun` 的 detail 字段命名必须与 issue #226 后续 change 保持一致，runtime 视角只允许做摘要裁剪，不允许另起一套命名。

## 风险边界

- 如果先做聚合 dashboard endpoint，后续 AgentRun / ToolInvocation / SchedulerRun 详情页会被迫反向兼容临时字段。
- 如果不先收住脱敏边界，最容易在排障场景下泄露完整 prompt、原始工具参数和 provider 细节。
- 如果 shared filters 不统一，Runtime 页面与 Event / Approval 的跳转会长期补债。
