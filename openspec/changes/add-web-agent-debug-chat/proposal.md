## Why

后端已经提供 non-production Agent debug SSE API，但 Web 端还没有能直接观察 DeepAgents / MainAgent 运行过程的调试页面。现在需要把 NVDA earnings fixture 的完整流式调试体验收束到 `/debug` 工作台，避免开发者绕过 API、直接调用测试函数，或用一次性 REST/log dump 替代真实流式反馈。

## What Changes

- 在 Web development-only `/debug` 工作台下新增 Agent Debug Chat 子页面，用 AI 对话式布局展示一次 fixture run 的 coordinator 输出、todo/progress、tool、SubAgent、artifact 和 final summary。
- 新增 `features/debug/agent-run-chat/` feature，按 `api/`、`hooks/`、`components/`、`types/`、`utils/`、`README.md` 拆分职责。
- 新增 feature API / stream client，调用 #285 的 `GET /debug/agent-runs/fixtures` 和 `POST /debug/agent-runs/fixtures/{fixture_id}/stream`，以 SSE 逐帧消费 `AgentRunEvent`。
- 新增 event-to-message reducer，将稳定 `AgentRunEvent` 映射为 chat message、tool card、SubAgent card、artifact card、run status，而不是把原始 JSON dump 到页面。
- 更新 debug route registration 和 debug root 入口，保持 production router 不注册、不打包该 debug 页面模块。
- 补充 unit/component 或 smoke 验证，覆盖 streaming 中间态、完成态、OpenSpec、生产排除和 build。

## Capabilities

### New Capabilities

- `web-agent-debug-chat`: 覆盖 `/debug/agent-run-chat` development-only 页面、feature 目录职责、SSE streaming 消费、event-to-message 映射、AI chat-like UI 状态和生产排除。

### Modified Capabilities

- `web-debug-route-workbench`: 扩展 `/debug` 工作台固定调试入口，新增 Agent Debug Chat 子路由，同时保持 production 排除边界。

## Impact

- 受影响目录：
  - `apps/web/src/debug/router/`：development-only route attachment 新增 `/debug/agent-run-chat`，production noop 不变。
  - `apps/web/src/debug/workbench/`：debug root 增加 Agent Debug Chat 入口。
  - `apps/web/src/features/debug/agent-run-chat/`：新增 feature API、types、utils、hooks、components、README。
  - `apps/web/src/app/runtime/`：将 debug Agent API 挂到 runtime-scoped `apis` 对象，避免页面裸 `fetch`。
  - `apps/web/tests/` 或 feature unit tests：验证 reducer / stream client / 页面状态。
- 依赖已有 API：`/api/v1/debug/agent-runs/fixtures` 和 `/api/v1/debug/agent-runs/fixtures/{fixture_id}/stream`。
- 不新增生产依赖，不接真实 broker、真实账户、真实 Tavily key，也不展示完整 prompt、CoT、secret、私有策略或 provider raw response。
