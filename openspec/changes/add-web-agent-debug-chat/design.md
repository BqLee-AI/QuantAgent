## Context

当前 `apps/web` 已有 development-only `/debug` 工作台，并通过 `src/debug/router/route-api.development.tsx` 动态挂载 debug routes；`route-api.production.ts` 返回 noop，满足 production 不注册、不打包 debug page modules 的稳定约束。#285 已在 API 侧合入 `AgentDebugRunService` 和 SSE endpoint，能够流式输出稳定 `AgentRunEvent`。

用户要求该页面“像 AI 对话的页面布局”，并能测试英伟达案例文档里的全流程。DeepAgents 官方 frontend 文档推荐用 `useStream` 展示 coordinator message、`subagents`、`values.todos`、tool call 和 HITL 等运行过程；本项目后端不是 LangGraph deployment，而是 FastAPI SSE adapter。因此本 change 复用官方的展示模型和信息层级，不直接引入 `@langchain/react` 或要求 LangGraph server。

## Goals / Non-Goals

**Goals:**

- 在 development 环境提供 `/debug/agent-run-chat` 页面，能启动 NVDA earnings fixture 并逐帧展示 SSE 事件。
- 页面主体验为 AI chat-like workbench：fixture controls + message stream + run status / artifact / tool / subagent cards。
- 实现真正 streaming：收到 `AgentRunEvent` 时立即更新 reducer 状态，不等待完整 run 结束。
- 按 Web gate 拆分 feature：API/contract、hook、components、types、utils、README 分层清晰，route 只组合页面。
- production build 不注册、不打包 debug page module，不进入正式导航。
- 安全展示：只展示后端 safe payload / summary，不展示完整 prompt、CoT、secret、私有策略、provider raw response。

**Non-Goals:**

- 不实现正式 Agent Run dashboard、历史 run 查询、持久化 replay 或生产可见页面。
- 不做通用 prompt playground、任意 fixture 路径输入、任意 tool 调用器。
- 不接真实交易按钮，不让前端推断交易是否执行成功。
- 不把 LangGraph `useStream` 强行接入当前 FastAPI SSE endpoint。

## Decisions

### 1. Debug route 仍挂在 development-only route API

新增页面使用现有 debug route registration：

```text
apps/web/src/debug/router/route-api.development.tsx
  -> createRoute path: 'agent-run-chat'
  -> component: DebugAgentRunChatPage
apps/web/src/debug/router/route-api.production.ts
  -> noop
```

这样能保持 production router 不含该 route，也避免把 debug 页面加入正式导航。route component 只渲染 feature page，不写 SSE、reducer 或 API 逻辑。

### 2. Feature 使用 `features/debug/agent-run-chat`

目标目录：

```text
apps/web/src/features/debug/agent-run-chat/
  README.md
  api/
    agent-debug.api.ts
    agent-debug.contracts.ts
    agent-debug.stream.ts
    index.ts
  hooks/
    use-agent-run-chat-page.ts
    index.ts
  components/
    page/AgentRunChatPage.tsx
    controls/AgentRunControls.tsx
    conversation/AgentRunMessageList.tsx
    conversation/AgentRunMessageBubble.tsx
    events/AgentRunToolCard.tsx
    events/AgentRunSubagentCard.tsx
    events/AgentRunArtifactCard.tsx
    status/AgentRunStatusBar.tsx
    states/AgentRunChatState.tsx
    index.ts
  types/
    agent-debug.types.ts
    index.ts
  utils/
    agent-run-event-reducer.ts
    agent-run-event-format.ts
    agent-run-sse-parser.ts
    index.ts
```

API 文件只封装 endpoint 和 stream iterator；hook 负责 page 状态、abort/retry、启动 run；utils 负责纯 reducer / formatter / parser；components 只渲染 props。

### 3. Runtime-scoped API ownership

新增 `AgentDebugApi` 通过 `createAppRuntime()` 挂到 `runtime.apis.agentDebug`，页面 hook 通过 `useApis()` 或 `useAppRuntime()` 取稳定对象。为了 SSE 需要读取原始 stream，`AgentDebugApi` 可以在 `api/agent-debug.stream.ts` 内复用 `ApiClient` 的 base URL / credentials 能力；若现有 `ApiClient` 未暴露 streaming helper，则在 feature 内新增明确的 stream adapter，并在 README/注释说明它是 SSE 协议适配，不是页面裸 `fetch`。

