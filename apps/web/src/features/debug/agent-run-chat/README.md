# Agent Debug Chat feature

负责 development-only `/debug/agent-run-chat` 页面，用 AI 对话式布局流式观察 allowlisted Agent debug fixture。

入口：
- route: `src/debug/router/route-api.development.tsx`
- page: `components/page/AgentRunChatPage.tsx`
- page hook: `hooks/use-agent-run-chat-page.ts`
- runtime API: `api/agent-debug.api.ts`

当前职责：
- `api/`: Agent debug fixture list、SSE stream endpoint contract 和 feature-scoped stream adapter。
- `queries/`: fixture list 的 TanStack Query key 与 query hook。
- `hooks/`: 页面级业务状态、start/stop/retry 和 stream lifecycle。
- `components/`: 控制区、状态条、对话消息、tool/SubAgent/artifact cards 和状态组件。
- `types/`: 页面展示模型与 chat state 类型。
- `utils/`: SSE parser、AgentRunEvent reducer 和安全格式化。

不负责：
- 正式 Agent Run dashboard、历史 run 查询或持久化 replay。
- 任意 prompt playground、任意工具调用器或任意 fixture path 输入。
- 真实交易按钮、broker 执行或前端交易判断。
- 展示完整 prompt、CoT、secret、私有策略或 provider raw response。

不要继续放入：
- 不要在 route 文件里新增 stream/reducer/API 逻辑。
- 不要在组件中裸写 `fetch` 或后端 endpoint。
- 不要把原始 SSE JSON dump 作为主体验；新增事件展示应先扩展 reducer 的 display model。
