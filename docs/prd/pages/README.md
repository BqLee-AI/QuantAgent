# 页面 PRD 附录索引

本目录是 [操盘者工作台 V1 页面与治理信息架构](../08-frontend-pages-overview.md) 的页面附录。

页面附录只描述页面任务、入口、出口、状态、风险边界和验收口径；最终 API 字段、DTO、Zod schema 和 generated client 以后续 OpenSpec 与 `packages/contracts` 为准。

## 阅读顺序

1. 先读 `../08-frontend-pages-overview.md`，确认主链路和治理对象层级。
2. 再读 `../09-scoring-and-prioritization.md`，确认评分展示语义。
3. 最后按本目录阅读页面附录。

## P0 主链路页面

- [00 Dashboard](00-dashboard.md)
- [01 登录页](01-login.md)
- [02 高价值事件中心](02-events-home.md)
- [03 事件详情 / 决策页](03-event-detail.md)
- [04 审批工作台](04-approvals-index.md)
- [05 审批详情页](05-approval-detail.md)
- [06 一次性授权页](06-approval-link.md)
- [16 事件级审计时间线](16-event-audit-timeline.md)

## P1 解释与排障页面

- [07 Runtime](07-runtime-dashboard.md)
- [08 Agent Run 详情](08-runtime-agent-run-detail.md)
- [09 Tool Invocation 详情](09-runtime-tool-detail.md)

## P2 治理页面

- [10 Registry / Plugins](10-plugins-index.md)
- [11 Plugin Detail](11-plugin-detail.md)
- [12 Model Providers / LLM Policies](12-models.md)
- [15 Settings](15-settings.md)

## 不是 V1 顶层页面的对象

以下对象可以在运行详情、插件详情或后续 deep link 中展示，但不作为 V1 顶层产品导航：

- Skill：在 Agent Run、Plugin Detail、Industry 插件能力视图中展示。
- Tool：在 Tool Invocation、Agent Run、Plugin Detail 中展示。
- Industry Package：作为 `industry` 类型插件治理，不单独和 Plugin 平铺。
- Source Binding：作为 Industry 插件详情和路由解释的一部分。
- Broker：作为 `broker` 类型插件治理，并受 Approval / Policy Gate 约束。

对应旧草案中的独立 Skill、Tool、Industry 页面已删除，避免误导后续实现。

## 页面附录写法

每个页面应尽量覆盖：

- 页面定位。
- 用户任务。
- 主对象和真源。
- 入口与出口。
- 关键模块。
- 状态与失败路径。
- 安全和风控边界。
- 验收口径。
- 非目标。
