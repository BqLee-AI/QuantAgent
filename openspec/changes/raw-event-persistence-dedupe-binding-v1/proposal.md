## 为什么现在做

issue #221 已经明确 `RawEvent` 是 Source Plugin 输出进入平台后的第一层持久化真源，但当前仓库仍缺少一份可审查的 OpenSpec 来回答几个会直接阻塞后续实现的问题：

- dedupe 到底按 `plugin`、`binding` 还是 `run` 作用域计算。
- 同一条 source 内容被多个 binding 或多个 run 捕获时，归属如何保留。
- 并发写入、数据库重试或重复投递时，如何避免 canonical row 冲突和 ownership 丢失。
- `raw_payload` 到底保存什么、不保存什么，以及大小边界在哪里。
- 后续实现是否必须按 PostgreSQL 真正验证，而不是只用 SQLite 假通过。

PR #250 已经暴露出这些真空：如果只定义一个 canonical RawEvent 并在重复时简单累加计数，后续就无法稳定回答“这条重复内容来自哪个 binding/run”，也无法把 dedupe、scheduler ownership 和未来 Event 标准化拆成可验证的边界。

## 当前缺口

- `docs/design/06-source-plugin-design.md` 和 `docs/design/11-crawler-source-plugin-boundary.md` 只收住了“平台负责 RawEvent 入库、去重和 SourceBinding 归属”的方向，没有落成可实现的表层与 service 契约。
- `source-binding-scheduler-run-persistence-v1` 已把 `binding_id` / `run_id` 收成稳定关联位点，但 #221 还没有定义 RawEvent 应如何复用这些位点。
- 现有相邻 change 没有给出 `raw_payload` 的受控边界、并发 duplicate upsert 语义或目标数据库验证口径。

## 本轮目标

- 定义 RawEvent V1 的 canonical 持久化模型、binding/run ownership 记录模型和 core service / repository 分层。
- 固定 dedupe 作用域与优先级，明确何时视为“同一条 source 原始内容”。
- 固定跨 binding / run duplicate 的 ownership 语义，避免 canonical 去重吞掉归属链路。
- 固定并发 duplicate upsert、数据库唯一键冲突和重试的处理语义。
- 固定 `raw_payload` 的脱敏、字段边界、大小边界和未来大对象非目标。
- 固定后续实现 PR 的 PostgreSQL 验证口径。

## 非目标

- 不实现 Event 标准化、Event Bus outbox、worker 消费、replay、DLQ 或前端查询页。
- 不实现完整网页快照、二进制附件、对象存储或 Playwright crawler。
- 不让插件、scheduler app 或 API router 直接写 ORM session。
- 不定义公开 API DTO；本轮只定义 core / persistence 真源。

## 影响范围

- `packages/core`：后续实现 RawEvent ORM、repository、service 和 README。
- `source-binding-scheduler-run-persistence-v1`：继续作为 `binding_id` / `run_id` 的上游真源，本 change 只能复用不能重命名。
- `plugin-io-dto-v1` / source 插件：继续只产出 `SourceItemDraft`，不拥有 RawEvent persistence 语义。

## 风险边界

- dedupe 如果按 binding 作用域计算，会让同一 source 内容在多 binding 复用时无法共享 canonical identity。
- dedupe 如果只保留 canonical row 而不保留 append-only ownership，就会丢失 run / binding 审计链。
- `raw_payload` 如果没有上限和脱敏边界，会同时引入 PostgreSQL 行膨胀、敏感信息泄露和迁移困难。
- 如果实现只在 SQLite 上验证，无法证明 PostgreSQL 唯一约束、JSONB、并发 upsert 和事务语义真的成立。
