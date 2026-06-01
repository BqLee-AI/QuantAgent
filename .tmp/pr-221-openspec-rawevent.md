## 关联

- refs #221
- 补齐 issue #221 缺失的 RawEvent OpenSpec-only PR

## 为什么现在做

issue #221 已经把 RawEvent 定位为 `Source Plugin -> RawEvent -> Event` 中间层的持久化真源，但当前仓库还没有一份 active change 明确回答 reviewer 已经指出的几个关键真空：

- dedupe 作用域到底按 plugin、binding 还是 run 计算
- 跨 binding / run duplicate 的归属如何保留
- 并发 duplicate upsert / 数据库重试如何避免 canonical row 或 ownership 丢失
- `raw_payload` 的可存边界和大小上限是什么
- 后续实现到底以什么数据库验证口径为准

本 PR 只补这份 OpenSpec 真源，不进入任何实现代码。

## 改动摘要

- 新增 active change `raw-event-persistence-dedupe-binding-v1`
- 在 `proposal.md` 收住 why now、问题边界、非目标和 PostgreSQL 验证口径
- 在 `design.md` 明确：
  - canonical `raw_events` + append-only `raw_event_captures` 双层模型
  - dedupe scope 固定为 `source_plugin_id` 内，而不是按 binding/run 切分
  - duplicate ownership 用 capture ledger 留痕，不再只靠 canonical row 的 duplicate summary
  - 并发 duplicate upsert / 同 run 幂等重试的数据库唯一键与事务语义
  - `raw_payload` 的脱敏、128 KiB 上限和拒绝/裁剪规则
- 在 `specs/raw-event-persistence-v1/spec.md` 定义可验证 requirement / scenario
- 在 `tasks.md` 明确后续实现和 #250 对齐要求

## 与 PR #250 的对齐要求

PR #250 后续如继续推进实现，应先对齐本 change，再继续改代码：

- 不再把 duplicate 语义只压成 canonical row + `duplicate_count`
- 需要把 canonical 内容与 ownership 留痕拆成 `raw_events` + `raw_event_captures`
- dedupe scope 固定为 `source_plugin_id` 内，不把 `binding_id` / `run_id` 放进 canonical identity
- 同一 canonical RawEvent 被多个 binding / run 命中时，要追加 ownership capture，而不是直接吞掉归属
- 数据库验证必须以 PostgreSQL 为准，SQLite 只能作为补充 harness

## 验证

- `openspec validate raw-event-persistence-dedupe-binding-v1 --type change --strict --json`
  - 结果：通过

## 非目标 / 残余风险

- 本 PR 不实现 migration、ORM、repository、service、scheduler loop、Event 标准化或 API route
- `provider_dedupe_hint` 的统一字段名仍留在后续实现前确认
- `raw_event_captures.metadata` 是否首版携带 item position / batch index 仍留在实现 PR 最小化决定

## Review Notes

- 重点看 canonical row 与 ownership ledger 双层模型是否足够收住 reviewer 提到的归属真空
- 重点看 dedupe scope、并发 upsert、payload 边界和 PostgreSQL 验证口径是否清晰到足以指导 #250 后续实现
