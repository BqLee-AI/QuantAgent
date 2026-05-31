## Context

当前 Source Plugin 体系已经明确：

- 插件开发者只声明插件能力和 `config.schema.json`
- 平台负责配置校验、保存、启停、调度、审计和生命周期
- 插件只消费平台传入的 DTO / `effective_config` 并返回标准 DTO
- 平台负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus 和权限控制

在这个边界下，`Twelve Data` 更适合作为一个最小可运行的官方 market-data Source Plugin 单独落地，而不是直接把行情、新闻、搜索和流式订阅混成一个“股价爬虫系统”。当前讨论已经明确本轮目标是“指定 symbols 的 latest quote pull source plugin”，因此需要用 design 固化“只做首个 quote 插件基线”的边界，避免后续实现时扩 scope。

## Goals / Non-Goals

**Goals:**

- 定义官方 `Twelve Data` latest quote Source Plugin 的最小插件包契约。
- 明确插件输出贴齐平台约定的 Source Plugin 输出结构，不新增 quote 专用平台 DTO，也不反向固化 core 内部 DTO 名称。
- 明确插件消费的最小配置字段集合，并由平台传入 `effective_config`。
- 明确 Twelve Data API key 等敏感鉴权信息由平台统一控制，不进入插件公开 schema 的普通非敏感字段定义。
- 明确首版按分钟级 `pull source` 设计，默认只支持 latest quote 拉取，不承担秒级高频或流式行情职责。
- 定义最小插件级验证方式，优先使用 mock / fixture / 受控响应。

**Non-Goals:**

- 不实现 WebSocket / stream source。
- 不实现历史 K 线、技术指标、公司基本面、财报、新闻、搜索或 provider 聚合。
- 不同时引入多 provider failover 或通用 provider abstraction layer。
- 不实现价格告警、策略联动、行业路由增强或交易执行联动。
- 不实现 API、Runtime、Scheduler、SourceBinding、RawEvent 入库、Event Bus 发布或前端管理台接入。
- 不引入 `Readability` / `Jina Reader` fallback、Playwright、复杂反爬、代理池或网页快照存储。

## Decisions

### Decision 1: 本轮只收住 latest quote pull source 形态

`Twelve Data` 本轮只作为官方 `pull` Source Plugin 交付，能力聚焦于按配置拉取指定 symbols 的 latest quote。

原因：

- 当前仓库已经有 `pull source` 运行时和官方 source plugin 样例，最容易承接 quote 插件首版。
- Twelve Data 免费 credits 更适合分钟级轮询验证，不适合把首版目标定义成秒级高频行情流。
- 如果同时引入历史时间序列或流式订阅，会扩展到完全不同的执行模式和验收口径。

### Decision 2: 插件输出贴齐平台约定的 Source Plugin 输出结构

插件输出不引入新的平台级 quote 专用 DTO，也不在本 change 中把契约钉死为某个 core 内部 DTO 名称或文件路径，而是保持为平台约定的 Source Plugin 输出结构 / source runtime 可消费 DTO。

原因：

- 现有 Source Plugin 设计已经明确“插件返回标准 DTO，由平台写入事件链路”。
- 首版 quote 插件只需要让运行时能消费 latest quote 结果，不需要先引入新的跨模块契约层。
- 这可以避免在核心行情模型尚未稳定前，过早把平台内部类型名固化到 OpenSpec。

该输出结构至少应承载：

- `source_plugin_id`
- `source_type`
- `external_id`
- `title`
- 可选 `url`
- 可选 `canonical_url`
- 可选 `content`
- 可选 `published_at`
- `captured_at`
- `raw_payload`
- `metadata`

其中 `metadata` 至少应能表达：

- `provider`
- `symbol`
- `price`
- 可选 `currency`
- 可选 `market`
- `quote_timestamp`

### Decision 3: `source_type` 首版固定为 `market_quote`

首版 quote 插件输出的 `source_type` 固定为 `market_quote`。

原因：

- `rss`、`readability`、`jina` 已经通过 `source_type` 表达来源类型，quote 插件也需要稳定的最小来源分类。
- `market_quote` 比泛化的 `market_data` 更能限制首版范围，避免把历史序列、深度、基本面等未来行情能力一起带入。
- 后续若需要扩展到 `market_timeseries` 或其他类型，可以通过新 change 演进，不必在首版就预留过宽命名。

### Decision 4: `external_id` 首版固定采用 `provider:symbol:quote_timestamp`，缺失时间戳时直接失败

当 Twelve Data 响应无法提供可解析的 `quote_timestamp` 时，首版实现直接返回清晰失败，不做 fallback external_id 拼接。

原因：

- latest quote 场景通常没有 RSS 式天然 GUID，需要在首版定义最小稳定去重标识来源。
- `provider + symbol + quote timestamp` 能较好区分同一 symbol 不同时间点的行情。
- 直接失败比首版引入 provider_time / capture_time fallback 更容易保持去重语义稳定，避免不同实现各自扩展降级规则。
- 该约定仍然保持在 Source Plugin 输出边界内，后续若运行时 dedupe 需要补充策略，可以在后续 change 调整。

### Decision 5: 平台统一控制 Twelve Data 鉴权与频率策略

插件公开 `config.schema.json` 只覆盖最小业务字段和非敏感控制字段，不直接暴露真实 API key 值；调度频率和 credits 约束由平台 scheduler / binding policy 控制，插件只校验最小可接受配置并按单次调用执行。

原因：

- 仓库规则禁止把真实 secret、token 或生产配置固化到插件交付物中。
- Source Plugin 设计已明确 pull source 不允许自行 while loop 或后台线程调度。
- Twelve Data 免费 credits 同时受每分钟和每日额度约束，这更适合放在平台调度策略和 README 约束中，而不是让插件自行扩展为限额 runtime。

### Decision 6: Twelve Data 失败只清晰报错，不做 provider fallback

本轮对 Twelve Data 限流、超时、服务不可用或响应异常，只要求插件清晰失败返回，不要求自动切换到其他行情 provider。

原因：

- provider fallback 会扩展到供应商优先级、字段差异吸收和多 provider 配置，超出当前最小首版目标。
- 先收住单一 provider 的最小 quote 插件，更容易验证 Source Plugin 契约本身。

## Risks / Trade-offs

- Twelve Data 免费 credits 对 symbol 数量和轮询频率限制较强 -> 首版通过 README、schema 和 issue 边界把目标收成分钟级、少量 symbols 验证。
- 固定 `source_type=market_quote` 能限制首版范围 -> 但后续扩展历史行情时需要新增 change 演进。
- 不引入 provider fallback 能保持首版简单 -> 但在外部服务抖动时只能清晰报错，不能自动降级。
- 输出贴齐平台约定结构能减少当前实现阻力 -> 但后续若出现专门行情 DTO，需要再做契约升级。

## Migration Plan

1. 本 change 审核通过后，先创建 OpenSpec-only PR。
2. 获得维护者明确认可后，再进入实现分支。
3. 实现阶段新增官方 `twelve-data` quote source plugin 目录、README 和最小测试。
4. 如果后续需要 WebSocket / stream source、历史序列或新闻联动，应新开 issue / change，而不是在本实现 PR 中扩 scope。

## Open Questions

- Twelve Data API key 最终通过哪种平台 secret / policy 入口传入插件运行时，而不暴露为公开 schema 普通字段？
- 首版是否在 README 中直接声明“默认只建议 1-5 个 symbols，60 秒及以上轮询”，还是由 runtime policy 单独约束？
