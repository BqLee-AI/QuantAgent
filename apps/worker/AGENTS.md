# AGENTS.md

## 定位

- `apps/worker` 是后台任务执行入口的预留目录。
- 该目录面向数据抓取、事件路由、插件任务和长耗时任务的独立运行入口。
- 当前目录尚未落地实现，只保留运行入口边界。

## 行为约束

- 不在没有 issue、OpenSpec 或设计文档真源支撑的情况下提前实现 worker 框架。
- 不把 worker 专属逻辑塞进 `apps/api` 来临时代替后台任务入口。
- 落地 worker 时，应复用 `packages/core` 的配置、数据库和共享基础设施。
- worker 不承担 HTTP 展示边界，不作为 API 路由的替代品。
- Source、Agent、插件任务等能力正式落地时，必须遵守 Event Bus、AgentRuntime、Registry 和审计边界。
- worker 的启动命令、健康检查和测试入口正式落地后，再补充到本文件。
