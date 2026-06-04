## Why

AgentRuntime 与半导体 NVDA fixture 已经可以在测试中产出稳定 `AgentRunEvent`，但前端 debug chat 还没有 API 流式入口。需要先在 API 层收住 development-only SSE 协议，避免 Web 页面绕过 runtime、直接调用测试函数或以一次性 REST 结果替代流式调试。

## What Changes

- 新增 development/test/local 可用、production 不注册的 Agent debug run SSE API。
- 支持启动半导体 NVDA fixture run，并以 `text/event-stream` 连续返回 `AgentRunEvent`。
- 新增 API request/response DTO 和 SSE event 序列化边界，保持字段稳定、脱敏、前端可消费。
- 新增 API 私有 `AgentDebugRunService` / fixture registry，router 只处理 HTTP 参数、依赖注入和 SSE response。
- 覆盖断开、runtime failure、timeout 或启动后失败的 stream 失败事件；启动前参数错误仍使用 API envelope。

## Capabilities

### New Capabilities

- `agent-debug-sse-api`: development-only Agent debug fixture registry、SSE stream endpoint、event serialization、production exclusion 和 API 分层行为。

### Modified Capabilities

- `api-cookie-session-auth`: 复用既有 debug route production exclusion 约束；本 change 不改变认证 requirement。

## Impact

- 受影响目录：
  - `apps/api/src/quantagent/api/schemas/`：新增 Agent debug request / event DTO。
  - `apps/api/src/quantagent/api/services/`：新增 Agent debug run service 与 fixture registry。
  - `apps/api/src/quantagent/api/routers/v1/`：新增或扩展非生产 debug router。
  - `apps/api/src/tests/`：覆盖 SSE、production exclusion、OpenAPI 和脱敏。
- 依赖 `packages/agent` 的公开 `AgentRuntime.run_stream`、NVDA fixture harness 和 `AgentRunEvent`，不直接创建 DeepAgents。
- 不接真实 Tavily、真实账户、真实 broker 或生产交易。
