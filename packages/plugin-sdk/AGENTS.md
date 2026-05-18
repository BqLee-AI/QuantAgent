# AGENTS.md

## 定位

- `packages/plugin-sdk` 是插件开发 SDK 的预留 package。
- 该目录面向插件 manifest、生命周期接口、配置 schema 和插件开发辅助能力。
- 当前目录尚未落地实现，只保留 package 边界。

## 行为约束

- 不在没有 issue、OpenSpec 或设计文档真源支撑的情况下提前设计完整 SDK。
- SDK 规则应服务 `plugins/` 和 `runtime/plugins` 的真实插件边界。
- 插件配置不得要求提交真实 secret；应使用 secret reference 或环境变量引用。
- 插件接口一旦落地，需要保持向后兼容或提供清晰迁移说明。
- `plugin.yaml`、受控 RuntimeContext、配置 schema、生命周期和依赖隔离是 SDK 的长期边界，但具体接口落地前不要在占位 package 中提前写死实现形态。
- SDK 不能让插件绕过 Registry、ToolRegistry、storage port、secret 管理或审计边界。
- 插件依赖自动安装必须受控、可审计、可重建，不污染主 Python 环境。
