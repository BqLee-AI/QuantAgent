## Context

`packages/agent` 已提供 `AgentRuntime`、`AgentDefinition`、`SubAgentDefinition`、`ToolProfile`、run-scoped artifact store、工具 hidden context 注入和稳定 stream event。半导体行业包当前只有 source binding 资产，还没有 MainAgent 资产或可验证的行业分析闭环。

本轮要把 `docs/agent` 中的 MVP 方案落到一个行业包 fixture，而不是实现完整生产交易系统。DeepAgents 的职责边界是：通过 `create_deep_agent()` 复用 `write_todos`、`task`、skills、backend 和 stream；QuantAgent 的职责边界是：由 `AgentRuntime` 注入工具、上下文、artifact store、权限和可审计事件。

## Goals / Non-Goals

**Goals:**

- 半导体行业包声明 MainAgent、一个 `evidence_research_analyst` SubAgent、行业 skill、tool profile 和 NVDA fixture。
- MainAgent 作为 PlannerExecutor 总控：读取 run context、规划 todo、决定是否委派 Research SubAgent、合成 `IndustryAnalysis`、调用评分/计划/提交工具。
- Research SubAgent 只负责搜索和证据压缩，产出 `EvidenceResearchReport` / `EvidenceBoard` artifact 引用。
- 一手财报 fixture 证明：发布后 5 分钟的第一手材料可通过搜索补充通用对照证据，再生成 ActionPlan 并走 mock/dry-run `submit_action_plan`。
- 后续媒体报道 fixture 证明：30 分钟后的二手报道能识别已有同主题 action / notification，最终 `record_only`，不生成 ActionPlan、不调用 submit、不重复通知。
- 测试在没有外部 LLM provider、Tavily key、真实账户和 broker 的情况下可运行。

**Non-Goals:**

- 不实现真实 Tavily HTTP adapter、真实 broker、真实账户读取、真实通知发送或生产 Policy Gate。
- 不新增 Market / Demand / SupplyChain / Risk / TradePlan 多个专家 SubAgent。
- 不新增财报、NVDA、市场预期、收入 surprise 等场景专用 tool schema 字段。
- 不改变 `AgentRuntime` 已有公共 contract，不让行业包绕过 runtime 直接创建 DeepAgents。

## Decisions

### 1. 行业包只声明资产，不创建 runtime

半导体行业包新增目录建议：

```text
plugins/industries/semiconductor-industry/
  agents/
    main.md
    subagents/evidence_research_analyst.md
    tool_profiles/main.yaml
    tool_profiles/evidence_research_analyst.yaml
  skills/
    market-analysis/SKILL.md
    evidence-research/SKILL.md
  fixtures/
    nvda_earnings_chain/
      events.yaml
      run_contexts.yaml
      fake_search_results.yaml
      fake_account_contexts.yaml
      expected_flows.yaml
  mappings/
    instruments.yaml
  README.md
```

实现可以按现有 loader 能力做最小切片，但文件职责必须保持清晰：prompt/skill、tool profile、fixture、mapping 和 README 不混在一个大文件。行业包不 import `packages/agent` 内部 runtime 实现，不直接调用 DeepAgents；测试或平台 loader 读取这些资产后构造通用 `AgentDefinition` / `SubAgentDefinition` / `ToolProfile`。

备选方案是把 NVDA fixture 放在 `packages/agent/testing`。本轮不选它作为唯一位置，因为 fixture 需要验证行业包资产和 README 边界；如需可复用 fake harness，可在 `packages/agent/testing` 放通用工具实现，但行业样例本身留在插件目录。

### 2. MainAgent 工具集保持精简

MainAgent tool profile 固定为：

- `get_run_context`
- `search_web`
- `get_account_context`
- `evaluate_thesis`
- `build_action_plan`
- `submit_action_plan`

Research SubAgent tool profile 固定为：

- `get_run_context`
- `search_web`

账户、持仓、近期 action、通知和用户策略只由 MainAgent 在行动前读取，不能扩散给 Research SubAgent。通知、审批、broker 和监控底层能力不直接暴露给 Agent，只能由 `submit_action_plan` 内部编排。

备选方案是给 MainAgent 暴露 `notify_user`、`request_approval` 或 broker 工具。该方案会导致通知与审批重复、行动入口分散和审计难以统一，因此不采用。

### 3. 证据获取用搜索工具 + EvidenceBoard artifact，而不是 collect_evidence 全能工具

MVP 只有 Tavily 搜索插件能力时，`search_web` 只负责按 run 记录 query、返回搜索结果摘要和必要 artifact 引用。`EvidenceBoard` 由 Research SubAgent 或 MainAgent 基于多次搜索和上下文读取形成，字段保持通用：

