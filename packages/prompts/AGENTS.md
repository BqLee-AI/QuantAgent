# AGENTS.md

## 定位

- `packages/prompts` 是共享 Prompt 资产的预留 package。
- 该目录面向可复用 Prompt 模板、系统提示片段和评估样例。
- 当前目录尚未落地实现，只保留 package 边界。

## 行为约束

- 不提交包含真实 secret、私有策略、未公开业务数据或敏感上下文的 Prompt。
- Prompt 应服务具体 workflow 或评估场景，不沉淀泛泛的方法论文字。
- Prompt 变更应说明影响的 Agent workflow 或使用场景。
- Prompt 不能替代 ToolRegistry、Skill Registry、IndustryAnalysis schema 或 Decision / Policy Gate。
- Market mapping、工具权限、输出 schema 和风险规则不能只藏在 Prompt 里。
- Agent 定义、Prompt 模板和评估样例正式落地后，再补充文件结构、验证方式和局部规则。
