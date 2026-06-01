## Context

issue #221 的目标不是“先给 source 抓取结果找个表塞进去”，而是先把 Source Plugin 输出进入平台后的第一层事实层收住。相关真源已经给出几条硬边界：

- `docs/design/06-source-plugin-design.md` 要求 source 输出采用 `Source Plugin -> RawEvent -> Normalizer -> Event` 双层结构，且平台负责 `RawEvent` 入库与 dedupe。
- `docs/design/11-crawler-source-plugin-boundary.md` 要求插件不负责 `RawEvent`、`SourceBinding`、Event Bus 或生命周期。
- `docs/design/04-database-and-persistence-design.md` 要求结构化字段优先、JSONB 只补充扩展和原始载荷，不把所有数据都塞进 JSONB。
- `packages/core/AGENTS.md`、`engineering-quality-gate.md` 和 `core-and-plugin-architecture-gate.md` 要求持久化真源留在 `packages/core`，并通过 repository / service seam 暴露给 scheduler 或 API。
- `source-binding-scheduler-run-persistence-v1` 已把 `binding_id` / `run_id` 固定成 scheduler 侧稳定关联位点，本 change 必须复用这些字段名。

PR #250 的 reviewer 真空点集中在五处：dedupe 作用域、跨 binding/run duplicate 归属、并发 duplicate upsert/重试、payload 边界、目标 DB 验证口径。本设计直接围绕这五处收口。

## Goals / Non-Goals

**Goals**

- 定义 `raw_events` canonical 主表与 `raw_event_captures` append-only ownership 表的职责边界。
- 定义 dedupe 作用域、dedupe material、canonical row 选择和 duplicate capture 语义。
- 定义后续实现必须复用的 `binding_id` / `run_id` ownership 链路。
- 定义并发 upsert、唯一约束冲突和数据库重试时的事务语义。
- 定义 `raw_payload` 的允许内容、禁止内容、大小上限和截断/脱敏语义。
- 定义 PostgreSQL 作为目标数据库的验证要求。

**Non-Goals**

- 不定义 Event 标准化字段、Event 状态机或 Event Bus publish 语义。
- 不定义前端 DTO、公开 API route、WebSocket 或 Dashboard 查询。
- 不定义完整网页快照、附件存储、对象存储或全文检索。
- 不把 source 插件 DTO 直接命名成 RawEvent DTO，也不让插件自己算最终 dedupe 结果。

## Decisions

### 1. RawEvent V1 采用两层持久化：canonical `raw_events` + append-only `raw_event_captures`

后续实现建议采用以下目录蓝图：

```text
packages/core/src/quantagent/core/
  db/
    models/
      raw_event.py
      raw_event_capture.py
    repositories/
      raw_event_repository.py
      raw_event_capture_repository.py
  raw_events/
    models.py
    service.py
    README.md

packages/core/tests/
  test_raw_event_service.py
  test_raw_event_repository.py
  test_raw_event_capture_repository.py
```

职责：

- `raw_events`：保存 dedupe 后的 canonical source 原始内容行。
- `raw_event_captures`：保存每次 binding/run 命中该 canonical 内容的 append-only ownership 记录。
- `raw_events/service.py`：编排 dedupe key 计算、canonical upsert、ownership capture 写入和重试策略。
- `db/repositories/*.py`：只承接 ORM 查询、唯一键冲突处理和事务内写入，不承载业务规则。
- `README.md`：说明 canonical row、capture row、payload 边界和不要把 Event / API / plugin 逻辑塞进这里。

原因：

- 同一 source 内容可以在多个 binding 或多个 run 中重复出现。只保留 canonical row 会丢失 ownership；只保留 capture row 又无法提供统一 dedupe 真源。
- `raw_event_captures` 作为 append-only ownership ledger，可以稳定回答“哪个 binding / 哪次 run 捕获了同一条 canonical RawEvent”。

备选方案：

- 只保留 `raw_events` 一张表，并在 duplicate 时更新 `duplicate_count`。放弃原因是无法回答跨 binding/run 归属，也无法给 #217 / #226 / future replay 提供稳定 ownership 链路。

### 2. dedupe 作用域固定为 `source_plugin_id` 内的 canonical 内容身份，不按 binding 或 run 切分

V1 dedupe scope：

```text
source_plugin_id
  + canonical_dedupe_key
  = unique canonical RawEvent identity
```

规则：

- V1 dedupe 只在同一个 `source_plugin_id` 内生效，不跨插件类型共享 canonical row。
- 同一条 source 内容即使被多个 `binding_id` 或 `run_id` 捕获，也应复用同一个 canonical `raw_event_id`。
- `binding_id` / `run_id` 只进入 ownership capture，不进入 canonical 唯一键。

原因：

