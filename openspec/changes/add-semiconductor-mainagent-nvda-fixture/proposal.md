## Why

`AgentRuntime` 基础设施已经具备统一 DeepAgents 入口，但还缺少一个真实行业包样例来证明 MainAgent 能按 MVP 架构完成“路由事件 -> 证据补充 -> 评分 -> 行动计划 -> 受控提交 / record_only”的闭环。半导体 NVDA 财报链路同时覆盖一手消息时效性、补市场对照、后续媒体报道去重、通知抑制和 dry-run 自动审批边界，适合作为首个可测试 fixture。

## What Changes

- 在半导体行业包中声明 MainAgent、`evidence_research_analyst` SubAgent、行业 skill / prompt 资产、tool profile 和 NVDA 两事件 fixture。
- 固定 MVP 只包含一个可选 Research SubAgent；市场、需求、供应链、风险和交易计划专家 Agent 不进入本轮实现。
- 为 MainAgent 配置精简工具集：`get_run_context`、`search_web`、`get_account_context`、`evaluate_thesis`、`build_action_plan`、`submit_action_plan`。
- 为 Research SubAgent 配置最小工具集：`get_run_context`、`search_web`，并明确不得读取账户、生成交易计划或提交动作。
- 提供无外部 API key 的 fixture / fake tools，覆盖 NVDA 一手财报触发 dry-run 做多和 30 分钟后二手媒体报道 `record_only` 两条链路。
- 约束工具和产物传递继续使用通用 schema 与 ID-first 引用，不新增财报或 NVDA 专用字段。

## Capabilities

### New Capabilities

- `semiconductor-mainagent-fixture`: 半导体 MainAgent / Research SubAgent 资产、工具 profile、NVDA 两事件 fixture、产物归属、去重和受控提交行为。

### Modified Capabilities

- `deepagents-agent-runtime-mvp`: 复用已合入的 AgentRuntime 行业包资产声明与 run-scoped tool / artifact / stream 契约；本 change 不修改该 capability 的既有 requirement。

## Impact

- 受影响目录：
  - `plugins/industries/semiconductor-industry/`：新增 agent、subagent、skill、fixture、mapping 或 README usage note。
  - `packages/agent/`：如需补充测试 harness fixture 或通用 mock tool，可在既有 runtime 契约内扩展，不改变公共 contract 的语义。
  - `openspec/changes/add-semiconductor-mainagent-nvda-fixture/`：记录本轮设计、规范和任务。
- 不引入真实 Tavily secret、真实 broker、真实账户或生产交易执行。
- 不让行业包直接调用 `create_deep_agent()`；行业包只声明资产，由 `AgentRuntime` 创建并运行 DeepAgents。
