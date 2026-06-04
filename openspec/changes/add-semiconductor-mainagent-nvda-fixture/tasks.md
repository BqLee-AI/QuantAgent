## 1. OpenSpec / 设计确认

- [x] 1.1 校验本 change 的 `proposal.md`、`design.md`、`specs/semiconductor-mainagent-fixture/spec.md` 和 `tasks.md` 通过 strict validate。
- [x] 1.2 OpenSpec-only PR 只包含本 change artifacts，不混入实现代码、依赖升级或无关文档。

## 2. 行业包资产实现

- [x] 2.1 在 `plugins/industries/semiconductor-industry/` 下新增 MainAgent prompt、`evidence_research_analyst` SubAgent prompt、tool profile、skill、mapping 和 README usage note。
- [x] 2.2 MainAgent 资产声明只描述编排职责、停止条件、工具选择和输出约束；不得直接调用通知、审批、broker 或监控底层能力。
- [x] 2.3 Research SubAgent 资产声明完整任务边界：多次窄 query、来源分层、EvidenceBoard / report 输出、禁止账户和交易计划。
- [x] 2.4 README 更新行业包职责：行业包声明资产，`AgentRuntime` 运行；真实 source binding 资产仍保留既有边界。

## 3. Fixture 与 fake tool

- [x] 3.1 新增 NVDA 两事件 fixture：T+5 一手财报公告、T+30 二手媒体报道。
- [x] 3.2 新增 fake search / account / evaluate / build action / submit 工具或复用 `packages/agent/testing` 既有 harness，确保无外部 API key 可运行。
- [x] 3.3 fake 工具 schema 使用通用 Pydantic contract 和 ID-first 引用；不得加入财报或 NVDA 专用字段。
- [x] 3.4 fake account context 支持 recent action / notification，用于后续媒体报道去重。

## 4. Runtime 组装与测试

- [x] 4.1 用行业包资产构造 `AgentDefinition`、`SubAgentDefinition` 和 `ToolProfile`，通过 `AgentRuntime` 启动 run，不直接创建 DeepAgents。
- [x] 4.2 测试一手事件：断言 Research SubAgent / task 被使用，EvidenceBoard artifact 创建，`evaluate_thesis`、`build_action_plan`、`submit_action_plan` 按顺序发生，submit 调用次数为 1。
- [x] 4.3 测试一手事件：断言 ActionPlan 包含方向、仓位、止损、止盈、失效条件、监控计划和用户通知草案，提交结果包含 mock/dry-run、policy gate、通知和监控摘要。
- [x] 4.4 测试二手报道：断言 recent activity 被读取，最终 `record_only`，`build_action_plan` 和 `submit_action_plan` 调用次数均为 0，不重复通知。
- [x] 4.5 测试两个 run 都产出 `IndustryAnalysis`，并断言关键 stream events：run、todo/planning、tool、subagent/task、artifact、final output。

## 5. Review / 验证 / PR

- [x] 5.1 实现后运行与范围匹配的 unittest 命令，例如 `uv run --package quantagent-agent python -m unittest discover -s packages/agent/tests`，并记录结果。
- [x] 5.2 运行 `openspec validate add-semiconductor-mainagent-nvda-fixture --type change --strict --json`。
- [x] 5.3 安排 SubAgent CR，重点检查 SubAgent 数量、工具权限、schema 通用性、账户上下文隔离、submit_action_plan 唯一行动入口和二手报道去重。
- [ ] 5.4 根据 CR finding 修复后再创建实现 PR；PR 说明写清 DeepAgents docs/examples、本地版本确认、验证命令、未验证风险和非目标。
