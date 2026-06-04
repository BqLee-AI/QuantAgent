## ADDED Requirements

### Requirement: Agent Debug Chat route is development-only
Web 应用 SHALL 在 development/test/local 环境提供 `/debug/agent-run-chat` 路由，并 SHALL 在 production router 中排除该 route 和页面模块。

#### Scenario: Development route is available
- **WHEN** 开发者在 development 环境访问 `/debug/agent-run-chat`
- **THEN** Web 应用渲染 Agent Debug Chat 页面
- **AND** 页面使用现有应用 layout 壳层

#### Scenario: Production route is excluded
- **WHEN** 应用以 production route API 构建或运行
- **THEN** `/debug/agent-run-chat` 不会被注册
- **AND** production route API 不 import Agent Debug Chat feature page module

### Requirement: Agent Debug Chat uses streaming SSE
Agent Debug Chat SHALL 通过后端 Agent debug SSE endpoint 启动 allowlisted fixture run，并 SHALL 在收到每个 `AgentRunEvent` 后增量更新页面。

#### Scenario: NVDA fixture streams visible intermediate states
- **WHEN** 开发者选择 `semiconductor-nvda-earnings` fixture 和 `primary` scenario 并启动运行
- **THEN** 页面请求 `POST /api/v1/debug/agent-runs/fixtures/{fixture_id}/stream`
- **AND** 页面在 stream 未结束前展示 streaming 状态和中间事件
- **AND** 页面不是等待完整 run 结束后一次性渲染结果

#### Scenario: Stream can be stopped
- **WHEN** 开发者在 streaming 状态点击停止或离开页面
- **THEN** Web 应用 abort 当前 SSE 请求
- **AND** 页面状态变为 aborted 或安全结束状态

### Requirement: AgentRunEvent maps to chat display model
Web 应用 SHALL 将 `AgentRunEvent` 映射成稳定的 chat display model，用于展示 coordinator 输出、todo/progress、tool、SubAgent、artifact 和 final summary。

#### Scenario: Core event kinds render as structured chat content
- **WHEN** stream 收到 `run.started`、`todo.updated`、`tool.completed`、`subagent.completed`、`artifact.created` 和 `run.completed`
- **THEN** 页面展示 assistant-like message、todo/progress 信息、tool card、SubAgent card、artifact card 和 final summary
- **AND** 组件不直接把原始 SSE JSON 作为主内容 dump 出来

#### Scenario: Failed event renders safe error state
- **WHEN** stream 收到 `run.failed` 或 stream adapter 抛出错误
- **THEN** 页面展示失败状态和安全摘要
- **AND** 页面不展示 traceback、secret、完整 prompt、CoT、私有策略或 provider raw response

### Requirement: Agent Debug Chat feature follows Web file responsibility rules
Agent Debug Chat SHALL 按 feature 目录拆分 API、contracts、stream adapter、business hook、components、types、utils 和 README，route 文件 SHALL 只做入口组合。

#### Scenario: Route stays thin
- **WHEN** `/debug/agent-run-chat` route 被注册
- **THEN** route component 只渲染 feature page
- **AND** route 文件不直接执行 fetch、SSE parsing、message reducer、业务状态编排或复杂 JSX

#### Scenario: Feature exposes documented responsibilities
- **WHEN** 维护者查看 `features/debug/agent-run-chat/README.md`
- **THEN** README 说明 route 入口、公开 page/hook/API、子目录职责和非目标
- **AND** README 明确该 feature 不负责正式 Agent Run dashboard、真实交易、任意 prompt playground 或敏感信息展示

### Requirement: Agent Debug Chat follows DeepAgents frontend interaction model
Agent Debug Chat SHALL 参考 DeepAgents 官方 frontend 的 coordinator、todo/progress、tool call、SubAgent 和 artifact 展示模型，但 MUST 使用 QuantAgent 后端提供的稳定 SSE `AgentRunEvent` 契约。

#### Scenario: Official pattern is adapted rather than copied blindly
- **WHEN** 实现 Web debug chat
- **THEN** UI 信息层级覆盖 coordinator/assistant message、todo/progress、tool/subagent/artifact cards
- **AND** 实现不要求 LangGraph deployment endpoint 或 `@langchain/react useStream`
- **AND** 代码和 PR 说明记录已参考 DeepAgents frontend docs / examples