- 不同 binding 可能只是同一个 source 插件的不同消费配置；若把 binding 放进 canonical dedupe scope，会把同一 source 内容重复持久化多次。
- 不同插件即使碰巧抓到同一 URL，也可能存在不同解析、不同供应商限制或不同 payload 结构；跨插件 dedupe 会过度合并。

### 3. canonical dedupe key 固定采用三级优先级，插件只能提供受控 hint，不能绕过平台规则

V1 dedupe material 与优先级：

1. `source_plugin_id + external_id`
2. `source_plugin_id + canonical_url + content_hash`
3. `source_plugin_id + provider_dedupe_hint`

约束：

- `external_id` 命中时，后续层级不参与 canonical identity 选择。
- 若没有 `external_id`，平台必须使用规范化后的 `canonical_url` 与稳定 `content_hash`。
- `provider_dedupe_hint` 只允许作为第三层回退值，并且必须是 JSON-safe、可审计、无 secret 的受控字段。
- 插件不得直接提交最终 `dedupe_key` 来绕过平台规则；平台必须自己计算 canonical key。

原因：

- 这与 `docs/design/06-source-plugin-design.md` 中的 dedupe 方向一致，但补齐了可执行优先级。
- reviewer 提到的 dedupe scope 真空，本质是没有把 canonical identity 和 ownership identity 分开。

### 4. duplicate ownership 采用“canonical row 复用 + 每次 capture 独立留痕”，不把 duplicate 视为无记录事件

核心模型草案：

```text
RawEvent
  raw_event_id
  source_plugin_id
  dedupe_scope
  canonical_dedupe_key
  dedupe_strategy
  external_id
  canonical_url
  content_hash
  title
  content
  author
  published_at
  first_captured_at
  last_captured_at
  raw_payload
  metadata
  first_binding_id
  first_run_id
  duplicate_capture_count

RawEventCapture
  capture_id
  raw_event_id
  binding_id
  run_id
  source_plugin_id
  capture_dedupe_key
  duplicate_of_raw_event_id
  capture_status
  captured_at
  request_id
  metadata
```

ownership 语义：

- 当 service 首次命中某个 canonical identity 时，创建 `RawEvent` 和首条 `RawEventCapture`。
- 当后续 binding 或 run 命中同一 canonical identity 时，不新增第二条 canonical `RawEvent`，但必须新增一条新的 `RawEventCapture`。
- `duplicate_capture_count` 只是 canonical summary，不替代 `RawEventCapture` append-only ownership history。
- 同一 `run_id` 的重复数据库重试不得创建两条语义相同的 capture；不同 `run_id` 命中同一内容则必须保留新的 capture。

原因：

- 这直接收住“跨 binding/run duplicate 归属”真空：canonical 去重与 ownership 留痕可以同时成立。

### 5. 并发 duplicate upsert 与重试采用数据库唯一键 + 幂等 capture key，不依赖应用层先查后写

V1 并发语义：

- `raw_events` 必须有 canonical 唯一约束：`(source_plugin_id, canonical_dedupe_key)`。
- `raw_event_captures` 必须有 run-scoped 幂等唯一约束，至少覆盖“同一 `run_id` 下同一 canonical identity 不能重复 capture”。
- service 必须使用单事务或受控重试语义完成：
  1. 计算 canonical key。
  2. 尝试插入 canonical row。
  3. 若命中唯一约束冲突，则重新读取已存在 canonical row。
  4. 为当前 binding/run 写入 capture row。

重试约束：

- 同一个数据库事务在 canonical upsert 冲突后允许重试读取，但不得因为应用层 race condition 生成两条 canonical row。
- 调度重试若生成新的 `run_id`，允许新增新的 capture row，并继续指向同一 canonical row。
- 同一 `run_id` 的幂等重试必须命中 capture 唯一键，返回同一 ownership 语义，而不是把 duplicate 重新累计成新 capture。

原因：

- reviewer 提到的“并发 duplicate upsert/重试”不是单纯测试问题，而是 schema 与 service contract 问题。V1 必须把它固定到数据库唯一键和受控事务里。

### 6. `raw_payload` 是受控、脱敏、有限大小的 provider-native 上下文，不是黑盒大对象

V1 payload 边界：

- `raw_payload` 只保存 provider-native、JSON-safe、对重放标准化和排障必要的字段。
- `raw_payload` 禁止保存：
  - secret、token、cookie、auth header、signed URL query
  - 完整 HTTP request / response header dump
  - 完整网页 HTML、二进制附件、截图或未裁剪的大对象
  - 插件运行时内部对象、DB session、ORM model 或 service 引用
- `title`、`content`、`author`、`published_at`、`canonical_url` 等高价值字段必须结构化，不允许只藏在 `raw_payload`。

V1 大小口径：

