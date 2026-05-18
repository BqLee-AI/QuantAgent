# AGENTS.md

## 定位

- `apps/scheduler` 是定时任务入口的预留目录。
- 该目录面向周期性抓取、扫描、限流和调度触发。
- 当前目录尚未落地实现，只保留运行入口边界。

## 行为约束

- 不在没有 issue、OpenSpec 或设计文档真源支撑的情况下提前实现 scheduler 框架。
- 不把长期调度逻辑隐藏在 API 请求生命周期里。
- scheduler 落地时，应复用 `packages/core` 的配置、数据库和共享基础设施。
- Pull 类 Source Plugin 不应自己随意启动轮询循环；调度、限流、重试和失败记录应由 scheduler 边界统一承接。
- 调度模型正式落地前，不在占位目录中提前写死 SourceBinding、队列或运行时实现形态。
- scheduler 的启动命令、健康检查和测试入口正式落地后，再补充到本文件。
