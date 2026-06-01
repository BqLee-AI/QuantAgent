## Why

Issue #215 要先把 `SourceBinding Template` 与 `Effective Config` 的平台契约收住，才能继续推进 `#216` 的持久化、`#217` 的 scheduler loop、`#225` 的行业包模板目录和 `#226` 的 API 契约。当前设计文档已经明确“source 默认配置 + 行业包覆盖 = effective config”，但仓库里还没有一份可审查的规范来回答字段归属、合成优先级、secret reference 边界和谁能消费哪一层配置。

如果继续直接做 `SourceBinding` ORM、调度器或 API，执行者会各自发明不同的配置对象、合并逻辑和审计方式，最终让 scheduler、persistence、industry package 和 source plugin 对同一个 binding 使用不同命名和不同安全边界。

## What Changes

- 新增一份 `SourceBinding Template` 契约，定义平台归一化后的模板层字段、允许的 override 形式，以及哪些字段明确不属于模板层。
- 新增一份 `Effective Source Config` 契约，定义平台合成后的稳定快照字段、配置来源层级、合并优先级、校验入口和未知字段处理策略。
- 明确三层边界：模板层、可审计的 `EffectiveSourceConfig` 快照层、仅运行时短暂存在的 secret 注入执行层。
- 明确 `schedule_policy`、`retry_policy`、`rate_limit_policy` 与 source-specific `config` 的分层关系，避免平铺成单一大 JSON blob。
- 明确平台、scheduler、持久化、API 和插件各自的消费边界，禁止插件自行做 override 合并、secret 解引用或重新计算 effective config。

## Capabilities

### New Capabilities

- `source-binding-effective-config-contract`: 定义 `SourceBindingTemplate` 与 `EffectiveSourceConfig` 的字段、来源层级、secret 边界和跨模块消费契约。

### Modified Capabilities

- 无

## Impact

- `packages/core` 后续将承接模板归一化、effective config 合成、策略对象校验和审计快照所有权。
- `packages/plugin-sdk` 后续只复用既有 runtime DTO 入口传递平台生成的 `effective_config`，不新增插件自管合成逻辑。
- `plugins/**/config.schema.json` 与未来行业包模板资产会成为该契约的输入真源，但本 PR 不修改任何插件代码或模板目录。
- `apps/scheduler`、未来 `SourceBinding` 持久化和 API 只消费平台生成的快照，不重算合成逻辑，也不接触 secret 明文。
