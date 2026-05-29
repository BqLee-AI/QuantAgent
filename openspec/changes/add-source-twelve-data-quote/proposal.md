## Why

QuantAgent 已经通过 `docs/design/06-source-plugin-design.md`、`docs/design/11-crawler-source-plugin-boundary.md` 和现有 RSS / Readability / Jina Source Plugin 实现，收住了官方 Source Plugin 的最小交付边界。但“股价 / 行情抓取插件”虽然已经在设计文档中被列为允许的 Source Plugin 类型，仓库里仍没有首个官方 market-data source 插件可作为后续行业包、事件链路和行情相关能力的基线。

如果现在直接开始实现股价插件，容易把“指定 symbols 的最新价格拉取”与历史 K 线、WebSocket 实时流、新闻联动、provider 聚合、策略告警等未来能力混在同一个首版实现中，导致插件配置契约、DTO 形状和运行时边界漂移。

这一刀先只收住官方 `Twelve Data` 股价 Source Plugin 的最小插件包边界、配置契约、频率约束和标准输出 DTO，让仓库先有一个与当前 `pull source` 运行时边界匹配的最新行情插件基线。

## What Changes

- 定义官方 `Twelve Data` 股价 Source Plugin 的插件包边界和最小目录结构。
- 定义 `plugin.yaml`、`config.schema.json`、README、入口实现和最小测试的最小交付物要求。
- 定义插件最小配置契约，覆盖 `symbols`、可选 `market`、超时控制和最小频率约束，不把真实 API key 暴露为公开 schema 普通字段。
- 定义插件输出贴齐平台约定的 Source Plugin 输出结构 / source runtime 可消费输出 DTO，用于表达 latest quote 类型事件。
- 明确插件只负责调用 Twelve Data latest quote / price 类接口、标准化响应和清晰失败返回，不负责调度、`RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限或生命周期。
- 明确首版按分钟级 pull source 设计，不在本 change 中引入 WebSocket / stream source、历史时间序列或多 provider 聚合。

## Capabilities

### New Capabilities

- `source-twelve-data-quote`: 官方 `Twelve Data` 股价 Source Plugin 按配置拉取指定 symbols 的最新价格，并返回平台约定的 Source Plugin 输出结构，供平台写入事件链路。

## Impact

- `openspec/changes/add-source-twelve-data-quote/`
- `plugins/sources/` 下新增官方 `Twelve Data` quote source plugin 时应遵循本 change
- `docs/design/06-source-plugin-design.md`
- `docs/design/11-crawler-source-plugin-boundary.md`
- 后续实现阶段可能新增 `plugins/sources/twelve-data-source/` 下的插件包与测试，但不应要求同时修改 API / web 才能成立
