# AGENTS.md

## 定位

- `packages/plugin-sdk` 是插件开发 SDK 的预留 package。
- 该目录面向插件 manifest、生命周期接口、配置 schema 和插件开发辅助能力。
- 当前已落地 Plugin Runtime V1 的最小 SDK 基座，面向插件作者提供 DTO、Protocol、结构化错误和可选轻量基类。

## 行为约束

- 涉及 `packages/plugin-sdk/**` 的规划、实现和 review 必须读取 `.agents/skills/references/core-and-plugin-architecture-gate.md`，把目标分层落实到 issue、OpenSpec、实现计划或 PR 说明。
- 不在没有 issue、OpenSpec 或设计文档真源支撑的情况下提前设计完整 SDK。
- SDK 规则应服务 `plugins/` 和 `runtime/plugins` 的真实插件边界。
- 插件配置不得要求提交真实 secret；应使用 secret reference 或环境变量引用。
- 插件接口一旦落地，需要保持向后兼容或提供清晰迁移说明。
- `plugin.yaml`、受控 RuntimeContext、配置 schema、生命周期和依赖隔离是 SDK 的长期边界，但具体接口落地前不要在占位 package 中提前写死实现形态。
- `BasePlugin` 是插件作者体验层，用于减少生命周期样板；Runtime 不能把继承 `BasePlugin` 作为唯一接收条件。
- SDK 负责稳定 Runtime DTO、Protocol 和结构化错误边界；不要把宿主侧插件加载、Registry 查询或生命周期编排塞进 SDK。
- SDK 不能让插件绕过 Registry、ToolRegistry、storage port、secret 管理或审计边界。
- SDK 不能向插件暴露 DB session、ORM model、scheduler、Event Bus publisher、内部 service 或任意 secret resolver。
- 插件依赖自动安装必须受控、可审计、可重建，不污染主 Python 环境。