- `source_items`
- `claims`
- `relation_summary`
- `conflicts`
- `gaps`
- `safe_summary`

市场预期、历史基准、媒体报道、冲突证据都只是 `claims.role` 的不同取值或摘要，不进入工具 schema 专用字段。

### 4. ActionPlan 由工具生成，自动审批由 submit 结果表达

MainAgent 不在 prompt 中手写“已批准”或“已执行”。行动链路为：

```text
IndustryAnalysis draft
  -> evaluate_thesis
  -> build_action_plan
  -> submit_action_plan
  -> SubmitActionPlanResult
```

`build_action_plan` 负责仓位、止盈止损、失效条件、监控计划和用户通知草案。`submit_action_plan` 是唯一外部行动入口，负责 mock/dry-run 结果、自动审批策略、Policy Gate 摘要、通知结果和 monitoring task 摘要。自动审批成立的原因只能出现在 `SubmitActionPlanResult`，不能由 MainAgent 直接声明。

### 5. 两事件 fixture 使用同一通用产物链路

Event A：第一手财报公告。

```text
get_run_context
  -> task(evidence_research_analyst)
  -> get_account_context(include_recent_activity=true)
  -> evaluate_thesis(suggested_intent=propose_trade)
  -> build_action_plan
  -> submit_action_plan(mock/dry-run execute_then_notify)
  -> IndustryAnalysis
```

Event B：30 分钟后二手媒体报道。

```text
get_run_context
  -> get_account_context(include_recent_activity=true)
  -> optional lightweight search_web
  -> evaluate_thesis(suggested_intent=record_only, prior_coverage=fully_covered)
  -> IndustryAnalysis
```

Event B 不调用 `build_action_plan` 和 `submit_action_plan`，`IndustryAnalysis` 中 `action_plan_artifact_id` 与 `submission_id` 为空，并记录 `related_action_ids` / `related_notification_ids`。

### 6. Stream / artifact 验证以 fake harness 为主

测试优先使用已存在的 fake/scripted harness，不依赖真实模型。fixture 需要能断言这些事件类型或等价稳定摘要：

- `run.started`
- todo / planning 事件
- Research SubAgent task 事件
- tool call / tool result 事件
- artifact created 事件
- `run.completed`

如果 scripted harness 无法完全模拟 DeepAgents 内部 todo chunk，测试可断言 runtime 转换后的稳定 `AgentRunEvent`，而不是绑定 provider raw chunk。

## Risks / Trade-offs

- [Risk] 行业包资产目录过早复杂化。→ Mitigation：MVP 只新增 MainAgent、一个 Research SubAgent、两个 skill、两个 tool profile 和一个 fixture；README 写清后续专家 Agent 是非目标。
- [Risk] fixture 变成 NVDA 财报专用实现。→ Mitigation：tool schema、EvidenceBoard、IndustryAnalysis、ActionPlan 都保持通用字段；NVDA 只作为 fixture 数据。
- [Risk] Research SubAgent 获得账户上下文后造成隐私扩散。→ Mitigation：tool profile 测试必须断言 Research SubAgent 不包含 `get_account_context`，且 fake tool ledger 不出现该调用。
- [Risk] 自动审批被 MainAgent 当成自行决策。→ Mitigation：测试断言 `submit_action_plan` 的 result 才包含 `resolved_mode=execute_then_notify` 和 policy 摘要；MainAgent 输出只引用结果。
- [Risk] 后续媒体报道重复加仓或重复通知。→ Mitigation：Event B fixture 必须带近期 action / notification，测试断言 `submit_action_plan` 调用次数为 0，`recommended_actions` 为空。
- [Risk] 真实 Tavily / broker 后续接入时与 fake schema 不一致。→ Mitigation：fake tools 实现同名通用 Pydantic contract，真实 adapter 后续只替换工具实现，不改变 Agent prompt 与 fixture 语义。

## Migration Plan

1. 先合并 OpenSpec-only PR。
2. 实现 PR 从最新 `main` 新建分支，新增半导体行业包资产和必要测试 harness。
3. 使用 `uv run --package quantagent-agent python -m unittest discover -s packages/agent/tests` 或等价 unittest 命令验证无外部依赖测试。
4. 运行 `openspec validate add-semiconductor-mainagent-nvda-fixture --type change --strict --json`。
5. 若实现发现 `packages/agent` 公共 contract 需要变更，停止并补新的 OpenSpec，而不是在本 change 中静默扩大范围。
