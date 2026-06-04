## 1. OpenSpec / 外部参考确认

- [x] 1.1 运行 `openspec validate add-web-agent-debug-chat --type change --strict --json`，确认 artifacts 可校验。
- [x] 1.2 创建 OpenSpec-only PR 并合并后再进入实现。
- [x] 1.3 实现前读取 DeepAgents frontend docs / examples，并记录可复用的 coordinator、todo、tool、SubAgent、artifact 展示模式和不照搬 `useStream` 的原因。

## 2. Runtime API / Stream Adapter

- [x] 2.1 新增 `features/debug/agent-run-chat/api/agent-debug.contracts.ts`，定义 fixture summary、run request、SSE event、stream options 类型。
- [x] 2.2 新增 `features/debug/agent-run-chat/api/agent-debug.api.ts`，封装 fixture list 和 start stream endpoint，不在组件中裸写 endpoint。
- [x] 2.3 新增 `features/debug/agent-run-chat/api/agent-debug.stream.ts`，封装 SSE fetch、credentials、abort signal、frame parsing 和错误转换。
- [x] 2.4 更新 `app/runtime/runtime.types.ts` 与 `runtime.factory.ts`，将 `agentDebug` API 挂到 runtime-scoped `apis`。

## 3. Event Model / Hook

- [x] 3.1 新增 `types/agent-debug.types.ts`，定义 chat status、message、tool/subagent/artifact display model。
- [x] 3.2 新增 `utils/agent-run-sse-parser.ts`，实现分块 SSE text 到 event frame 的纯解析。
- [x] 3.3 新增 `utils/agent-run-event-reducer.ts`，将 `AgentDebugSseEvent` 归并为 chat display state。
- [x] 3.4 新增 `hooks/use-agent-run-chat-page.ts`，组合 fixture list、scenario 选择、start/stop/retry、stream lifecycle 和 reducer 状态。

## 4. UI Components / Debug Route

- [x] 4.1 新增 `components/page/AgentRunChatPage.tsx`，组合控制区、状态条、消息流和状态组件。
- [x] 4.2 新增 controls、conversation、tool/subagent/artifact cards、status 和 states 组件，覆盖 idle、loading、streaming、completed、failed、aborted、API unavailable。
- [x] 4.3 更新 `debug/router/route-api.development.tsx`，挂载 `/debug/agent-run-chat`，route 只渲染 feature page。
- [x] 4.4 更新 `debug/workbench/DebugPages.tsx` 根页入口，production route API 保持 noop。
- [x] 4.5 新增 `features/debug/agent-run-chat/README.md`，说明入口、公开模块、子目录职责、安全边界和非目标。

## 5. 测试 / 验证

- [x] 5.1 为 SSE parser / event reducer 补 unit tests，覆盖 started、todo、tool、subagent、artifact、completed、failed 和敏感字段不展示。
- [x] 5.2 补 component 或 smoke test，使用 mock stream 验证页面 streaming 中间态、tool/subagent/artifact/final 内容和停止行为。
- [x] 5.3 运行 `bun run --cwd apps/web test:unit`。
- [x] 5.4 运行 `bun run --cwd apps/web build`，确认 route tree 和 production build 通过。
- [x] 5.5 运行 `git diff --check`。

## 6. Review / PR

- [x] 6.1 安排 SubAgent CR，重点检查 route 是否变厚、feature 是否拆分、stream adapter 是否裸 fetch 泄漏到组件、debug 是否进入 production、敏感信息是否展示。
- [x] 6.2 根据 CR 修复后创建实现 PR，并在 PR 说明中写清 DeepAgents docs/examples 参考点、验证结果和残余风险。
