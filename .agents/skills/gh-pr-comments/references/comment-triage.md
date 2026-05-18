# PR 评论分诊清单

## must-fix

- 破坏 OpenSpec requirement 或 issue 验收。
- 引入 secret 泄露、权限绕过、Policy Gate 绕过。
- API envelope、DTO、WebSocket 状态真源或数据库迁移边界被破坏。
- 测试显示失败，或评论指出当前 PR 范围内的真实未覆盖风险。
- 违反当前路径的 `AGENTS.md`。

## should-fix

- 命名、边界或测试可以小成本变清楚。
- 错误处理、脱敏、验证命令说明可以小范围补齐。
- 文档或 PR body 缺少证据链。

## needs-discussion

- 要新增 package、依赖、外部服务、持久化模型或执行路径。
- 要改变 issue 非目标或 OpenSpec scope。
- 要把 dry-run/mock 提升为真实执行。
- 要改变插件、AgentRuntime、ToolRegistry、Decision / Policy Gate 长期边界。

## defer

- 与当前 PR 目标相邻但不是同一个问题。
- 需要单独 OpenSpec change 或更大验证。
- 有价值但不在当前 critical path。

## not-applicable

- 评论指向的代码已不存在或上下文错误。
- 建议基于旧版本 API。
- 建议与本仓库已确认的非目标冲突。
- 建议会引入过度抽象或跨 package 反向依赖。

## 回复证据优先级

1. 当前代码和测试结果
2. OpenSpec artifacts
3. 路径下 `AGENTS.md`
4. `docs/design/`
5. 官方文档或已安装版本
6. PR/issue 中维护者明确确认