- `raw_payload` 序列化后的目标上限固定为 128 KiB。
- 超过上限时，平台必须先裁剪到 allowlisted 子集；若仍超过上限，平台必须拒绝写入并返回结构化错误，而不是静默写入超大 JSON。
- 若发生裁剪，canonical row 或 capture metadata 必须留有 `payload_truncated=true` 之类的审计标记。

原因：

- `docs/design/04-database-and-persistence-design.md` 已明确“大型内容和完整网页快照暂缓”；V1 必须把这句话变成可执行边界。

### 7. 目标数据库验证口径以 PostgreSQL 为准，SQLite 只能作为补充 harness

V1 后续实现验证要求：

- 必须在 PostgreSQL 上验证 migration、唯一约束、JSON/JSONB 列、canonical upsert 和 capture 幂等写入。
- SQLite 可以保留为快速单测补充，但不能作为本 change 的唯一数据库验收口径。
- 至少需要覆盖：
  - canonical 唯一约束真的阻止并发 duplicate 插入
  - capture 唯一约束真的阻止同一 `run_id` 下重复 capture
  - PostgreSQL 事务下的“冲突后重读 canonical row”语义可成立

原因：

- `docs/design/01-tech-stack-and-project-structure.md` 和 `docs/design/04-database-and-persistence-design.md` 已把 PostgreSQL 作为项目数据库真源。
- PR #250 暴露出“SQLite 通过但 PostgreSQL 语义未验证”的风险，这一口径必须在 OpenSpec 里提前固定。

## Data Flow

### 正常写入

```text
SourceItemDraft
  -> RawEventService.persist_source_item(...)
  -> calculate canonical_dedupe_key
  -> upsert/read canonical RawEvent
  -> append RawEventCapture(binding_id, run_id)
  -> return canonical ref + capture ref + duplicate status
```

### 跨 binding duplicate

```text
binding A / run 1  -> canonical RawEvent R1 + capture C1
binding B / run 9  -> reuse RawEvent R1 + append capture C2
```

### 同一 run 的 DB 重试

```text
run 9 insert capture C2
  -> transient error / retry
  -> same run 9 same canonical key
  -> hit capture idempotency key
  -> return existing ownership instead of creating C3
```

## Failure Paths

- `binding_id` 或 `run_id` 缺失，且当前入口声称来自 scheduler capture：service 返回结构化失败，不允许写 orphan ownership。
- `binding_id` / `run_id` 与 `source_plugin_id` 归属不一致：service 返回结构化失败，不允许跨插件串绑。
- `external_id`、`canonical_url`、`content_hash` 和 `provider_dedupe_hint` 都不足以形成 canonical key：service 返回结构化失败，不允许无 identity 裸写入。
- `raw_payload` 超过 128 KiB 且无法裁剪到 allowlist：service 返回结构化失败，并保留脱敏错误摘要。
- PostgreSQL 唯一约束冲突后的重读失败：service 允许受控重试；若仍失败，返回结构化 duplicate-upsert error。

## Risks / Trade-offs

- [Risk] append-only `raw_event_captures` 会增加写入量。  
  Mitigation：capture row 只保存 ownership 和最小 metadata，不重复复制整份 `raw_payload`。

- [Risk] 128 KiB payload 上限可能让某些 provider-native 字段被裁剪。  
  Mitigation：高价值字段结构化落表；超大原始对象留给 future blob/storage change。

- [Risk] dedupe 只在 `source_plugin_id` 内生效，无法跨插件自动合并同一 URL。  
  Mitigation：这是刻意选择，避免不同插件解析语义被过度合并；跨插件归并应由 future Event/analysis 层处理。

- [Risk] 相邻实现 issue 继续把 duplicate 语义写回 canonical summary。  
  Mitigation：spec 明确 `duplicate_capture_count` 只是摘要，ownership 真源永远是 `raw_event_captures`。

## Migration / Validation Plan

本 PR 为 OpenSpec-only，不执行 migration。后续实现 PR 应按以下顺序推进：

1. 确认 `source-binding-scheduler-run-persistence-v1` 的 `binding_id` / `run_id` 命名已作为上游真源接受。
2. 在 `packages/core` 增加 canonical ORM、capture ORM、repository 和 service seam。
3. 在 PostgreSQL 上创建 `raw_events`、`raw_event_captures` 及其唯一键与索引。
4. 覆盖并发 duplicate upsert、跨 binding duplicate ownership、同 run 幂等重试和 payload 上限测试。
5. 只有在 PostgreSQL 验证通过后，才允许把 #217 scheduler loop 或 #250 后续实现接到该 seam。

## Open Questions

- `provider_dedupe_hint` 是否需要在实现前定义成统一字段名，还是允许先作为 `metadata` 中的受控保留键。
- `raw_event_captures.metadata` 是否需要首版就携带 item position / batch index，还是留给实现 PR 按 source plugin 需要最小扩展。