接口草案：

```ts
type AgentDebugFixtureSummary = {
  fixture_id: string
  name: string
  scenarios: string[]
  description: string
}

type AgentDebugRunRequest = {
  scenario: 'primary' | 'media_follow_up'
}

type AgentDebugSseEvent = {
  event_id: string
  agent_run_id: string
  type: string
  seq: number
  created_at: string
  payload: Record<string, unknown>
  safe_summary: string | null
  trace_id: string
}
```

### 4. SSE parser 和 reducer 分离

`agent-run-sse-parser.ts` 只把 SSE text chunks 解析成 event frames；`agent-run-event-reducer.ts` 只把 `AgentDebugSseEvent` 归并到展示状态。

展示状态草案：

```ts
type AgentRunChatStatus = 'idle' | 'streaming' | 'completed' | 'failed' | 'aborted'

type AgentRunChatMessage =
  | { kind: 'assistant'; id: string; title: string; body: string; createdAt: string }
  | { kind: 'todo'; id: string; items: TodoItem[]; createdAt: string }
  | { kind: 'tool'; id: string; toolName: string; status: string; summary: string; createdAt: string }
  | { kind: 'subagent'; id: string; agentName: string; status: string; summary: string; createdAt: string }
  | { kind: 'artifact'; id: string; artifactId: string; title: string; summary: string; createdAt: string }
  | { kind: 'final'; id: string; title: string; summary: string; createdAt: string }
  | { kind: 'error'; id: string; summary: string; createdAt: string }
```

DeepAgents 官方 frontend pattern 在这里落为 UI 信息层级：coordinator/assistant message 是主线，todo/progress 作为 sticky status，tool/subagent/artifact 作为结构化 cards。

### 5. UI 使用管理台密度的 AI chat workbench

页面布局不做营销 hero，不使用日志 dump 作为主体验：

- 顶部：fixture/scenario selector、start/stop/retry、run status、trace id。
- 主区域：消息流，assistant-like bubble 承载 run started / narrative / final summary。
- 侧边或消息内：tool/subagent/artifact cards，展示名称、状态、safe summary、关键字段。
- 状态覆盖：idle、loading fixtures、API unavailable、streaming、completed、failed、aborted、empty fixture。

### 6. 测试策略

- Unit test：`agent-run-sse-parser` 能处理分块 SSE；`agent-run-event-reducer` 能把 started/todo/tool/subagent/artifact/completed/failed 映射为展示状态。
- Component test 或 smoke：mock `AgentDebugApi` stream，断言页面启动后先出现 streaming 中间态，再出现 tool/subagent/artifact/final 内容。
- Build：`bun run --cwd apps/web build`。
- Production exclusion：通过现有 debug route production test 或新增 router/runtime test 证明 production route API 仍 noop；构建产物不包含 debug route modules 的验证可沿用既有 debug workbench 测试口径，PR 中说明。

## Risks / Trade-offs

- [Risk] 直接用 `@langchain/react useStream` 会要求 LangGraph deployment endpoint，与当前 FastAPI SSE 不兼容。→ Mitigation：只复用官方 frontend 的展示模型和事件层级，stream transport 使用 #285 的 SSE API。
- [Risk] stream adapter 看起来像裸 `fetch`。→ Mitigation：封装在 feature API 层，由 runtime-owned `AgentDebugApi` 持有；组件和 hook 不直接 fetch。
- [Risk] SSE payload 泄露敏感信息。→ Mitigation：页面只渲染 `safe_summary` 和 allowlisted payload 字段；JSON detail 默认折叠或不展示，测试断言不展示 `sk-`、`prompt`、`raw_response` 等敏感字符串。
- [Risk] Debug 页面进入 production bundle。→ Mitigation：继续使用 development-only route API；production route API 不 import feature page module。
- [Risk] UI 变成日志列表。→ Mitigation：reducer 输出 chat/display model，components 渲染 bubble/card/status，而不是逐行 dump SSE。
