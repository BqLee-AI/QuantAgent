## Context

QuantAgent 的事件链路以 Source Plugin 作为输入边界，设计文档已经约定 pull source 必须由统一调度边界触发，Source Plugin 只负责采集和标准化原始信息。当前代码只有 placeholder source plugin，没有可运行的 RSS 采集、RawEvent 持久化、SourceBinding 调度单位或 fetch run 记录。

本 change 的目标是在不引入复杂 crawler 的前提下，打通最小 RSS pull source 到 RawEvent 的闭环。实现需要同时触及 core DTO、ORM model、repository、source service、manifest 发现和官方插件目录，因此需要用 design 固化关键边界。

## Goals / Non-Goals

**Goals:**

- 建立最小 pull Source Plugin 协议，让 worker / scheduler 后续可以通过稳定接口触发 source fetch。
- 建立 RawEvent 入库和去重能力，为后续 RawEvent -> Event 标准化和 Event Bus 提供输入。
- 建立 SourceBinding 作为调度单位，而不是直接调度裸 source plugin。
- 记录每次手动 fetch 的运行状态、计数、耗时和错误摘要。
- 以官方插件形式新增 RSS Source，通过 `plugin.yaml` 注册并产出 RawEventDraft。

**Non-Goals:**

- 不实现长期 scheduler loop。
- 不实现 push source 或 stream source。
- 不实现 Playwright crawler、代理池、验证码处理、复杂反爬或网页快照。
- 不实现 Router Agent、Industry Plugin、Decision、Notification 或交易执行。
- 不接入真实私有 feed、token、API key 或生产 secret。
- 不实现完整插件市场、签名校验、复杂依赖安装或热重载。

## Decisions

### Decision 1: 协议和领域 DTO 放在 `packages/core`

运行时消费的 `RawEventDraft`、`SourceBindingConfig` 和 pull source 协议放在 `packages/core`。官方 RSS 插件依赖这些稳定协议，core 不依赖具体插件实现。

替代方案是先把所有协议放进 `packages/plugin-sdk`。这个方案暂不采用，因为当前 SDK 仍是预留边界，过早扩张 SDK 容易把运行时协议、插件作者辅助工具和具体实现混在一起。先让 core 承载运行时需要的最小契约，更符合 API、worker、scheduler 共享基础设施的边界。

### Decision 2: 第一版只实现手动 fetch service，不实现 scheduler loop

`SourceFetchService` 负责给定 plugin 和 SourceBinding 后触发一次 fetch，并记录结果。它不负责长期循环、队列、定时策略或分布式调度。

替代方案是直接实现 `apps/scheduler` 的 loop。这个方案暂不采用，因为当前第一刀需要先验证 RawEvent、去重、绑定配置和 fetch run 记录；长期调度涉及频率、并发、重试、熔断、暂停恢复和运维状态，适合后续独立 change。

### Decision 3: RawEvent 去重优先使用 source external id

去重 identity 优先使用 `source_plugin_id + external_id`。当 source 没有 external id 时，使用 `source_plugin_id + canonical_url + content_hash`。保留 dedupe reason 便于后续审计。

替代方案是只用 URL 或只用内容 hash。只用 URL 对不稳定 URL 和 feed mirror 不够稳；只用内容 hash 又可能把不同来源的相似短内容误合并。组合 source plugin id 能降低跨 source 误判。

### Decision 4: RSS 插件使用标准库解析，不新增依赖

RSS Source 使用 Python 标准库 `urllib.request` 和 `xml.etree.ElementTree` 实现最小 RSS / Atom 解析。

替代方案是引入 feedparser。这个方案后续可以考虑，但第一版先避免新增依赖和 lockfile 变更，降低 PR 风险。标准库实现只覆盖基础字段，复杂 feed 扩展留给后续增强。

### Decision 5: manifest 解析使用最小 YAML 子集

第一版只需要识别当前官方插件 manifest 的简单字段和 list 字段，因此实现最小解析器用于本地发现和测试。

替代方案是引入完整 YAML 解析库。这个方案适合正式 Registry 落地时采用；当前没有新增依赖，且 manifest 解析不是本 change 的核心目标，因此保持最小实现。

## Risks / Trade-offs

- 最小 YAML 解析不支持完整 YAML 语法 -> 后续 Registry 落地时替换为受控 YAML parser，并补充 manifest schema 校验。
- RSS 标准库解析覆盖面有限 -> 初版只承诺 RSS / Atom 基础字段，复杂字段和 feed 扩展后续按真实需求增强。
- 当前只支持手动 fetch -> 后续必须在 worker / scheduler 边界实现长期调度，不允许让 source plugin 自行启动循环。
- SQLite migration 验证不能完全代表 PostgreSQL 行为 -> PR 说明保留未验证风险，后续接入真实数据库时补充 PostgreSQL migration 验证。
- SourceBinding 只有最小 DTO / ORM -> 后续需要 API 管理端、配置 schema 表单和审计日志时另开 change 扩展。

## Migration Plan

1. 新增 Alembic revision，创建 `raw_events`、`source_bindings` 和 `source_fetch_runs`。
2. 发布代码后由部署流程执行 `alembic upgrade head`。
3. 若需要回滚，执行 migration downgrade 删除本 change 新增三张表；当前没有生产数据迁移要求。
4. RSS Source 插件通过 `plugins/sources/rss-source/plugin.yaml` 随代码分发，不需要 runtime 安装步骤。

## Open Questions

- 正式 Registry 落地时，manifest YAML parser 和 schema validation 应采用哪个受控依赖？
- SourceBinding 的 API 管理端、配置表单和审计日志是否与 scheduler loop 同一个 change 交付，还是拆成独立 change？
- PostgreSQL 环境下 RawEvent 去重冲突是否需要改为数据库原生 upsert？
