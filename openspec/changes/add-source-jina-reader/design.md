## Context

当前 Source Plugin 体系已经明确：

- 插件开发者只声明插件能力和 `config.schema.json`
- 平台负责配置校验、保存、启停、调度、审计和生命周期
- 插件只消费平台传入的 DTO / `effective_config` 并返回标准 DTO
- 平台负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus 和权限控制

在这个边界下，`Jina Reader` 更适合作为一个可复用的官方 Source Plugin 能力单独落地，再被新闻、财报、搜索等 crawler 插件复用。当前 issue `#169` 已经明确本轮不做 Runtime 接入、不做 `tool.read_url`、不做业务抓取插件，因此需要用 design 固化“只做 reader 插件包能力”的边界，避免后续实现时扩 scope。

## Goals / Non-Goals

**Goals:**

- 定义官方 `Jina Reader` Source Plugin 的最小插件包契约。
- 明确插件输出贴齐平台约定的 Source Plugin 输出结构，不新增 reader 专用 DTO，也不反向固化 core 内部 DTO 名称。
- 明确插件消费最小公开配置字段集合，并由平台传入 `effective_config`。
- 明确外部 reader 鉴权信息由平台统一控制，不进入插件公开 schema。
- 明确是否允许外发 URL 由平台策略结果决定，插件只遵循平台传入的允许/禁止外发边界。
- 定义最小插件级验证方式，优先使用 mock / fixture / 受控响应。

**Non-Goals:**

- 不修改 `Readability` 插件的边界、实现或验收口径。
- 不同时暴露 `tool.read_url` 查询工具。
- 不实现新闻聚合、RSS 轮询、搜索、财报、X/Twitter 或行情抓取。
- 不实现 API、Runtime、Scheduler、SourceBinding、RawEvent 入库、Event Bus 发布或前端管理台接入。
- 不引入 Playwright、浏览器自动化、复杂反爬、代理池或网页快照存储。
- 不实现自动 fallback 到 `Readability` 或其他 reader 的运行时编排。

## Decisions

### Decision 1: 本轮只收住 `source/read` 插件形态

`Jina Reader` 本轮只作为官方 Source Plugin 交付，不同时暴露 `tool.read_url` 查询工具。

原因：

- issue `#169` 目标是先收住插件包能力和最小交付物。
- 同时引入 tool 形态会扩展到 ToolRegistry input/output schema、风险级别和更广的运行时契约。
- 后续如果确认有 Agent / UI 直接调用需要，再为 `tool.read_url` 开独立 issue 或 change。

### Decision 2: 插件输出贴齐平台约定的 Source Plugin 输出结构

插件输出不引入新的 reader 专用 DTO，也不在本 change 中把契约钉死为某个 core 内部 DTO 名称或文件路径，而是保持为平台约定的 Source Plugin 输出结构 / source runtime 可消费 DTO。

原因：

- `#155` 已经把 reader / source 插件边界收回到“插件遵循平台统一运行时 IO 契约”，而不是为某个 reader change 先锁死 core 内部实现名词。
- issue `#169` 本轮只需要定义 `Jina Reader` 作为插件包应返回的平台约定输出形状，避免后续实现直接耦合到某个内部模块路径。
- 这也符合当前文档已明确的“插件返回标准 DTO，由平台写入事件链路”的边界。

当前 change 只要求该输出结构能承载 source runtime 消费所需的最小信息，例如：

- `source_plugin_id`
- `source_type`
- `title`
- 可选 `external_id`
- 可选 `url`
- 可选 `canonical_url`
- 可选 `content`
- 可选 `author`
- 可选 `published_at`
- `captured_at`
- `raw_payload`
- `metadata`
- 可选 `dedupe_hint`

具体 DTO 名称、模块路径和最终统一 IO 契约由平台插件协议收口，本 change 不单独定义或绑定。

### Decision 3: 外部 reader 鉴权由平台统一控制

插件公开 `config.schema.json` 只覆盖最小非敏感字段，不直接暴露原始 token、私有账号或其他外部 reader 鉴权秘密。

原因：

- issue `#169` 明确不提交真实 token、cookie、付费服务账号或生产 URL 白名单。
- 外部 reader 调用属于插件实现细节，但鉴权仍应受平台统一 secret / policy 边界约束。
- 这能避免插件 schema 直接变成真实敏感配置入口，降低后续控制台和 API 配置泄露风险。

### Decision 4: 是否允许外发 URL 由平台策略边界决定

插件不自行猜测某个 URL 是否可以外发，而是遵循平台传入的允许/禁止外发策略、DTO 标记或等价 policy 结果；当平台判定该 URL 不应外发时，插件不进入外部 reader 请求路径，并返回清晰拒绝或失败信息。

原因：

- `docs/design/06-source-plugin-design.md` 已明确敏感或私有链接不应默认走外部 reader。
- issue `#169` 目标是先收住安全边界，不把真实外部服务账号、配额和组织级策略混进本轮。
- 某个 URL 是否允许外发，本质上是平台权限 / policy / allowlist 决策，不是 reader 插件自己可靠判断的职责。

### Decision 5: 外部 reader 失败只清晰报错，不做自动 fallback 编排

本轮对限流、服务不可用、超时或外部 reader 返回失败，只要求插件清晰失败返回，不要求自动切换到 `Readability` 或其他 reader。

原因：

- 自动 fallback 会扩展到多 reader 编排、优先级和失败恢复策略，已经超出当前插件包边界。
- issue `#169` 明确本轮不做运行时编排和复杂抓取链路。
- 保持清晰失败返回，足以为后续实现层或 runtime 层单独设计 fallback 提供稳定契约。

## Risks / Trade-offs

- 外部服务依赖会带来可用性、限流和超时风险 -> 本轮通过清晰失败返回和最小验证收住，不做自动恢复。
- 由平台决定 URL 是否允许外发可以降低插件越权判断和策略漂移风险 -> 但要求后续平台明确策略传递方式。
- 不暴露 `tool.read_url` 会让 Agent / UI 直接调用场景延后 -> 但能保持本轮 reader 插件边界清晰。
- 贴齐平台约定的 source 输出结构能减少后续适配歧义 -> 但要求统一插件 IO / source runtime 契约继续保持清晰稳定。

## Migration Plan

1. 本 change 审核通过后，先创建 OpenSpec-only PR。
2. 获得维护者明确认可后，再进入实现分支。
3. 实现阶段新增官方 `jina` 插件目录和最小测试。
4. 如果需要访问外部 reader 服务，在实现 PR 中说明平台统一鉴权策略、网络假设和最小本地验证方式。

## Open Questions

- 平台后续以什么 secret / policy 入口向 `Jina Reader` 提供外部服务鉴权，而不暴露为插件公开 schema？
- 平台后续以什么 DTO 标记、policy 结果或 allowlist 机制把“允许/禁止外发 URL”传入插件协议？
