# AGENTS.md

## 定位

- `packages/agent` 是 Agent workflow 能力的预留 package。
- 该目录面向路由、分析、评分、记忆和多步骤工作流，不是 HTTP 入口。
- 当前目录尚未落地实现，只保留 package 边界。

## 行为约束

- 不在没有 issue、OpenSpec 或设计文档真源支撑的情况下提前实现 Agent 框架。
- 不把 Agent workflow 逻辑写进 `apps/api` 路由中。
- 落地后应通过 `packages/core` 使用共享配置、事件模型和持久化能力。
- Prompt、模型调用、工具调用和推理摘要需要避免泄露 secret、私有策略或完整敏感上下文。
- 当前设计方向是复用成熟 Agent / workflow / provider 能力；如果改为自研核心框架，必须有关联真源和验证证据。
- AgentRuntime、ToolRegistry 和 schema 化输出是长期边界；业务代码和插件不能绕过它们创建失控 Agent 行为。
- Agent 可以提出分析、交易计划草案或执行请求，但最终必须进入 Decision / Policy Gate。
- 不默认保存完整 chain-of-thought 或 provider 原始响应。
