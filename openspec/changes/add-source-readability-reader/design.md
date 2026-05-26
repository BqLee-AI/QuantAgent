## Context

当前 Source Plugin 体系已经明确：

- 插件开发者只声明插件能力和 `config.schema.json`
- 平台负责配置校验、保存、启停、调度、审计和生命周期
- 插件只消费平台传入的 DTO / `effective_config` 并返回标准 DTO
- 平台负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus 和权限控制

在这个边界下，`Readability Link Reader` 更适合作为一个可复用的官方 Source Plugin 能力先落地，再被新闻、财报、搜索等 crawler 插件复用。当前 issue `#139` 已经明确本轮不做 Runtime 接入、不做 `Jina Reader`、不做业务抓取插件，因此需要用 design 固化“只做 reader 插件包能力”的边界，避免后续实现时扩 scope。

## Goals / Non-Goals

**Goals:**

- 定义官方 `Readability Link Reader` Source Plugin 的最小插件包契约。
- 明确插件输出贴齐平台约定的 Source Plugin 输出结构 / source runtime 可消费输出 DTO。
- 明确插件消费最小配置字段集合，并由平台传入 `effective_config`。
- 明确插件内部可以封装成熟 Python 开源正文抽取库。
- 定义最小插件级验证方式，优先使用静态 HTML fixture 或受控输入。

**Non-Goals:**

- 不实现 `Jina Reader`。
- 不同时暴露 `tool.read_url` 查询工具。
- 不实现新闻聚合、RSS 轮询、搜索、财报、X/Twitter 或行情抓取。
- 不实现 API、Runtime、Scheduler、SourceBinding、RawEvent 入库、Event Bus 发布或前端管理台接入。
- 不引入 Playwright、浏览器自动化、复杂反爬、代理池或网页快照存储。

## Decisions

### Decision 1: 本轮只收住 `source/read` 插件形态

`Readability Link Reader` 本轮只作为官方 Source Plugin 交付，不同时暴露 `tool.read_url` 查询工具。

原因：

- issue `#139` 目标是先收住插件包能力和最小交付物。
- 同时引入 tool 形态会扩展到 ToolRegistry input/output schema、风险级别和更广的运行时契约。
- 后续如果确认有 Agent / UI 直接调用需要，再为 `tool.read_url` 开独立 issue 或 change。

### Decision 2: 插件输出对齐平台约定的 Source Plugin 输出结构

插件输出不引入新的轻量 reader DTO，而是对齐平台约定的 Source Plugin 输出结构 / source runtime 可消费输出 DTO。

原因：

- `docs/design/06-source-plugin-design.md` 和 `docs/design/11-crawler-source-plugin-boundary.md` 已经定义了“插件返回标准 DTO，由平台接管事件链路”的边界，reader 插件应贴齐这一条统一契约。
- issue `#139` 明确本轮要给后续 crawler / search 插件提供可复用基础件，直接贴齐平台约定输出结构能减少后续适配层。
- 这也符合当前文档已明确的“插件返回标准 DTO，由平台写入事件链路”的边界。

### Decision 3: 允许插件内部封装成熟 Python 开源正文抽取库

本轮不要求纯 Python 自写正文抽取逻辑，允许在插件内部封装成熟 Python 开源库作为实现细节。

原因：

- `Readability` 能力本质上依赖 HTML 正文抽取算法，成熟库更适合第一版快速建立稳定边界。
- 依赖只属于插件目录，不改变 `packages/core`、`apps/api`、`apps/web` 的依赖方向。
- 具体库名可在实现 PR 中结合许可证、维护性和本地验证再最终落定，但 OpenSpec 先允许这种实现路径。

### Decision 4: 正文读取输入以单 URL 和可选请求参数为主

插件最小配置字段只覆盖：

- `url`
- `headers`（可选）
- `timeout_seconds`（可选）
- 少量正文抽取相关参数（仅在实现需要时加入）

原因：

- 这符合 `#139` 当前边界，不提前引入反爬、代理、浏览器、批量 URL 或复杂策略配置。
- 也符合 `#137` 和 `11-crawler-source-plugin-boundary.md` 里“插件只声明需要的配置字段”的协作模型。

## Risks / Trade-offs

- 本轮不锁死具体正文抽取库名 -> 实现阶段仍需为许可证、维护性和平台兼容性做一次最终确认。
- 输出结构名称先保持在 Source Plugin 统一契约层，能避免 reader change 先行钉死后续还会统一的 DTO 名称；代价是实现阶段仍需把字段集合进一步落到具体运行时契约。
- 不同时暴露 `tool.read_url` 会让后续 Agent / UI 直接调用场景延后，但可以保持本轮边界清晰。
- 静态 HTML fixture 适合最小验证，但不能完全代表真实网页结构差异；真实站点兼容性仍要在后续插件增强中逐步验证。

## Migration Plan

1. 本 change 审核通过后，先创建 OpenSpec-only PR。
2. 获得维护者明确认可后，再进入实现分支。
3. 实现阶段新增官方 `readability` 插件目录和最小测试。
4. 如果引入插件内部依赖，在实现 PR 中说明用途、许可证边界和本地验证方式。

## Open Questions

- 具体选用哪一个 Python 正文抽取库最符合当前仓库的依赖、许可证和可维护性要求？
- `Readability Link Reader` 后续是否要再扩展为同时暴露 `tool.read_url`？
