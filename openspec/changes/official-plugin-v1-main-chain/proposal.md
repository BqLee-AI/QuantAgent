## 背景

Plugin Registry V1 已经把 `plugin.yaml`、manifest 扫描、配置 schema 查询和插件管理 API 的第一段收住，但官方插件体系还缺少一条可评审的主链路。当前讨论中的目标链路是：

```text
RSS -> Evidence -> Analysis -> Strategy Draft -> Discord -> Approval -> Binance Dry-run
```

这条链路横跨 Source Plugin、Data Tool、Analysis、Strategy、Notification、Approval、Executor 和核心 runtime。如果直接拆给具体实现 issue，容易让 RSS、Tavily、Discord 或 Binance 插件夹带核心底座职责，例如 RawEvent repository、SourceBinding、Scheduler、ToolRegistry、Policy Gate 或真实交易执行。

本 change 先用 OpenSpec 收住第一版官方插件主链路的职责边界、DTO 交接和推进顺序。它不实现插件代码，不改 runtime，不接真实交易，只为后续具体插件 issue 和 PR review 提供统一依据。

## 改动

- 定义官方插件 V1 主链路：RSS 发现事件，Readability/Tavily 补 evidence，Analysis 生成结构化分析，Strategy Draft 生成可审批策略草案，Discord 推送通知，Approval 承接审批，Binance Executor 只做 dry-run。
- 明确插件开发者边界：插件只负责自身能力、manifest、schema、输入输出 DTO 和插件级测试。
- 明确核心底座边界：Plugin Runtime、Scheduler、ToolRegistry、Event Bus、Persistence、Approval、Decision / Policy Gate、Audit 和 secrets/config 注入由核心系统负责。
- 明确 RSS 需要重新按插件包边界推进，不沿用旧的 “RSS -> RawEvent 入库” 大范围任务。
- 明确 Tavily 是 Source/Data Tool Plugin，不是插件编排器；其他插件或 Agent 后续只能通过 Plugin Runtime / ToolRegistry 调用它暴露的工具能力。
- 明确 Analysis 与 Strategy 分层：Analysis 输出事实解释和影响判断，Strategy Draft 输出可审批策略草案，不产生已批准执行请求。
- 明确 Binance 第一版只做 dry-run/mock executor，禁止 live trading、真实密钥和绕过审批。
- 定义后续实现 issue 和 PR 的 OpenSpec 依赖关系，避免具体插件 PR 偏离主线。

## 能力

### 新增能力

- `official-plugin-v1-main-chain`: 定义 QuantAgent 官方插件 V1 主链路、插件/核心职责边界、DTO 交接和 OpenSpec-first 推进方式。

## 影响

- `openspec/changes/plugin-registry-v1/**`：作为已存在的 Registry 前置能力，本 change 不修改它，但依赖其 manifest-first 方向。
- `plugins/sources/**`：后续 RSS、Readability、Tavily 等官方 source/data tool 插件的落位。
- `plugins/notifications/**`：后续 Discord Notification 插件的落位。
- `plugins/executors/**` 或后续 canonical executor 目录：后续 Binance dry-run executor 的落位。
- `packages/core/**`：后续 Plugin Runtime、Scheduler、ToolRegistry、Decision / Policy Gate、Audit 等核心底座不得被具体插件绕过。
- `apps/web/**`：后续插件控制台和审批工作台消费核心 API/DTO，不接插件自定义前端组件。
